import unittest
import sys
import datetime
import json
import random
from sqlalchemy.orm import Session

# Add backend directory to path
sys.path.append(".")

from database import SessionLocal
import models
from services.matching_service import MatchingService, SentenceTransformerSingleton
from config import settings

class TestSemanticMatching(unittest.TestCase):
    def setUp(self):
        self.db: Session = SessionLocal()
        
        # Create unique usernames for test isolation
        suffix = random.randint(1000, 9999)
        self.donor_email = f"test_donor_{suffix}@matching.com"
        self.ngo_email = f"test_ngo_{suffix}@matching.com"
        self.org_name = f"Matching NGO {suffix}"
        self.reg_num = f"REG/{suffix}"

        # 1. Seed Tenant
        self.tenant = models.Tenant(name=f"Tenant {suffix}", slug=f"tenant-{suffix}")
        self.db.add(self.tenant)
        self.db.flush()

        # 2. Seed Donor User & Profile
        self.donor_user = models.User(email=self.donor_email, password_hash="dummy_hash", role=models.UserRole.DONOR)
        self.db.add(self.donor_user)
        self.db.flush()

        self.donor_profile = models.DonorProfile(
            user_id=self.donor_user.id,
            full_name="Test Donor",
            phone="1234567890",
            city="Vijayawada",
            state="Andhra Pradesh"
        )
        self.db.add(self.donor_profile)

        # 3. Seed NGO User & Profile
        self.ngo_user = models.User(email=self.ngo_email, password_hash="dummy_hash", role=models.UserRole.NGO)
        self.db.add(self.ngo_user)
        self.db.flush()

        self.ngo_profile = models.NGOProfile(
            tenant_id=self.tenant.id,
            user_id=self.ngo_user.id,
            organization_name=self.org_name,
            registration_number=self.reg_num,
            contact_person="Test NGO contact",
            phone="0987654321",
            address="1 NGO Street",
            city="Vijayawada",
            state="Andhra Pradesh",
            mission="Testing semantic matching logic."
        )
        self.db.add(self.ngo_profile)
        self.db.commit()

    def tearDown(self):
        # Cleanup database records created for this test case
        try:
            # Delete donor user, NGO user, and tenant (cascades to profiles, focus areas, matches, requests)
            self.db.query(models.User).filter(models.User.id.in_([self.donor_user.id, self.ngo_user.id])).delete(synchronize_session=False)
            self.db.query(models.Tenant).filter(models.Tenant.id == self.tenant.id).delete(synchronize_session=False)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"TearDown cleanup error: {e}")
        finally:
            self.db.close()

    def test_01_text_normalization(self):
        print("\n--- Test 01: Text Normalization ---")
        norm1 = MatchingService.normalize_text("Mathematics Textbooks", "Books")
        norm2 = MatchingService.normalize_text("mathematics textbook", "books")
        print(f"Norm 1: '{norm1}'")
        print(f"Norm 2: '{norm2}'")
        self.assertEqual(norm1, norm2)

    def test_02_ngo_foreign_key_correctness(self):
        print("\n--- Test 02: NGO Foreign Key Correctness ---")
        # Creating a match row to verify donation_matches.ngo_id maps to ngo_profiles.id
        donation = models.Donation(donor_id=self.donor_user.id, status="ITEMS_SUBMITTED")
        self.db.add(donation)
        self.db.flush()

        demand = models.NGODemand(
            tenant_id=self.tenant.id,
            ngo_id=self.ngo_user.id,
            title="Supplies",
            priority="HIGH",
            status="OPEN",
            city="Vijayawada"
        )
        self.db.add(demand)
        self.db.flush()

        match = models.DonationMatch(
            donation_id=donation.id,
            ngo_id=self.ngo_profile.id, # Must map to NGOProfile.id, not User.id
            tenant_id=self.tenant.id,
            demand_id=demand.id,
            final_score=85.0,
            item_match_score=90.0,
            quantity_fit_score=80.0,
            geographic_score=100.0,
            priority_score=80.0,
            matched_items_count=1,
            match_explanation="{}",
            status="ACTIVE"
        )
        self.db.add(match)
        self.db.commit()
        
        # Verify from database
        persisted = self.db.query(models.DonationMatch).filter(models.DonationMatch.id == match.id).first()
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.ngo_id, self.ngo_profile.id)
        print("Verified DonationMatch.ngo_id maps successfully to NGOProfile.id!")

    def test_03_condition_incompatibility(self):
        print("\n--- Test 03: Condition Incompatibility Penalty ---")
        donation = models.Donation(donor_id=self.donor_user.id, status="ITEMS_SUBMITTED")
        self.db.add(donation)
        self.db.flush() # Flush to populate donation.id
        
        # Donated item is POOR
        item = models.DonationItem(
            donation_id=donation.id,
            item_name="Notebook",
            category="Education",
            quantity=10,
            condition="POOR",
            source="MANUAL"
        )
        self.db.add(item)
        self.db.flush()

        # Demand acceptable condition is only NEW and GOOD
        demand = models.NGODemand(
            tenant_id=self.tenant.id,
            ngo_id=self.ngo_user.id,
            title="School Needs",
            priority="HIGH",
            status="OPEN",
            city="Vijayawada"
        )
        self.db.add(demand)
        self.db.flush()

        dem_item = models.NGODemandItem(
            demand_id=demand.id,
            item_name="Notebook",
            category="Education",
            quantity_needed=10,
            minimum_condition="NEW,GOOD"
        )
        self.db.add(dem_item)
        self.db.commit()

        # Run matching
        success = MatchingService.run_matching(self.db, donation)
        self.assertTrue(success)

        # Retrieve matches
        match = self.db.query(models.DonationMatch).filter(
            models.DonationMatch.donation_id == donation.id,
            models.DonationMatch.demand_id == demand.id
        ).first()

        # The penalty (0.4 multiplier) will drop similarity (1.0 * 0.4 = 0.4)
        # since it is below 0.65 threshold, it shouldn't produce a match!
        self.assertIsNone(match)
        print("Incompatible condition correctly excluded matching candidates!")

    def test_04_expired_demand_exclusion(self):
        print("\n--- Test 04: Expired Demand Exclusion ---")
        donation = models.Donation(donor_id=self.donor_user.id, status="ITEMS_SUBMITTED")
        self.db.add(donation)
        self.db.flush() # Flush to populate donation.id

        item = models.DonationItem(
            donation_id=donation.id,
            item_name="Notebook",
            category="Education",
            quantity=10,
            condition="GOOD",
            source="MANUAL"
        )
        self.db.add(item)
        self.db.flush()

        # Demand expired yesterday
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        demand = models.NGODemand(
            tenant_id=self.tenant.id,
            ngo_id=self.ngo_user.id,
            title="Expired Needs",
            priority="HIGH",
            status="OPEN",
            city="Vijayawada",
            needed_by_date=yesterday
        )
        self.db.add(demand)
        self.db.flush()

        dem_item = models.NGODemandItem(
            demand_id=demand.id,
            item_name="Notebook",
            category="Education",
            quantity_needed=10
        )
        self.db.add(dem_item)
        self.db.commit()

        MatchingService.run_matching(self.db, donation)
        match = self.db.query(models.DonationMatch).filter(
            models.DonationMatch.donation_id == donation.id,
            models.DonationMatch.demand_id == demand.id
        ).first()

        self.assertIsNone(match)
        print("Expired demand correctly excluded from matching candidates!")

    def test_05_fully_satisfied_demand_exclusion(self):
        print("\n--- Test 05: Fully Satisfied Demand Exclusion ---")
        donation = models.Donation(donor_id=self.donor_user.id, status="ITEMS_SUBMITTED")
        self.db.add(donation)
        self.db.flush() # Flush to populate donation.id

        item = models.DonationItem(
            donation_id=donation.id,
            item_name="Notebook",
            category="Education",
            quantity=10,
            condition="GOOD",
            source="MANUAL"
        )
        self.db.add(item)
        self.db.flush()

        # Demand is fully satisfied (quantity_needed = 10, quantity_fulfilled = 10)
        demand = models.NGODemand(
            tenant_id=self.tenant.id,
            ngo_id=self.ngo_user.id,
            title="Satisfied Needs",
            priority="HIGH",
            status="OPEN",
            city="Vijayawada"
        )
        self.db.add(demand)
        self.db.flush()

        dem_item = models.NGODemandItem(
            demand_id=demand.id,
            item_name="Notebook",
            category="Education",
            quantity_needed=10,
            quantity_fulfilled=10
        )
        self.db.add(dem_item)
        self.db.commit()

        MatchingService.run_matching(self.db, donation)
        match = self.db.query(models.DonationMatch).filter(
            models.DonationMatch.donation_id == donation.id,
            models.DonationMatch.demand_id == demand.id
        ).first()

        self.assertIsNone(match)
        print("Fully satisfied demand correctly excluded from matching candidates!")

    def test_06_diluted_score_multiple_items(self):
        print("\n--- Test 06: Multiple Items Dilution Check ---")
        donation = models.Donation(donor_id=self.donor_user.id, status="ITEMS_SUBMITTED")
        self.db.add(donation)
        self.db.flush() # Flush to populate donation.id
        
        # Donor has 3 items, but only 1 matches the NGO demand
        item1 = models.DonationItem(donation_id=donation.id, item_name="Notebook", category="Education", quantity=10, condition="GOOD", source="MANUAL")
        item2 = models.DonationItem(donation_id=donation.id, item_name="Spoon", category="Kitchen", quantity=10, condition="GOOD", source="MANUAL")
        item3 = models.DonationItem(donation_id=donation.id, item_name="Towel", category="Household", quantity=10, condition="GOOD", source="MANUAL")
        self.db.add_all([item1, item2, item3])
        self.db.flush()

        demand = models.NGODemand(
            tenant_id=self.tenant.id,
            ngo_id=self.ngo_user.id,
            title="Dilution Test",
            priority="HIGH",
            status="OPEN",
            city="Vijayawada"
        )
        self.db.add(demand)
        self.db.flush()

        dem_item = models.NGODemandItem(
            demand_id=demand.id,
            item_name="Notebook",
            category="Education",
            quantity_needed=10
        )
        self.db.add(dem_item)
        self.db.commit()

        MatchingService.run_matching(self.db, donation)
        match = self.db.query(models.DonationMatch).filter(
            models.DonationMatch.donation_id == donation.id,
            models.DonationMatch.demand_id == demand.id
        ).first()

        self.assertIsNotNone(match)
        # Item match score should be around 33.3% because only 1 of 3 items matched
        print(f"Item match score: {match.item_match_score} (Expected: ~33.3)")
        self.assertAlmostEqual(match.item_match_score, 33.33, delta=2.0)

    def test_07_duplicate_notification_deduplication(self):
        print("\n--- Test 07: Duplicate Notification Deduplication ---")
        donation = models.Donation(donor_id=self.donor_user.id, status="ITEMS_SUBMITTED")
        self.db.add(donation)
        self.db.flush() # Flush to populate donation.id

        item = models.DonationItem(donation_id=donation.id, item_name="Notebook", category="Education", quantity=10, condition="GOOD", source="MANUAL")
        self.db.add(item)
        self.db.flush()

        demand = models.NGODemand(
            tenant_id=self.tenant.id,
            ngo_id=self.ngo_user.id,
            title="Deduplication Test",
            priority="HIGH",
            status="OPEN",
            city="Vijayawada"
        )
        self.db.add(demand)
        self.db.flush()

        dem_item = models.NGODemandItem(
            demand_id=demand.id,
            item_name="Notebook",
            category="Education",
            quantity_needed=10
        )
        self.db.add(dem_item)
        self.db.commit()

        # Run matching first time (creates notification since priority is HIGH, geo same city, score > 75)
        MatchingService.run_matching(self.db, donation)
        notifs_count1 = self.db.query(models.Notification).filter(
            models.Notification.user_id == self.ngo_user.id,
            models.Notification.type == "MATCH"
        ).count()
        print(f"Notifications after first run: {notifs_count1}")
        self.assertEqual(notifs_count1, 1)

        # Run matching second time
        MatchingService.run_matching(self.db, donation)
        notifs_count2 = self.db.query(models.Notification).filter(
            models.Notification.user_id == self.ngo_user.id,
            models.Notification.type == "MATCH"
        ).count()
        print(f"Notifications after second run: {notifs_count2}")
        self.assertEqual(notifs_count2, 1) # Must remain 1 (no duplicate alerts)

    def test_08_semantic_model_unavailable(self):
        print("\n--- Test 08: Semantic Model Unavailable Check ---")
        # Save old model name and singleton state
        old_model_name = settings.EMBEDDING_MODEL_NAME
        singleton = SentenceTransformerSingleton()
        old_model = singleton._model
        
        # Override settings to a dummy model that will fail to load, and reset cached model
        settings.EMBEDDING_MODEL_NAME = "invalid-dummy-model-name-xyz"
        singleton._model = None
        
        try:
            donation = models.Donation(donor_id=self.donor_user.id, status="ITEMS_SUBMITTED")
            self.db.add(donation)
            self.db.flush() # Flush to populate donation.id

            item = models.DonationItem(donation_id=donation.id, item_name="Notebook", category="Education", quantity=10, condition="GOOD", source="MANUAL")
            self.db.add(item)
            self.db.commit()

            # Execute matching - should return False because the model fails to load
            success = MatchingService.run_matching(self.db, donation)
            self.assertFalse(success)
            print("Successfully failed gracefully when model is unavailable!")
        finally:
            settings.EMBEDDING_MODEL_NAME = old_model_name
            singleton._model = old_model

    def test_09_embedding_regeneration_on_changed_text(self):
        print("\n--- Test 09: Embedding Regeneration Check ---")
        # 1. Add demand item
        demand = models.NGODemand(
            tenant_id=self.tenant.id,
            ngo_id=self.ngo_user.id,
            title="Text Change Test",
            priority="HIGH",
            status="OPEN",
            city="Vijayawada"
        )
        self.db.add(demand)
        self.db.flush()

        dem_item = models.NGODemandItem(
            demand_id=demand.id,
            item_name="Initial Text",
            category="Education",
            quantity_needed=10
        )
        self.db.add(dem_item)
        self.db.commit()

        # Load first embedding
        normalized_text = MatchingService.normalize_text(dem_item.item_name, dem_item.category)
        emb1 = MatchingService.get_embedding(normalized_text)
        self.assertIsNotNone(emb1)
        
        # Verify different text produces different embedding
        normalized_text2 = MatchingService.normalize_text("Changed Text", dem_item.category)
        emb2 = MatchingService.get_embedding(normalized_text2)
        self.assertNotEqual(emb1[:5], emb2[:5])
        print("Different texts successfully generate distinct embeddings!")


if __name__ == "__main__":
    unittest.main()
