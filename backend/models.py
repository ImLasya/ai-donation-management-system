from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Text, BigInteger, Integer, Float, Date, UniqueConstraint, CheckConstraint, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    tenant_type = Column(String(50), default="NGO", nullable=False)  # "PLATFORM" / "NGO"
    slug = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class UserRole(str, enum.Enum):
    DONOR = "DONOR"
    NGO = "NGO"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, name="user_role", create_type=False), nullable=False)
    is_active = Column(Boolean, default=True)
    email_notifications_enabled = Column(Boolean, default=True, server_default='true', nullable=False)
    inapp_notifications_enabled = Column(Boolean, default=True, server_default='true', nullable=False)
    password_reset_token = Column(String(256), nullable=True, index=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    donor_profile = relationship("DonorProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    ngo_profile = relationship("NGOProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class DonorProfile(Base):
    __tablename__ = "donor_profiles"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="donor_profile")

class NGOProfile(Base):
    __tablename__ = "ngo_profiles"

    id = Column(BigInteger, primary_key=True, index=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    organization_name = Column(String(200), nullable=False)
    registration_number = Column(String(100), unique=True, nullable=False)
    contact_person = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False)
    mission = Column(Text, nullable=False)
    verification_status = Column(String(30), default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="ngo_profile")
    tenant = relationship("Tenant")
    focus_areas = relationship("NGOFocusArea", back_populates="ngo", cascade="all, delete-orphan")

class NGOFocusArea(Base):
    __tablename__ = "ngo_focus_areas"

    id = Column(BigInteger, primary_key=True, index=True)
    ngo_id = Column(BigInteger, ForeignKey("ngo_profiles.id", ondelete="CASCADE"), nullable=False)
    focus_area = Column(String(100), nullable=False)

    __table_args__ = (UniqueConstraint("ngo_id", "focus_area", name="ngo_focus_areas_ngo_id_focus_area_key"),)

    ngo = relationship("NGOProfile", back_populates="focus_areas")

# ----------------- NEW WORKFLOW TABLES -----------------

class Donation(Base):
    __tablename__ = "donations"

    id = Column(BigInteger, primary_key=True, index=True)
    donor_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ngo_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(50), default="DRAFT", nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    items = relationship("DonationItem", back_populates="donation", cascade="all, delete-orphan")
    requests = relationship("DonationRequest", back_populates="donation", cascade="all, delete-orphan")
    status_history = relationship("DonationStatusHistory", back_populates="donation", cascade="all, delete-orphan")
    pickup_schedule = relationship("PickupSchedule", back_populates="donation", uselist=False, cascade="all, delete-orphan")

class DonationItem(Base):
    __tablename__ = "donation_items"

    id = Column(BigInteger, primary_key=True, index=True)
    donation_id = Column(BigInteger, ForeignKey("donations.id", ondelete="CASCADE"), nullable=False, index=True)
    item_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    condition = Column(String(50), nullable=False)
    confidence_score = Column(Float, nullable=True)
    source = Column(String(50), nullable=False) # "AI" or "MANUAL"
    notes = Column(Text, nullable=True)
    embedding = Column(ARRAY(Float), nullable=True)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="donation_items_quantity_check"),
        CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="donation_items_confidence_check"),
    )

    donation = relationship("Donation", back_populates="items")

class DonationRequest(Base):
    __tablename__ = "donation_requests"

    id = Column(BigInteger, primary_key=True, index=True)
    donation_id = Column(BigInteger, ForeignKey("donations.id", ondelete="CASCADE"), nullable=False, index=True)
    donor_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ngo_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="PENDING", nullable=False, index=True) # "PENDING", "ACCEPTED", "REJECTED"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    donation = relationship("Donation", back_populates="requests")

class DonationStatusHistory(Base):
    __tablename__ = "donation_status_history"

    id = Column(BigInteger, primary_key=True, index=True)
    donation_id = Column(BigInteger, ForeignKey("donations.id", ondelete="CASCADE"), nullable=False, index=True)
    old_status = Column(String(50), nullable=False)
    new_status = Column(String(50), nullable=False)
    changed_by_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    donation = relationship("Donation", back_populates="status_history")

class PickupSchedule(Base):
    __tablename__ = "pickup_schedules"

    id = Column(BigInteger, primary_key=True, index=True)
    donation_id = Column(BigInteger, ForeignKey("donations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    pickup_date = Column(Date, nullable=False)
    time_slot = Column(String(100), nullable=False)
    pickup_address = Column(Text, nullable=False)
    contact_phone = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    reminder_status = Column(String(50), default="PENDING", server_default='PENDING', nullable=False)
    volunteer_name = Column(String(255), nullable=True)
    volunteer_phone = Column(String(50), nullable=True)
    volunteer_email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    donation = relationship("Donation", back_populates="pickup_schedule")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False) # "REQUEST", "ACCEPT", "REJECT", "PICKUP"
    related_request_id = Column(BigInteger, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    deduplication_key = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")

class NGODemand(Base):
    __tablename__ = "ngo_demands"

    id = Column(BigInteger, primary_key=True, index=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    ngo_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(50), default="MEDIUM", nullable=False) # "LOW", "MEDIUM", "HIGH", "URGENT"
    status = Column(String(50), default="OPEN", nullable=False) # "OPEN", "PARTIALLY_FULFILLED", "FULFILLED", "CLOSED"
    city = Column(String(100), nullable=False)
    needed_by_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    items = relationship("NGODemandItem", back_populates="demand", cascade="all, delete-orphan")
    ngo = relationship("User")
    tenant = relationship("Tenant")

class NGODemandItem(Base):
    __tablename__ = "ngo_demand_items"

    id = Column(BigInteger, primary_key=True, index=True)
    demand_id = Column(BigInteger, ForeignKey("ngo_demands.id", ondelete="CASCADE"), nullable=False, index=True)
    item_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    quantity_needed = Column(Integer, nullable=False)
    quantity_fulfilled = Column(Integer, default=0, nullable=False)
    minimum_condition = Column(String(50), nullable=True)
    embedding = Column(ARRAY(Float), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    demand = relationship("NGODemand", back_populates="items")

class PackagingRecord(Base):
    __tablename__ = "packaging_records"

    id = Column(BigInteger, primary_key=True, index=True)
    donation_id = Column(BigInteger, ForeignKey("donations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    packaging_status = Column(String(50), default="COMPLETED", nullable=False)
    package_count = Column(Integer, default=1, nullable=False)
    packaging_notes = Column(Text, nullable=True)
    completed_items = Column(Text, nullable=True) # JSON-serialized list of checkbox keys
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    donation = relationship("Donation")

class DonationMatch(Base):
    __tablename__ = "donation_matches"

    id = Column(BigInteger, primary_key=True, index=True)
    donation_id = Column(BigInteger, ForeignKey("donations.id", ondelete="CASCADE"), nullable=False, index=True)
    ngo_id = Column(BigInteger, ForeignKey("ngo_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    demand_id = Column(BigInteger, ForeignKey("ngo_demands.id", ondelete="CASCADE"), nullable=False, index=True)
    final_score = Column(Float, nullable=False)
    item_match_score = Column(Float, nullable=False)
    quantity_fit_score = Column(Float, nullable=False)
    geographic_score = Column(Float, nullable=False)
    priority_score = Column(Float, nullable=False)
    matched_items_count = Column(Integer, nullable=False)
    match_explanation = Column(Text, nullable=False) # JSON-serialized explanation
    status = Column(String(50), default="ACTIVE", nullable=False, index=True) # "ACTIVE", "NOTIFIED", "SELECTED", "EXPIRED"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("donation_id", "ngo_id", "demand_id", name="uq_donation_match_key"),
    )

    donation = relationship("Donation")
    ngo = relationship("NGOProfile")
    tenant = relationship("Tenant")
    demand = relationship("NGODemand")
