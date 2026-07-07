import requests
import json
import random

BASE_URL = "http://127.0.0.1:8000"

def get_random_email(prefix):
    return f"{prefix}_{random.randint(1000,9999)}@example.com"

def test_workflow():
    print("=== STARTING FULL WORKFLOW AND CAP AUDIT TESTS ===")
    
    # Define credentials
    donor_a_email = get_random_email("donor_a")
    donor_b_email = get_random_email("donor_b")
    ngo_a_email = get_random_email("ngo_a")
    ngo_b_email = get_random_email("ngo_b")
    
    # Helper to register a Donor
    def register_donor(email, name):
        res = requests.post(f"{BASE_URL}/api/auth/register/donor", json={
            "email": email,
            "password": "DonorPassword@2026",
            "name": name,
            "phone": "+91 99999 88888",
            "city": "Bengaluru",
            "state": "Karnataka"
        })
        assert res.status_code == 200, f"Donor registration failed: {res.text}"

    # Helper to register an NGO
    def register_ngo(email, org_name, reg_num):
        res = requests.post(f"{BASE_URL}/api/auth/register/ngo", json={
            "email": email,
            "password": "NgoPassword@2026",
            "org": org_name,
            "registrationNumber": reg_num,
            "contactPerson": "Rohan NGO",
            "phone": "+91 80 5000 6789",
            "address": "45 Residency Road, Bengaluru",
            "city": "Bengaluru",
            "state": "Karnataka",
            "focusAreas": "Education",
            "mission": "Essentials support."
        })
        assert res.status_code == 200, f"NGO registration failed: {res.text}"

    # Register users
    register_donor(donor_a_email, "Donor A")
    register_donor(donor_b_email, "Donor B")
    register_ngo(ngo_a_email, "NGO A Org", f"KA/2026/{random.randint(10000,99999)}")
    register_ngo(ngo_b_email, "NGO B Org", f"KA/2026/{random.randint(10000,99999)}")

    # Helper to login and get headers
    def login(email, password):
        res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
        assert res.status_code == 200, f"Login failed: {res.text}"
        data = res.json()
        return {
            "headers": {"Authorization": f"Bearer {data['access_token']}"},
            "user_id": data["user"]["id"],
            "tenant_id": data["user"].get("tenantId")
        }

    # Obtain sessions
    sess_donor_a = login(donor_a_email, "DonorPassword@2026")
    sess_donor_b = login(donor_b_email, "DonorPassword@2026")
    sess_ngo_a = login(ngo_a_email, "NgoPassword@2026")
    sess_ngo_b = login(ngo_b_email, "NgoPassword@2026")

    # 1. Verification of POST /api/donations status = ITEMS_SUBMITTED (Gap 1)
    print("\n[Test 1] Submit items for Donor A...")
    items_payload = {
        "items": [
            {
                "item_name": "Textbook",
                "category": "Books",
                "quantity": 10,
                "condition": "Good",
                "confidence_score": 0.95,
                "source": "AI"
            }
        ]
    }
    res = requests.post(f"{BASE_URL}/api/donations", json=items_payload, headers=sess_donor_a["headers"])
    assert res.status_code == 201
    donation_id = res.json()["donation_id"]
    status_submitted = res.json()["status"]
    print(f"Success! Status after creation is: {status_submitted} (Expected: ITEMS_SUBMITTED)")
    assert status_submitted == "ITEMS_SUBMITTED"

    # 2. Input Constraint Validation (Gap 8)
    print("\n[Test 2] Validating quantity constraint <= 0...")
    bad_qty_payload = {
        "items": [{
            "item_name": "Pen",
            "category": "Books",
            "quantity": 0,
            "condition": "Good",
            "source": "MANUAL"
        }]
    }
    res = requests.post(f"{BASE_URL}/api/donations", json=bad_qty_payload, headers=sess_donor_a["headers"])
    print(f"Quantity 0 Response status: {res.status_code} (Expected 422)")
    assert res.status_code == 422

    print("Validating confidence outside 0..1...")
    bad_conf_payload = {
        "items": [{
            "item_name": "Pen",
            "category": "Books",
            "quantity": 5,
            "condition": "Good",
            "confidence_score": 1.5,
            "source": "AI"
        }]
    }
    res = requests.post(f"{BASE_URL}/api/donations", json=bad_conf_payload, headers=sess_donor_a["headers"])
    print(f"Confidence 1.5 Response status: {res.status_code} (Expected 422)")
    assert res.status_code == 422

    # 3. Cross-User Donation Access Checks (Gap 8)
    print("\n[Test 3] Verifying Donor B cannot access Donor A's donation...")
    res = requests.get(f"{BASE_URL}/api/donations/{donation_id}/track", headers=sess_donor_b["headers"])
    print(f"Response status: {res.status_code} (Expected 403)")
    assert res.status_code == 403

    # 4. Cross-Tenant Demands isolation (Gap 8)
    print("\n[Test 4] NGO A creates a demand...")
    demand_payload = {
        "title": "Need Primary Books",
        "priority": "HIGH",
        "items": [{
            "item_name": "Textbook",
            "category": "Books",
            "quantity_needed": 10
        }]
    }
    res = requests.post(f"{BASE_URL}/api/donations/demands", json=demand_payload, headers=sess_ngo_a["headers"])
    assert res.status_code == 201
    demand_id = res.json()["demand_id"]

    print("Verifying NGO B cannot edit NGO A's demand...")
    res = requests.put(f"{BASE_URL}/api/donations/demands/{demand_id}", json={"description": "Hacked"}, headers=sess_ngo_b["headers"])
    print(f"Response status: {res.status_code} (Expected 403)")
    assert res.status_code == 403

    # Verify Archiving instead of permanent delete (Gap 6)
    print("Verifying NGO A can archive demand (sets status to CLOSED)...")
    res = requests.delete(f"{BASE_URL}/api/donations/demands/{demand_id}", headers=sess_ngo_a["headers"])
    assert res.status_code == 200
    # Fetch demands and make sure it has CLOSED status
    res = requests.get(f"{BASE_URL}/api/donations/demands/my", headers=sess_ngo_a["headers"])
    demands_list = res.json()
    closed_demand = [d for d in demands_list if d["id"] == str(demand_id)][0]
    print(f"Demand status after archiving: {closed_demand['status']} (Expected: Paused/CLOSED)")
    assert closed_demand["status"] == "Paused"

    # Re-create demand for matching test
    res = requests.post(f"{BASE_URL}/api/donations/demands", json=demand_payload, headers=sess_ngo_a["headers"])
    assert res.status_code == 201
    demand_id = res.json()["demand_id"]

    # 5. Early packaging and scheduling guards (Gap 8)
    print("\n[Test 5] Verifying Donor cannot start packaging before NGO acceptance...")
    res = requests.post(f"{BASE_URL}/api/donations/{donation_id}/start-packaging", headers=sess_donor_a["headers"])
    print(f"Response status: {res.status_code} (Expected 400)")
    assert res.status_code == 400

    print("Verifying Donor cannot schedule pickup before READY_FOR_PICKUP...")
    pickup_payload = {
        "pickup_date": "2026-07-15",
        "time_slot": "10:00 AM – 12:00 PM",
        "pickup_address": "45 Address Rd",
        "contact_phone": "+91 99000 88888"
    }
    res = requests.post(f"{BASE_URL}/api/donations/{donation_id}/pickup", json=pickup_payload, headers=sess_donor_a["headers"])
    print(f"Response status: {res.status_code} (Expected 400)")
    assert res.status_code == 400

    # 6. NGO Requests Matching & Request dispatch
    print("\n[Test 6] Donor A sends request to NGO A...")
    res = requests.post(f"{BASE_URL}/api/donations/{donation_id}/requests", json={"ngo_id": sess_ngo_a["user_id"]}, headers=sess_donor_a["headers"])
    assert res.status_code == 200
    request_id = res.json()["request_id"]

    print("Verifying duplicate active pending requests are blocked...")
    res = requests.post(f"{BASE_URL}/api/donations/{donation_id}/requests", json={"ngo_id": sess_ngo_a["user_id"]}, headers=sess_donor_a["headers"])
    print(f"Response status: {res.status_code} (Expected 400)")
    assert res.status_code == 400

    # 7. NGO Authorization & Accept guards (Gap 8)
    print("\n[Test 7] Verifying NGO B cannot accept NGO A's request...")
    res = requests.post(f"{BASE_URL}/api/donations/requests/{request_id}/accept", headers=sess_ngo_b["headers"])
    print(f"Response status: {res.status_code} (Expected 403)")
    assert res.status_code == 403

    print("NGO A accepts the request successfully...")
    res = requests.post(f"{BASE_URL}/api/donations/requests/{request_id}/accept", headers=sess_ngo_a["headers"])
    assert res.status_code == 200

    print("Verifying duplicate accept fails...")
    res = requests.post(f"{BASE_URL}/api/donations/requests/{request_id}/accept", headers=sess_ngo_a["headers"])
    print(f"Response status: {res.status_code} (Expected 400)")
    assert res.status_code == 400

    # 8. Complete Packaging
    print("\n[Test 8] Donor A starting packaging checklist...")
    res = requests.post(f"{BASE_URL}/api/donations/{donation_id}/start-packaging", headers=sess_donor_a["headers"])
    assert res.status_code == 200

    print("Donor A completes packaging checklist...")
    res = requests.post(f"{BASE_URL}/api/donations/{donation_id}/package", json={"package_count": 2, "packaging_notes": "All packed"}, headers=sess_donor_a["headers"])
    assert res.status_code == 200

    # 9. Schedule Pickup
    print("\n[Test 9] Donor A schedules pickup...")
    res = requests.post(f"{BASE_URL}/api/donations/{donation_id}/pickup", json=pickup_payload, headers=sess_donor_a["headers"])
    assert res.status_code == 200

    # 10. Transit & Delivery complete flow (Gap 4)
    print("\n[Test 10] Transitioning to PICKUP_IN_PROGRESS (Transit)...")
    res = requests.post(f"{BASE_URL}/api/donations/{donation_id}/transit", headers=sess_ngo_a["headers"])
    assert res.status_code == 200

    print("Transitioning to COMPLETED (Delivery)...")
    res = requests.post(f"{BASE_URL}/api/donations/{donation_id}/complete", headers=sess_ngo_a["headers"])
    assert res.status_code == 200

    # 11. Notification isolation verification (Gap 8)
    print("\n[Test 11] Verifying notifications are user-isolated...")
    res = requests.get(f"{BASE_URL}/api/donations/notifications/list", headers=sess_donor_a["headers"])
    donor_a_notifs = res.json()
    assert len(donor_a_notifs) > 0

    res = requests.get(f"{BASE_URL}/api/donations/notifications/list", headers=sess_donor_b["headers"])
    donor_b_notifs = res.json()
    # Donor B has not received any notification since they are not involved in any transaction
    assert len(donor_b_notifs) == 0
    print("Success! Notification isolation verified.")

    # 12. Verification of status history logs (Gap 2)
    print("\n[Test 12] Fetching status history logs...")
    res = requests.get(f"{BASE_URL}/api/donations/{donation_id}/track", headers=sess_donor_a["headers"])
    track_data = res.json()
    print("Logged events list:")
    for ev in track_data["events"]:
        print(f"  - [{ev['status']}] {ev['description']}")
    
    # Assert COMPLETED status
    assert track_data["status"] == "COMPLETED"
    print("\n=== ALL AUDITED CAP CHECKS PASSED SUCCESSFULLY ===")

    # 13. Idempotent cleanup of all test records
    print("\n[Cleanup] Cleaning up seeded test records from database...")
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from database import SessionLocal
    import models
    db = SessionLocal()
    try:
        user_ids = [sess_donor_a["user_id"], sess_donor_b["user_id"], sess_ngo_a["user_id"], sess_ngo_b["user_id"]]
        tenant_ids = [sess_ngo_a["tenant_id"], sess_ngo_b["tenant_id"]]
        # Delete users and tenants (ON DELETE CASCADE handles profiles, demands, items, donations, matches, schedule, history, notifications)
        db.query(models.User).filter(models.User.id.in_(user_ids)).delete(synchronize_session=False)
        db.query(models.Tenant).filter(models.Tenant.id.in_(tenant_ids)).delete(synchronize_session=False)
        db.commit()
        print("Database cleanup completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Database cleanup failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_workflow()
