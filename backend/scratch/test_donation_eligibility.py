import sys
import os
import unittest
from sqlalchemy.orm import Session

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
import models
from services.donation_eligibility_service import DonationEligibilityService
from services.matching_service import MatchingService
from routes.detection_routes import analyze_image

class TestDonationEligibility(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        # Clean up any potential database records created during test
        test_emails = ["donor_elig_test@example.com", "ngo_elig_test@example.com"]
        self.db.query(models.User).filter(models.User.email.in_(test_emails)).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_individual_classifications(self):
        print("\n--- Running classification tests ---")
        
        # Test non-donatables
        self.assertEqual(DonationEligibilityService.classify_detection("person"), "NON_DONATABLE")
        self.assertEqual(DonationEligibilityService.classify_detection("tree"), "NON_DONATABLE")
        self.assertEqual(DonationEligibilityService.classify_detection("cloud"), "NON_DONATABLE")
        self.assertEqual(DonationEligibilityService.classify_detection("sky"), "NON_DONATABLE")
        self.assertEqual(DonationEligibilityService.classify_detection("car"), "NON_DONATABLE")
        self.assertEqual(DonationEligibilityService.classify_detection("cat"), "NON_DONATABLE")

        # Test donatables
        self.assertEqual(DonationEligibilityService.classify_detection("book"), "DONATABLE")
        self.assertEqual(DonationEligibilityService.classify_detection("bottle"), "DONATABLE")
        self.assertEqual(DonationEligibilityService.classify_detection("cell phone"), "DONATABLE")
        self.assertEqual(DonationEligibilityService.classify_detection("backpack"), "DONATABLE")
        self.assertEqual(DonationEligibilityService.classify_detection("couch"), "DONATABLE")
        self.assertEqual(DonationEligibilityService.classify_detection("banana"), "DONATABLE")
        self.assertEqual(DonationEligibilityService.classify_detection("orange"), "DONATABLE")

        # Test categories
        self.assertEqual(DonationEligibilityService.get_donation_category("cell phone"), "Electronics")
        self.assertEqual(DonationEligibilityService.get_donation_category("book"), "Books")
        self.assertEqual(DonationEligibilityService.get_donation_category("backpack"), "Education")
        self.assertEqual(DonationEligibilityService.get_donation_category("banana"), "Food")
        self.assertEqual(DonationEligibilityService.get_donation_category("orange"), "Food")

        # Test unknown class (neither explicitly in donatable or non-donatable)
        # e.g., "remote", "microwave", "xyz"
        self.assertEqual(DonationEligibilityService.classify_detection("remote"), "REVIEW_REQUIRED")
        self.assertEqual(DonationEligibilityService.classify_detection("unknown_random_object"), "REVIEW_REQUIRED")

        print("Classification tests: PASSED")

    def test_quantity_grouping_and_rejection_split(self):
        print("\n--- Running quantity grouping and split tests ---")

        # Simulate a list of detections returned from YOLO
        mock_raw_classes = ["person", "book", "book", "book", "bottle", "bottle", "chair", "tree", "remote"]
        raw_detections = []
        donatable_detections = []
        rejected_detections = []

        for idx, cls in enumerate(mock_raw_classes):
            norm = DonationEligibilityService.normalize_label(cls)
            status = DonationEligibilityService.classify_detection(cls)
            category = DonationEligibilityService.get_donation_category(cls)
            reason = DonationEligibilityService.get_rejection_reason(cls)
            display_label = DonationEligibilityService.get_display_label(cls)

            det_data = {
                "id": f"det-{idx}",
                "class_id": idx,
                "label": display_label,
                "normalized_label": norm,
                "confidence": 0.9,
                "bbox": {"x1": 10, "y1": 10, "x2": 50, "y2": 50},
                "eligibility_status": status,
                "donation_category": category,
                "rejection_reason": reason
            }

            raw_detections.append(det_data)
            if status == "DONATABLE":
                donatable_detections.append(det_data)
            else:
                rejected_detections.append(det_data)

        # 1. Verify split list lengths
        # 3 books, 2 bottles, 1 chair = 6 donatable
        # 1 person, 1 tree, 1 remote = 3 rejected
        self.assertEqual(len(donatable_detections), 6)
        self.assertEqual(len(rejected_detections), 3)

        # 2. Group items ONLY from donatables
        grouped = {}
        for det in donatable_detections:
            name = det["label"]
            if name not in grouped:
                grouped[name] = {
                    "item_name": name,
                    "category": det["donation_category"],
                    "count": 0,
                }
            grouped[name]["count"] += 1

        # Assert Person, Tree, Remote are NOT in grouped items
        self.assertNotIn("Person", grouped)
        self.assertNotIn("Tree", grouped)
        self.assertNotIn("Remote Control", grouped)  # Remote control needs review, not auto-donatable

        # Assert correct quantity for donatables
        self.assertEqual(grouped["Book"]["count"], 3)
        self.assertEqual(grouped["Bottle"]["count"], 2)
        self.assertEqual(grouped["Chair"]["count"], 1)

        print("Quantity grouping and split tests: PASSED")

    def test_database_submission_protection_and_matching(self):
        print("\n--- Running database submission & matching tests ---")

        # 1. Create a mock donor user and NGO
        donor = models.User(
            email="donor_elig_test@example.com",
            password_hash="pw",
            role=models.UserRole.DONOR,
            is_active=True
        )
        ngo = models.User(
            email="ngo_elig_test@example.com",
            password_hash="pw",
            role=models.UserRole.NGO,
            is_active=True
        )
        self.db.add_all([donor, ngo])
        self.db.flush()

        # Add profile for NGO
        ngo_profile = models.NGOProfile(
            user_id=ngo.id,
            organization_name="Eligibility NGO",
            registration_number="REG-ELIG",
            contact_person="Elig Person",
            phone="000",
            address="Addr",
            city="Bengaluru",
            state="Karnataka",
            mission="Test mission"
        )
        donor_profile = models.DonorProfile(
            user_id=donor.id,
            full_name="Elig Donor",
            phone="111",
            city="Bengaluru",
            state="Karnataka"
        )
        self.db.add_all([ngo_profile, donor_profile])
        self.db.flush()

        # 2. Check insertion logic using DonationEligibilityService directly
        # Simulate items received from payload
        items_payload = [
            {"item_name": "book", "category": "Books", "quantity": 3, "is_confirmed": False},
            {"item_name": "person", "category": "Other", "quantity": 1, "is_confirmed": False},
            {"item_name": "remote", "category": "Electronics", "quantity": 1, "is_confirmed": False},
            {"item_name": "remote", "category": "Electronics", "quantity": 1, "is_confirmed": True}, # Confirmed review item
        ]

        # Verify that person gets rejected
        with self.assertRaises(ValueError) as context_rejection:
            for item in items_payload:
                status = DonationEligibilityService.classify_detection(item["item_name"])
                if status == "NON_DONATABLE":
                    raise ValueError(f"Rejection: {item['item_name']} is non-donatable")
        self.assertIn("person is non-donatable", str(context_rejection.exception))

        # Verify that unconfirmed review required item gets rejected
        with self.assertRaises(ValueError) as context_unconfirmed:
            for item in items_payload:
                # Skip person to test next validation
                if item["item_name"] == "person":
                    continue
                status = DonationEligibilityService.classify_detection(item["item_name"])
                if status == "REVIEW_REQUIRED" and not item["is_confirmed"]:
                    raise ValueError(f"Confirmation required for {item['item_name']}")
        self.assertIn("Confirmation required for remote", str(context_unconfirmed.exception))

        # 3. Verify matching skipped logic
        # Create a donation with one donatable and one non-donatable item manually inserted to test MatchingService bypass
        donation = models.Donation(
            donor_id=donor.id,
            status="ITEMS_SUBMITTED"
        )
        self.db.add(donation)
        self.db.flush()

        valid_item = models.DonationItem(
            donation_id=donation.id,
            item_name="book",
            category="Books",
            quantity=2,
            condition="Good",
            source="AI"
        )
        invalid_item = models.DonationItem(
            donation_id=donation.id,
            item_name="person",
            category="Other",
            quantity=1,
            condition="Good",
            source="AI"
        )
        self.db.add_all([valid_item, invalid_item])
        self.db.commit()

        # Run embedding step simulated in MatchingService
        # Non-donatable should NOT receive embedding
        MatchingService.run_matching(self.db, donation)
        self.db.refresh(valid_item)
        self.db.refresh(invalid_item)

        # Valid item should have embedding generated (if embedding model is available, otherwise None)
        # Invalid item MUST remain with None embedding
        self.assertIsNone(invalid_item.embedding, "Rejected items must never receive embeddings")

        print("Database submission protection and matching tests: PASSED")

if __name__ == "__main__":
    unittest.main()
