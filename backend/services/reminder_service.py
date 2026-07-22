import logging
import datetime
from sqlalchemy.orm import Session
import models
from services.email_service import EmailService
from config import settings

logger = logging.getLogger("reminder_service")

class ReminderService:
    @classmethod
    def send_pickup_reminders(cls, db: Session) -> dict:
        """
        Queries all PickupSchedule records scheduled for tomorrow (or within the next 24-48 hours)
        that have not yet been notified successfully (status PENDING or FAILED).
        Sends reminder notifications to both donor and NGO.
        Updates reminder_status accordingly (SENT, FAILED, or DEVELOPMENT_LOG_ONLY).
        Returns a summary dict of processed reminders.
        """
        # Find schedules for tomorrow
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        
        schedules = db.query(models.PickupSchedule).filter(
            models.PickupSchedule.pickup_date == tomorrow,
            models.PickupSchedule.reminder_status.in_(["PENDING", "FAILED"])
        ).all()

        results = {
            "processed": len(schedules),
            "sent": 0,
            "failed": 0,
            "dev_logged": 0
        }

        for p in schedules:
            donation = p.donation
            if not donation:
                continue

            # Fetch donor and NGO emails
            donor = db.query(models.User).filter(models.User.id == donation.donor_id).first()
            ngo = db.query(models.User).filter(models.User.id == donation.ngo_id).first()

            if not donor or not ngo:
                logger.warning(f"Donor or NGO not found for donation DON-{donation.id}, skipping reminder.")
                continue

            # Prepare templates
            donor_name = donor.donor_profile.full_name if donor.donor_profile else "Donor"
            ngo_name = ngo.ngo_profile.organization_name if ngo.ngo_profile else "NGO Partner"
            
            replacements = {
                "donation_id": donation.id,
                "pickup_date": p.pickup_date.strftime("%Y-%m-%d"),
                "time_slot": p.time_slot,
                "address": p.pickup_address,
                "phone": p.contact_phone,
                "action_url": f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/donor/track/{donation.id}"
            }

            html_body = EmailService.load_template("pickup_reminder.html", replacements)
            text_fallback = (
                f"Upcoming Pickup Reminder: Your pickup with {ngo_name} for donation DON-{donation.id} "
                f"is scheduled for tomorrow {p.pickup_date} during the slot: {p.time_slot}."
            )

            # Send to donor
            donor_status = "PENDING"
            if donor.email_notifications_enabled:
                donor_status = EmailService.send_html_email(
                    to_email=donor.email,
                    subject="Upcoming Pickup Reminder - Donate",
                    html_body=html_body,
                    text_fallback=text_fallback
                )

            # Send to NGO
            ngo_status = "PENDING"
            if ngo.email_notifications_enabled:
                ngo_status = EmailService.send_html_email(
                    to_email=ngo.email,
                    subject="Upcoming Pickup Reminder - Donate",
                    html_body=html_body,
                    text_fallback=text_fallback
                )

            # Send to Volunteer (if assigned)
            vol_status = "PENDING"
            if getattr(p, "volunteer_email", None):
                replacements["action_url"] = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/login"
                html_body_vol = EmailService.load_template("pickup_reminder.html", replacements)
                vol_status = EmailService.send_html_email(
                    to_email=p.volunteer_email,
                    subject="Upcoming Courier Pickup Reminder - Donate",
                    html_body=html_body_vol,
                    text_fallback=text_fallback
                )

            # Resolve final reminder status: if any failed, set FAILED.
            # If both console logged, set DEVELOPMENT_LOG_ONLY.
            # Otherwise set SENT.
            statuses = {donor_status, ngo_status}
            if getattr(p, "volunteer_email", None):
                statuses.add(vol_status)
                
            if "FAILED" in statuses:
                p.reminder_status = "FAILED"
                results["failed"] += 1
            elif "DEVELOPMENT_LOG_ONLY" in statuses or (len(statuses) == 1 and "PENDING" in statuses):
                # If only PENDING is present, or DEVELOPMENT_LOG_ONLY is present
                if "DEVELOPMENT_LOG_ONLY" in statuses:
                    p.reminder_status = "DEVELOPMENT_LOG_ONLY"
                    results["dev_logged"] += 1
                else:
                    p.reminder_status = "SENT" # fallback safety
                    results["sent"] += 1
            else:
                p.reminder_status = "SENT"
                results["sent"] += 1

            db.add(p)
            db.commit()

        logger.info(f"Reminder Job completed. Results: {results}")
        return results
