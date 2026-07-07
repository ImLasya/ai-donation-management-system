import os
import logging
import datetime
import json
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_

import models
from config import settings

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
    def run_matching(cls, db: Session, donation: models.Donation) -> bool:
        """
        Run the semantic matching engine for a given donation.
        Persists matches in `donation_matches` and triggers deduplicated notifications.
        Returns True on success, False if matching failed (but does not crash the app).
        """
        try:
            logger.info(f"Running matching for donation {donation.id}...")
            
            # Fetch donor location details
            donor_profile = db.query(models.DonorProfile).filter(models.DonorProfile.user_id == donation.donor_id).first()
            if not donor_profile:
                logger.error(f"Donor profile not found for donor ID {donation.donor_id}")
                return False

            # Check model availability first
            model = SentenceTransformerSingleton().model
            if model is None:
                logger.error("Embedding model is unavailable. Aborting matching algorithm.")
                return False

            # 1. Ensure all donation items have embeddings
            for item in donation.items:
                normalized_text = cls.normalize_text(item.item_name, item.category)
                # Check if changed or missing
                if not item.embedding:
                    emb = cls.get_embedding(normalized_text)
                    if emb:
                        item.embedding = emb
                        db.add(item)
            db.flush()

            # 2. Retrieve open, unexpired, non-fully satisfied NGO demands
            today = datetime.date.today()
            open_demands = db.query(models.NGODemand).filter(
                and_(
                    models.NGODemand.status == "OPEN",
                    (models.NGODemand.needed_by_date == None) | (models.NGODemand.needed_by_date >= today)
                )
            ).all()

            if not open_demands:
                logger.info("No open or active demands found for matching.")
                return True

            # Pre-load/calculate embeddings for demand items
            for demand in open_demands:
                for item in demand.items:
                    if not item.embedding:
                        normalized_text = cls.normalize_text(item.item_name, item.category)
                        emb = cls.get_embedding(normalized_text)
                        if emb:
                            item.embedding = emb
                            db.add(item)
            db.flush()

            # 3. Calculate scores per demand
            for demand in open_demands:
                # Exclude cross-tenant issues by ensuring the demand has a valid tenant_id
                if not demand.tenant_id or not demand.ngo_id:
                    continue

                ngo_profile = db.query(models.NGOProfile).filter(models.NGOProfile.user_id == demand.ngo_id).first()
                if not ngo_profile:
                    continue

                # A. Exclude if all items in this demand are fully satisfied
                has_unsatisfied_item = False
                valid_demand_items = []
                for it in demand.items:
                    rem = max(it.quantity_needed - it.quantity_fulfilled, 0)
                    if rem > 0:
                        has_unsatisfied_item = True
                        valid_demand_items.append((it, rem))

                if not has_unsatisfied_item:
                    logger.info(f"Skipping demand {demand.id} because all items are fully satisfied.")
                    continue

                # B. Compare donation items with valid demand items
                matched_items_list = []
                total_similarity = 0.0
                qty_fit_sum = 0.0
                matched_count = 0
                reasons = []

                for d_item in donation.items:
                    best_sim = 0.0
                    best_match_item = None
                    best_match_rem = 0
                    best_match_type = "SEMANTIC"
                    condition_text = "compatible"

                    # Normalize donation item text
                    d_norm = cls.normalize_text(d_item.item_name, d_item.category)

                    for dem_item, rem in valid_demand_items:
                        dem_norm = cls.normalize_text(dem_item.item_name, dem_item.category)
                        
                        # Calculate similarity
                        if d_norm == dem_norm:
                            sim = 1.0
                            match_type = "EXACT"
                        else:
                            sim = cls.cosine_similarity(d_item.embedding, dem_item.embedding)
                            match_type = "SEMANTIC"

                        # Apply category check to avoid cross-category false positives
                        if d_item.category.lower().strip() != dem_item.category.lower().strip():
                            # Severe category penalty if not exact
                            if match_type != "EXACT":
                                sim *= 0.1

                        # Track best fit
                        if sim > best_sim:
                            best_sim = sim
                            best_match_item = dem_item
                            best_match_rem = rem
                            best_match_type = match_type

                    # Apply condition compatibility check
                    if best_sim >= settings.SEMANTIC_SIMILARITY_THRESHOLD and best_match_item:
                        cond_ok = True
                        cond_penalty = 1.0
                        if best_match_item.minimum_condition:
                            acceptable = [c.strip().upper() for c in best_match_item.minimum_condition.split(",") if c.strip()]
                            donated_cond = d_item.condition.strip().upper()
                            if acceptable and donated_cond not in acceptable and donated_cond not in ("NOT ASSESSED", "NOT_ASSESSED", ""):
                                cond_penalty = 0.4  # Apply 60% penalty
                                cond_ok = False
                                condition_text = f"penalty applied (NGO accepts {', '.join(acceptable)} but donated is {d_item.condition})"
                        
                        # Apply penalty
                        best_sim *= cond_penalty

                        if best_sim >= settings.SEMANTIC_SIMILARITY_THRESHOLD:
                            matched_count += 1
                            total_similarity += best_sim
                            
                            # Quantity Fit Calculation: normalized 0-100 fit ratio
                            # formula: min(Q_d / R_n, R_n / Q_d)
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

                # If no matching items meet the threshold, skip this NGO demand entirely
                if matched_count == 0:
                    continue

                # 4-Factor Scoring Computations:
                # Factor A: Item Type Match (diluted by number of donation items to prevent false 100% scores)
                item_match_score = (total_similarity / len(donation.items)) * 100.0

                # Factor B: Quantity Fit
                quantity_fit_score = qty_fit_sum / matched_count

                # Factor C: Geographic Proximity Falling back to deterministic matching
                if donor_profile.city.lower() == ngo_profile.city.lower():
                    geographic_score = 100.0
                    reasons.append("✓ Location: Donor and NGO are in the same city")
                elif donor_profile.state.lower() == ngo_profile.state.lower():
                    geographic_score = 70.0
                    reasons.append("✓ Location: Donor and NGO are in the same state")
                else:
                    geographic_score = 30.0
                    reasons.append("✓ Location: Distance requires transit cross-state")

                # Factor D: NGO Priority Level
                priority_map = {
                    "URGENT": 100.0,
                    "HIGH": 80.0,
                    "MEDIUM": 55.0,
                    "LOW": 30.0
                }
                priority_score = priority_map.get(demand.priority.upper(), 55.0)
                reasons.append(f"✓ Urgency: Demand is marked as {demand.priority} priority")

                # Final Composite score matching weights config (45/20/20/15)
                final_score = (
                    settings.WEIGHT_ITEM_MATCH * item_match_score +
                    settings.WEIGHT_QUANTITY_FIT * quantity_fit_score +
                    settings.WEIGHT_GEOGRAPHIC * geographic_score +
                    settings.WEIGHT_PRIORITY * priority_score
                )

                # Skip matches below minimum threshold
                if final_score < settings.MATCH_MIN_SCORE:
                    continue

                # Persist or update the match record
                match_record = db.query(models.DonationMatch).filter(
                    and_(
                        models.DonationMatch.donation_id == donation.id,
                        models.DonationMatch.ngo_id == ngo_profile.id,
                        models.DonationMatch.demand_id == demand.id
                    )
                ).first()

                if not match_record:
                    match_record = models.DonationMatch(
                        donation_id=donation.id,
                        ngo_id=ngo_profile.id,
                        tenant_id=demand.tenant_id,
                        demand_id=demand.id,
                        status="ACTIVE"
                    )

                match_record.final_score = round(final_score, 2)
                match_record.item_match_score = round(item_match_score, 2)
                match_record.quantity_fit_score = round(quantity_fit_score, 2)
                match_record.geographic_score = round(geographic_score, 2)
                match_record.priority_score = round(priority_score, 2)
                match_record.matched_items_count = matched_count
                match_record.match_explanation = json.dumps({
                    "matched_items": matched_items_list,
                    "reasons": reasons
                })
                db.add(match_record)
                db.flush()

                # Trigger dynamic notification if qualifying notification threshold
                if final_score >= settings.MATCH_NOTIFICATION_THRESHOLD:
                    # Deduplication check: check if notification already exists
                    dup_check = db.query(models.Notification).filter(
                        and_(
                            models.Notification.user_id == ngo_profile.user_id,
                            models.Notification.type == "MATCH",
                            models.Notification.related_request_id == donation.id
                        )
                    ).first()

                    if not dup_check:
                        logger.info(f"Creating notification for NGO user {ngo_profile.user_id} for donation {donation.id}")
                        items_str = ", ".join([f"{it['donated_quantity']} {it['donated_item']}" for it in matched_items_list])
                        msg = f"A donor submitted items matching your demand '{demand.title}' (Score: {int(final_score)}%). Match items: {items_str}."
                        
                        notification = models.Notification(
                            user_id=ngo_profile.user_id,
                            title="New compatible donation available",
                            message=msg,
                            type="MATCH",
                            related_request_id=donation.id
                        )
                        db.add(notification)

            db.commit()
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error during matching algorithm run: {e}", exc_info=True)
            return False
