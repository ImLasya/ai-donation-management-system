import os
import logging
import datetime
import json
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_

import models
from config import settings
from services.email_service import EmailService

logger = logging.getLogger(__name__)

# Singleton class to load and cache the SentenceTransformer model
class SentenceTransformerSingleton:
    _instance = None
    _model = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SentenceTransformerSingleton, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    @property
    def model(self):
        if self._model is None:
            try:
                # Lazy import to avoid loading unless matching is triggered
                from sentence_transformers import SentenceTransformer
                model_name = settings.EMBEDDING_MODEL_NAME
                logger.info(f"Loading SentenceTransformer model: {model_name}...")
                self._model = SentenceTransformer(model_name)
                logger.info("SentenceTransformer model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer model: {e}")
                self._model = None
        return self._model


class MatchingService:
    @staticmethod
    def normalize_text(item_name: str, category: str) -> str:
        """
        Normalize item name and category by converting to lowercase, trimming,
        and applying basic singularization to normalize plural words safely.
        """
        n = item_name.lower().strip()
        c = category.lower().strip()

        # Basic singularization mapping
        if n.endswith("s") and not n.endswith("ss") and len(n) > 3:
            # e.g., "books" -> "book", "jackets" -> "jacket"
            if n.endswith("es") and n[:-2].endswith(("ch", "sh", "x", "z", "s")):
                n = n[:-2]
            else:
                n = n[:-1]

        return f"{n} {c}"

    @classmethod
    def normalize_name_only(cls, item_name: str) -> str:
        """
        Normalize item name by converting to lowercase, trimming,
        and applying basic singularization to normalize plural words safely.
        """
        n = item_name.lower().strip()
        if n.endswith("s") and not n.endswith("ss") and len(n) > 3:
            if n.endswith("es") and n[:-2].endswith(("ch", "sh", "x", "z", "s")):
                n = n[:-2]
            else:
                n = n[:-1]
        return n

    @staticmethod
    def get_embedding(text: str) -> list:
        """
        Generate 384-dimensional embedding vector for the given text using cached SentenceTransformer.
        Returns None if model is unavailable.
        """
        model = SentenceTransformerSingleton().model
        if model is None:
            logger.error("SentenceTransformer model is unavailable. Cannot generate embedding.")
            return None
        try:
            emb = model.encode(text)
            return [float(x) for x in emb]
        except Exception as e:
            logger.error(f"Error encoding embedding: {e}")
            return None

    @staticmethod
    def cosine_similarity(v1: list, v2: list) -> float:
        """
        Calculate cosine similarity between two vectors.
        """
        if not v1 or not v2:
            return 0.0
        try:
            arr1 = np.array(v1, dtype=np.float32)
            arr2 = np.array(v2, dtype=np.float32)
            dot = np.dot(arr1, arr2)
            n1 = np.linalg.norm(arr1)
            n2 = np.linalg.norm(arr2)
            if n1 == 0.0 or n2 == 0.0:
                return 0.0
            return float(dot / (n1 * n2))
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

    @classmethod
    def match_donation_against_demand(cls, db: Session, donation: models.Donation, demand: models.NGODemand) -> str:
        """
        Evaluate and score matching between a single donation and a single demand.
        Returns one of: CREATED, UPDATED, EXISTING, NO_MATCH.
        """
        # Concurrency safety: check locks or status check
        if donation.status in ["COMPLETED", "NGO_REJECTED", "EXPIRED", "PENDING_NGO_RESPONSE", "NGO_ACCEPTED"]:
            return "NO_MATCH"
        if demand.status != "OPEN":
            return "NO_MATCH"

        donor_profile = db.query(models.DonorProfile).filter(models.DonorProfile.user_id == donation.donor_id).first()
        ngo_profile = db.query(models.NGOProfile).filter(models.NGOProfile.user_id == demand.ngo_id).first()
        if not donor_profile or not ngo_profile:
            return "NO_MATCH"

        # Check model availability
        model = SentenceTransformerSingleton().model
        if model is None:
            return "NO_MATCH"

        # Ensure donation items have embeddings
        from services.donation_eligibility_service import DonationEligibilityService
        for item in donation.items:
            if DonationEligibilityService.classify_detection(item.item_name) == "NON_DONATABLE":
                continue
            normalized_text = cls.normalize_text(item.item_name, item.category)
            if not item.embedding:
                emb = cls.get_embedding(normalized_text)
                if emb:
                    item.embedding = emb
                    db.add(item)
        db.flush()

        # Pre-load/calculate embeddings for demand items
        for item in demand.items:
            if not item.embedding:
                normalized_text = cls.normalize_text(item.item_name, item.category)
                emb = cls.get_embedding(normalized_text)
                if emb:
                    item.embedding = emb
                    db.add(item)
        db.flush()

        # Check unsatisfied items in demand
        has_unsatisfied_item = False
        valid_demand_items = []
        for it in demand.items:
            rem = max(it.quantity_needed - it.quantity_fulfilled, 0)
            if rem > 0:
                has_unsatisfied_item = True
                valid_demand_items.append((it, rem))

        if not has_unsatisfied_item:
            return "NO_MATCH"

        # Compare items
        matched_items_list = []
        total_similarity = 0.0
        qty_fit_sum = 0.0
        matched_count = 0
        reasons = []

        for d_item in donation.items:
            if DonationEligibilityService.classify_detection(d_item.item_name) == "NON_DONATABLE":
                continue
            best_sim = 0.0
            best_match_item = None
            best_match_rem = 0
            best_match_type = "SEMANTIC"
            condition_text = "compatible"

            d_norm = cls.normalize_text(d_item.item_name, d_item.category)
            d_name_only = cls.normalize_name_only(d_item.item_name)

            for dem_item, rem in valid_demand_items:
                dem_norm = cls.normalize_text(dem_item.item_name, dem_item.category)
                dem_name_only = cls.normalize_name_only(dem_item.item_name)
                
                if d_norm == dem_norm or d_name_only == dem_name_only:
                    sim = 1.0
                    match_type = "EXACT"
                else:
                    sim = cls.cosine_similarity(d_item.embedding, dem_item.embedding)
                    match_type = "SEMANTIC"

                if d_item.category.lower().strip() != dem_item.category.lower().strip():
                    if match_type != "EXACT":
                        sim *= 0.1

                if sim > best_sim:
                    best_sim = sim
                    best_match_item = dem_item
                    best_match_rem = rem
                    best_match_type = match_type

            if best_sim >= settings.SEMANTIC_SIMILARITY_THRESHOLD and best_match_item:
                cond_penalty = 1.0
                if best_match_item.minimum_condition:
                    acceptable = [c.strip().upper() for c in best_match_item.minimum_condition.split(",") if c.strip()]
                    donated_cond = d_item.condition.strip().upper()
                    if acceptable and donated_cond not in acceptable and donated_cond not in ("NOT ASSESSED", "NOT_ASSESSED", ""):
                        cond_penalty = 0.4
                        condition_text = f"penalty applied (NGO accepts {', '.join(acceptable)} but donated is {d_item.condition})"
                best_sim *= cond_penalty

                if best_sim >= settings.SEMANTIC_SIMILARITY_THRESHOLD:
                    matched_count += 1
                    total_similarity += best_sim
                    q_d = d_item.quantity
                    r_n = best_match_rem
                    fit_ratio = min(q_d / r_n, r_n / q_d)
                    qty_fit_score_val = fit_ratio * 100.0
                    qty_fit_sum += qty_fit_score_val

                    matched_items_list.append({
                        "donated_item": d_item.item_name,
                        "demand_item": best_match_item.item_name,
                        "donated_quantity": d_item.quantity,
                        "remaining_needed": best_match_rem,
                        "semantic_similarity": round(best_sim, 2),
                        "match_type": best_match_type,
                        "condition_status": condition_text
                    })

                    if best_match_type == "EXACT":
                        reasons.append(f"✓ Direct match: Donated '{d_item.item_name}' exactly matches requested '{best_match_item.item_name}' ({condition_text})")
                    else:
                        reasons.append(f"✓ Semantic match: '{d_item.item_name}' matches '{best_match_item.item_name}' with {int(best_sim * 100)}% similarity ({condition_text})")

                    pct_covered = min(100, int((q_d / r_n) * 100))
                    reasons.append(f"  - Quantity covers {pct_covered}% of remaining need ({q_d} available / {r_n} needed)")

        if matched_count == 0:
            return "NO_MATCH"

        # Scores
        item_match_score = (total_similarity / len(donation.items)) * 100.0 if donation.items else 0.0
        quantity_fit_score = qty_fit_sum / matched_count
        
        if donor_profile.city.lower() == ngo_profile.city.lower():
            geographic_score = 100.0
            reasons.append("✓ Location: Donor and NGO are in the same city")
        elif donor_profile.state.lower() == ngo_profile.state.lower():
            geographic_score = 70.0
            reasons.append("✓ Location: Donor and NGO are in the same state")
        else:
            geographic_score = 30.0
            reasons.append("✓ Location: Distance requires transit cross-state")

        priority_map = {"URGENT": 100.0, "HIGH": 80.0, "MEDIUM": 55.0, "LOW": 30.0}
        priority_score = priority_map.get(demand.priority.upper(), 55.0)
        reasons.append(f"✓ Urgency: Demand is marked as {demand.priority} priority")

        final_score = (
            settings.WEIGHT_ITEM_MATCH * item_match_score +
            settings.WEIGHT_QUANTITY_FIT * quantity_fit_score +
            settings.WEIGHT_GEOGRAPHIC * geographic_score +
            settings.WEIGHT_PRIORITY * priority_score
        )

        if final_score < settings.MATCH_MIN_SCORE:
            return "NO_MATCH"

        # Check existing match record (using with_for_update for concurrency safety)
        match_record = db.query(models.DonationMatch).filter(
            models.DonationMatch.donation_id == donation.id,
            models.DonationMatch.ngo_id == ngo_profile.id,
            models.DonationMatch.demand_id == demand.id
        ).with_for_update().first()

        result_state = "EXISTING"
        if not match_record:
            match_record = models.DonationMatch(
                donation_id=donation.id,
                ngo_id=ngo_profile.id,
                tenant_id=demand.tenant_id,
                demand_id=demand.id,
                status="ACTIVE"
            )
            result_state = "CREATED"

        # Round values for comparison
        new_final = round(final_score, 2)
        new_item = round(item_match_score, 2)
        new_qty = round(quantity_fit_score, 2)
        new_geo = round(geographic_score, 2)
        new_pri = round(priority_score, 2)
        new_explanation = json.dumps({"matched_items": matched_items_list, "reasons": reasons})

        # Track old score for crossings checks
        old_score = match_record.final_score if result_state == "EXISTING" else 0.0

        if result_state == "EXISTING":
            if (match_record.final_score != new_final or
                match_record.item_match_score != new_item or
                match_record.quantity_fit_score != new_qty or
                match_record.geographic_score != new_geo or
                match_record.priority_score != new_pri or
                match_record.matched_items_count != matched_count or
                match_record.match_explanation != new_explanation):
                result_state = "UPDATED"

        match_record.final_score = new_final
        match_record.item_match_score = new_item
        match_record.quantity_fit_score = new_qty
        match_record.geographic_score = new_geo
        match_record.priority_score = new_pri
        match_record.matched_items_count = matched_count
        match_record.match_explanation = new_explanation
        db.add(match_record)
        db.flush()

        # Handle notifications based on result state and safeguards
        if new_final >= settings.MATCH_NOTIFICATION_THRESHOLD:
            ngo_key = f"FUTURE_MATCH_NGO:{donation.id}:{ngo_profile.user_id}:{demand.id}"
            donor_key = f"FUTURE_MATCH_DONOR:{donation.id}:{ngo_profile.user_id}:{demand.id}"
            
            # Send fresh future-match notifications only for CREATED,
            # or if UPDATED and the match newly crosses the configured threshold
            should_notify = (result_state == "CREATED" or 
                             (result_state == "UPDATED" and old_score < settings.MATCH_NOTIFICATION_THRESHOLD))

            if should_notify:
                ngo_user = db.query(models.User).filter(models.User.id == ngo_profile.user_id).first()
                donor_user = db.query(models.User).filter(models.User.id == donation.donor_id).first()

                # NGO In-app & Email notifications
                if ngo_user:
                    ngo_dup = db.query(models.Notification).filter(models.Notification.deduplication_key == ngo_key).first()
                    if not ngo_dup and ngo_user.inapp_notifications_enabled:
                        msg = f"A compatible donation is now available for your demand: {demand.title}."
                        ngo_notif = models.Notification(
                            user_id=ngo_profile.user_id,
                            title="Compatible donation available",
                            message=msg,
                            type="MATCH",
                            related_request_id=donation.id,
                            deduplication_key=ngo_key
                        )
                        db.add(ngo_notif)

                    # Send Email (reusing centralized service, preventing duplicates via the same should_notify logic)
                    if ngo_user.email_notifications_enabled:
                        items_li = "".join([f"<li>{it.get('donated_item', '')} (x{it.get('donated_quantity', 1)})</li>" for it in matched_items_list])
                        replacements = {
                            "demand_title": demand.title,
                            "donation_id": donation.id,
                            "match_score": int(new_final),
                            "matched_items_list": items_li,
                            "action_url": f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/ngo/incoming"
                        }
                        html = EmailService.load_template("match_available.html", replacements)
                        EmailService.send_html_email(
                            to_email=ngo_user.email,
                            subject="Compatible Donation Available - Donate",
                            html_body=html,
                            text_fallback=f"A new compatible donation is available for your demand: {demand.title}."
                        )

                # Donor In-app & Email notifications
                if donor_user:
                    donor_dup = db.query(models.Notification).filter(models.Notification.deduplication_key == donor_key).first()
                    if not donor_dup and donor_user.inapp_notifications_enabled:
                        first_item = donation.items[0].item_name if donation.items else "items"
                        msg = f"A new NGO match is available for your {first_item} donation."
                        donor_notif = models.Notification(
                            user_id=donation.donor_id,
                            title="New compatible NGO match found",
                            message=msg,
                            type="MATCH",
                            related_request_id=donation.id,
                            deduplication_key=donor_key
                        )
                        db.add(donor_notif)

                    if donor_user.email_notifications_enabled:
                        items_li = "".join([f"<li>{it.get('donated_item', '')} (x{it.get('donated_quantity', 1)})</li>" for it in matched_items_list])
                        replacements = {
                            "donation_id": donation.id,
                            "ngo_name": ngo_profile.organization_name,
                            "demand_title": demand.title,
                            "matched_items_list": items_li,
                            "action_url": f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/donor/matches"
                        }
                        html = EmailService.load_template("future_match_available.html", replacements)
                        EmailService.send_html_email(
                            to_email=donor_user.email,
                            subject="New compatible NGO match found - Donate",
                            html_body=html,
                            text_fallback=f"A new NGO match is available for your donation DON-{donation.id}."
                        )

        return result_state

    @classmethod
    def run_matching(cls, db: Session, donation: models.Donation) -> bool:
        """
        Run the semantic matching engine for a given donation.
        """
        # Check model availability (Safeguard)
        model = SentenceTransformerSingleton().model
        if model is None:
            logger.error("SentenceTransformer model is unavailable. Cannot run matching.")
            return False

        try:
            logger.info(f"Running matching for donation {donation.id}...")
            
            # Retrieve open, unexpired, non-fully satisfied NGO demands
            today = datetime.date.today()
            open_demands = db.query(models.NGODemand).filter(
                and_(
                    models.NGODemand.status == "OPEN",
                    (models.NGODemand.needed_by_date == None) | (models.NGODemand.needed_by_date >= today)
                )
            ).all()

            for demand in open_demands:
                cls.match_donation_against_demand(db, donation, demand)

            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error during matching run: {e}", exc_info=True)
            return False

    @classmethod
    def run_rematching_for_demand(cls, db: Session, demand_id: int) -> bool:
        """
        Runs matching specifically for a single demand against all eligible candidate waiting donations.
        """
        # Check model availability (Safeguard)
        model = SentenceTransformerSingleton().model
        if model is None:
            logger.error("SentenceTransformer model is unavailable. Cannot run re-matching.")
            return False

        try:
            demand = db.query(models.NGODemand).filter(models.NGODemand.id == demand_id).first()
            if not demand:
                logger.error(f"Demand {demand_id} not found.")
                return False

            # Exclude CLOSED or expired demands
            today = datetime.date.today()
            if demand.status == "CLOSED" or (demand.needed_by_date and demand.needed_by_date < today):
                logger.info(f"Skipping re-matching: Demand {demand_id} is closed or expired.")
                return False

            # Query waiting donations (WAITING_FOR_MATCH, active donor, not expired)
            active_donors_query = db.query(models.User.id).filter(
                models.User.role == models.UserRole.DONOR,
                models.User.is_active == True
            ).all()
            active_donors = [uid for (uid,) in active_donors_query]

            cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=settings.DONATION_MATCH_WAIT_DAYS)
            candidate_donations = db.query(models.Donation).filter(
                models.Donation.status == "WAITING_FOR_MATCH",
                models.Donation.donor_id.in_(active_donors),
                models.Donation.created_at >= cutoff_date
            ).all()

            for donation in candidate_donations:
                # Lock row for update to ensure concurrency safety
                donation_locked = db.query(models.Donation).filter(
                    models.Donation.id == donation.id
                ).with_for_update().first()

                if not donation_locked or donation_locked.status != "WAITING_FOR_MATCH":
                    continue

                state = cls.match_donation_against_demand(db, donation_locked, demand)
                if state in ["CREATED", "UPDATED"]:
                    # If match discovered, transition status to ITEMS_SUBMITTED
                    donation_locked.status = "ITEMS_SUBMITTED"
                    db.add(donation_locked)

                    history = models.DonationStatusHistory(
                        donation_id=donation_locked.id,
                        old_status="WAITING_FOR_MATCH",
                        new_status="ITEMS_SUBMITTED",
                        changed_by_user_id=donation_locked.donor_id,
                        note=f"Future match found against demand: {demand.title}"
                    )
                    db.add(history)

            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error during re-matching for demand {demand_id}: {e}", exc_info=True)
            return False

    @classmethod
    def expire_waiting_donations(cls, db: Session) -> int:
        """
        Finds WAITING_FOR_MATCH donations older than settings.DONATION_MATCH_WAIT_DAYS,
        sets their status to EXPIRED, and logs a DonationStatusHistory entry.
        Returns the number of expired donations.
        """
        try:
            today = datetime.datetime.now(datetime.timezone.utc)
            cutoff = today - datetime.timedelta(days=settings.DONATION_MATCH_WAIT_DAYS)
            
            expired_donations = db.query(models.Donation).filter(
                models.Donation.status == "WAITING_FOR_MATCH",
                models.Donation.created_at < cutoff
            ).with_for_update().all()
            
            count = 0
            for donation in expired_donations:
                donation.status = "EXPIRED"
                db.add(donation)
                
                history = models.DonationStatusHistory(
                    donation_id=donation.id,
                    old_status="WAITING_FOR_MATCH",
                    new_status="EXPIRED",
                    changed_by_user_id=donation.donor_id,
                    note="Donation matching period expired."
                )
                db.add(history)
                count += 1
            
            if count > 0:
                db.commit()
                logger.info(f"Expired {count} waiting donations.")
            return count
        except Exception as e:
            db.rollback()
            logger.error(f"Error while expiring waiting donations: {e}")
            return 0

