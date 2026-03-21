import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timezone

from database import get_db
from models import Claim, Brand, Seller
from dependencies import get_current_seller

router = APIRouter(tags=["Claims"])


# ── SCHEMAS ────────────────────────────────────────────────
class ClaimSubmitRequest(BaseModel):
    brand_id:      str
    business_name: str
    ntn_number:    str
    website:       Optional[str] = None
    docs_url:      Optional[str] = None   # GCP Storage URL (uploaded separately)


class ClaimReviewRequest(BaseModel):
    status: str   # "approved" or "rejected"
    notes:  Optional[str] = None


# ── SELLER ROUTES ──────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# POST /claims/submit
# Seller submits an ownership claim for a brand already taken
# ─────────────────────────────────────────────────────────────
@router.post("/claims/submit")
async def submit_claim(
    body:   ClaimSubmitRequest,
    seller: Seller = Depends(get_current_seller),
    db:     Session = Depends(get_db)
):
    """
    Submit an ownership claim for a brand already registered by someone else.

    Flow:
    1. Seller sees "Claim Official Ownership" button after conflict
    2. Fills in: business name, NTN number, website, doc URL
    3. We save the claim as 'pending'
    4. Admin reviews it manually in /admin/claims
    5. If approved → brand transferred, old owner notified
    """
    # Validate brand exists
    try:
        brand_uuid = uuid.UUID(body.brand_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid brand ID")

    brand = db.query(Brand).filter(Brand.id == brand_uuid).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Can't claim your own brand
    if str(brand.seller_id) == str(seller.id):
        raise HTTPException(status_code=400, detail="You already own this brand")

    # Check if already submitted a pending claim
    existing = db.query(Claim).filter(
        Claim.brand_id == brand_uuid,
        Claim.claimant_seller_id == seller.id,
        Claim.status == "pending"
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="You already have a pending claim for this brand. Please wait for admin review."
        )

    # Save the claim
    claim = Claim(
        brand_id           = brand_uuid,
        claimant_seller_id = seller.id,
        business_name      = body.business_name,
        ntn_number         = body.ntn_number,
        website            = body.website,
        docs_url           = body.docs_url,
        status             = "pending",
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)

    print(f"[Claims] New claim submitted by {seller.shop_name} for brand '{brand.name}'")

    return {
        "success":  True,
        "message":  f"Your ownership claim for '{brand.name}' has been submitted. We will review it within 3-5 business days.",
        "claim_id": str(claim.id),
        "status":   "pending",
    }


# ─────────────────────────────────────────────────────────────
# GET /claims/status/{claim_id}
# Seller checks status of their submitted claim
# ─────────────────────────────────────────────────────────────
@router.get("/claims/status/{claim_id}")
async def get_claim_status(
    claim_id: str,
    seller:   Seller = Depends(get_current_seller),
    db:       Session = Depends(get_db)
):
    """Check the current status of a submitted ownership claim."""
    try:
        claim_uuid = uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID")

    claim = db.query(Claim).filter(
        Claim.id == claim_uuid,
        Claim.claimant_seller_id == seller.id
    ).first()

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    brand = db.query(Brand).filter(Brand.id == claim.brand_id).first()

    return {
        "claim_id":     str(claim.id),
        "brand_name":   brand.name if brand else None,
        "status":       claim.status,
        "submitted_at": str(claim.submitted_at),
        "reviewed_at":  str(claim.reviewed_at) if claim.reviewed_at else None,
        "notes":        claim.notes,
        "message": {
            "pending":  "Your claim is under review. We will notify you within 3-5 business days.",
            "approved": "✅ Your claim has been approved! You are now the verified owner of this brand.",
            "rejected": f"❌ Your claim was rejected. Reason: {claim.notes or 'No reason provided'}",
        }.get(claim.status, "Unknown status")
    }


# ── ADMIN ROUTES ───────────────────────────────────────────

ADMIN_SECRET = "admin-secret-change-this-in-production"

def verify_admin(x_admin_secret: str = Header(...)):
    """Simple admin auth — replace with proper auth in production."""
    if x_admin_secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Admin access required")


# ─────────────────────────────────────────────────────────────
# GET /admin/claims
# Admin sees all pending claims for review
# ─────────────────────────────────────────────────────────────
@router.get("/admin/claims")
async def list_all_claims(
    status: Optional[str] = "pending",
    db:     Session = Depends(get_db),
    _:      None    = Depends(verify_admin)
):
    """
    Admin endpoint — list all claims filtered by status.
    Default: show pending claims only.
    """
    query = db.query(Claim)
    if status:
        query = query.filter(Claim.status == status)

    claims = query.order_by(Claim.submitted_at.desc()).all()

    result = []
    for claim in claims:
        brand    = db.query(Brand).filter(Brand.id == claim.brand_id).first()
        claimant = db.query(Seller).filter(Seller.id == claim.claimant_seller_id).first()
        current_owner = db.query(Seller).filter(Seller.id == brand.seller_id).first() if brand else None

        result.append({
            "claim_id":          str(claim.id),
            "brand_name":        brand.name if brand else None,
            "current_owner":     current_owner.shop_name if current_owner else None,
            "current_owner_store": current_owner.shopify_store_id if current_owner else None,
            "claimant_name":     claimant.shop_name if claimant else None,
            "claimant_store":    claimant.shopify_store_id if claimant else None,
            "business_name":     claim.business_name,
            "ntn_number":        claim.ntn_number,
            "website":           claim.website,
            "docs_url":          claim.docs_url,
            "status":            claim.status,
            "submitted_at":      str(claim.submitted_at),
            "reviewed_at":       str(claim.reviewed_at) if claim.reviewed_at else None,
            "notes":             claim.notes,
        })

    return {
        "total":  len(result),
        "status": status,
        "claims": result,
    }


# ─────────────────────────────────────────────────────────────
# PATCH /admin/claims/{claim_id}
# Admin approves or rejects a claim
# ─────────────────────────────────────────────────────────────
@router.patch("/admin/claims/{claim_id}")
async def review_claim(
    claim_id: str,
    body:     ClaimReviewRequest,
    db:       Session = Depends(get_db),
    _:        None    = Depends(verify_admin)
):
    """
    Admin approves or rejects a claim.

    If APPROVED:
    - brand.seller_id → transferred to claimant
    - brand.verified  → True
    - brand.badge_type → 'official'
    - claim.status → 'approved'

    If REJECTED:
    - claim.status → 'rejected'
    - claim.notes  → reason
    - brand stays with current owner
    """
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")

    try:
        claim_uuid = uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID")

    claim = db.query(Claim).filter(Claim.id == claim_uuid).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if claim.status != "pending":
        raise HTTPException(status_code=400, detail=f"Claim is already {claim.status}")

    brand = db.query(Brand).filter(Brand.id == claim.brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # ── Update claim ──
    claim.status      = body.status
    claim.notes       = body.notes
    claim.reviewed_at = datetime.now(timezone.utc)
    claim.reviewed_by = "admin"

    if body.status == "approved":
        # Transfer brand ownership to claimant
        old_owner        = brand.seller_id
        brand.seller_id  = claim.claimant_seller_id
        brand.verified   = True
        brand.badge_type = "official"

        print(f"[Claims] Brand '{brand.name}' transferred from {old_owner} to {claim.claimant_seller_id}")

        db.commit()
        return {
            "success": True,
            "message": f"✅ Claim approved. '{brand.name}' is now owned by the claimant with 'official' badge.",
            "brand":   brand.name,
            "status":  "approved",
        }

    else:
        db.commit()
        return {
            "success": True,
            "message": f"❌ Claim rejected. '{brand.name}' remains with its current owner.",
            "brand":   brand.name,
            "status":  "rejected",
            "reason":  body.notes,
        }