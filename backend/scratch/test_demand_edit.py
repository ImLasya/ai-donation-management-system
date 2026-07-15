import sys
import os
import unittest
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
import models
from services.matching_service import MatchingService
from config import settings

class TestDemandEdit(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        # Find or create a tenant
        tenant = self.db.query(models.Tenant).first()
        if not tenant:
            tenant = models.Tenant(name="Default Edit Test Tenant")
            self.db.add(tenant)
            self.db.flush()
        self.tenant_id = tenant.id
        
        # Test Donor User
        self.donor = models.User(
            email="donor_edit_test@example.com",
            password_hash="fakehash",
            role=models.UserRole.DONOR,
            is_active=True
        )
        self.db.add(self.donor)
        self.db.flush()

        self.donor_profile = models.DonorProfile(
            user_id=self.donor.id,
            full_name="Edit Test Donor",
            phone="1234567890",
            city="Seattle",
            state="WA"
        )
        self.db.add(self.donor_profile)

        # Test NGO User
        self.ngo = models.User(
            email="ngo_edit_test@example.com",
            password_hash="fakehash",
            role=models.UserRole.NGO,
            is_active=True
        )
        self.db.add(self.ngo)
        self.db.flush()

        self.ngo_profile = models.NGOProfile(
            user_id=self.ngo.id,
            tenant_id=self.tenant_id,
            organization_name="Edit Test NGO",
            registration_number="REG-EDIT-TEST",
            contact_person="Edit Person",
            phone="0987654321",
            address="NGO Road",
            city="Seattle",
            state="WA",
            mission="Helper mission"
        )
        self.db.add(self.ngo_profile)
        self.db.commit()

    def tearDown(self):
        # Clean up database records
        test_emails = ["donor_edit_test@example.com", "ngo_edit_test@example.com"]
        
        # Find user IDs
        users = self.db.query(models.User).filter(models.User.email.in_(test_emails)).all()
        user_ids = [u.id for u in users]
        
        if user_ids:
            # Delete notifications
            self.db.query(models.Notification).filter(models.Notification.user_id.in_(user_ids)).delete(synchronize_session=False)
            
            # Find donations
            donations = self.db.query(models.Donation).filter(models.Donation.donor_id.in_(user_ids)).all()
            don_ids = [d.id for d in donations]
            if don_ids:
                self.db.query(models.DonationMatch).filter(models.DonationMatch.donation_id.in_(don_ids)).delete(synchronize_session=False)
                self.db.query(models.DonationStatusHistory).filter(models.DonationStatusHistory.donation_id.in_(don_ids)).delete(synchronize_session=False)
                self.db.query(models.DonationItem).filter(models.DonationItem.donation_id.in_(don_ids)).delete(synchronize_session=False)
                self.db.query(models.Donation).filter(models.Donation.id.in_(don_ids)).delete(synchronize_session=False)

            # Find demands
            demands = self.db.query(models.NGODemand).filter(models.NGODemand.ngo_id.in_(user_ids)).all()
            dem_ids = [dem.id for dem in demands]
            if dem_ids:
                self.db.query(models.NGODemandItem).filter(models.NGODemandItem.demand_id.in_(dem_ids)).delete(synchronize_session=False)
                self.db.query(models.NGODemand).filter(models.NGODemand.id.in_(dem_ids)).delete(synchronize_session=False)
                
            self.db.query(models.DonorProfile).filter(models.DonorProfile.user_id.in_(user_ids)).delete(synchronize_session=False)
            self.db.query(models.NGOProfile).filter(models.NGOProfile.user_id.in_(user_ids)).delete(synchronize_session=False)
            self.db.query(models.User).filter(models.User.id.in_(user_ids)).delete(synchronize_session=False)
            self.db.commit()
            
        self.db.close()

    def test_demand_edit_flow(self):
        print("\n--- Starting test_demand_edit_flow ---")
        
        # 1. Create a demand for "Book" under category "Education"
        print("1. Creating original demand...")
        demand = models.NGODemand(
            tenant_id=self.tenant_id,
            ngo_id=self.ngo.id,
            title="School Book Demand",
            description="Original description",
            priority="MEDIUM",
            status="OPEN",
            city="Seattle",
            needed_by_date=date(2026, 12, 31)
        )
        self.db.add(demand)
        self.db.flush()

        demand_item = models.NGODemandItem(
            demand_id=demand.id,
            item_name="Book",
            category="Education",
            quantity_needed=5,
            quantity_fulfilled=0,
            minimum_condition="GOOD"
        )
        self.db.add(demand_item)
        self.db.commit()

        # Generate original embedding manually for the test baseline
        norm_text = MatchingService.normalize_text(demand_item.item_name, demand_item.category)
        demand_item.embedding = MatchingService.get_embedding(norm_text)
        self.db.add(demand_item)
        self.db.commit()

        self.db.refresh(demand_item)
        
        orig_embedding = demand_item.embedding
        self.assertIsNotNone(orig_embedding, "Original embedding should have been generated")
        print(f"Original embedding loaded, length: {len(orig_embedding) if orig_embedding else 0}")

        # 2. Create a waiting donor donation for "School Book" (semantic similarity but not exact)
        print("2. Creating waiting donation for 'School Book'...")
        donation = models.Donation(
            donor_id=self.donor.id,
            status="WAITING_FOR_MATCH"
        )
        self.db.add(donation)
        self.db.flush()

        donation_item = models.DonationItem(
            donation_id=donation.id,
            item_name="School Book",
            category="Education",
            quantity=5,
            condition="GOOD",
            confidence_score=0.95,
            source="AI"
        )
        self.db.add(donation_item)
        self.db.commit()

        # Run initial matching for donation (should fail to match well, or remain WAITING)
        MatchingService.run_matching(self.db, donation)
        self.db.refresh(donation)
        
        # Wait, does "School Book" match "Book"? Let's check similarity. 
        # In case it matches, let's look at the matches. If it doesn't match above 60%, status remains WAITING.
        active_matches = self.db.query(models.DonationMatch).filter(
            models.DonationMatch.donation_id == donation.id,
            models.DonationMatch.status == "ACTIVE"
        ).count()
        print(f"Active matches found before edit: {active_matches}, donation status: {donation.status}")

        # Let's perform a demand edit. NGO updates demand:
        # Title -> "School Supplies", Priority -> "HIGH", Item Name -> "School Book" (exact match to donation)
        # Quantity Needed -> 10, Acceptable conditions -> "NEW,GOOD"
        print("3. Simulating demand edit payload...")
        payload = {
            "title": "School Supplies",
            "priority": "HIGH",
            "needed_by_date": date(2026, 12, 31),
            "description": "Updated description",
            "status": "Active",
            "items": [
                {
                    "id": demand_item.id,
                    "item_name": "School Book", # Name changed!
                    "category": "Education",
                    "quantity_needed": 10, # Qty changed!
                    "acceptable_conditions": ["NEW", "GOOD"]
                }
            ]
        }

        # Simulating donation_routes.py PUT /demands/{demand_id} logic:
        # Load demand with_for_update
        demand_to_edit = self.db.query(models.NGODemand).filter(models.NGODemand.id == demand.id).with_for_update().first()
        self.assertIsNotNone(demand_to_edit)

        demand_to_edit.title = payload["title"]
        demand_to_edit.priority = payload["priority"]
        demand_to_edit.description = payload["description"]
        demand_to_edit.needed_by_date = payload["needed_by_date"]
        demand_to_edit.updated_at = func.now()

        trigger_rematch = True
        db_items = {it.id: it for it in demand_to_edit.items}
        payload_ids = set()

        for item_payload in payload["items"]:
            item_id = item_payload.get("id")
            min_cond = ",".join(item_payload["acceptable_conditions"])
            new_name = item_payload["item_name"].strip()
            new_category = item_payload["category"]
            new_qty = item_payload["quantity_needed"]

            db_item = db_items.get(item_id)
            if db_item:
                payload_ids.add(db_item.id)
                # Check name/category changes for embedding regeneration
                if db_item.item_name != new_name or db_item.category != new_category:
                    db_item.embedding = None
                    normalized_text = MatchingService.normalize_text(new_name, new_category)
                    emb = MatchingService.get_embedding(normalized_text)
                    if emb:
                        db_item.embedding = emb
                    trigger_rematch = True

                db_item.item_name = new_name
                db_item.category = new_category
                db_item.quantity_needed = new_qty
                db_item.minimum_condition = min_cond
                self.db.add(db_item)

        # Commit edit
        self.db.commit()
        print("Demand edit committed successfully.")

        # Refresh objects
        self.db.refresh(demand_item)
        self.db.refresh(demand)

        # Assert audit trail timestamp was updated
        self.assertIsNotNone(demand.updated_at)
        
        # Assert embedding was updated/regenerated
        new_embedding = demand_item.embedding
        self.assertIsNotNone(new_embedding, "New embedding should have been generated")
        self.assertNotEqual(orig_embedding, new_embedding, "Embedding should have changed after item name edit")
        print("Verified: original embedding and new embedding are different!")

        # 4. Trigger background re-matching task
        print("4. Triggering re-matching after edit...")
        if trigger_rematch and demand.status == "OPEN":
            MatchingService.run_rematching_for_demand(self.db, demand.id)
            self.db.commit()

        # 5. Assert waiting donation has now transitioned status & matched!
        self.db.refresh(donation)
        print(f"Waiting donation status after demand edit and rematch: {donation.status}")
        
        # Check if matched
        new_active_matches = self.db.query(models.DonationMatch).filter(
            models.DonationMatch.donation_id == donation.id,
            models.DonationMatch.status == "ACTIVE"
        ).count()
        print(f"Active matches found after edit: {new_active_matches}")
        
        # The donation should have matched and transitioned to ITEMS_SUBMITTED
        self.assertGreater(new_active_matches, 0, "Should find at least 1 active match after demand item edit")
        
        # Verify transition occurred
        self.assertEqual(donation.status, "ITEMS_SUBMITTED", "Donation should have transitioned from WAITING_FOR_MATCH to ITEMS_SUBMITTED")
        print("SUCCESS: All edit, embedding, timestamp and re-matching assertions passed successfully!")

if __name__ == "__main__":
    unittest.main()
