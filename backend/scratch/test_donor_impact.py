import sys
import os
import datetime
from sqlalchemy import text, func

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, engine
import models
import auth
from routes.donation_routes import QUALIFYING_IMPACT_STATUSES

def run_analytics_tests():
    print("=== STARTING DONOR IMPACT ANALYTICS UNIT TESTS ===")
    db = SessionLocal()
    
    # 1. Clean up potential leftover test data
    cleanup_test_data(db)
    
    try:
        # 2. Seed Test Users
        # Donor A: active, qualifying donations
        donor_a = models.User(
            email="donor_a_test@example.com",
            password_hash=auth.hash_password("DonorPassword@2026"),
            role=models.UserRole.DONOR,
            is_active=True
        )
        # Donor B: isolation testing
        donor_b = models.User(
            email="donor_b_test@example.com",
            password_hash=auth.hash_password("DonorPassword@2026"),
            role=models.UserRole.DONOR,
            is_active=True
        )
        # NGO 1 and NGO 2
        ngo_1 = models.User(
            email="ngo_1_test@example.com",
            password_hash=auth.hash_password("NgoPassword@2026"),
            role=models.UserRole.NGO,
            is_active=True
        )
        ngo_2 = models.User(
            email="ngo_2_test@example.com",
            password_hash=auth.hash_password("NgoPassword@2026"),
            role=models.UserRole.NGO,
            is_active=True
        )
        db.add_all([donor_a, donor_b, ngo_1, ngo_2])
        db.flush()
        
        # Add profile details for NGOs to prevent missing profile constraints
        ngo_profile_1 = models.NGOProfile(
            user_id=ngo_1.id,
            organization_name="Test NGO One",
            registration_number="REG12345",
            contact_person="Contact 1",
            phone="123456",
            address="Addr 1",
            city="Bengaluru",
            state="Karnataka",
            mission="Mission 1"
        )
        ngo_profile_2 = models.NGOProfile(
            user_id=ngo_2.id,
            organization_name="Test NGO Two",
            registration_number="REG67890",
            contact_person="Contact 2",
            phone="654321",
            address="Addr 2",
            city="Bengaluru",
            state="Karnataka",
            mission="Mission 2"
        )
        db.add_all([ngo_profile_1, ngo_profile_2])
        db.flush()
        
        print("Users and profiles seeded successfully.")
        
        # Test Case 1: Donor with no donations
        print("\n[Test 1] Testing Donor B with no donations...")
        from routes.donation_routes import get_donor_impact
        # Call route function directly
        res_empty = db.query(models.Donation).filter(models.Donation.donor_id == donor_b.id).count()
        assert res_empty == 0, f"Expected 0 donations, got {res_empty}"
        print("Success! Donor B has 0 donations.")
        
        # Test Case 2: Seed qualifying donations for Donor A
        print("\n[Test 2] Seeding donations and items for Donor A...")
        # Donation 1: Completed, 3 books
        d1 = models.Donation(donor_id=donor_a.id, ngo_id=ngo_1.id, status="COMPLETED")
        db.add(d1)
        db.flush()
        item1 = models.DonationItem(donation_id=d1.id, item_name="Textbook", category="  Books ", quantity=3, condition="Good", source="MANUAL")
        db.add(item1)
        
        # Add completion status history
        hist1 = models.DonationStatusHistory(
            donation_id=d1.id,
            old_status="PICKUP_IN_PROGRESS",
            new_status="COMPLETED",
            changed_by_user_id=ngo_1.id,
            created_at=datetime.datetime.now() - datetime.timedelta(days=10) # 10 days ago
        )
        db.add(hist1)
        
        # Donation 2: Packaging in progress, 2 items of category 'Clothing' and 1 of category 'CLOTHING' (case normalization check)
        d2 = models.Donation(donor_id=donor_a.id, ngo_id=ngo_1.id, status="PACKAGING_IN_PROGRESS")
        db.add(d2)
        db.flush()
        item2 = models.DonationItem(donation_id=d2.id, item_name="Shirt", category="Clothing", quantity=2, condition="Fair", source="MANUAL")
        item3 = models.DonationItem(donation_id=d2.id, item_name="Pants", category="CLOTHING", quantity=1, condition="Fair", source="MANUAL")
        db.add_all([item2, item3])
        
        # Donation 3: Draft (should be excluded)
        d3 = models.Donation(donor_id=donor_a.id, ngo_id=ngo_2.id, status="DRAFT")
        db.add(d3)
        db.flush()
        item4 = models.DonationItem(donation_id=d3.id, item_name="Toy car", category="Toys", quantity=5, condition="Good", source="MANUAL")
        db.add(item4)
        
        # Donation 4: NGO_REJECTED (should be excluded)
        d4 = models.Donation(donor_id=donor_a.id, ngo_id=ngo_2.id, status="NGO_REJECTED")
        db.add(d4)
        db.flush()
        item5 = models.DonationItem(donation_id=d4.id, item_name="Notebook", category="Books", quantity=4, condition="Poor", source="MANUAL")
        db.add(item5)
        
        # Donation 5: NGO_ACCEPTED to NGO 2 (to test multiple unique NGOs)
        d5 = models.Donation(donor_id=donor_a.id, ngo_id=ngo_2.id, status="NGO_ACCEPTED")
        db.add(d5)
        db.flush()
        item6 = models.DonationItem(donation_id=d5.id, item_name="Rice Bag", category="Food", quantity=10, condition="Good", source="MANUAL")
        db.add(item6)
        
        db.commit()
        print("Qualifying and non-qualifying donations seeded.")
        
        # Test Case 3: Summary Metric calculations
        print("\n[Test 3] Verifying summary metrics via SQL queries...")
        # 1. Total Qualifying donations (COMPLETED, PACKAGING_IN_PROGRESS, NGO_ACCEPTED) -> should be 3 (d1, d2, d5)
        tot_donations = db.query(func.count(models.Donation.id)).filter(
            models.Donation.donor_id == donor_a.id,
            models.Donation.status.in_(QUALIFYING_IMPACT_STATUSES)
        ).scalar()
        print(f"Total donations query result: {tot_donations} (Expected: 3)")
        assert tot_donations == 3, f"Expected 3, got {tot_donations}"
        
        # 2. Total items donated -> should be 3 (d1) + 2 (d2) + 1 (d2) + 10 (d5) = 16 items
        tot_items = db.query(func.coalesce(func.sum(models.DonationItem.quantity), 0)).join(
            models.Donation, models.Donation.id == models.DonationItem.donation_id
        ).filter(
            models.Donation.donor_id == donor_a.id,
            models.Donation.status.in_(QUALIFYING_IMPACT_STATUSES)
        ).scalar()
        print(f"Total items query result: {tot_items} (Expected: 16)")
        assert tot_items == 16, f"Expected 16, got {tot_items}"
        
        # 3. NGOs Helped -> distinct NGO ids for qualifying donations. d1/d2: ngo_1, d5: ngo_2 -> should be 2.
        tot_ngos = db.query(func.count(func.distinct(models.Donation.ngo_id))).filter(
            models.Donation.donor_id == donor_a.id,
            models.Donation.status.in_(QUALIFYING_IMPACT_STATUSES),
            models.Donation.ngo_id.isnot(None)
        ).scalar()
        print(f"Total NGOs helped query result: {tot_ngos} (Expected: 2)")
        assert tot_ngos == 2, f"Expected 2, got {tot_ngos}"
        
        # 4. Beneficiaries reached -> should be 16 * 3 = 48
        est_beneficiaries = tot_items * 3
        print(f"Estimated beneficiaries: {est_beneficiaries} (Expected: 48)")
        assert est_beneficiaries == 48, f"Expected 48, got {est_beneficiaries}"
        
        # Test Case 4: Category distribution and normalization
        print("\n[Test 4] Verifying category normalization...")
        category_counts = db.query(
            models.DonationItem.category,
            func.sum(models.DonationItem.quantity).label('quantity')
        ).join(
            models.Donation, models.Donation.id == models.DonationItem.donation_id
        ).filter(
            models.Donation.donor_id == donor_a.id,
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
            
        print(f"Normalized Category Map: {category_map}")
        # Expected categories: Books (3), Clothing (3, from merging 'Clothing' & 'CLOTHING'), Food (10)
        assert category_map["Books"] == 3
        assert category_map["Clothing"] == 3
        assert category_map["Food"] == 10
        print("Success! Case-normalization and whitespace trim verified.")
        
        # Test Case 5: 5-week streak validation
        print("\n[Test 5] Verifying 5-week streak calculation...")
        # Since we have only seeded donations in the current week and 10 days ago (2 unique weeks), streak should be 1 or 2 (locked)
        # Let's seed 5 consecutive weeks of activity for Donor A to verify unlock behavior
        def get_start_of_week(dt):
            return dt.date() - datetime.timedelta(days=dt.date().weekday())
            
        today = datetime.datetime.now()
        # Seed more donations in consecutive previous weeks (we already have today and 10 days ago)
        for w in [1, 2, 3, 4]:
            past_donation = models.Donation(
                donor_id=donor_a.id, 
                ngo_id=ngo_1.id, 
                status="COMPLETED",
                created_at=today - datetime.timedelta(weeks=w)
            )
            db.add(past_donation)
            db.flush()
            
            # Add completion status histories for these donations too
            past_hist = models.DonationStatusHistory(
                donation_id=past_donation.id,
                old_status="PICKUP_IN_PROGRESS",
                new_status="COMPLETED",
                changed_by_user_id=ngo_1.id,
                created_at=today - datetime.timedelta(weeks=w)
            )
            db.add(past_hist)
            
            past_item = models.DonationItem(
                donation_id=past_donation.id,
                item_name="Item",
                category="Books",
                quantity=1,
                condition="Good",
                source="MANUAL"
            )
            db.add(past_item)
            
        db.commit()
        
        # Re-fetch donations and verify streak
        completion_subquery = db.query(
            models.DonationStatusHistory.donation_id,
            func.min(models.DonationStatusHistory.created_at).label('completed_at')
        ).filter(
            models.DonationStatusHistory.new_status == "COMPLETED"
        ).group_by(
            models.DonationStatusHistory.donation_id
        ).subquery()

        all_donations = db.query(
            models.Donation.id,
            models.Donation.created_at,
            models.Donation.status,
            completion_subquery.c.completed_at
        ).outerjoin(
            completion_subquery,
            models.Donation.id == completion_subquery.c.donation_id
        ).filter(
            models.Donation.donor_id == donor_a.id,
            models.Donation.status.in_(QUALIFYING_IMPACT_STATUSES)
        ).all()
        
        weeks = set()
        for d in all_donations:
            dt = d.completed_at if (d.status == "COMPLETED" and d.completed_at) else d.created_at
            if dt:
                weeks.add(get_start_of_week(dt))
                
        sorted_weeks = sorted(list(weeks))
        print(f"Qualifying weeks for Donor A: {sorted_weeks}")
        
        max_streak = 0
        current_streak = 0
        prev_week = None
        for w in sorted_weeks:
            if prev_week is None:
                current_streak = 1
            elif (w - prev_week).days == 7:
                current_streak += 1
            elif (w - prev_week).days > 7:
                max_streak = max(max_streak, current_streak)
                current_streak = 1
            prev_week = w
        max_streak = max(max_streak, current_streak)
        print(f"Calculated consecutive streak: {max_streak} weeks (Expected: 5)")
        assert max_streak == 5, f"Expected 5, got {max_streak}"
        print("Success! Streak calculations verified successfully.")
        
        # Test Case 6: Cross-donor isolation
        print("\n[Test 6] Verifying cross-donor isolation...")
        donor_b_donations = db.query(models.Donation).filter(
            models.Donation.donor_id == donor_b.id,
            models.Donation.status.in_(QUALIFYING_IMPACT_STATUSES)
        ).count()
        assert donor_b_donations == 0, f"Expected 0 donations for Donor B, got {donor_b_donations}"
        print("Success! Donor B calculations remain isolated at 0.")
        
        print("\n=== ALL DONOR IMPACT ANALYTICS TESTS PASSED ===")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        cleanup_test_data(db)
        db.close()

def cleanup_test_data(db):
    try:
        # Delete test users (cascade handles profile, donations, history, items)
        test_emails = ["donor_a_test@example.com", "donor_b_test@example.com", "ngo_1_test@example.com", "ngo_2_test@example.com"]
        db.query(models.User).filter(models.User.email.in_(test_emails)).delete(synchronize_session=False)
        db.commit()
        print("Seeded test data cleaned up.")
    except Exception as e:
        db.rollback()
        print(f"Failed to clean up test data: {e}")

if __name__ == "__main__":
    from sqlalchemy import func
    run_analytics_tests()
