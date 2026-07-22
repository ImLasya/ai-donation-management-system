import logging
import asyncio
import json
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from database import get_db, SessionLocal
from routes.auth_routes import get_current_user
import models
from config import settings
from services.matching_service import MatchingService
from services.email_service import EmailService

# Configure logger
logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/donations", tags=["Donations Workflow"])

def rematch_demand_background(demand_id: int):
    db = SessionLocal()
    try:
        # Run expiration checks before re-matching (Safeguard 1)
        MatchingService.expire_waiting_donations(db)
        # Trigger rematching (Safeguard 1)
        MatchingService.run_rematching_for_demand(db, demand_id)
    except Exception as e:
        logger.error(f"Background re-matching task failed for demand {demand_id}: {e}")
    finally:
        db.close()

def run_matching_background(donation_id: int, user_id: int):
    db = SessionLocal()
    try:
        donation = db.query(models.Donation).filter(models.Donation.id == donation_id).first()
        if donation:
            MatchingService.run_matching(db, donation)
            # Re-fetch/query for active match count (Safeguard 2)
            active_matches = db.query(models.DonationMatch).filter(
                models.DonationMatch.donation_id == donation.id,
                models.DonationMatch.status.in_(["ACTIVE", "NOTIFIED"]),
                models.DonationMatch.final_score >= settings.MATCH_MIN_SCORE
            ).count()

            if active_matches == 0:
                donation.status = "WAITING_FOR_MATCH"
                db.add(donation)
                
                # Add status history for transition
                history_wait = models.DonationStatusHistory(
                    donation_id=donation.id,
                    old_status="ITEMS_SUBMITTED",
                    new_status="WAITING_FOR_MATCH",
                    changed_by_user_id=user_id,
                    note="No immediate matches found. Donation is waiting for compatible NGO demands."
                )
                db.add(history_wait)
                db.commit()
    except Exception as e:
        logger.error(f"Background matching task failed for donation {donation_id}: {e}")
    finally:
        db.close()

# ----------------- PYDANTIC SCHEMAS -----------------

class DonationItemCreate(BaseModel):
    item_name: str
    category: str
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")
    condition: str
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence must be between 0 and 1")
    source: str  # "AI" or "MANUAL"
    notes: Optional[str] = None
    is_confirmed: Optional[bool] = Field(False, description="Manual confirmation for items that need review")


class DonationCreate(BaseModel):
    items: List[DonationItemCreate]

class NGORequestCreate(BaseModel):
    ngo_id: int

class PickupScheduleCreate(BaseModel):
    pickup_date: date
    time_slot: str
    pickup_address: str
    contact_phone: str
    notes: Optional[str] = None

# Packaging record schema
class PackagingRecordCreate(BaseModel):
    package_count: int = Field(1, gt=0)
    packaging_notes: Optional[str] = None
    completed_items: Optional[List[str]] = None

# Demand registry schemas
class NGODemandItemCreate(BaseModel):
    item_name: str
    category: str
    quantity_needed: int = Field(..., gt=0)
    minimum_condition: Optional[str] = None
    acceptable_conditions: Optional[List[str]] = None

class NGODemandCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str  # "LOW", "MEDIUM", "HIGH", "URGENT"
    needed_by_date: Optional[date] = None
    needed_by: Optional[date] = None  # alternate field name from frontend
    city: Optional[str] = None       # optional: backend uses NGO profile city if absent
    status: Optional[str] = "OPEN"
    items: List[NGODemandItemCreate]

# ----------------- API ENDPOINTS -----------------

# 1. Create Donation (Submit Items)
@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_donation(
    payload: DonationCreate,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.DONOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only donors can submit donation items."
        )

    if not payload.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit an empty list of items."
        )

    # Validate items through DonationEligibilityService before persisting
    from services.donation_eligibility_service import DonationEligibilityService

    for item in payload.items:
        eligibility = DonationEligibilityService.classify_detection(item.item_name)
        if eligibility == "NON_DONATABLE":
            reason = DonationEligibilityService.get_rejection_reason(item.item_name) or "Item is not eligible for donation."
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rejection: '{item.item_name}' was rejected: {reason}"
            )
        if eligibility == "REVIEW_REQUIRED":
            if not item.is_confirmed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Confirmation required: '{item.item_name}' requires manual review and confirmation before it can be submitted."
                )

    try:
        # Create donation in ITEMS_SUBMITTED status
        donation = models.Donation(
            donor_id=current_user.id,
            status="ITEMS_SUBMITTED"
        )
        db.add(donation)
        db.flush()  # Generate donation.id

        # Save donation items
        for item in payload.items:
            db_item = models.DonationItem(
                donation_id=donation.id,
                item_name=item.item_name,
                category=item.category,
                quantity=item.quantity,
                condition=item.condition,
                confidence_score=item.confidence_score,
                source=item.source,
                notes=item.notes
            )
            db.add(db_item)

        # Create status history record
        history = models.DonationStatusHistory(
            donation_id=donation.id,
            old_status="DRAFT",
            new_status="ITEMS_SUBMITTED",
            changed_by_user_id=current_user.id,
            note="Donation items submitted and matching initialized."
        )
        db.add(history)
        db.commit()

        # Run semantic matching asynchronously in background
        background_tasks.add_task(run_matching_background, donation.id, current_user.id)

        return {"donation_id": donation.id, "status": donation.status}

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating donation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit donation items."
        )

# 2. Create Request to selected NGO
@router.post("/{donation_id}/requests", response_model=dict)
async def send_ngo_request(
    donation_id: int,
    payload: NGORequestCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.DONOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only donors can send requests to NGOs."
        )

    # Run expiration checks before donor selects an NGO match (Safeguard 1)
    MatchingService.expire_waiting_donations(db)

    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation record not found.")

    if donation.status == "EXPIRED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This donation has expired and cannot be requested.")

    if donation.donor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this donation record.")

    # Verify NGO exists and fetch tenant context
    ngo_user = db.query(models.User).filter(
        models.User.id == payload.ngo_id,
        models.User.role == models.UserRole.NGO
    ).first()
    if not ngo_user or not ngo_user.ngo_profile:
        raise HTTPException(status_code=400, detail="Selected NGO profile does not exist.")

    # Validate that a DonationMatch exists for this donation and this NGO profile
    match_rec = db.query(models.DonationMatch).filter(
        models.DonationMatch.donation_id == donation_id,
        models.DonationMatch.ngo_id == ngo_user.ngo_profile.id
    ).first()
    if not match_rec:
        MatchingService.run_matching(db, donation)
        match_rec = db.query(models.DonationMatch).filter(
            models.DonationMatch.donation_id == donation_id,
            models.DonationMatch.ngo_id == ngo_user.ngo_profile.id
        ).first()

    if not match_rec:
        raise HTTPException(status_code=400, detail="No matching demand record exists for this NGO.")

    # Validate that the NGO demand is still OPEN
    demand = db.query(models.NGODemand).filter(models.NGODemand.id == match_rec.demand_id).first()
    if not demand or demand.status != "OPEN":
        raise HTTPException(status_code=400, detail="The matching NGO demand is no longer open.")

    # Constraint 7: Check if there is already an active pending request for this donation
    active_request = db.query(models.DonationRequest).filter(
        models.DonationRequest.donation_id == donation_id,
        models.DonationRequest.status == "PENDING"
    ).first()
    if active_request:
        raise HTTPException(status_code=400, detail="An active pending request already exists for this donation.")

    try:
        old_status = donation.status
        donation.status = "PENDING_NGO_RESPONSE"
        donation.ngo_id = payload.ngo_id

        # Mark selected match as SELECTED
        match_rec.status = "SELECTED"
        db.add(match_rec)

        # Create donation request
        req = models.DonationRequest(
            donation_id=donation_id,
            donor_id=current_user.id,
            ngo_id=payload.ngo_id,
            status="PENDING"
        )
        db.add(req)

        # Log history
        history = models.DonationStatusHistory(
            donation_id=donation_id,
            old_status=old_status,
            new_status="PENDING_NGO_RESPONSE",
            changed_by_user_id=current_user.id,
            note=f"Request sent to NGO {ngo_user.ngo_profile.organization_name}."
        )
        db.add(history)

        # Create notification for NGO user (linked to their user_id)
        donor_name = current_user.donor_profile.full_name if current_user.donor_profile else "A Donor"
        notification = models.Notification(
            user_id=payload.ngo_id,
            title="New Donation Request Received",
            message=f"You have received a new donation request from {donor_name}.",
            type="REQUEST",
            related_request_id=donation_id
        )
        db.add(notification)
        db.commit()

        return {"message": "Request sent successfully", "request_id": req.id}

    except Exception as e:
        db.rollback()
        logger.error(f"Error sending request: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit NGO request.")

# 3. NGO Accepts Request
@router.post("/requests/{request_id}/accept", response_model=dict)
async def accept_donation_request(
    request_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.NGO:
        raise HTTPException(status_code=403, detail="Only NGOs can accept donation requests.")

    # Lock request for updates
    req = db.query(models.DonationRequest).filter(models.DonationRequest.id == request_id).with_for_update().first()
    if not req:
        raise HTTPException(status_code=404, detail="Donation request not found.")

    # Enforce multi-tenant constraint: only the target NGO tenant can act on the request
    if req.ngo_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied. This request belongs to another NGO tenant.")

    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Cannot accept request in status '{req.status}'.")

    donation = db.query(models.Donation).filter(models.Donation.id == req.donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Associated donation record not found.")

    try:
        req.status = "ACCEPTED"
        old_status = donation.status
        donation.status = "NGO_ACCEPTED"

        # Concurrency guard: check duplicate history
        last_history = db.query(models.DonationStatusHistory).filter(
            models.DonationStatusHistory.donation_id == donation.id
        ).order_by(models.DonationStatusHistory.created_at.desc()).first()

        if not last_history or last_history.new_status != "NGO_ACCEPTED":
            history = models.DonationStatusHistory(
                donation_id=donation.id,
                old_status=old_status,
                new_status="NGO_ACCEPTED",
                changed_by_user_id=current_user.id,
                note="Request accepted by NGO. Packaging unlocked."
            )
            db.add(history)

        # Notify Donor
        donor_user = db.query(models.User).filter(models.User.id == req.donor_id).first()
        ngo_name = current_user.ngo_profile.organization_name if current_user.ngo_profile else "NGO"
        items_summary = ", ".join([f"{it.item_name} (x{it.quantity})" for it in donation.items])
        
        if donor_user and donor_user.inapp_notifications_enabled:
            notification = models.Notification(
                user_id=req.donor_id,
                title="Donation Request Accepted!",
                message=f"Your donation containing {items_summary} has been accepted by {ngo_name}. You can now prepare items for pickup.",
                type="ACCEPT",
                related_request_id=donation.id
            )
            db.add(notification)
            
        db.commit()

        # Asynchronously send email notification after commit
        if donor_user and donor_user.email_notifications_enabled:
            def send_email_task():
                items_li_html = "".join([f"<li>{it.item_name} (x{it.quantity})</li>" for it in donation.items])
                replacements = {
                    "donor_name": donor_user.donor_profile.full_name if donor_user.donor_profile else "Donor",
                    "ngo_name": ngo_name,
                    "items_list": items_li_html,
                    "action_url": f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/donor/packaging"
                }
                html_body = EmailService.load_template("donation_accepted.html", replacements)
                text_fallback = (
                    f"Your donation request has been accepted by {ngo_name}! "
                    f"Please log in and proceed to the packaging checklist for items: {items_summary}."
                )
                EmailService.send_html_email(
                    to_email=donor_user.email,
                    subject="Your Donation Has Been Accepted - Donate",
                    html_body=html_body,
                    text_fallback=text_fallback
                )
            background_tasks.add_task(send_email_task)

        return {"message": "Donation request accepted."}

    except Exception as e:
        db.rollback()
        logger.error(f"Error accepting request: {e}")
        raise HTTPException(status_code=500, detail="Failed to accept request.")

# 4. NGO Rejects Request
@router.post("/requests/{request_id}/reject", response_model=dict)
async def reject_donation_request(
    request_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.NGO:
        raise HTTPException(status_code=403, detail="Only NGOs can reject donation requests.")

    # Lock request for updates
    req = db.query(models.DonationRequest).filter(models.DonationRequest.id == request_id).with_for_update().first()
    if not req:
        raise HTTPException(status_code=404, detail="Donation request not found.")

    # Enforce multi-tenant constraint
    if req.ngo_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied. This request belongs to another NGO tenant.")

    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Cannot reject request in status '{req.status}'.")

    donation = db.query(models.Donation).filter(models.Donation.id == req.donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Associated donation record not found.")

    try:
        req.status = "REJECTED"
        old_status = donation.status
        ngo_name = current_user.ngo_profile.organization_name if current_user.ngo_profile else "NGO"

        # Check other active matches (Safeguard 2 / Intelligent Rejection Fallback)
        active_matches = db.query(models.DonationMatch).filter(
            models.DonationMatch.donation_id == donation.id,
            models.DonationMatch.ngo_id != current_user.ngo_profile.id, # other than this NGO
            models.DonationMatch.status.in_(["ACTIVE", "NOTIFIED"]),
            models.DonationMatch.final_score >= settings.MATCH_MIN_SCORE
        ).count()

        if active_matches > 0:
            target_status = "ITEMS_SUBMITTED"
            note = f"Request declined by {ngo_name}. Status reset to ITEMS_SUBMITTED because {active_matches} other matches are available."
        else:
            target_status = "WAITING_FOR_MATCH"
            note = f"Request declined by {ngo_name}. Status reset to WAITING_FOR_MATCH as no other active matches are available."

        donation.status = target_status
        donation.ngo_id = None

        # Concurrency guard: check duplicate history
        last_history = db.query(models.DonationStatusHistory).filter(
            models.DonationStatusHistory.donation_id == donation.id
        ).order_by(models.DonationStatusHistory.created_at.desc()).first()

        if not last_history or last_history.new_status != target_status:
            history = models.DonationStatusHistory(
                donation_id=donation.id,
                old_status=old_status,
                new_status=target_status,
                changed_by_user_id=current_user.id,
                note=note
            )
            db.add(history)

        # Notify Donor
        donor_user = db.query(models.User).filter(models.User.id == req.donor_id).first()
        items_summary = ", ".join([f"{it.item_name} (x{it.quantity})" for it in donation.items])
        
        if donor_user and donor_user.inapp_notifications_enabled:
            notification = models.Notification(
                user_id=req.donor_id,
                title="Donation Request Declined",
                message=f"{ngo_name} could not accept your donation containing {items_summary}. Please select another matched NGO.",
                type="REJECT",
                related_request_id=donation.id
            )
            db.add(notification)
            
        db.commit()

        # Asynchronously send email notification after commit
        if donor_user and donor_user.email_notifications_enabled:
            def send_email_task():
                items_li_html = "".join([f"<li>{it.item_name} (x{it.quantity})</li>" for it in donation.items])
                replacements = {
                    "donor_name": donor_user.donor_profile.full_name if donor_user.donor_profile else "Donor",
                    "ngo_name": ngo_name,
                    "items_list": items_li_html,
                    "action_url": f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/donor/matches"
                }
                html_body = EmailService.load_template("donation_rejected.html", replacements)
                text_fallback = (
                    f"Your donation request containing {items_summary} was declined by {ngo_name}. "
                    f"We have returned it to matching so you can select another NGO."
                )
                EmailService.send_html_email(
                    to_email=donor_user.email,
                    subject="Donation Request Update - Donate",
                    html_body=html_body,
                    text_fallback=text_fallback
                )
            background_tasks.add_task(send_email_task)

        return {"message": "Donation request rejected."}

    except Exception as e:
        db.rollback()
        logger.error(f"Error rejecting request: {e}")
        raise HTTPException(status_code=500, detail="Failed to reject request.")

# 5. Donor optionally transitions to PACKAGING_IN_PROGRESS
@router.post("/{donation_id}/start-packaging", response_model=dict)
async def start_packaging(
    donation_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.DONOR:
        raise HTTPException(status_code=403, detail="Only donors can manage packaging.")

    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found.")

    if donation.donor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied. You do not own this donation.")

    # Guard: must be accepted by NGO
    if donation.status != "NGO_ACCEPTED":
        raise HTTPException(status_code=400, detail="Cannot start packaging before NGO accept.")

    try:
        old_status = donation.status
        donation.status = "PACKAGING_IN_PROGRESS"
        
        history = models.DonationStatusHistory(
            donation_id=donation.id,
            old_status=old_status,
            new_status="PACKAGING_IN_PROGRESS",
            changed_by_user_id=current_user.id,
            note="Donor has started packaging items."
        )
        db.add(history)
        db.commit()
        return {"message": "Packaging is now in progress."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# 6. Complete Packaging (Save packaging record + transition to READY_FOR_PICKUP)
@router.post("/{donation_id}/package", response_model=dict)
async def complete_packaging(
    donation_id: int,
    payload: PackagingRecordCreate,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.DONOR:
        raise HTTPException(status_code=403, detail="Only donors can complete packaging.")

    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found.")

    if donation.donor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Guard: Packaging is only allowed when status is accepted or packaging in progress
    if donation.status not in ["NGO_ACCEPTED", "PACKAGING_IN_PROGRESS"]:
        raise HTTPException(
            status_code=400,
            detail="Packaging is only allowed after NGO accepts request."
        )

    try:
        import json
        completed_items_str = json.dumps(payload.completed_items) if payload.completed_items is not None else None

        # Create or update packaging record
        pkg_rec = db.query(models.PackagingRecord).filter(models.PackagingRecord.donation_id == donation_id).first()
        if not pkg_rec:
            pkg_rec = models.PackagingRecord(
                donation_id=donation_id,
                packaging_status="COMPLETED",
                package_count=payload.package_count,
                packaging_notes=payload.packaging_notes,
                completed_items=completed_items_str,
                completed_at=func.now()
            )
            db.add(pkg_rec)
        else:
            pkg_rec.package_count = payload.package_count
            pkg_rec.packaging_notes = payload.packaging_notes
            pkg_rec.completed_items = completed_items_str
            pkg_rec.completed_at = func.now()

        old_status = donation.status
        donation.status = "READY_FOR_PICKUP"

        # Concurrency guard: check duplicate history
        last_history = db.query(models.DonationStatusHistory).filter(
            models.DonationStatusHistory.donation_id == donation.id
        ).order_by(models.DonationStatusHistory.created_at.desc()).first()
        
        if not last_history or last_history.new_status != "READY_FOR_PICKUP":
            history = models.DonationStatusHistory(
                donation_id=donation.id,
                old_status=old_status,
                new_status="READY_FOR_PICKUP",
                changed_by_user_id=current_user.id,
                note=f"Items packaging complete. Total package count: {payload.package_count}."
            )
            db.add(history)

        # Notify NGO
        ngo_user = db.query(models.User).filter(models.User.id == donation.ngo_id).first()
        donor_name = current_user.donor_profile.full_name if current_user.donor_profile else "Donor"
        
        if ngo_user and ngo_user.inapp_notifications_enabled:
            notification = models.Notification(
                user_id=donation.ngo_id,
                title="Donation Ready for Pickup",
                message=f"{donor_name} completed packaging. Total packages: {payload.package_count}.",
                type="PICKUP",
                related_request_id=donation.id
            )
            db.add(notification)
        
        db.commit()

        # Asynchronously send email notification after transaction commit
        if ngo_user and ngo_user.email_notifications_enabled:
            def send_email_task():
                replacements = {
                    "donor_name": donor_name,
                    "donation_id": donation.id,
                    "package_count": payload.package_count,
                    "packaging_notes": payload.packaging_notes or "None",
                    "action_url": f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/ngo/incoming"
                }
                html_body = EmailService.load_template("packaging_complete.html", replacements)
                text_fallback = (
                    f"Donation Ready for Pickup: Donor {donor_name} completed packaging "
                    f"for donation DON-{donation.id}. Total packages: {payload.package_count}."
                )
                EmailService.send_html_email(
                    to_email=ngo_user.email,
                    subject="Donation Ready for Pickup - Donate",
                    html_body=html_body,
                    text_fallback=text_fallback
                )
            background_tasks.add_task(send_email_task)

        return {"message": "Donation marked as ready for pickup."}

    except Exception as e:
        db.rollback()
        logger.error(f"Error completing packaging: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete packaging.")

# 6b. Get Packaging Checklist
@router.get("/{donation_id}/packaging-checklist", response_model=dict)
async def get_packaging_checklist(
    donation_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found.")

    if current_user.role == models.UserRole.DONOR and donation.donor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if current_user.role == models.UserRole.NGO and donation.ngo_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Get checklist tips
    from services.packaging_service import PackagingService
    categories = [it.category for it in donation.items if it.category]
    checklist_tips = PackagingService.get_tips_for_categories(categories)

    # Fetch previously saved completed items
    pkg_rec = db.query(models.PackagingRecord).filter(models.PackagingRecord.donation_id == donation_id).first()
    completed_items = []
    package_count = 1
    packaging_notes = ""
    if pkg_rec:
        import json
        try:
            completed_items = json.loads(pkg_rec.completed_items) if pkg_rec.completed_items else []
        except:
            completed_items = []
        package_count = pkg_rec.package_count
        packaging_notes = pkg_rec.packaging_notes or ""

    return {
        "checklist": checklist_tips,
        "completedItems": completed_items,
        "packageCount": package_count,
        "packagingNotes": packaging_notes
    }

# 7. Schedule Pickup (READY_FOR_PICKUP -> PICKUP_SCHEDULED)
@router.post("/{donation_id}/pickup", response_model=dict)
async def schedule_pickup(
    donation_id: int,
    payload: PickupScheduleCreate,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.DONOR:
        raise HTTPException(status_code=403, detail="Only donors can schedule pickups.")

    # Validate pickup date (prevent past dates)
    if payload.pickup_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot schedule pickup in the past.")

    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found.")

    if donation.donor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Guard: only allow scheduling when status is READY_FOR_PICKUP
    if donation.status != "READY_FOR_PICKUP":
        raise HTTPException(
            status_code=400,
            detail="Pickups can only be scheduled once packaging is completed."
        )

    # Constraint: One pickup schedule per donation
    existing_pickup = db.query(models.PickupSchedule).filter(models.PickupSchedule.donation_id == donation_id).first()
    if existing_pickup:
        raise HTTPException(status_code=400, detail="A pickup schedule already exists.")

    try:
        pickup = models.PickupSchedule(
            donation_id=donation_id,
            pickup_date=payload.pickup_date,
            time_slot=payload.time_slot,
            pickup_address=payload.pickup_address,
            contact_phone=payload.contact_phone,
            notes=payload.notes,
            reminder_status="PENDING"
        )
        db.add(pickup)

        old_status = donation.status
        donation.status = "PICKUP_SCHEDULED"

        # Concurrency guard: check duplicate history
        last_history = db.query(models.DonationStatusHistory).filter(
            models.DonationStatusHistory.donation_id == donation.id
        ).order_by(models.DonationStatusHistory.created_at.desc()).first()

        if not last_history or last_history.new_status != "PICKUP_SCHEDULED":
            history = models.DonationStatusHistory(
                donation_id=donation.id,
                old_status=old_status,
                new_status="PICKUP_SCHEDULED",
                changed_by_user_id=current_user.id,
                note=f"Pickup scheduled for {payload.pickup_date} at {payload.time_slot}."
            )
            db.add(history)

        # Notify NGO
        ngo_user = db.query(models.User).filter(models.User.id == donation.ngo_id).first()
        ngo_org = db.query(models.NGOProfile).filter(models.NGOProfile.user_id == donation.ngo_id).first()
        org_name = ngo_org.organization_name if ngo_org else "NGO"

        if ngo_user and ngo_user.inapp_notifications_enabled:
            notification_ngo = models.Notification(
                user_id=donation.ngo_id,
                title="Pickup Scheduled",
                message=f"Pickup has been scheduled for {payload.pickup_date} at {payload.time_slot}.",
                type="PICKUP",
                related_request_id=donation.id
            )
            db.add(notification_ngo)

        # Notify Donor
        if current_user.inapp_notifications_enabled:
            notification_donor = models.Notification(
                user_id=current_user.id,
                title="Pickup Confirmed",
                message=f"Your pickup with {org_name} is scheduled successfully.",
                type="PICKUP",
                related_request_id=donation.id
            )
            db.add(notification_donor)
            
        db.commit()

        # Asynchronously send email notification after commit
        def send_emails_task():
            replacements = {
                "ngo_name": org_name,
                "donation_id": donation.id,
                "pickup_date": payload.pickup_date.strftime("%Y-%m-%d"),
                "time_slot": payload.time_slot,
                "address": payload.pickup_address,
                "phone": payload.contact_phone,
                "notes_li": f"<li><strong>Special Notes:</strong> {payload.notes}</li>" if payload.notes else "",
                "action_url": f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/donor/track/{donation.id}"
            }
            html_body = EmailService.load_template("pickup_scheduled.html", replacements)
            text_fallback = (
                f"Donation Pickup Scheduled: Donation DON-{donation.id} scheduled with {org_name} "
                f"for {payload.pickup_date} during slot {payload.time_slot}."
            )

            # Send to Donor
            if current_user.email_notifications_enabled:
                EmailService.send_html_email(
                    to_email=current_user.email,
                    subject="Pickup Scheduled - Donate",
                    html_body=html_body,
                    text_fallback=text_fallback
                )

            # Send to NGO
            if ngo_user and ngo_user.email_notifications_enabled:
                replacements["action_url"] = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/ngo/incoming"
                html_body_ngo = EmailService.load_template("pickup_scheduled.html", replacements)
                EmailService.send_html_email(
                    to_email=ngo_user.email,
                    subject="Pickup Scheduled - Donate",
                    html_body=html_body_ngo,
                    text_fallback=text_fallback
                )

            # Send to Volunteer (if assigned)
            if pickup and getattr(pickup, "volunteer_email", None):
                replacements["action_url"] = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/login"
                html_body_vol = EmailService.load_template("pickup_scheduled.html", replacements)
                EmailService.send_html_email(
                    to_email=pickup.volunteer_email,
                    subject="Donation Pickup Scheduled - Donate",
                    html_body=html_body_vol,
                    text_fallback=text_fallback
                )

        background_tasks.add_task(send_emails_task)

        return {"message": "Pickup scheduled successfully."}

    except Exception as e:
        db.rollback()
        logger.error(f"Error scheduling pickup: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule pickup.")

# 8. List user-specific donations
@router.get("/list", response_model=list)
async def list_donations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Run expiration checks on donations list load (Safeguard 1)
    MatchingService.expire_waiting_donations(db)

    if current_user.role == models.UserRole.DONOR:
        donations = db.query(models.Donation).filter(models.Donation.donor_id == current_user.id).order_by(models.Donation.created_at.desc()).all()
    elif current_user.role == models.UserRole.NGO:
        donations = db.query(models.Donation).filter(models.Donation.ngo_id == current_user.id).order_by(models.Donation.created_at.desc()).all()
    else:
        donations = db.query(models.Donation).order_by(models.Donation.created_at.desc()).all()

    res = []
    for d in donations:
        ngo_name = "—"
        if d.ngo_id:
            ngo_profile = db.query(models.NGOProfile).filter(models.NGOProfile.user_id == d.ngo_id).first()
            if ngo_profile:
                ngo_name = ngo_profile.organization_name
        
        items_summary = [{"id": it.id, "label": it.item_name, "category": it.category, "quantity": it.quantity, "condition": it.condition} for it in d.items]
        
        # Calculate active matches count for metadata (Safeguard 2)
        active_match_count = db.query(models.DonationMatch).filter(
            models.DonationMatch.donation_id == d.id,
            models.DonationMatch.status.in_(["ACTIVE", "NOTIFIED"]),
            models.DonationMatch.final_score >= settings.MATCH_MIN_SCORE
        ).count()
        has_available_matches = active_match_count > 0

        # Self-heal status transition if active matches exist (Safeguard 3)
        if d.status == "WAITING_FOR_MATCH" and has_available_matches:
            d.status = "ITEMS_SUBMITTED"
            db.add(d)
            history = models.DonationStatusHistory(
                donation_id=d.id,
                old_status="WAITING_FOR_MATCH",
                new_status="ITEMS_SUBMITTED",
                changed_by_user_id=d.donor_id,
                note="Status transitioned to ITEMS_SUBMITTED because active matches exist."
            )
            db.add(history)
            db.flush()

        # Fetch donor profile and pickup details if requested by NGO or admin
        donor_name = "—"
        donor_phone = ""
        pickup_details = None
        
        donor_profile = db.query(models.DonorProfile).filter(models.DonorProfile.user_id == d.donor_id).first()
        if donor_profile:
            donor_name = donor_profile.full_name
            donor_phone = donor_profile.phone or ""

        pickup = d.pickup_schedule
        if pickup:
            pickup_details = {
                "date": pickup.pickup_date.strftime("%Y-%m-%d"),
                "timeSlot": pickup.time_slot,
                "address": pickup.pickup_address,
                "phone": pickup.contact_phone,
                "notes": pickup.notes,
                "volunteerName": pickup.volunteer_name,
                "volunteerPhone": pickup.volunteer_phone,
                "volunteerEmail": pickup.volunteer_email
            }

        res.append({
            "id": str(d.id),
            "status": d.status,
            "date": d.created_at.strftime("%Y-%m-%d") if d.created_at else "—",
            "ngoName": ngo_name,
            "donorName": donor_name,
            "donorPhone": donor_phone,
            "pickup": pickup_details,
            "items": items_summary,
            "beneficiaries": sum(it.quantity for it in d.items) * 3,
            "active_match_count": active_match_count,
            "has_available_matches": has_available_matches
        })
    db.commit()
    return res

# 9. NGO Incoming requests
@router.get("/requests/incoming", response_model=list)
async def list_incoming_requests(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.NGO:
        raise HTTPException(status_code=403, detail="Only NGOs can fetch incoming requests.")

    requests = db.query(models.DonationRequest).filter(
        models.DonationRequest.ngo_id == current_user.id,
        models.DonationRequest.status == "PENDING"
    ).order_by(models.DonationRequest.created_at.desc()).all()

    res = []
    for r in requests:
        donation = r.donation
        if not donation:
            continue
        
        donor_profile = db.query(models.DonorProfile).filter(models.DonorProfile.user_id == r.donor_id).first()
        donor_name = donor_profile.full_name if donor_profile else "Anonymous Donor"
        donor_city = donor_profile.city if donor_profile else "Unknown City"

        items_list = [{
            "id": it.id,
            "label": it.item_name,
            "category": it.category,
            "quantity": it.quantity,
            "condition": it.condition,
            "confidence_score": it.confidence_score,
            "source": it.source
        } for it in donation.items]

        res.append({
            "id": r.id,
            "donation_id": donation.id,
            "status": donation.status,
            "date": r.created_at.strftime("%Y-%m-%d") if r.created_at else "—",
            "donorName": donor_name,
            "donorCity": donor_city,
            "items": items_list
        })
    return res

# 10. Fetch Donation details / Journey status (Responsive Labels + Volunteer assignment validation)
@router.get("/{donation_id}/track", response_model=dict)
async def track_donation(
    donation_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Run expiration checks on detail/track load (Safeguard 1)
    MatchingService.expire_waiting_donations(db)

    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found.")

    if current_user.id not in [donation.donor_id, donation.ngo_id] and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You do not own this donation.")

    # Calculate active matches count for metadata (Safeguard 2)
    active_matches = db.query(models.DonationMatch).filter(
        models.DonationMatch.donation_id == donation_id,
        models.DonationMatch.status.in_(["ACTIVE", "NOTIFIED"]),
        models.DonationMatch.final_score >= settings.MATCH_MIN_SCORE
    ).count()
    has_available_matches = active_matches > 0

    # Self-heal status transition if active matches exist (Safeguard 3)
    if donation.status == "WAITING_FOR_MATCH" and has_available_matches:
        donation.status = "ITEMS_SUBMITTED"
        db.add(donation)
        history = models.DonationStatusHistory(
            donation_id=donation.id,
            old_status="WAITING_FOR_MATCH",
            new_status="ITEMS_SUBMITTED",
            changed_by_user_id=donation.donor_id,
            note="Status transitioned to ITEMS_SUBMITTED because active matches exist."
        )
        db.add(history)
        db.commit()

    # Short human-readable labels mapping dynamically (Safeguard 4)
    if donation.status == "ITEMS_SUBMITTED":
        items_lbl = "New Match Available" if has_available_matches else "Items Submitted"
    else:
        items_lbl = "Items Submitted"

    STATUS_LABELS_MAP = {
        "DRAFT": "Submitted",
        "ITEMS_SUBMITTED": items_lbl,
        "WAITING_FOR_MATCH": "Waiting for NGO Match",
        "EXPIRED": "Expired",
        "PENDING_NGO_RESPONSE": "Awaiting NGO Response",
        "NGO_ACCEPTED": "Accepted by NGO",
        "PACKAGING_IN_PROGRESS": "Packaging In Progress",
        "READY_FOR_PICKUP": "Ready for Pickup",
        "PICKUP_SCHEDULED": "Pickup Scheduled",
        "COLLECTED": "Collected (In Transit)",
        "PICKUP_IN_PROGRESS": "Collected (In Transit)",
        "DELIVERED": "Delivered to NGO",
        "COMPLETED": "Delivered to NGO",
        "ACKNOWLEDGED": "Acknowledged (Thank You)",
        "NGO_REJECTED": "Declined"
    }

    history_logs = db.query(models.DonationStatusHistory).filter(
        models.DonationStatusHistory.donation_id == donation_id
    ).order_by(models.DonationStatusHistory.created_at.asc()).all()

    events = []
    # Deduplicate status transitions for a cleaner responsive timeline
    rendered_statuses = set()
    for h in history_logs:
        lbl = STATUS_LABELS_MAP.get(h.new_status, h.new_status)
        if lbl in rendered_statuses:
            continue
        rendered_statuses.add(lbl)
        events.append({
            "status": lbl,
            "description": h.note or f"Status changed to {lbl}",
            "timestamp": h.created_at.strftime("%Y-%m-%d %H:%M") if h.created_at else "—",
            "done": True
        })

    # Add future steps
    workflow_steps = ["ITEMS_SUBMITTED", "PENDING_NGO_RESPONSE", "NGO_ACCEPTED", "PACKAGING_IN_PROGRESS", "READY_FOR_PICKUP", "PICKUP_SCHEDULED", "COLLECTED", "DELIVERED", "ACKNOWLEDGED"]
    current_idx = workflow_steps.index(donation.status) if donation.status in workflow_steps else 0

    for i in range(current_idx + 1, len(workflow_steps)):
        step_status = workflow_steps[i]
        lbl = STATUS_LABELS_MAP.get(step_status, step_status)
        if lbl not in rendered_statuses:
            events.append({
                "status": lbl,
                "description": f"Awaiting {lbl.lower()}",
                "timestamp": "—",
                "done": False
            })

    ngo_org = db.query(models.NGOProfile).filter(models.NGOProfile.user_id == donation.ngo_id).first()
    ngo_name = ngo_org.organization_name if ngo_org else "NGO Partner"

    items_list = [{
        "id": it.id,
        "label": it.item_name,
        "category": it.category,
        "quantity": it.quantity,
        "condition": it.condition
    } for it in donation.items]

    pickup = donation.pickup_schedule
    pickup_details = {
        "date": pickup.pickup_date.strftime("%Y-%m-%d") if pickup else None,
        "timeSlot": pickup.time_slot if pickup else None,
        "address": pickup.pickup_address if pickup else None,
        "phone": pickup.contact_phone if pickup else None,
        "notes": pickup.notes if pickup else None
    } if pickup else None

    # Check if a real volunteer assignment exists (Requirement 10)
    volunteer = None
    if pickup and (pickup.volunteer_name or pickup.volunteer_phone):
        volunteer = {
            "name": pickup.volunteer_name,
            "phone": pickup.volunteer_phone,
            "email": pickup.volunteer_email
        }

    return {
        "id": str(donation.id),
        "status": donation.status,
        "date": donation.created_at.strftime("%Y-%m-%d") if donation.created_at else "—",
        "ngoName": ngo_name,
        "items": items_list,
        "pickup": pickup_details,
        "volunteer": volunteer,
        "events": events,
        "beneficiaries": sum(it.quantity for it in donation.items) * 3,
        "active_match_count": active_matches,
        "has_available_matches": has_available_matches
    }

# 11. Notifications list (JWT secured)
@router.get("/notifications/list", response_model=list)
async def list_notifications(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notifications = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id
    ).order_by(models.Notification.created_at.desc()).all()

    return [{
        "id": n.id,
        "title": n.title,
        "message": n.message,
        "type": n.type,
        "isRead": n.is_read,
        "relatedRequestId": n.related_request_id,
        "createdAt": n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else "—"
    } for n in notifications]

# 11b. Server-Sent Events notifications stream
@router.get("/notifications/stream")
async def stream_notifications(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    async def event_generator():
        # Retrieve starting state
        last_seen_id = 0
        
        # Seed last_seen_id with the max notification ID currently present to only stream new ones
        initial_max = db.query(models.func.max(models.Notification.id)).filter(
            models.Notification.user_id == current_user.id
        ).scalar()
        if initial_max:
            last_seen_id = initial_max

        while True:
            # Check for new unread/any notifications
            new_notifications = db.query(models.Notification).filter(
                models.Notification.user_id == current_user.id,
                models.Notification.id > last_seen_id
            ).order_by(models.Notification.id.asc()).all()

            for n in new_notifications:
                last_seen_id = max(last_seen_id, n.id)
                data = {
                    "id": n.id,
                    "title": n.title,
                    "message": n.message,
                    "type": n.type,
                    "isRead": n.is_read,
                    "relatedRequestId": n.related_request_id,
                    "createdAt": n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else "—"
                }
                yield f"data: {json.dumps(data)}\n\n"
            
            await asyncio.sleep(4)  # Poll database periodically inside stream

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# 12. Mark notification as read
@router.post("/notifications/read/{notification_id}", response_model=dict)
async def mark_notification_read(
    notification_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    n = db.query(models.Notification).filter(
        models.Notification.id == notification_id
    ).with_for_update().first()

    if not n:
        raise HTTPException(status_code=404, detail="Notification not found.")

    if n.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    try:
        n.is_read = True
        db.commit()
        return {"message": "Notification marked as read."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update notification.")

# 13. Dynamic Matching Engine comparing Donation Items against registered OPEN NGO demands
@router.get("/matches", response_model=list)
async def get_ngo_matches(
    donation_id: Optional[int] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Retrieve donation record to run matching
    donation = None
    if donation_id:
        donation = db.query(models.Donation).filter(models.Donation.id == donation_id).first()
    else:
        # Fallback to donor's latest ITEMS_SUBMITTED donation
        donation = db.query(models.Donation).filter(
            models.Donation.donor_id == current_user.id,
            models.Donation.status == "ITEMS_SUBMITTED"
        ).order_by(models.Donation.created_at.desc()).first()

    if not donation:
        # Return empty matched lists if no active donation items are present
        return []

    # Enforce ownership boundary check
    if donation.donor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this donation record.")

    # Recalculate matches dynamically to capture newly created demands
    MatchingService.run_matching(db, donation)

    # Self-heal status transition if active matches exist (Safeguard 3)
    active_matches_count = db.query(models.DonationMatch).filter(
        models.DonationMatch.donation_id == donation.id,
        models.DonationMatch.status.in_(["ACTIVE", "NOTIFIED"]),
        models.DonationMatch.final_score >= settings.MATCH_MIN_SCORE
    ).count()
    if donation.status == "WAITING_FOR_MATCH" and active_matches_count > 0:
        donation.status = "ITEMS_SUBMITTED"
        db.add(donation)
        history = models.DonationStatusHistory(
            donation_id=donation.id,
            old_status="WAITING_FOR_MATCH",
            new_status="ITEMS_SUBMITTED",
            changed_by_user_id=donation.donor_id,
            note="Status transitioned to ITEMS_SUBMITTED because active matches exist."
        )
        db.add(history)
        db.commit()
    
    persisted_matches = db.query(models.DonationMatch).filter(
        models.DonationMatch.donation_id == donation.id
    ).all()

    res = []
    seen = set()
    donor_profile = current_user.donor_profile
    for m in persisted_matches:
        # Deduplicate to prevent duplicate cards
        key = (m.ngo_id, m.demand_id)
        if key in seen:
            continue
        seen.add(key)

        ngo_profile = m.ngo
        if not ngo_profile:
            continue

        # Parse match explanation JSON
        try:
            explanation = json.loads(m.match_explanation)
        except Exception:
            explanation = {"matched_items": [], "reasons": []}

        urgency_lbl = "High Urgency" if m.demand.priority in ["URGENT", "HIGH"] else "Medium Urgency"
        items_needed_names = [it["demand_item"] for it in explanation.get("matched_items", [])]

        res.append({
            "match_id": m.id,
            "demand_id": m.demand_id,
            "demand_title": m.demand.title,
            "final_score": m.final_score,
            "item_match_score": m.item_match_score,
            "quantity_fit_score": m.quantity_fit_score,
            "geographic_score": m.geographic_score,
            "priority_score": m.priority_score,
            "matched_items": explanation.get("matched_items", []),
            "reasons": explanation.get("reasons", []),

            # Legacy compat fields
            "id": str(ngo_profile.user_id),
            "overallScore": int(m.final_score),
            "urgency": urgency_lbl,
            "demandExpiry": "in 5 days" if m.demand.priority == "URGENT" else "in 2 weeks",
            "itemsNeeded": items_needed_names,
            "ngo": {
                "id": ngo_profile.user_id,
                "name": ngo_profile.organization_name,
                "city": ngo_profile.city,
                "distanceKm": 1.2 if donor_profile and donor_profile.city.lower() == ngo_profile.city.lower() else 12.5,
                "verified": ngo_profile.verification_status == "APPROVED"
            },
            "breakdown": {
                "itemTypeMatch": int(m.item_match_score),
                "quantityFit": int(m.quantity_fit_score),
                "proximity": int(m.geographic_score),
                "ngoPriority": int(m.priority_score)
            }
        })

    # Sort matches descending by score
    res.sort(key=lambda x: x["final_score"], reverse=True)
    return res

# ----------------- NGO DEMANDS APIs -----------------

# Create Demand (NGO operational, tenant-scoped)
@router.post("/demands", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_ngo_demand(
    payload: NGODemandCreate,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.NGO:
        raise HTTPException(status_code=403, detail="Only NGOs can create demand registries.")

    ngo_profile = current_user.ngo_profile
    if not ngo_profile or not ngo_profile.tenant_id:
        raise HTTPException(status_code=400, detail="Authenticated user NGO profile/tenant is missing.")

    # Resolve needed_by_date — accept either field name
    resolved_date = payload.needed_by_date or payload.needed_by

    try:
        # Create demand record; city always comes from the authenticated NGO profile
        demand = models.NGODemand(
            tenant_id=ngo_profile.tenant_id,
            ngo_id=current_user.id,
            title=payload.title,
            description=payload.description,
            priority=payload.priority.upper(),
            status="OPEN",
            city=ngo_profile.city,
            needed_by_date=resolved_date
        )
        db.add(demand)
        db.flush()

        # Create demand items atomically
        for item in payload.items:
            # Flatten acceptable_conditions → minimum_condition for storage
            min_cond = item.minimum_condition
            if not min_cond and item.acceptable_conditions:
                min_cond = ",".join(item.acceptable_conditions)

            db_item = models.NGODemandItem(
                demand_id=demand.id,
                item_name=item.item_name,
                category=item.category,
                quantity_needed=item.quantity_needed,
                quantity_fulfilled=0,
                minimum_condition=min_cond
            )
            db.add(db_item)

        db.commit()
        
        # Trigger background re-matching task for open demand (Safeguards 1, 5, 6)
        if demand.status == "OPEN":
            background_tasks.add_task(rematch_demand_background, demand.id)

        return {"demand_id": demand.id, "title": demand.title, "status": demand.status}

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating NGO demand: {e}")
        raise HTTPException(status_code=500, detail="Failed to create demand record.")





# Fetch NGO Demands (scoped to authenticated NGO's tenant)
@router.get("/demands/my", response_model=list)
async def get_my_demands(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.NGO:
        raise HTTPException(status_code=403, detail="Access denied.")

    ngo_profile = current_user.ngo_profile
    if not ngo_profile or not ngo_profile.tenant_id:
        return []

    # Scope query by NGO tenant ID (Requirement 5: prevent cross-tenant reads)
    demands = db.query(models.NGODemand).filter(
        models.NGODemand.tenant_id == ngo_profile.tenant_id
    ).order_by(models.NGODemand.created_at.desc()).all()

    res = []
    for d in demands:
        items_data = [
            {
                "id": str(it.id),
                "item_name": it.item_name,
                "category": it.category,
                "quantity_needed": it.quantity_needed,
                "quantity_fulfilled": it.quantity_fulfilled,
                "minimum_condition": it.minimum_condition or "",
            }
            for it in d.items
        ]
        # Legacy single-item fields (used for progress bar & compact view)
        first_item = d.items[0] if d.items else None
        res.append({
            "id": str(d.id),
            "title": d.title,
            "description": d.description or "",
            "city": d.city or "",
            "priority": d.priority.capitalize(),
            "status": "Active" if d.status == "OPEN" else "Paused",
            "db_status": d.status,
            "expiryDate": d.needed_by_date.strftime("%Y-%m-%d") if d.needed_by_date else "—",
            "createdAt": d.created_at.strftime("%Y-%m-%d") if d.created_at else "—",
            # legacy compat fields
            "itemName": first_item.item_name if first_item else d.title,
            "category": first_item.category if first_item else "Other",
            "quantityRequired": first_item.quantity_needed if first_item else 0,
            "quantityFulfilled": first_item.quantity_fulfilled if first_item else 0,
            "items": items_data,
        })
    return res


# 11b. Assign/Update Volunteer (NGO only)
@router.post("/{donation_id}/assign-volunteer", response_model=dict)
async def assign_volunteer(
    donation_id: int,
    payload: dict,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found.")

    if current_user.role != models.UserRole.ADMIN and (current_user.role != models.UserRole.NGO or donation.ngo_id != current_user.id):
        raise HTTPException(status_code=403, detail="Only the matched NGO or admin can assign a volunteer.")

    pickup = donation.pickup_schedule
    if not pickup:
        raise HTTPException(status_code=400, detail="No pickup schedule exists yet. Donors must schedule it first.")

    v_name = payload.get("volunteer_name", "").strip()
    v_phone = payload.get("volunteer_phone", "").strip()
    v_email = payload.get("volunteer_email", "").strip()

    if not v_name or not v_phone or not v_email:
        raise HTTPException(status_code=400, detail="Volunteer name, phone, and email are required.")

    # Check if volunteer details actually changed (deduplication)
    details_changed = (
        pickup.volunteer_name != v_name or
        pickup.volunteer_phone != v_phone or
        pickup.volunteer_email != v_email
    )

    pickup.volunteer_name = v_name
    pickup.volunteer_phone = v_phone
    pickup.volunteer_email = v_email
    db.add(pickup)

    # Notify Donor in-app if details changed
    donor_user = db.query(models.User).filter(models.User.id == donation.donor_id).first()
    ngo_name = current_user.ngo_profile.organization_name if current_user.ngo_profile else "NGO Partner"

    if details_changed and donor_user and donor_user.inapp_notifications_enabled:
        notification = models.Notification(
            user_id=donation.donor_id,
            title="Courier Volunteer Assigned",
            message=f"{ngo_name} has assigned volunteer {v_name} (Phone: {v_phone}) to pick up your donation DON-{donation.id}.",
            type="PICKUP",
            related_request_id=donation.id
        )
        db.add(notification)

    db.commit()

    # Asynchronously send email notifications after commit if details changed
    if details_changed:
        ngo_user = db.query(models.User).filter(models.User.id == donation.ngo_id).first()
        
        def send_emails_task():
            replacements = {
                "ngo_name": ngo_name,
                "donation_id": str(donation.id),
                "volunteer_name": v_name,
                "volunteer_phone": v_phone,
                "pickup_date": pickup.pickup_date.strftime("%Y-%m-%d") if pickup.pickup_date else "—",
                "time_slot": pickup.time_slot,
                "action_url": f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/donor/track/{donation.id}"
            }
            html_body = EmailService.load_template("volunteer_assigned.html", replacements)
            text_fallback = (
                f"Hello,\n\nVolunteer {v_name} ({v_phone}) has been assigned by {ngo_name} to pick up your donation DON-{donation.id}.\n"
                f"Scheduled Date: {pickup.pickup_date}\nSlot: {pickup.time_slot}.\n\nTrack: http://localhost:8080/donor/track/{donation.id}"
            )
            
            # 1. Send to Donor
            if donor_user and donor_user.email_notifications_enabled:
                EmailService.send_html_email(donor_user.email, "Courier Volunteer Assigned - Donate", html_body, text_fallback)
            
            # 2. Send to NGO
            if ngo_user and ngo_user.email_notifications_enabled:
                replacements["action_url"] = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/ngo/incoming"
                html_body_ngo = EmailService.load_template("volunteer_assigned.html", replacements)
                EmailService.send_html_email(ngo_user.email, "Courier Volunteer Assigned - Donate", html_body_ngo, text_fallback)

            # 3. Send to Volunteer
            if v_email:
                replacements["action_url"] = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/login"
                html_body_vol = EmailService.load_template("volunteer_assigned.html", replacements)
                EmailService.send_html_email(v_email, "Courier Volunteer Assignment - Donate", html_body_vol, text_fallback)

        background_tasks.add_task(send_emails_task)

    return {"success": True, "message": f"Volunteer '{v_name}' assigned successfully."}


# 12. Transit Donation (PICKUP_SCHEDULED -> COLLECTED)
@router.post("/{donation_id}/transit", response_model=dict)
async def mark_in_transit(
    donation_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found.")

    # Authorization Check: only target NGO or Admin
    if current_user.role != models.UserRole.ADMIN and (current_user.role != models.UserRole.NGO or donation.ngo_id != current_user.id):
        raise HTTPException(status_code=403, detail="Only the matched NGO or admin can start collection transit.")

    if donation.status != "PICKUP_SCHEDULED":
        raise HTTPException(status_code=400, detail="Donation pickup is not scheduled yet.")

    try:
        old_status = donation.status
        donation.status = "COLLECTED"

        # Concurrency guard: check duplicate history
        last_history = db.query(models.DonationStatusHistory).filter(
            models.DonationStatusHistory.donation_id == donation.id
        ).order_by(models.DonationStatusHistory.created_at.desc()).first()

        if not last_history or last_history.new_status != "COLLECTED":
            history = models.DonationStatusHistory(
                donation_id=donation.id,
                old_status=old_status,
                new_status="COLLECTED",
                changed_by_user_id=current_user.id,
                note="Donation collected and in transit to NGO facility."
            )
            db.add(history)

        # Notify Donor
        donor_user = db.query(models.User).filter(models.User.id == donation.donor_id).first()
        ngo_name = current_user.ngo_profile.organization_name if current_user.role == models.UserRole.NGO and current_user.ngo_profile else "NGO Partner"

        if donor_user and donor_user.inapp_notifications_enabled:
            notification = models.Notification(
                user_id=donation.donor_id,
                title="Donation Collected",
                message=f"Your donation DON-{donation.id} has been collected by {ngo_name} and is in transit.",
                type="PICKUP",
                related_request_id=donation.id
            )
            db.add(notification)

        db.commit()

        # Asynchronously send email notifications after commit
        ngo_user = db.query(models.User).filter(models.User.id == donation.ngo_id).first()
        pickup = donation.pickup_schedule

        def send_emails_task():
            replacements = {
                "donor_name": donor_user.donor_profile.full_name if donor_user and donor_user.donor_profile else "Donor",
                "ngo_name": ngo_name,
                "donation_id": donation.id,
                "action_url": f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/donor/track/{donation.id}"
            }
            html_body = EmailService.load_template("donation_collected.html", replacements)
            text_fallback = (
                f"Donation Collected: Your donation DON-{donation.id} "
                f"has been collected by {ngo_name} and is currently in transit."
            )

            # 1. Send to Donor
            if donor_user and donor_user.email_notifications_enabled:
                EmailService.send_html_email(
                    to_email=donor_user.email,
                    subject="Donation Collected - Donate",
                    html_body=html_body,
                    text_fallback=text_fallback
                )

            # 2. Send to NGO
            if ngo_user and ngo_user.email_notifications_enabled:
                replacements["action_url"] = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/ngo/incoming"
                html_body_ngo = EmailService.load_template("donation_collected.html", replacements)
                EmailService.send_html_email(
                    to_email=ngo_user.email,
                    subject="Donation Collected - Donate",
                    html_body=html_body_ngo,
                    text_fallback=text_fallback
                )

            # 3. Send to Volunteer
            if pickup and getattr(pickup, "volunteer_email", None):
                replacements["action_url"] = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/login"
                html_body_vol = EmailService.load_template("donation_collected.html", replacements)
                EmailService.send_html_email(
                    to_email=pickup.volunteer_email,
                    subject="Upcoming Courier Pickup Transit - Donate",
                    html_body=html_body_vol,
                    text_fallback=text_fallback
                )

        background_tasks.add_task(send_emails_task)

        return {"message": "Donation marked as collected and in transit."}
    except Exception as e:
        db.rollback()
        logger.error(f"Error marking in transit: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark in transit.")

# 13. Complete Delivery (COLLECTED -> DELIVERED)
@router.post("/{donation_id}/complete", response_model=dict)
async def mark_delivered(
    donation_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found.")

    # Authorization Check: only target NGO or Admin
    if current_user.role != models.UserRole.ADMIN and (current_user.role != models.UserRole.NGO or donation.ngo_id != current_user.id):
        raise HTTPException(status_code=403, detail="Only the matched NGO or admin can mark donation as delivered.")

    if donation.status != "COLLECTED":
        raise HTTPException(status_code=400, detail="Donation has not been collected/in-transit yet.")

    try:
        old_status = donation.status
        donation.status = "DELIVERED"

        # Concurrency guard: check duplicate history
        last_history = db.query(models.DonationStatusHistory).filter(
            models.DonationStatusHistory.donation_id == donation.id
        ).order_by(models.DonationStatusHistory.created_at.desc()).first()

        if not last_history or last_history.new_status != "DELIVERED":
            history = models.DonationStatusHistory(
                donation_id=donation.id,
                old_status=old_status,
                new_status="DELIVERED",
                changed_by_user_id=current_user.id,
                note="Donation delivered successfully to NGO facility."
            )
            db.add(history)

        # Notify Donor
        donor_user = db.query(models.User).filter(models.User.id == donation.donor_id).first()
        ngo_name = current_user.ngo_profile.organization_name if current_user.role == models.UserRole.NGO and current_user.ngo_profile else "NGO Partner"

        if donor_user and donor_user.inapp_notifications_enabled:
            notification = models.Notification(
                user_id=donation.donor_id,
                title="Donation Delivered",
                message=f"Your donation DON-{donation.id} has been delivered to {ngo_name}.",
                type="PICKUP",
                related_request_id=donation.id
            )
            db.add(notification)

        db.commit()

        # Asynchronously send email notifications after commit
        ngo_user = db.query(models.User).filter(models.User.id == donation.ngo_id).first()

        def send_emails_task():
            items_li_html = "".join([f"<li>{it.item_name} (x{it.quantity})</li>" for it in donation.items])
            replacements = {
                "ngo_name": ngo_name,
                "donation_id": donation.id,
                "items_list": items_li_html,
                "action_url": f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/donor/track/{donation.id}"
            }
            html_body = EmailService.load_template("donation_delivered.html", replacements)
            text_fallback = (
                f"Donation Delivered: Your donation DON-{donation.id} "
                f"has been delivered to {ngo_name}."
            )

            # 1. Send to Donor
            if donor_user and donor_user.email_notifications_enabled:
                EmailService.send_html_email(
                    to_email=donor_user.email,
                    subject="Donation Safely Delivered - Donate",
                    html_body=html_body,
                    text_fallback=text_fallback
                )

            # 2. Send to NGO
            if ngo_user and ngo_user.email_notifications_enabled:
                replacements["action_url"] = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/ngo/incoming"
                html_body_ngo = EmailService.load_template("donation_delivered.html", replacements)
                EmailService.send_html_email(
                    to_email=ngo_user.email,
                    subject="Donation Safely Delivered - Donate",
                    html_body=html_body_ngo,
                    text_fallback=text_fallback
                )

        background_tasks.add_task(send_emails_task)

        return {"message": "Donation marked as delivered."}
    except Exception as e:
        db.rollback()
        logger.error(f"Error marking delivered: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark delivered.")

# 14. Acknowledge Receipt (DELIVERED -> ACKNOWLEDGED)
@router.post("/{donation_id}/acknowledge", response_model=dict)
async def acknowledge_receipt(
    donation_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found.")

    # Authorization Check: only target NGO can acknowledge
    if current_user.role != models.UserRole.NGO or donation.ngo_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the matched NGO can acknowledge receipt.")

    if donation.status != "DELIVERED":
        raise HTTPException(status_code=400, detail="Donation has not been delivered to your facility yet.")

    try:
        old_status = donation.status
        donation.status = "ACKNOWLEDGED"

        # Concurrency guard: check duplicate history
        last_history = db.query(models.DonationStatusHistory).filter(
            models.DonationStatusHistory.donation_id == donation.id
        ).order_by(models.DonationStatusHistory.created_at.desc()).first()

        if not last_history or last_history.new_status != "ACKNOWLEDGED":
            history = models.DonationStatusHistory(
                donation_id=donation.id,
                old_status=old_status,
                new_status="ACKNOWLEDGED",
                changed_by_user_id=current_user.id,
                note="NGO acknowledged receipt of all items."
            )
            db.add(history)

        # Notify Donor
        donor_user = db.query(models.User).filter(models.User.id == donation.donor_id).first()
        ngo_name = current_user.ngo_profile.organization_name if current_user.ngo_profile else "NGO Partner"

        if donor_user and donor_user.inapp_notifications_enabled:
            notification = models.Notification(
                user_id=donation.donor_id,
                title="Donation Acknowledged",
                message=f"Thank you! {ngo_name} has acknowledged receipt of donation DON-{donation.id}.",
                type="PICKUP",
                related_request_id=donation.id
            )
            db.add(notification)

        db.commit()

        # Asynchronously send email notifications after commit
        ngo_user = db.query(models.User).filter(models.User.id == donation.ngo_id).first()

        def send_emails_task():
            items_li_html = "".join([f"<li>{it.item_name} (x{it.quantity})</li>" for it in donation.items])
            replacements = {
                "donor_name": donor_user.donor_profile.full_name if donor_user and donor_user.donor_profile else "Donor",
                "ngo_name": ngo_name,
                "donation_id": donation.id,
                "items_list": items_li_html,
                "action_url": f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/donor/dashboard"
            }
            html_body = EmailService.load_template("donation_acknowledged.html", replacements)
            text_fallback = (
                f"Donation Acknowledged: Thank you! {ngo_name} "
                f"has acknowledged receipt of donation DON-{donation.id}."
            )

            # 1. Send to Donor
            if donor_user and donor_user.email_notifications_enabled:
                EmailService.send_html_email(
                    to_email=donor_user.email,
                    subject="Donation Receipt Acknowledged - Donate",
                    html_body=html_body,
                    text_fallback=text_fallback
                )

            # 2. Send to NGO
            if ngo_user and ngo_user.email_notifications_enabled:
                replacements["action_url"] = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/ngo/incoming"
                html_body_ngo = EmailService.load_template("donation_acknowledged.html", replacements)
                EmailService.send_html_email(
                    to_email=ngo_user.email,
                    subject="Donation Receipt Acknowledged - Donate",
                    html_body=html_body_ngo,
                    text_fallback=text_fallback
                )

        background_tasks.add_task(send_emails_task)

        return {"message": "Donation receipt acknowledged."}
    except Exception as e:
        db.rollback()
        logger.error(f"Error acknowledging receipt: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge receipt.")

# Debug: Test Email (POST /api/donations/debug/test-email)
@router.post("/debug/test-email", response_model=dict)
async def send_test_email(
    current_user: models.User = Depends(get_current_user),
):
    """
    Sends a real HTML test email to the currently logged-in user's email address.
    Use this endpoint to verify SMTP configuration is working correctly.
    """
    from datetime import datetime
    replacements = {
        "user_name": current_user.email,
        "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action_url": f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/login"
    }
    html_body = EmailService.load_template("test_email.html", replacements)
    if not html_body:
        # Fallback inline if template is missing
        html_body = f"""
        <!DOCTYPE html>
        <html><body style="font-family:sans-serif;padding:20px;">
        <h2 style="color:#0d9488;">✅ SMTP Test Successful</h2>
        <p>Hello <strong>{current_user.email}</strong>,</p>
        <p>This test email confirms your SMTP configuration is working correctly.</p>
        <p><small>Sent at: {replacements['test_time']}</small></p>
        </body></html>
        """

    text_fallback = (
        f"SMTP Test Email\n\n"
        f"Hello {current_user.email},\n\n"
        f"This test email confirms your SMTP configuration is working correctly.\n"
        f"Sent at: {replacements['test_time']}"
    )

    status = EmailService.send_html_email(
        to_email=current_user.email,
        subject="SMTP Configuration Test - Donate",
        html_body=html_body,
        text_fallback=text_fallback
    )

    return {
        "status": status,
        "recipient": current_user.email,
        "message": (
            "Test email sent successfully. Check your inbox." if status == "SENT"
            else "SMTP not configured. Email logged to console (DEVELOPMENT_LOG_ONLY)." if status == "DEVELOPMENT_LOG_ONLY"
            else "Email delivery failed. Check SMTP credentials and server logs."
        )
    }


# 15. Donor Dashboard Stats
@router.get("/donor/dashboard-stats", response_model=dict)
async def get_donor_dashboard_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.DONOR:
        raise HTTPException(status_code=403, detail="Access denied.")

    # 1. Counts
    total_donations_count = db.query(models.Donation).filter(models.Donation.donor_id == current_user.id).count()
    
    active_donations_count = db.query(models.Donation).filter(
        models.Donation.donor_id == current_user.id,
        models.Donation.status.in_([
            "ITEMS_SUBMITTED", "PENDING_NGO_RESPONSE", "NGO_ACCEPTED",
            "PACKAGING_IN_PROGRESS", "READY_FOR_PICKUP", "PICKUP_SCHEDULED", "COLLECTED", "DELIVERED",
            "PICKUP_IN_PROGRESS"
        ])
    ).count()

    completed_donations_count = db.query(models.Donation).filter(
        models.Donation.donor_id == current_user.id,
        models.Donation.status.in_(["ACKNOWLEDGED", "COMPLETED"])
    ).count()

    waiting_for_match_count = db.query(models.Donation).filter(
        models.Donation.donor_id == current_user.id,
        models.Donation.status == "WAITING_FOR_MATCH"
    ).count()

    # 2. Upcoming Pickups
    upcoming_pickups = []
    import datetime
    today = datetime.date.today()
    pickups = db.query(models.PickupSchedule).join(
        models.Donation, models.Donation.id == models.PickupSchedule.donation_id
    ).filter(
        models.Donation.donor_id == current_user.id,
        models.PickupSchedule.pickup_date >= today
    ).order_by(models.PickupSchedule.pickup_date.asc()).all()

    for p in pickups:
        donation = p.donation
        ngo_profile = db.query(models.NGOProfile).filter(models.NGOProfile.user_id == donation.ngo_id).first()
        ngo_name = ngo_profile.organization_name if ngo_profile else "NGO Partner"
        upcoming_pickups.append({
            "donationId": str(donation.id),
            "date": p.pickup_date.strftime("%Y-%m-%d"),
            "timeSlot": p.time_slot,
            "ngoName": ngo_name,
            "address": p.pickup_address,
            "phone": p.contact_phone
        })

    # 3. New matches available count
    donations = db.query(models.Donation).filter(
        models.Donation.donor_id == current_user.id,
        models.Donation.status.in_(["ITEMS_SUBMITTED", "WAITING_FOR_MATCH"])
    ).all()
    
    new_matches_available = 0
    for d in donations:
        has_matches = db.query(models.DonationMatch).filter(
            models.DonationMatch.donation_id == d.id,
            models.DonationMatch.status.in_(["ACTIVE", "NOTIFIED"]),
            models.DonationMatch.final_score >= settings.MATCH_MIN_SCORE
        ).count() > 0
        if has_matches:
            new_matches_available += 1

    # 4. Recent activity
    recent_activity = []
    activities = db.query(models.DonationStatusHistory).join(
        models.Donation, models.Donation.id == models.DonationStatusHistory.donation_id
    ).filter(
        models.Donation.donor_id == current_user.id
    ).order_by(models.DonationStatusHistory.created_at.desc()).limit(5).all()

    for a in activities:
        recent_activity.append({
            "donationId": str(a.donation_id),
            "oldStatus": a.old_status,
            "newStatus": a.new_status,
            "timestamp": a.created_at.strftime("%Y-%m-%d %H:%M"),
            "note": a.note
        })

    return {
        "totalDonations": total_donations_count,
        "activeDonations": active_donations_count,
        "completedDonations": completed_donations_count,
        "waitingForMatch": waiting_for_match_count,
        "newMatchesAvailable": new_matches_available,
        "upcomingPickups": upcoming_pickups,
        "recentActivity": recent_activity
    }


# Fetch NGO Dashboard statistics (scoped to authenticated NGO's tenant)
@router.get("/ngo/dashboard-stats", response_model=dict)
async def get_ngo_dashboard_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.NGO:
        raise HTTPException(status_code=403, detail="Access denied.")

    ngo_profile = current_user.ngo_profile
    if not ngo_profile or not ngo_profile.tenant_id:
        raise HTTPException(status_code=400, detail="NGO Profile/Tenant context not found.")

    # 1. Active Demands
    active_demands_count = db.query(models.NGODemand).filter(
        models.NGODemand.tenant_id == ngo_profile.tenant_id,
        models.NGODemand.status == "OPEN"
    ).count()

    # 2. High Priority Demands
    high_priority_count = db.query(models.NGODemand).filter(
        models.NGODemand.tenant_id == ngo_profile.tenant_id,
        models.NGODemand.status == "OPEN",
        models.NGODemand.priority.in_(["HIGH", "URGENT"])
    ).count()

    # 3. Incoming Donations (Pending requests to this NGO)
    incoming_donations_count = db.query(models.DonationRequest).filter(
        models.DonationRequest.ngo_id == current_user.id,
        models.DonationRequest.status == "PENDING"
    ).count()

    # 4. Beneficiaries (Sum of quantities of fulfilled items * 3, fallback to sum of needed items * 3)
    demands = db.query(models.NGODemand).filter(
        models.NGODemand.tenant_id == ngo_profile.tenant_id
    ).all()

    total_fulfilled_qty = 0
    total_needed_qty = 0
    for d in demands:
        for it in d.items:
            total_fulfilled_qty += it.quantity_fulfilled
            total_needed_qty += it.quantity_needed

    beneficiaries = (total_fulfilled_qty * 3) if total_fulfilled_qty > 0 else (total_needed_qty * 3)
    # Avoid showing 0 if there are active demands
    if beneficiaries == 0 and total_needed_qty > 0:
        beneficiaries = total_needed_qty * 3

    # 5. Demand vs Supply chart data (grouped by month of creation for the current year)
    months = ["Mar", "Apr", "May", "Jun", "Jul"]
    import datetime
    current_year = datetime.datetime.now().year
    
    chart_data = []
    # Fetch all demands created this year
    demands_this_year = db.query(models.NGODemand).filter(
        models.NGODemand.tenant_id == ngo_profile.tenant_id,
        func.extract('year', models.NGODemand.created_at) == current_year
    ).all()
    
    # Aggregate by month name
    monthly_stats = {}
    for d in demands_this_year:
        m_name = d.created_at.strftime("%b")
        if m_name not in monthly_stats:
            monthly_stats[m_name] = {"demand": 0, "supply": 0}
        for it in d.items:
            monthly_stats[m_name]["demand"] += it.quantity_needed
            monthly_stats[m_name]["supply"] += it.quantity_fulfilled

    # Fallback/seed default months to keep chart populated nicely
    for m in months:
        stats = monthly_stats.get(m, {"demand": 0, "supply": 0})
        # If there is no real data, seed 0 or a base value to show the month
        chart_data.append({"month": m, "demand": stats["demand"], "supply": stats["supply"]})

    # 6. Urgent Needs (demands priority critical/high and not satisfied)
    urgent_needs = []
    for d in demands:
        if d.status == "OPEN" and d.priority in ["HIGH", "URGENT"]:
            for it in d.items:
                if it.quantity_fulfilled < it.quantity_needed:
                    urgent_needs.append({
                        "id": str(it.id),
                        "itemName": it.item_name,
                        "quantityRequired": it.quantity_needed,
                        "quantityFulfilled": it.quantity_fulfilled,
                        "priority": d.priority.capitalize()
                    })

    # Sort/limit urgent needs
    urgent_needs = urgent_needs[:4]

    # 7. Recent Matched Donations (recent requests)
    recent_requests = db.query(models.DonationRequest).filter(
        models.DonationRequest.ngo_id == current_user.id
    ).order_by(models.DonationRequest.created_at.desc()).limit(3).all()

    recent_donations = []
    for req in recent_requests:
        donation = req.donation
        if donation:
            items_list = [{"id": str(it.id), "itemName": it.item_name, "quantity": it.quantity} for it in donation.items]
            recent_donations.append({
                "id": f"Donation #{donation.id}",
                "status": donation.status,
                "date": req.created_at.strftime("%Y-%m-%d") if req.created_at else "—",
                "items": items_list
            })

    # 8. Compatible Matches (active matches)
    matches = db.query(models.DonationMatch).filter(
        models.DonationMatch.ngo_id == ngo_profile.id,
        models.DonationMatch.status == "ACTIVE",
        models.DonationMatch.final_score >= settings.MATCH_MIN_SCORE
    ).all()
    
    compatible_matches_list = []
    for m in matches:
        donation = m.donation
        if donation:
            items_list = [{"id": str(it.id), "itemName": it.item_name, "quantity": it.quantity} for it in donation.items]
            donor_prof = db.query(models.DonorProfile).filter(models.DonorProfile.user_id == donation.donor_id).first()
            compatible_matches_list.append({
                "id": str(m.id),
                "donationId": str(donation.id),
                "donorName": donor_prof.full_name if donor_prof else "Anonymous Donor",
                "finalScore": int(m.final_score),
                "items": items_list,
                "date": donation.created_at.strftime("%Y-%m-%d") if donation.created_at else "—"
            })

    # 9. Accepted/Active Donations
    accepted = db.query(models.Donation).filter(
        models.Donation.ngo_id == current_user.id,
        models.Donation.status.in_([
            "NGO_ACCEPTED", "PACKAGING_IN_PROGRESS", "READY_FOR_PICKUP", "PICKUP_SCHEDULED", "COLLECTED", "DELIVERED", "PICKUP_IN_PROGRESS"
        ])
    ).all()
    
    accepted_donations_list = []
    for d in accepted:
        donor_prof = db.query(models.DonorProfile).filter(models.DonorProfile.user_id == d.donor_id).first()
        accepted_donations_list.append({
            "id": str(d.id),
            "status": d.status,
            "donorName": donor_prof.full_name if donor_prof else "Anonymous Donor",
            "date": d.created_at.strftime("%Y-%m-%d") if d.created_at else "—",
            "itemCount": sum(it.quantity for it in d.items)
        })

    # 10. Upcoming Pickups
    today = datetime.date.today()
    pickups = db.query(models.PickupSchedule).join(
        models.Donation, models.Donation.id == models.PickupSchedule.donation_id
    ).filter(
        models.Donation.ngo_id == current_user.id,
        models.PickupSchedule.pickup_date >= today
    ).order_by(models.PickupSchedule.pickup_date.asc()).all()
    
    upcoming_pickups_list = []
    for p in pickups:
        donor_prof = db.query(models.DonorProfile).filter(models.DonorProfile.user_id == p.donation.donor_id).first()
        upcoming_pickups_list.append({
            "donationId": str(p.donation_id),
            "date": p.pickup_date.strftime("%Y-%m-%d"),
            "timeSlot": p.time_slot,
            "address": p.pickup_address,
            "phone": p.contact_phone,
            "donorName": donor_prof.full_name if donor_prof else "Anonymous Donor"
        })

    # 11. Expiring Demands (OPEN and needed_by_date is close, e.g. next 7 days or past)
    expiring_demands = []
    exp_dem = db.query(models.NGODemand).filter(
        models.NGODemand.tenant_id == ngo_profile.tenant_id,
        models.NGODemand.status == "OPEN",
        models.NGODemand.needed_by_date.isnot(None)
    ).order_by(models.NGODemand.needed_by_date.asc()).limit(5).all()
    
    for d in exp_dem:
        expiring_demands.append({
            "id": str(d.id),
            "title": d.title,
            "expiryDate": d.needed_by_date.strftime("%Y-%m-%d")
        })

    # 12. Completed Donation History
    completed = db.query(models.Donation).filter(
        models.Donation.ngo_id == current_user.id,
        models.Donation.status.in_(["ACKNOWLEDGED", "COMPLETED"])
    ).order_by(models.Donation.updated_at.desc()).limit(10).all()
    
    completed_history_list = []
    for d in completed:
        donor_prof = db.query(models.DonorProfile).filter(models.DonorProfile.user_id == d.donor_id).first()
        completed_history_list.append({
            "id": str(d.id),
            "donorName": donor_prof.full_name if donor_prof else "Anonymous Donor",
            "date": d.created_at.strftime("%Y-%m-%d") if d.created_at else "—",
            "completedDate": d.updated_at.strftime("%Y-%m-%d") if d.updated_at else "—",
            "itemCount": sum(it.quantity for it in d.items)
        })

    # 13. Notifications
    notifs = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id
    ).order_by(models.Notification.created_at.desc()).limit(5).all()
    
    notifications_list = []
    for n in notifs:
        notifications_list.append({
            "id": str(n.id),
            "title": n.title,
            "message": n.message,
            "isRead": n.is_read,
            "date": n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else "—"
        })

    return {
        "activeDemands": active_demands_count,
        "highPriority": high_priority_count,
        "incomingDonations": incoming_donations_count,
        "beneficiaries": beneficiaries,
        "demandSupply": chart_data,
        "urgentNeeds": urgent_needs,
        "recentDonations": recent_donations,
        "compatibleMatches": compatible_matches_list,
        "acceptedDonations": accepted_donations_list,
        "upcomingPickups": upcoming_pickups_list,
        "expiringDemands": expiring_demands,
        "completedDonationHistory": completed_history_list,
        "notifications": notifications_list
    }


# Fetch single NGO Demand details (scoped to authenticated NGO's tenant)
@router.get("/demands/{demand_id}", response_model=dict)
async def get_demand_details(
    demand_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.NGO:
        raise HTTPException(status_code=403, detail="Access denied.")

    ngo_profile = current_user.ngo_profile
    if not ngo_profile or not ngo_profile.tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context not found.")

    demand = db.query(models.NGODemand).filter(
        models.NGODemand.id == demand_id,
        models.NGODemand.tenant_id == ngo_profile.tenant_id
    ).first()

    if not demand:
        raise HTTPException(status_code=404, detail="Demand registry not found.")

    items_data = [
        {
            "id": str(it.id),
            "item_name": it.item_name,
            "category": it.category,
            "quantity_needed": it.quantity_needed,
            "quantity_fulfilled": it.quantity_fulfilled,
            "minimum_condition": it.minimum_condition or "",
        }
        for it in demand.items
    ]

    return {
        "id": str(demand.id),
        "title": demand.title,
        "description": demand.description or "",
        "city": demand.city or "",
        "priority": demand.priority,
        "status": "Active" if demand.status == "OPEN" else "Paused",
        "db_status": demand.status,
        "expiryDate": demand.needed_by_date.strftime("%Y-%m-%d") if demand.needed_by_date else "",
        "items": items_data,
    }


# Update/Pause Demand (tenant scoped)
@router.put("/demands/{demand_id}", response_model=dict)
async def update_ngo_demand(
    demand_id: int,
    payload: dict,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.NGO:
        raise HTTPException(status_code=403, detail="Access denied.")

    ngo_profile = current_user.ngo_profile
    if not ngo_profile or not ngo_profile.tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context not found.")

    demand = db.query(models.NGODemand).filter(models.NGODemand.id == demand_id).with_for_update().first()
    if not demand:
        raise HTTPException(status_code=404, detail="Demand registry not found.")

    # Enforce multi-tenancy: NGO must own demand
    if demand.tenant_id != ngo_profile.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied. NGO owns a different tenant registry.")

    try:
        trigger_rematch = False

        if "status" in payload:
            new_status = "OPEN" if payload["status"] == "Active" else "CLOSED"
            # status transitions to OPEN
            if new_status == "OPEN" and demand.status != "OPEN":
                trigger_rematch = True
            demand.status = new_status
        if "priority" in payload:
            if demand.priority != payload["priority"]:
                trigger_rematch = True
            demand.priority = payload["priority"]
        if "description" in payload:
            demand.description = payload["description"]
        if "title" in payload:
            if demand.title != payload["title"]:
                trigger_rematch = True
            demand.title = payload["title"]
        if "needed_by_date" in payload:
            if str(demand.needed_by_date) != str(payload["needed_by_date"]):
                trigger_rematch = True
            demand.needed_by_date = payload["needed_by_date"]

        # Track audit history updated_at timestamp
        demand.updated_at = func.now()

        # Handle items updates, deleting removed ones and adding new ones, regenerating embeddings for changed ones
        if "items" in payload:
            db_items = {it.id: it for it in demand.items}
            payload_ids = set()

            for item_payload in payload["items"]:
                item_id = item_payload.get("id")
                # Parse conditions
                min_cond = item_payload.get("minimum_condition")
                if not min_cond and item_payload.get("acceptable_conditions"):
                    min_cond = ",".join(item_payload["acceptable_conditions"])

                new_name = item_payload["item_name"].strip()
                new_category = item_payload["category"]
                new_qty = item_payload["quantity_needed"]

                db_item = None
                if item_id is not None:
                    try:
                        item_id_val = int(item_id)
                        if item_id_val in db_items:
                            db_item = db_items[item_id_val]
                            payload_ids.add(item_id_val)
                    except ValueError:
                        pass

                if db_item:
                    # Check if name or category changed to regenerate embedding
                    if db_item.item_name != new_name or db_item.category != new_category:
                        db_item.embedding = None
                        normalized_text = MatchingService.normalize_text(new_name, new_category)
                        emb = MatchingService.get_embedding(normalized_text)
                        if emb:
                            db_item.embedding = emb
                        trigger_rematch = True

                    if db_item.quantity_needed != new_qty or db_item.minimum_condition != min_cond:
                        trigger_rematch = True

                    db_item.item_name = new_name
                    db_item.category = new_category
                    db_item.quantity_needed = new_qty
                    db_item.minimum_condition = min_cond
                    db.add(db_item)
                else:
                    # Create new item
                    db_item = models.NGODemandItem(
                        demand_id=demand.id,
                        item_name=new_name,
                        category=new_category,
                        quantity_needed=new_qty,
                        quantity_fulfilled=0,
                        minimum_condition=min_cond
                    )
                    # Generate embedding immediately
                    normalized_text = MatchingService.normalize_text(new_name, new_category)
                    emb = MatchingService.get_embedding(normalized_text)
                    if emb:
                        db_item.embedding = emb
                    db.add(db_item)
                    trigger_rematch = True

            # Delete any existing items that were removed
            for existing_id, existing_item in db_items.items():
                if existing_id not in payload_ids:
                    db.delete(existing_item)
                    trigger_rematch = True
        
        db.commit()

        # Trigger background rematching only if matching-relevant fields changed and demand is open (Safeguards 1, 5, 6)
        if trigger_rematch and demand.status == "OPEN":
            background_tasks.add_task(rematch_demand_background, demand.id)

        return {"message": "Demand registry updated successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Close/Delete Demand (tenant scoped)
@router.delete("/demands/{demand_id}", response_model=dict)
async def delete_ngo_demand(
    demand_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.NGO:
        raise HTTPException(status_code=403, detail="Access denied.")

    ngo_profile = current_user.ngo_profile
    if not ngo_profile or not ngo_profile.tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context not found.")

    demand = db.query(models.NGODemand).filter(models.NGODemand.id == demand_id).with_for_update().first()
    if not demand:
        raise HTTPException(status_code=404, detail="Demand not found.")

    # Scope protection
    if demand.tenant_id != ngo_profile.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    try:
        demand.status = "CLOSED"
        db.commit()
        return {"message": "Demand successfully closed."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Mark donation as in transit (PICKUP_SCHEDULED -> PICKUP_IN_PROGRESS)
@router.post("/{donation_id}/transit", response_model=dict)
async def mark_in_transit(
    donation_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found.")

    if current_user.id not in [donation.donor_id, donation.ngo_id] and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You are not authorized to update this donation.")

    if donation.status != "PICKUP_SCHEDULED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start transit. Donation must be PICKUP_SCHEDULED, current: {donation.status}"
        )

    try:
        old_status = donation.status
        donation.status = "PICKUP_IN_PROGRESS"

        history = models.DonationStatusHistory(
            donation_id=donation.id,
            old_status=old_status,
            new_status="PICKUP_IN_PROGRESS",
            changed_by_user_id=current_user.id,
            note="Donation pickup is in progress and in transit."
        )
        db.add(history)

        # Notify donor
        notification = models.Notification(
            user_id=donation.donor_id,
            title="Donation In Transit",
            message="Your donation is currently in transit to the NGO.",
            type="PICKUP",
            related_request_id=donation.id
        )
        db.add(notification)
        db.commit()

        return {"message": "Donation marked as in transit."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Mark donation as completed (PICKUP_IN_PROGRESS -> COMPLETED)
@router.post("/{donation_id}/complete", response_model=dict)
async def complete_donation(
    donation_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found.")

    if current_user.id not in [donation.donor_id, donation.ngo_id] and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You are not authorized to update this donation.")

    if donation.status != "PICKUP_IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete. Donation must be PICKUP_IN_PROGRESS, current: {donation.status}"
        )

    try:
        old_status = donation.status
        donation.status = "COMPLETED"

        history = models.DonationStatusHistory(
            donation_id=donation.id,
            old_status=old_status,
            new_status="COMPLETED",
            changed_by_user_id=current_user.id,
            note="Donation successfully delivered and completed."
        )
        db.add(history)

        # Notify Donor
        notification_donor = models.Notification(
            user_id=donation.donor_id,
            title="Donation Completed!",
            message="Thank you! Your donation has been safely delivered and completed.",
            type="PICKUP",
            related_request_id=donation.id
        )
        db.add(notification_donor)

        # Notify NGO
        notification_ngo = models.Notification(
            user_id=donation.ngo_id,
            title="Donation Completed",
            message="Donation has been marked as completed/received.",
            type="PICKUP",
            related_request_id=donation.id
        )
        db.add(notification_ngo)

        db.commit()
        return {"message": "Donation marked as completed."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- DONOR IMPACT ANALYTICS -----------------

class ImpactSummaryResponse(BaseModel):
    total_donations: int
    total_items_donated: int
    ngos_helped: int
    beneficiaries_reached: Optional[int]
    beneficiaries_is_estimated: bool
    beneficiaries_estimation_method: Optional[str]

class MonthlyDonationPoint(BaseModel):
    month: str
    year: int
    count: int

class CategoryDistributionItem(BaseModel):
    category: str
    quantity: int

class AchievementResponse(BaseModel):
    key: str
    title: str
    description: str
    unlocked: bool
    progress: int
    target: int
    unlocked_at: Optional[str] = None

class DonorImpactResponse(BaseModel):
    summary: ImpactSummaryResponse
    monthly_donations: List[MonthlyDonationPoint]
    category_distribution: List[CategoryDistributionItem]
    achievements: List[AchievementResponse]

QUALIFYING_IMPACT_STATUSES = {
    "NGO_ACCEPTED",
    "PACKAGING_IN_PROGRESS",
    "READY_FOR_PICKUP",
    "PICKUP_SCHEDULED",
    "PICKUP_IN_PROGRESS",
    "COMPLETED"
}

@router.get("/impact", response_model=DonorImpactResponse)
async def get_donor_impact(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.DONOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only donors can access impact analytics."
        )

    # 1. Total Qualifying Donations (Count)
    total_donations = db.query(func.count(models.Donation.id)).filter(
        models.Donation.donor_id == current_user.id,
        models.Donation.status.in_(QUALIFYING_IMPACT_STATUSES)
    ).scalar() or 0

    # 2. Total Items Donated (Sum)
    total_items_donated = db.query(func.coalesce(func.sum(models.DonationItem.quantity), 0)).join(
        models.Donation, models.Donation.id == models.DonationItem.donation_id
    ).filter(
        models.Donation.donor_id == current_user.id,
        models.Donation.status.in_(QUALIFYING_IMPACT_STATUSES)
    ).scalar() or 0

    # 3. NGOs Helped (Distinct Count)
    ngos_helped = db.query(func.count(func.distinct(models.Donation.ngo_id))).filter(
        models.Donation.donor_id == current_user.id,
        models.Donation.status.in_(QUALIFYING_IMPACT_STATUSES),
        models.Donation.ngo_id.isnot(None)
    ).scalar() or 0

    # 4. Beneficiaries Reached (Estimation Formula: total_items_donated * 3)
    beneficiaries_reached = total_items_donated * 3
    beneficiaries_is_estimated = True
    beneficiaries_estimation_method = "total_items_donated * 3"

    # 5. Monthly Donations Chart Data
    # Get completion subquery to find canonical first completion transition timestamp per donation
    completion_subquery = db.query(
        models.DonationStatusHistory.donation_id,
        func.min(models.DonationStatusHistory.created_at).label('completed_at')
    ).filter(
        models.DonationStatusHistory.new_status == "COMPLETED"
    ).group_by(
        models.DonationStatusHistory.donation_id
    ).subquery()

    donations_data = db.query(
        models.Donation.id,
        models.Donation.created_at,
        models.Donation.status,
        completion_subquery.c.completed_at
    ).outerjoin(
        completion_subquery,
        models.Donation.id == completion_subquery.c.donation_id
    ).filter(
        models.Donation.donor_id == current_user.id,
        models.Donation.status.in_(QUALIFYING_IMPACT_STATUSES)
    ).all()

    # Generate last 12 months array
    import datetime
    today = datetime.date.today()
    months_list = []
    for i in range(11, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        
        month_name = datetime.date(year, month, 1).strftime("%b")
        months_list.append({
            "month": month_name,
            "year": year,
            "count": 0,
            "month_num": month
        })

    # Group donations by "impact activity month"
    for d in donations_data:
        # completed donations -> first completion transition timestamp
        # other qualifying progressed donations -> donation.created_at
        if d.status == "COMPLETED" and d.completed_at:
            dt = d.completed_at
        else:
            dt = d.created_at
        
        if dt:
            d_year = dt.year
            d_month = dt.month
            for m in months_list:
                if m["year"] == d_year and m["month_num"] == d_month:
                    m["count"] += 1
                    break

    # Map to schema-compliant response points
    monthly_points = [
        MonthlyDonationPoint(month=m["month"], year=m["year"], count=m["count"])
        for m in months_list
    ]

    # 6. Category Distribution
    category_counts = db.query(
        models.DonationItem.category,
        func.sum(models.DonationItem.quantity).label('quantity')
    ).join(
        models.Donation, models.Donation.id == models.DonationItem.donation_id
    ).filter(
        models.Donation.donor_id == current_user.id,
        models.Donation.status.in_(QUALIFYING_IMPACT_STATUSES)
    ).group_by(
        models.DonationItem.category
    ).all()

    category_map = {}
    for row in category_counts:
        cat = row.category.strip() if row.category else ""
        if not cat:
            cat_key = "Other"
        else:
            cat_key = cat.title()
        
        category_map[cat_key] = category_map.get(cat_key, 0) + row.quantity

    category_distribution = sorted(
        [CategoryDistributionItem(category=k, quantity=v) for k, v in category_map.items()],
        key=lambda x: x.quantity,
        reverse=True
    )

    # 7. Achievements Calculation
    first_donation_date = None
    if total_donations >= 1:
        min_dt = None
        for d in donations_data:
            dt = d.completed_at if (d.status == "COMPLETED" and d.completed_at) else d.created_at
            if dt:
                if min_dt is None or dt < min_dt:
                    min_dt = dt
        if min_dt:
            first_donation_date = min_dt.isoformat()

    def get_start_of_week(dt):
        d = dt.date() if isinstance(dt, datetime.datetime) else dt
        return d - datetime.timedelta(days=d.weekday())

    donation_weeks = set()
    for d in donations_data:
        dt = d.completed_at if (d.status == "COMPLETED" and d.completed_at) else d.created_at
        if dt:
            donation_weeks.add(get_start_of_week(dt))
    
    unique_weeks = sorted(list(donation_weeks))
    max_streak = 0
    current_streak = 0
    prev_week = None
    for w in unique_weeks:
        if prev_week is None:
            current_streak = 1
        elif (w - prev_week).days == 7:
            current_streak += 1
        elif (w - prev_week).days > 7:
            max_streak = max(max_streak, current_streak)
            current_streak = 1
        prev_week = w
    max_streak = max(max_streak, current_streak)

    achievements = [
        AchievementResponse(
            key="FIRST_DONATION",
            title="First Donation",
            description="Complete your first donation",
            unlocked=total_donations >= 1,
            progress=min(total_donations, 1),
            target=1,
            unlocked_at=first_donation_date
        ),
        AchievementResponse(
            key="STREAK_5_WEEK",
            title="5-Week Streak",
            description="Donate in 5 consecutive calendar weeks",
            unlocked=max_streak >= 5,
            progress=min(max_streak, 5),
            target=5,
            unlocked_at=None
        ),
        AchievementResponse(
            key="HELPED_5_NGOS",
            title="5 NGOs Helped",
            description="Support 5 or more unique NGOs",
            unlocked=ngos_helped >= 5,
            progress=min(ngos_helped, 5),
            target=5,
            unlocked_at=None
        ),
        AchievementResponse(
            key="ITEMS_100_MILESTONE",
            title="100 Items Milestone",
            description="Donate 100 or more items",
            unlocked=total_items_donated >= 100,
            progress=min(total_items_donated, 100),
            target=100,
            unlocked_at=None
        ),
        AchievementResponse(
            key="BENEFICIARIES_1000",
            title="1,000 Beneficiaries",
            description="Reach 1,000 or more beneficiaries",
            unlocked=beneficiaries_reached >= 1000,
            progress=min(beneficiaries_reached, 1000),
            target=1000,
            unlocked_at=None
        )
    ]

    return DonorImpactResponse(
        summary=ImpactSummaryResponse(
            total_donations=total_donations,
            total_items_donated=total_items_donated,
            ngos_helped=ngos_helped,
            beneficiaries_reached=beneficiaries_reached,
            beneficiaries_is_estimated=beneficiaries_is_estimated,
            beneficiaries_estimation_method=beneficiaries_estimation_method
        ),
        monthly_donations=monthly_points,
        category_distribution=category_distribution,
        achievements=achievements
    )

