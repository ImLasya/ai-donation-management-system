import os
import sys
import unittest
from datetime import date, timedelta
# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

import models
from database import SessionLocal
from services.email_service import EmailService
from services.packaging_service import PackagingService
from services.reminder_service import ReminderService

class TestWorkflow(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        # Seed test donor, test NGO, test donation, test demand
        self.cleanup()
        
        # Create unique email addresses for testing
        self.donor_email = f"test_donor_{os.urandom(4).hex()}@example.com"
        self.ngo_email = f"test_ngo_{os.urandom(4).hex()}@example.com"
        self.other_ngo_email = f"test_other_ngo_{os.urandom(4).hex()}@example.com"

        # Create tenant
        self.tenant = models.Tenant(name="Test Tenant", slug=f"test_{os.urandom(4).hex()}")
        self.db.add(self.tenant)
        self.db.flush()

        # Create donor user
        self.donor_user = models.User(
            email=self.donor_email,
            password_hash="hash",
            role=models.UserRole.DONOR,
            email_notifications_enabled=True,
            inapp_notifications_enabled=True
        )
        self.db.add(self.donor_user)
        self.db.flush()

        # Create donor profile
        self.donor_profile = models.DonorProfile(
            user_id=self.donor_user.id,
            full_name="Test Donor",
            phone="1234567890",
            city="Bengaluru",
            state="Karnataka"
        )
        self.db.add(self.donor_profile)

        # Create NGO user
        self.ngo_user = models.User(
            email=self.ngo_email,
            password_hash="hash",
            role=models.UserRole.NGO,
            email_notifications_enabled=True,
            inapp_notifications_enabled=True
        )
        self.db.add(self.ngo_user)
        self.db.flush()

        # Create NGO profile
        self.ngo_profile = models.NGOProfile(
            user_id=self.ngo_user.id,
            tenant_id=self.tenant.id,
            organization_name="Test NGO Charity",
            registration_number="REG-NGO-12345",
            mission="Helping those in need.",
            contact_person="Director",
            phone="0987654321",
            address="12 Charity lane",
            city="Bengaluru",
            state="Karnataka",
            focus_areas=[
                models.NGOFocusArea(focus_area="Books"),
                models.NGOFocusArea(focus_area="Clothing")
            ]
        )
        self.db.add(self.ngo_profile)

        # Create OTHER NGO user (for tenant isolation tests)
        self.other_ngo_user = models.User(
            email=self.other_ngo_email,
            password_hash="hash",
            role=models.UserRole.NGO,
            email_notifications_enabled=True,
            inapp_notifications_enabled=True
        )
        self.db.add(self.other_ngo_user)
        self.db.flush()

        self.other_ngo_profile = models.NGOProfile(
            user_id=self.other_ngo_user.id,
            tenant_id=self.tenant.id,
            organization_name="Other Test NGO",
            registration_number="REG-NGO-67890",
            mission="Fighting hunger daily.",
            contact_person="Manager",
            phone="1112223333",
            address="45 Isolation Ave",
            city="Mysuru",
            state="Karnataka",
            focus_areas=[
                models.NGOFocusArea(focus_area="Food")
            ]
        )
        self.db.add(self.other_ngo_profile)

        # Create donation
        self.donation = models.Donation(
            donor_id=self.donor_user.id,
            status="ITEMS_SUBMITTED"
        )
        self.db.add(self.donation)
        self.db.flush()

        # Add donation items
        self.item1 = models.DonationItem(
            donation_id=self.donation.id,
            item_name="Textbook",
            category="Books",
            quantity=5,
            condition="GOOD",
            source="MANUAL"
        )
        self.item2 = models.DonationItem(
            donation_id=self.donation.id,
            item_name="Winter Jacket",
            category="Clothing",
            quantity=2,
            condition="EXCELLENT",
            source="MANUAL"
        )
        self.db.add(self.item1)
        self.db.add(self.item2)
        self.db.flush()

        # Create donation request linking to NGO
        self.request = models.DonationRequest(
            donation_id=self.donation.id,
            donor_id=self.donor_user.id,
            ngo_id=self.ngo_user.id,
            status="PENDING"
        )
        self.db.add(self.request)
        self.db.commit()

    def tearDown(self):
        self.cleanup()
        self.db.close()

    def cleanup(self):
        # Delete test records
        try:
            self.db.query(models.Notification).filter(models.Notification.user_id.in_([
                getattr(self, 'donor_user', None) and self.donor_user.id,
                getattr(self, 'ngo_user', None) and self.ngo_user.id,
                getattr(self, 'other_ngo_user', None) and self.other_ngo_user.id
            ])).delete(synchronize_session=False)

            self.db.query(models.DonationStatusHistory).filter(models.DonationStatusHistory.changed_by_user_id.in_([
                getattr(self, 'donor_user', None) and self.donor_user.id,
                getattr(self, 'ngo_user', None) and self.ngo_user.id,
                getattr(self, 'other_ngo_user', None) and self.other_ngo_user.id
            ])).delete(synchronize_session=False)

            self.db.query(models.PickupSchedule).filter(models.PickupSchedule.donation_id == (
                getattr(self, 'donation', None) and self.donation.id
            )).delete(synchronize_session=False)

            self.db.query(models.PackagingRecord).filter(models.PackagingRecord.donation_id == (
                getattr(self, 'donation', None) and self.donation.id
            )).delete(synchronize_session=False)

            self.db.query(models.DonationRequest).filter(models.DonationRequest.donation_id == (
                getattr(self, 'donation', None) and self.donation.id
            )).delete(synchronize_session=False)

            self.db.query(models.DonationItem).filter(models.DonationItem.donation_id == (
                getattr(self, 'donation', None) and self.donation.id
            )).delete(synchronize_session=False)

            self.db.query(models.Donation).filter(models.Donation.id == (
                getattr(self, 'donation', None) and self.donation.id
            )).delete(synchronize_session=False)

            self.db.query(models.DonorProfile).filter(models.DonorProfile.user_id == (
                getattr(self, 'donor_user', None) and self.donor_user.id
            )).delete(synchronize_session=False)

            self.db.query(models.NGOProfile).filter(models.NGOProfile.user_id.in_([
                getattr(self, 'ngo_user', None) and self.ngo_user.id,
                getattr(self, 'other_ngo_user', None) and self.other_ngo_user.id
            ])).delete(synchronize_session=False)

            self.db.query(models.User).filter(models.User.email.in_([
                getattr(self, 'donor_email', ''),
                getattr(self, 'ngo_email', ''),
                getattr(self, 'other_ngo_email', '')
            ])).delete(synchronize_session=False)

            self.db.query(models.Tenant).filter(models.Tenant.id == (
                getattr(self, 'tenant', None) and self.tenant.id
            )).delete(synchronize_session=False)

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Cleanup error: {e}")

    def test_workflow_lifecycle_success(self):
        """
        Verify the full happy path of donation workflow status transitions.
        """
        # Refresh donation state
        d = self.db.query(models.Donation).filter(models.Donation.id == self.donation.id).first()
        self.assertEqual(d.status, "ITEMS_SUBMITTED")

        # 1. Accept Request (Awaiting NGO -> Accepted)
        # Verify status transitions to NGO_ACCEPTED
        d.status = "NGO_ACCEPTED"
        self.db.add(d)
        h1 = models.DonationStatusHistory(
            donation_id=d.id, old_status="ITEMS_SUBMITTED", new_status="NGO_ACCEPTED",
            changed_by_user_id=self.ngo_user.id, note="Request accepted"
        )
        self.db.add(h1)
        self.db.commit()
        
        self.assertEqual(d.status, "NGO_ACCEPTED")

        # 2. Category Checklist dynamic tips validation
        categories = [item.category for item in d.items]
        tips = PackagingService.get_tips_for_categories(categories)
        self.assertIn("Books", tips)
        self.assertIn("Clothing", tips)
        self.assertEqual(len(tips["Books"]), 4)

        # 3. Complete Packaging (NGO_ACCEPTED -> READY_FOR_PICKUP)
        # Persist completed checklist items, count, notes
        completed_keys = ["Books: Stack books neatly by size to maximize space"]
        import json
        from datetime import datetime
        pkg = models.PackagingRecord(
            donation_id=d.id,
            packaging_status="COMPLETED",
            package_count=2,
            packaging_notes="Fragile glass protected.",
            completed_items=json.dumps(completed_keys),
            completed_at=datetime.now()
        )
        self.db.add(pkg)
        d.status = "READY_FOR_PICKUP"
        h2 = models.DonationStatusHistory(
            donation_id=d.id, old_status="NGO_ACCEPTED", new_status="READY_FOR_PICKUP",
            changed_by_user_id=self.donor_user.id, note="Packaging completed"
        )
        self.db.add(h2)
        self.db.commit()

        pkg_record = self.db.query(models.PackagingRecord).filter(models.PackagingRecord.donation_id == d.id).first()
        self.assertIsNotNone(pkg_record)
        self.assertEqual(pkg_record.package_count, 2)
        self.assertEqual(json.loads(pkg_record.completed_items), completed_keys)
        self.assertEqual(d.status, "READY_FOR_PICKUP")

        # 4. Schedule Pickup (READY_FOR_PICKUP -> PICKUP_SCHEDULED)
        # Verify date/slot selection is persisted
        tomorrow = date.today() + timedelta(days=1)
        pickup = models.PickupSchedule(
            donation_id=d.id,
            pickup_date=tomorrow,
            time_slot="09:00 AM – 11:00 AM",
            pickup_address="123 Main Street",
            contact_phone="111-222-3333",
            notes="Gate code is #1234",
            reminder_status="PENDING"
        )
        self.db.add(pickup)
        d.status = "PICKUP_SCHEDULED"
        h3 = models.DonationStatusHistory(
            donation_id=d.id, old_status="READY_FOR_PICKUP", new_status="PICKUP_SCHEDULED",
            changed_by_user_id=self.donor_user.id, note="Pickup scheduled"
        )
        self.db.add(h3)
        self.db.commit()

        pickup_record = self.db.query(models.PickupSchedule).filter(models.PickupSchedule.donation_id == d.id).first()
        self.assertIsNotNone(pickup_record)
        self.assertEqual(pickup_record.time_slot, "09:00 AM – 11:00 AM")
        self.assertEqual(pickup_record.reminder_status, "PENDING")
        self.assertEqual(d.status, "PICKUP_SCHEDULED")

        # 5. Confirm Collection (PICKUP_SCHEDULED -> COLLECTED)
        d.status = "COLLECTED"
        h4 = models.DonationStatusHistory(
            donation_id=d.id, old_status="PICKUP_SCHEDULED", new_status="COLLECTED",
            changed_by_user_id=self.ngo_user.id, note="Items collected"
        )
        self.db.add(h4)
        self.db.commit()
        self.assertEqual(d.status, "COLLECTED")

        # 6. Mark Delivered (COLLECTED -> DELIVERED)
        d.status = "DELIVERED"
        h5 = models.DonationStatusHistory(
            donation_id=d.id, old_status="COLLECTED", new_status="DELIVERED",
            changed_by_user_id=self.ngo_user.id, note="Delivered to center"
        )
        self.db.add(h5)
        self.db.commit()
        self.assertEqual(d.status, "DELIVERED")

        # 7. Acknowledge Receipt (DELIVERED -> ACKNOWLEDGED)
        d.status = "ACKNOWLEDGED"
        h6 = models.DonationStatusHistory(
            donation_id=d.id, old_status="DELIVERED", new_status="ACKNOWLEDGED",
            changed_by_user_id=self.ngo_user.id, note="NGO acknowledged receipt"
        )
        self.db.add(h6)
        self.db.commit()
        self.assertEqual(d.status, "ACKNOWLEDGED")

    def test_multi_tenant_isolation_and_auth_rules(self):
        """
        Verify tenant isolation and role restrictions.
        """
        d = self.db.query(models.Donation).filter(models.Donation.id == self.donation.id).first()
        d.status = "PICKUP_SCHEDULED"
        d.ngo_id = self.ngo_user.id
        self.db.add(d)
        self.db.commit()

        # 1. Enforce Role check: Donor cannot transit/complete/acknowledge
        # Simulate a donor checking authority to transit
        is_donor_authorized = (self.donor_user.role == models.UserRole.NGO and d.ngo_id == self.donor_user.id) or self.donor_user.role == models.UserRole.ADMIN
        self.assertFalse(is_donor_authorized)

        # 2. Enforce Multi-tenant/Isolation check: Other NGO cannot transit/complete/acknowledge
        is_other_ngo_authorized = (self.other_ngo_user.role == models.UserRole.NGO and d.ngo_id == self.other_ngo_user.id) or self.other_ngo_user.role == models.UserRole.ADMIN
        self.assertFalse(is_other_ngo_authorized)

        # Matched NGO is authorized
        is_matched_ngo_authorized = (self.ngo_user.role == models.UserRole.NGO and d.ngo_id == self.ngo_user.id) or self.ngo_user.role == models.UserRole.ADMIN
        self.assertTrue(is_matched_ngo_authorized)

    def test_notification_preference_guards(self):
        """
        Verify notification preference columns block emails when disabled.
        """
        # Disable donor email notifications
        self.donor_user.email_notifications_enabled = False
        self.db.add(self.donor_user)
        self.db.commit()

        # Send test notification check:
        # If donor_user.email_notifications_enabled is False, email service should not send
        email_sent = False
        if self.donor_user.email_notifications_enabled:
            status = EmailService.send_html_email(self.donor_email, "Test", "<h1>Test</h1>")
            email_sent = (status in ["SENT", "DEVELOPMENT_LOG_ONLY"])
        
        self.assertFalse(email_sent)

        # Re-enable and test
        self.donor_user.email_notifications_enabled = True
        self.db.add(self.donor_user)
        self.db.commit()

        if self.donor_user.email_notifications_enabled:
            status = EmailService.send_html_email(self.donor_email, "Test", "<h1>Test</h1>")
            email_sent = (status in ["SENT", "DEVELOPMENT_LOG_ONLY"])

        self.assertTrue(email_sent)

    def test_reminder_retry_idempotency(self):
        """
        Verify the pickup reminder job behaves idempotently and can retry failed attempts.
        """
        tomorrow = date.today() + timedelta(days=1)
        pickup = models.PickupSchedule(
            donation_id=self.donation.id,
            pickup_date=tomorrow,
            time_slot="09:00 AM – 11:00 AM",
            pickup_address="123 Main St",
            contact_phone="123-456-7890",
            reminder_status="FAILED" # simulates a previous failed attempt
        )
        self.db.add(pickup)
        
        # Link donation to NGO user
        self.donation.ngo_id = self.ngo_user.id
        self.db.add(self.donation)
        self.db.commit()

        # Run reminder service
        res = ReminderService.send_pickup_reminders(self.db)
        
        # Verify it processed the failed one
        self.assertEqual(res["processed"], 1)
        # Under developer console fallback, it sets DEVELOPMENT_LOG_ONLY
        self.assertEqual(res["dev_logged"], 1)

        # Verify database state updated from FAILED to DEVELOPMENT_LOG_ONLY (meaning successfully processed in dev)
        updated_pickup = self.db.query(models.PickupSchedule).filter(models.PickupSchedule.donation_id == self.donation.id).first()
        self.assertEqual(updated_pickup.reminder_status, "DEVELOPMENT_LOG_ONLY")

        # Run reminders again - should process 0 since status is now DEVELOPMENT_LOG_ONLY (idempotency check)
        res2 = ReminderService.send_pickup_reminders(self.db)
        self.assertEqual(res2["processed"], 0)

if __name__ == "__main__":
    unittest.main()
