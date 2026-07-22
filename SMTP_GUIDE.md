# SMTP Email Configuration Guide

This guide explains how to configure the Donate AI system to send **real emails** through Gmail SMTP.

---

## Prerequisites

You need a Gmail account with **2-Step Verification enabled**.

---

## Step 1: Generate a Gmail App Password

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Under **"How you sign in to Google"**, click **2-Step Verification** (must be enabled first)
3. Scroll to the bottom and click **App passwords**
4. Select app: `Mail`, select device: `Other` -> type `DonateAI`
5. Click **Generate**
6. Copy the 16-character password (spaces do not matter)

---

## Step 2: Configure `.env`

In the `backend/` directory, edit your `.env` file (or create one if missing):

```env
# SMTP Configuration (Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=yourgmail@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_FROM_EMAIL=yourgmail@gmail.com
SMTP_USE_TLS=True
```

Replace `xxxx xxxx xxxx xxxx` with the 16-character App Password from Step 1.

---

## Step 3: Restart the Backend

```bash
uvicorn main:app --reload
```

---

## Step 4: Verify with the Debug Endpoint

```bash
curl -X POST http://localhost:8000/api/donations/debug/test-email ^
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Expected response when SMTP is configured:

```json
{ "status": "SENT", "recipient": "youremail@gmail.com", "message": "Test email sent successfully. Check your inbox." }
```

Expected response when SMTP is NOT configured (development mode):

```json
{ "status": "DEVELOPMENT_LOG_ONLY", "recipient": "youremail@gmail.com", "message": "SMTP not configured. Email logged to console (DEVELOPMENT_LOG_ONLY)." }
```

---

## Notification Workflow Audit

Event | Route | Template | Recipients
--- | --- | --- | ---
1 Match Found | matching_service.py | match_available.html | NGO
2 Future Match Found | matching_service.py | future_match_available.html | Donor + NGO
3 NGO Accepts | POST /{id}/accept | donation_accepted.html | Donor
4 NGO Rejects | POST /{id}/reject | donation_rejected.html | Donor
5 Packaging Completed | POST /{id}/package | packaging_complete.html | NGO
6 Pickup Scheduled | POST /{id}/schedule | pickup_scheduled.html | Donor + NGO + Volunteer
7 Pickup Reminder | reminder_service.py | pickup_reminder.html | Donor + NGO + Volunteer
8 Volunteer Assigned | POST /{id}/assign-volunteer | volunteer_assigned.html | Donor + NGO + Volunteer
9 Donation Collected | POST /{id}/transit | donation_collected.html | Donor + NGO + Volunteer
10 Donation Delivered | POST /{id}/complete | donation_delivered.html | Donor + NGO
11 Donation Acknowledged | POST /{id}/acknowledge | donation_acknowledged.html | Donor + NGO

---

## Deduplication

Volunteer assignment emails are only sent when volunteer details (name, phone, or email) have actually changed. This prevents duplicate notifications when the same volunteer is saved without modifications.

---

## Troubleshooting

Issue | Solution
--- | ---
DEVELOPMENT_LOG_ONLY always shown | Check all 3 env vars are set: SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD
FAILED status in logs | Check App Password is correct and 2FA is enabled
Gmail blocks connection | Use port 587 with SMTP_USE_TLS=True
Less secure app error | Use an App Password, NOT your regular Gmail password
