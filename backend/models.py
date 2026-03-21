# FLOW:

# Seller installs app → stored in Seller
# Seller registers brand → stored in Brand
# Order happens → stored in OrderQR
# QR generated → customer scans
# If conflict → Claim is created
# Admin reviews → updates Brand.verified



from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base

from sqlalchemy import Enum


class Seller(Base):
    """
    Every Shopify merchant who installs the app.
    Created automatically during OAuth callback.
    """
    __tablename__ = "sellers"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shopify_store_id  = Column(String(255), unique=True, nullable=False)  # e.g. mystore.myshopify.com
    access_token      = Column(String(500), nullable=False)               # Shopify OAuth token
    shop_email        = Column(String(255))
    shop_name         = Column(String(255))
    is_active         = Column(Boolean, default=True)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    brands   = relationship("Brand",   back_populates="seller")
    orders   = relationship("OrderQR", back_populates="seller")
    claims   = relationship("Claim",   back_populates="claimant")


class Brand(Base):
    """
    Brand names registered by sellers.
    One seller → many brands.
    One brand → one seller.
    """
    __tablename__ = "brands"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name          = Column(String(255), unique=True, nullable=False)
    seller_id     = Column(UUID(as_uuid=True), ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    verified      = Column(Boolean, default=False)
    # badge_type    = Column(String(50), default="basic")   # basic / verified / official
    badge_type    = Column(Enum("basic", "verified", "official", name="badge_type_enum"),default="basic",nullable=False)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    seller = relationship("Seller", back_populates="brands")
    claims = relationship("Claim",  back_populates="brand")


class OrderQR(Base):
    """
    One row per Shopify order.
    Stores the unique QR hash printed on the package.
    """
    __tablename__ = "orders_qr"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shopify_order_id = Column(String(255), nullable=False)
    seller_id        = Column(UUID(as_uuid=True), ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    qr_hash          = Column(String(500), unique=True, nullable=False)
    customer_name    = Column(String(255))
    customer_email   = Column(String(255))
    order_total      = Column(Numeric(10, 2))
    currency         = Column(String(10), default="PKR")
    line_items       = Column(JSONB)       # product names + quantities
    shipping_address = Column(JSONB)       # delivery address
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    seller = relationship("Seller", back_populates="orders")


class Claim(Base):
    """
    Ownership claim requests.
    When a real brand wants to reclaim their name from a squatter.
    """
    __tablename__ = "claims"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id           = Column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    claimant_seller_id = Column(UUID(as_uuid=True), ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    business_name      = Column(String(255))
    ntn_number         = Column(String(100))
    docs_url           = Column(String(1000))     # GCP Storage URL
    website            = Column(String(500))
    notes              = Column(Text)
    # status             = Column(String(50), default="pending")  # pending / approved / rejected
    status             = Column(Enum("pending", "approved", "rejected", name="claim_status"),default="pending")
    submitted_at       = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at        = Column(DateTime(timezone=True))
    reviewed_by        = Column(String(255))

    # Relationships
    brand     = relationship("Brand",  back_populates="claims")
    claimant  = relationship("Seller", back_populates="claims")