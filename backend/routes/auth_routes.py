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
