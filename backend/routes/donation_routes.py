import logging
import asyncio
import json
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
from routes.auth_routes import get_current_user
import models

# Configure logger
logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/donations", tags=["Donations Workflow"])

# ----------------- PYDANTIC SCHEMAS -----------------

class DonationItemCreate(BaseModel):
    item_name: str
    category: str
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")
    condition: str
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence must be between 0 and 1")
    source: str  # "AI" or "MANUAL"
    notes: Optional[str] = None

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

        # Run semantic matching safely in a try-catch block
        try:
            from services.matching_service import MatchingService
            MatchingService.run_matching(db, donation)
        except Exception as matching_err:
            logger.error(f"Semantic matching failed after successful donation persist for ID {donation.id}: {matching_err}")

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

    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation record not found.")

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
        from services.matching_service import MatchingService
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

        history = models.DonationStatusHistory(
            donation_id=donation.id,
            old_status=old_status,
            new_status="NGO_ACCEPTED",
            changed_by_user_id=current_user.id,
            note="Request accepted by NGO. Packaging unlocked."
        )
        db.add(history)

        # Notify Donor
        ngo_name = current_user.ngo_profile.organization_name if current_user.ngo_profile else "NGO"
        notification = models.Notification(
            user_id=req.donor_id,
            title="Donation Request Accepted!",
            message=f"Your donation request has been accepted by {ngo_name}. You can now prepare items for pickup.",
            type="ACCEPT",
            related_request_id=donation.id
        )
        db.add(notification)
        db.commit()

        return {"message": "Donation request accepted."}

    except Exception as e:
        db.rollback()
        logger.error(f"Error accepting request: {e}")
        raise HTTPException(status_code=500, detail="Failed to accept request.")

# 4. NGO Rejects Request
@router.post("/requests/{request_id}/reject", response_model=dict)
async def reject_donation_request(
    request_id: int,
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
        donation.status = "NGO_REJECTED"

        history = models.DonationStatusHistory(
            donation_id=donation.id,
            old_status=old_status,
            new_status="NGO_REJECTED",
            changed_by_user_id=current_user.id,
            note="Request declined by NGO."
        )
        db.add(history)

        # Notify Donor
        ngo_name = current_user.ngo_profile.organization_name if current_user.ngo_profile else "NGO"
        notification = models.Notification(
            user_id=req.donor_id,
            title="Donation Request Declined",
            message=f"{ngo_name} could not accept this donation. Please select another matched NGO.",
            type="REJECT",
            related_request_id=donation.id
        )
        db.add(notification)
        db.commit()

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
        # Create or update packaging record
        pkg_rec = db.query(models.PackagingRecord).filter(models.PackagingRecord.donation_id == donation_id).first()
        if not pkg_rec:
            pkg_rec = models.PackagingRecord(
                donation_id=donation_id,
                packaging_status="COMPLETED",
                package_count=payload.package_count,
                packaging_notes=payload.packaging_notes,
                completed_at=date.today()
            )
            db.add(pkg_rec)
        else:
            pkg_rec.package_count = payload.package_count
            pkg_rec.packaging_notes = payload.packaging_notes
            pkg_rec.completed_at = date.today()

        old_status = donation.status
        donation.status = "READY_FOR_PICKUP"

        # Log history
        history = models.DonationStatusHistory(
            donation_id=donation.id,
            old_status=old_status,
            new_status="READY_FOR_PICKUP",
            changed_by_user_id=current_user.id,
            note=f"Items packaging complete. Total package count: {payload.package_count}."
        )
        db.add(history)

        # Notify NGO
        donor_name = current_user.donor_profile.full_name if current_user.donor_profile else "Donor"
        notification = models.Notification(
            user_id=donation.ngo_id,
            title="Donation Ready for Pickup",
            message=f"{donor_name} completed packaging. Total packages: {payload.package_count}.",
            type="PICKUP",
            related_request_id=donation.id
        )
        db.add(notification)
        db.commit()

        return {"message": "Donation marked as ready for pickup."}

    except Exception as e:
        db.rollback()
        logger.error(f"Error completing packaging: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete packaging.")

# 7. Schedule Pickup (READY_FOR_PICKUP -> PICKUP_SCHEDULED)
@router.post("/{donation_id}/pickup", response_model=dict)
async def schedule_pickup(
    donation_id: int,
    payload: PickupScheduleCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.DONOR:
        raise HTTPException(status_code=403, detail="Only donors can schedule pickups.")

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
            notes=payload.notes
        )
        db.add(pickup)

        old_status = donation.status
        donation.status = "PICKUP_SCHEDULED"

        # Log history
        history = models.DonationStatusHistory(
            donation_id=donation.id,
            old_status=old_status,
            new_status="PICKUP_SCHEDULED",
            changed_by_user_id=current_user.id,
            note=f"Pickup scheduled for {payload.pickup_date} at {payload.time_slot}."
        )
        db.add(history)

        # Notify NGO
        notification_ngo = models.Notification(
            user_id=donation.ngo_id,
            title="Pickup Scheduled",
            message=f"Pickup has been scheduled for {payload.pickup_date} at {payload.time_slot}.",
            type="PICKUP",
            related_request_id=donation.id
        )
        db.add(notification_ngo)

        # Notify Donor
        ngo_org = db.query(models.NGOProfile).filter(models.NGOProfile.user_id == donation.ngo_id).first()
        org_name = ngo_org.organization_name if ngo_org else "NGO"
        notification_donor = models.Notification(
            user_id=current_user.id,
            title="Pickup Confirmed",
            message=f"Your pickup with {org_name} is scheduled successfully.",
            type="PICKUP",
            related_request_id=donation.id
        )
        db.add(notification_donor)
        db.commit()

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
        
        res.append({
            "id": str(d.id),
            "status": d.status,
            "date": d.created_at.strftime("%Y-%m-%d") if d.created_at else "—",
            "ngoName": ngo_name,
            "items": items_summary,
            "beneficiaries": sum(it.quantity for it in d.items) * 3
        })
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
    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found.")

    if current_user.id not in [donation.donor_id, donation.ngo_id] and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You do not own this donation.")

    # Short human-readable labels mapping (Requirement 10)
    STATUS_LABELS_MAP = {
        "DRAFT": "Items Submitted",
        "ITEMS_SUBMITTED": "Items Submitted",
        "PENDING_NGO_RESPONSE": "Awaiting NGO",
        "NGO_ACCEPTED": "Accepted",
        "PACKAGING_IN_PROGRESS": "Packaging",
        "READY_FOR_PICKUP": "Ready",
        "PICKUP_SCHEDULED": "Scheduled",
        "PICKUP_IN_PROGRESS": "In Transit",
        "COMPLETED": "Completed",
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
    workflow_steps = ["ITEMS_SUBMITTED", "PENDING_NGO_RESPONSE", "NGO_ACCEPTED", "PACKAGING_IN_PROGRESS", "READY_FOR_PICKUP", "PICKUP_SCHEDULED", "PICKUP_IN_PROGRESS", "COMPLETED"]
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
    # Since we do not have a volunteers table, we return None (Volunteer not assigned yet)
    volunteer = None

    return {
        "id": str(donation.id),
        "status": donation.status,
        "date": donation.created_at.strftime("%Y-%m-%d") if donation.created_at else "—",
        "ngoName": ngo_name,
        "items": items_list,
        "pickup": pickup_details,
        "volunteer": volunteer,
        "events": events,
        "beneficiaries": sum(it.quantity for it in donation.items) * 3
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
    from services.matching_service import MatchingService
    MatchingService.run_matching(db, donation)
    
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
            # all items
            "items": items_data,
        })
    return res


# Update/Pause Demand (tenant scoped)
@router.put("/demands/{demand_id}", response_model=dict)
async def update_ngo_demand(
    demand_id: int,
    payload: dict,
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
        if "status" in payload:
            status_val = payload["status"]
            # Map status
            demand.status = "OPEN" if status_val == "Active" else "CLOSED"
        if "priority" in payload:
            demand.priority = payload["priority"]
        if "description" in payload:
            demand.description = payload["description"]
        
        db.commit()
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
