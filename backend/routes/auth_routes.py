from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> models.User:
    token = credentials.credentials
    sub = auth.decode_access_token(token)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(models.User).filter(models.User.id == int(sub)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user

def format_user_response(user: models.User, db: Session) -> schemas.UserResponse:
    res = {
        "id": user.id,
        "email": user.email,
        "role": user.role.value,  # Enum value ('DONOR', 'NGO', 'ADMIN')
        "emailNotificationsEnabled": user.email_notifications_enabled,
        "inappNotificationsEnabled": user.inapp_notifications_enabled,
    }
    if user.role == models.UserRole.DONOR:
        profile = user.donor_profile
        if profile:
            res["name"] = profile.full_name
            res["phone"] = profile.phone
            res["city"] = profile.city
            res["state"] = profile.state
        else:
            res["name"] = "Donor"
    elif user.role == models.UserRole.NGO:
        profile = user.ngo_profile
        if profile:
            res["name"] = profile.contact_person
            res["contactPerson"] = profile.contact_person
            res["org"] = profile.organization_name
            res["registrationNumber"] = profile.registration_number
            res["phone"] = profile.phone
            res["address"] = profile.address
            res["city"] = profile.city
            res["state"] = profile.state
            res["mission"] = profile.mission
            res["tenantId"] = profile.tenant_id
            # Fetch focus areas
            fa_list = [fa.focus_area for fa in profile.focus_areas]
            res["focusAreas"] = ", ".join(fa_list)
        else:
            res["name"] = "NGO Partner"
    elif user.role == models.UserRole.ADMIN:
        res["name"] = "System Admin"
    else:
        res["name"] = "Guest"
    return schemas.UserResponse(**res)

@router.post("/register/donor")
def register_donor(payload: schemas.DonorRegister, db: Session = Depends(get_db)):
    email_clean = payload.email.strip().lower()
    existing = db.query(models.User).filter(models.User.email == email_clean).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    try:
        # Create user
        new_user = models.User(
            email=email_clean,
            password_hash=auth.hash_password(payload.password),
            role=models.UserRole.DONOR,
            is_active=True
        )
        db.add(new_user)
        db.flush()  # gets new_user.id

        # Create profile
        profile = models.DonorProfile(
            user_id=new_user.id,
            full_name=payload.name.strip(),
            phone=payload.phone.strip(),
            city=payload.city.strip(),
            state=payload.state.strip()
        )
        db.add(profile)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during registration: {str(e)}")

    return {"success": True, "message": "Donor registered successfully"}

@router.post("/register/ngo")
def register_ngo(payload: schemas.NGORegister, db: Session = Depends(get_db)):
    email_clean = payload.email.strip().lower()
    existing = db.query(models.User).filter(models.User.email == email_clean).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
        
    existing_reg = db.query(models.NGOProfile).filter(models.NGOProfile.registration_number == payload.registrationNumber.strip()).first()
    if existing_reg:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An NGO with this registration number is already registered."
        )

    try:
        import re
        # Generate URL-safe slug from organization name
        slug = re.sub(r'[^a-z0-9]+', '-', payload.org.strip().lower()).strip('-')
        base_slug = slug or "ngo-tenant"
        counter = 1
        while db.query(models.Tenant).filter(models.Tenant.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        # 1. Create NGO Tenant
        new_tenant = models.Tenant(
            name=payload.org.strip(),
            tenant_type="NGO",
            slug=slug,
            is_active=True
        )
        db.add(new_tenant)
        db.flush()  # populate new_tenant.id

        # 2. Create User
        new_user = models.User(
            email=email_clean,
            password_hash=auth.hash_password(payload.password),
            role=models.UserRole.NGO,
            is_active=True
        )
        db.add(new_user)
        db.flush()

        # 3. Create profile linked to Tenant
        profile = models.NGOProfile(
            tenant_id=new_tenant.id,
            user_id=new_user.id,
            organization_name=payload.org.strip(),
            registration_number=payload.registrationNumber.strip(),
            contact_person=payload.contactPerson.strip(),
            phone=payload.phone.strip(),
            address=payload.address.strip(),
            city=payload.city.strip(),
            state=payload.state.strip(),
            mission=payload.mission.strip()
        )
        db.add(profile)
        db.flush()

        # 4. Focus areas
        if payload.focusAreas:
            areas = [a.strip() for a in payload.focusAreas.split(",") if a.strip()]
            for area in areas:
                fa = models.NGOFocusArea(
                    ngo_id=profile.id,
                    focus_area=area
                )
                db.add(fa)
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during registration: {str(e)}")

    return {"success": True, "message": "NGO registered successfully"}

@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    email_clean = payload.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email_clean).first()
    if not user or not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="We couldn't sign you in with those credentials.")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="This account has been disabled.")

    access_token = auth.create_access_token(subject=user.id)
    user_resp = format_user_response(user, db)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_resp
    }

@router.get("/me", response_model=schemas.UserResponse)
def get_me(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return format_user_response(user, db)

@router.put("/profile", response_model=schemas.UserResponse)
def update_profile(
    payload: dict,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the current user's profile fields.
    Accepts any subset of: name/full_name, phone, city, state, address (NGO only), contactPerson (NGO only), mission (NGO only).
    """
    try:
        if user.role == models.UserRole.DONOR:
            profile = user.donor_profile
            if not profile:
                raise HTTPException(status_code=404, detail="Donor profile not found.")
            if "name" in payload and payload["name"]:
                profile.full_name = payload["name"].strip()
            if "phone" in payload and payload["phone"]:
                profile.phone = payload["phone"].strip()
            if "city" in payload and payload["city"]:
                profile.city = payload["city"].strip()
            if "state" in payload and payload["state"]:
                profile.state = payload["state"].strip()

        elif user.role == models.UserRole.NGO:
            profile = user.ngo_profile
            if not profile:
                raise HTTPException(status_code=404, detail="NGO profile not found.")
            if "contactPerson" in payload and payload["contactPerson"]:
                profile.contact_person = payload["contactPerson"].strip()
            if "phone" in payload and payload["phone"]:
                profile.phone = payload["phone"].strip()
            if "city" in payload and payload["city"]:
                profile.city = payload["city"].strip()
            if "state" in payload and payload["state"]:
                profile.state = payload["state"].strip()
            if "address" in payload and payload["address"]:
                profile.address = payload["address"].strip()
            if "mission" in payload and payload["mission"]:
                profile.mission = payload["mission"].strip()
        else:
            raise HTTPException(status_code=403, detail="Profile updates are not supported for this role.")

        db.commit()
        db.refresh(user)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")

    return format_user_response(user, db)


# ─── Forgot Password ──────────────────────────────────────────────────────────

@router.post("/forgot-password")
def forgot_password(payload: dict, db: Session = Depends(get_db)):
    """
    Accepts { "email": "..." }.
    Generates a secure reset token, stores it hashed on the user row,
    and emails a reset link. Always returns 200 to prevent email enumeration.
    """
    import secrets
    from datetime import datetime, timezone, timedelta
    from config import settings
    from services.email_service import EmailService

    email_clean = payload.get("email", "").strip().lower()
    if not email_clean:
        raise HTTPException(status_code=400, detail="Email is required.")

    user = db.query(models.User).filter(models.User.email == email_clean).first()

    # Always return success — don't reveal whether the email exists
    if not user or not user.is_active:
        return {"success": True, "message": "If that email is registered, a reset link has been sent."}

    # Generate a URL-safe token (64 hex chars = 32 bytes)
    raw_token = secrets.token_urlsafe(32)
    hashed_token = auth.hash_password(raw_token)  # re-use bcrypt hasher

    user.password_reset_token = hashed_token
    user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}&email={email_clean}"

    html_body = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;background:#f8fafc;padding:30px">
<div style="max-width:520px;margin:0 auto;background:white;padding:32px;border-radius:12px;border:1px solid #e2e8f0">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:24px">
    <div style="background:#0d9488;padding:8px;border-radius:8px">
      <span style="color:white;font-size:18px">&#10084;</span>
    </div>
    <span style="font-weight:700;font-size:18px;color:#0f172a">Donate</span>
  </div>
  <h2 style="color:#0f172a;margin:0 0 8px">Reset your password</h2>
  <p style="color:#64748b;margin:0 0 24px">
    We received a request to reset the password for your account (<strong>{email_clean}</strong>).
    Click the button below to choose a new password.
  </p>
  <a href="{reset_url}"
     style="display:inline-block;background:#0d9488;color:white;padding:12px 28px;
            border-radius:8px;text-decoration:none;font-weight:600;font-size:15px">
    Reset Password
  </a>
  <p style="color:#94a3b8;font-size:13px;margin-top:24px">
    This link expires in <strong>1 hour</strong>. If you did not request a password reset,
    you can safely ignore this email.
  </p>
  <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0">
  <p style="color:#cbd5e1;font-size:12px">DonateAI &mdash; Connecting donors with NGOs</p>
</div>
</body></html>"""

    text_fallback = (
        f"Reset your Donate password\n\n"
        f"Click the link below to reset your password (expires in 1 hour):\n{reset_url}\n\n"
        f"If you did not request this, ignore this email."
    )

    EmailService.send_html_email(
        to_email=email_clean,
        subject="Reset your Donate password",
        html_body=html_body,
        text_fallback=text_fallback,
    )

    return {"success": True, "message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(payload: dict, db: Session = Depends(get_db)):
    """
    Accepts { "email": "...", "token": "...", "new_password": "..." }.
    Validates the token and updates the password.
    """
    from datetime import datetime, timezone

    email_clean = payload.get("email", "").strip().lower()
    raw_token   = payload.get("token", "").strip()
    new_password = payload.get("new_password", "").strip()

    if not email_clean or not raw_token or not new_password:
        raise HTTPException(status_code=400, detail="Email, token, and new password are required.")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    user = db.query(models.User).filter(models.User.email == email_clean).first()
    if not user or not user.password_reset_token or not user.password_reset_expires:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link. Please request a new one.")

    # Check expiry
    expires = user.password_reset_expires
    if expires.tzinfo is None:
        from datetime import timezone as tz
        expires = expires.replace(tzinfo=tz.utc)
    if datetime.now(timezone.utc) > expires:
        raise HTTPException(status_code=400, detail="This reset link has expired. Please request a new one.")

    # Verify token
    if not auth.verify_password(raw_token, user.password_reset_token):
        raise HTTPException(status_code=400, detail="Invalid or expired reset link. Please request a new one.")

    # Set new password and clear token
    user.password_hash = auth.hash_password(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()

    return {"success": True, "message": "Password updated successfully. You can now sign in."}
