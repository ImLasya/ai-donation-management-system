from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal
from routes import auth_routes, detection_routes, donation_routes
import models
import yolo_model

def run_seeder():
    db = SessionLocal()
    try:
        import auth
        
        # Seed Donor
        donor_email = "aarav@example.com"
        if not db.query(models.User).filter(models.User.email == donor_email).first():
            try:
                user = models.User(
                    email=donor_email,
                    password_hash=auth.hash_password("Donor@2026"),
                    role=models.UserRole.DONOR,
                    is_active=True
                )
                db.add(user)
                db.flush()
                profile = models.DonorProfile(
                    user_id=user.id,
                    full_name="Aarav Sharma",
                    phone="+91 98765 43210",
                    city="Bengaluru",
                    state="Karnataka"
                )
                db.add(profile)
                db.commit()
                print("Seeded donor mock user: aarav@example.com")
            except Exception as e:
                db.rollback()
                print(f"Failed to seed donor: {e}")

        # Seed NGO
        ngo_email = "priya@hopefoundation.org"
        if not db.query(models.User).filter(models.User.email == ngo_email).first():
            try:
                # Create mock tenant
                tenant = models.Tenant(
                    name="Hope Foundation",
                    tenant_type="NGO",
                    slug="hope-foundation",
                    is_active=True
                )
                db.add(tenant)
                db.flush()

                user = models.User(
                    email=ngo_email,
                    password_hash=auth.hash_password("Ngo@2026"),
                    role=models.UserRole.NGO,
                    is_active=True
                )
                db.add(user)
                db.flush()
                profile = models.NGOProfile(
                    tenant_id=tenant.id,
                    user_id=user.id,
                    organization_name="Hope Foundation",
                    registration_number="KA/2015/0012345",
                    contact_person="Priya Nair",
                    phone="+91 80 4000 1234",
                    address="12 Residency Road, Bengaluru 560025",
                    city="Bengaluru",
                    state="Karnataka",
                    mission="Empowering children through education."
                )
                db.add(profile)
                db.flush()
                for area in ["Education", "Food"]:
                    fa = models.NGOFocusArea(ngo_id=profile.id, focus_area=area)
                    db.add(fa)
                db.commit()
                print("Seeded NGO mock user: priya@hopefoundation.org")
            except Exception as e:
                db.rollback()
                print(f"Failed to seed NGO: {e}")

        # Seed Admin
        admin_email = "admin@donateai.org"
        if not db.query(models.User).filter(models.User.email == admin_email).first():
            try:
                user = models.User(
                    email=admin_email,
                    password_hash=auth.hash_password("Admin@2026"),
                    role=models.UserRole.ADMIN,
                    is_active=True
                )
                db.add(user)
                db.commit()
                print("Seeded admin mock user: admin@donateai.org")
            except Exception as e:
                db.rollback()
                print(f"Failed to seed admin: {e}")

        # Seed default Demands for NGO Hope Foundation
        if not db.query(models.NGODemand).first():
            try:
                from datetime import date
                priya = db.query(models.User).filter(models.User.email == "priya@hopefoundation.org").first()
                if priya and priya.ngo_profile:
                    if not priya.ngo_profile.tenant_id:
                        tenant = models.Tenant(
                            name="Hope Foundation",
                            tenant_type="NGO",
                            slug="hope-foundation",
                            is_active=True
                        )
                        db.add(tenant)
                        db.flush()
                        priya.ngo_profile.tenant_id = tenant.id
                        db.commit()

                    demand = models.NGODemand(
                        tenant_id=priya.ngo_profile.tenant_id,
                        ngo_id=priya.id,
                        title="Urgent Textbooks and Clothing Need",
                        description="Looking for primary school mathematics textbooks and children's winter clothing.",
                        priority="HIGH",
                        status="OPEN",
                        city=priya.ngo_profile.city,
                        needed_by_date=date(2026, 8, 1)
                    )
                    db.add(demand)
                    db.flush()

                    item1 = models.NGODemandItem(
                        demand_id=demand.id,
                        item_name="Textbook",
                        category="Books",
                        quantity_needed=10,
                        minimum_condition="Good"
                    )
                    item2 = models.NGODemandItem(
                        demand_id=demand.id,
                        item_name="T-shirt",
                        category="Clothing",
                        quantity_needed=20,
                        minimum_condition="Fair"
                    )
                    db.add(item1)
                    db.add(item2)
                    db.commit()
                    print("Seeded default NGO demands for Hope Foundation")
            except Exception as e:
                db.rollback()
                print(f"Failed to seed demands: {e}")
    finally:
        db.close()

app = FastAPI(title="DonateAI Backend API")

# Configure CORS origins (allowing standard dev server localhosts)
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes routers
app.include_router(auth_routes.router)
app.include_router(detection_routes.router)
app.include_router(donation_routes.router)

def load_yolo_model():
    from config import settings
    try:
        from ultralytics import YOLO
        logger_name = "uvicorn.error"
        import logging
        logger = logging.getLogger(logger_name)
        logger.info(f"Loading YOLOv8 model from {settings.YOLO_MODEL_PATH}...")
        yolo_model.yolo_instance = YOLO(settings.YOLO_MODEL_PATH)
        logger.info(f"YOLOv8 model loaded successfully: {settings.YOLO_MODEL_PATH}")
    except Exception as e:
        yolo_model.yolo_error = str(e)
        yolo_model.yolo_instance = None
        import logging
        logger = logging.getLogger("uvicorn.error")
        logger.error(f"Failed to load YOLO model: {e}")

@app.on_event("startup")
def startup_event():
    run_seeder()
    load_yolo_model()

@app.get("/")
def read_root():
    return {"message": "Welcome to DonateAI API. Go to /docs for OpenAPI spec."}
