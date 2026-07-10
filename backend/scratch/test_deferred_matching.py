import sys
import os
import unittest
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
import models
from services.matching_service import MatchingService
from config import settings

class TestDeferredMatching(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        # Find or create a tenant
        tenant = self.db.query(models.Tenant).first()
        if not tenant:
            tenant = models.Tenant(name="Default Defer Tenant")
            self.db.add(tenant)
            self.db.flush()
        self.tenant_id = tenant.id
        
        # Test Donor User
        self.donor = models.User(
            email="donor_defer_test@example.com",
            password_hash="fakehash",
            role=models.UserRole.DONOR,
            is_active=True
        )
        self.db.add(self.donor)
        self.db.flush()

        self.donor_profile = models.DonorProfile(
            user_id=self.donor.id,
            full_name="Deferred Test Donor",
            phone="1234567890",
            city="Seattle",
            state="WA"
        )
        self.db.add(self.donor_profile)

        # Test NGO User
        self.ngo = models.User(
            email="ngo_defer_test@example.com",
            password_hash="fakehash",
            role=models.UserRole.NGO,
            is_active=True
        )
        self.db.add(self.ngo)
        self.db.flush()

        self.ngo_profile = models.NGOProfile(
            user_id=self.ngo.id,
            tenant_id=self.tenant_id,
            organization_name="Deferred Test NGO",
            registration_number="REG-DEFER-TEST",
            contact_person="Defer Person",
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
        test_emails = ["donor_defer_test@example.com", "ngo_defer_test@example.com"]
        
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
        
        # Clean up default tenant if we created it
        test_tenant = self.db.query(models.Tenant).filter(models.Tenant.name == "Default Defer Tenant").first()
        if test_tenant:
            self.db.delete(test_tenant)
            self.db.commit()
            
        self.db.close()

    def test_deferred_matching_workflow(self):
        print("\n--- Testing Deferred Matching workflow ---")
        
        # 1. Create a donation with NO matching demands initially
        # We use a highly unique item to avoid matching other existing database demands
        donation = models.Donation(
            donor_id=self.donor.id,
            status="ITEMS_SUBMITTED"
        )
        self.db.add(donation)
        self.db.flush()

        item = models.DonationItem(
            donation_id=donation.id,
            item_name="vintage wooden widget",
            category="Household",
            quantity=1,
            condition="Good",
            source="AI"
        )
        self.db.add(item)
        self.db.commit()

        # Run initial matching
        MatchingService.run_matching(self.db, donation)
        self.db.refresh(donation)

        # Check active matches count
        active_matches = self.db.query(models.DonationMatch).filter(
            models.DonationMatch.donation_id == donation.id,
            models.DonationMatch.status.in_(["ACTIVE", "NOTIFIED"]),
            models.DonationMatch.final_score >= settings.MATCH_MIN_SCORE
        ).count()

        self.assertEqual(active_matches, 0)
        
        # Simulating donation_routes create transition
        if active_matches == 0:
            donation.status = "WAITING_FOR_MATCH"
            self.db.add(donation)
            self.db.commit()

        self.assertEqual(donation.status, "WAITING_FOR_MATCH")

        # 2. NGO creates a compatible demand
        demand = models.NGODemand(
            tenant_id=self.tenant_id,
            ngo_id=self.ngo.id,
            title="Need vintage wooden widgets",
            description="Looking for vintage wooden widgets.",
            priority="HIGH",
            status="OPEN",
            city="Seattle"
        )
        self.db.add(demand)
        self.db.flush()

        demand_item = models.NGODemandItem(
            demand_id=demand.id,
            item_name="vintage wooden widget",
            category="Household",
            quantity_needed=5,
            quantity_fulfilled=0,
            minimum_condition="Good"
        )
        self.db.add(demand_item)
        self.db.commit()

        # Trigger re-matching for this demand
        success = MatchingService.run_rematching_for_demand(self.db, demand.id)
        self.assertTrue(success)

        # Verify donation transitioned to ITEMS_SUBMITTED
        self.db.refresh(donation)
        self.assertEqual(donation.status, "ITEMS_SUBMITTED")

        # Verify a match record was created
        match = self.db.query(models.DonationMatch).filter(
            models.DonationMatch.donation_id == donation.id,
            models.DonationMatch.demand_id == demand.id
        ).first()
        self.assertIsNotNone(match)
        self.assertTrue(match.final_score >= settings.MATCH_MIN_SCORE)

        # Verify status history row is logged
        history = self.db.query(models.DonationStatusHistory).filter(
            models.DonationStatusHistory.donation_id == donation.id,
            models.DonationStatusHistory.new_status == "ITEMS_SUBMITTED"
        ).first()
        self.assertIsNotNone(history)
        self.assertIn("Future match found", history.note)

        # Verify notifications created
        ngo_notif = self.db.query(models.Notification).filter(
            models.Notification.user_id == self.ngo.id,
            models.Notification.type == "MATCH"
        ).first()
        self.assertIsNotNone(ngo_notif)
        self.assertIn("FUTURE_MATCH_NGO", ngo_notif.deduplication_key)

        donor_notif = self.db.query(models.Notification).filter(
            models.Notification.user_id == self.donor.id,
            models.Notification.type == "MATCH"
        ).first()
        self.assertIsNotNone(donor_notif)
        self.assertIn("FUTURE_MATCH_DONOR", donor_notif.deduplication_key)

    def test_expiration_logic(self):
        print("\n--- Testing Expiration Logic ---")
        
        # Create a donation WAITING_FOR_MATCH
        donation = models.Donation(
            donor_id=self.donor.id,
            status="WAITING_FOR_MATCH"
        )
        self.db.add(donation)
        self.db.flush()

        # Backdate it by 31 days (forcing timezone-awareness to match DB datetime(timezone=True))
        donation.created_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=31)
        self.db.add(donation)
        self.db.commit()

        # Run expiration checks
        expired_count = MatchingService.expire_waiting_donations(self.db)
        self.assertEqual(expired_count, 1)

        self.db.refresh(donation)
        self.assertEqual(donation.status, "EXPIRED")

        # Verify history logged
        history = self.db.query(models.DonationStatusHistory).filter(
            models.DonationStatusHistory.donation_id == donation.id,
            models.DonationStatusHistory.new_status == "EXPIRED"
        ).first()
        self.assertIsNotNone(history)
        self.assertIn("expired", history.note.lower())

if __name__ == "__main__":
    unittest.main()
