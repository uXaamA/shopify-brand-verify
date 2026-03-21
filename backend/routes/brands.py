from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid

from database import get_db
from models import Brand, Seller
from dependencies import get_current_seller
from fuzzy import check_conflict

router = APIRouter(prefix="/brands", tags=["Brands"])


# ── REQUEST / RESPONSE SCHEMAS ─────────────────────────────
class BrandRegisterRequest(BaseModel):
    name: str


class BrandResponse(BaseModel):
    id:            str
    name:          str
    verified:      bool
    badge_type:    str
    registered_at: str
    seller_name:   Optional[str] = None

    class Config:
        from_attributes = True


# ── ENDPOINTS ──────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────
# GET /brands/check?name=Nike
# Check if a brand name is available BEFORE registering
# Used for live checking as merchant types in the form
# No auth required — public check
# ─────────────────────────────────────────────────────────────
@router.get("/check")
async def check_brand_name(
    name: str = Query(..., min_length=1, max_length=100),
    db:   Session = Depends(get_db)
):
    """
    Check if a brand name is available or conflicts with existing brands.
    Returns conflict details so frontend can warn the user live.
    """
    if not name.strip():
        raise HTTPException(status_code=400, detail="Brand name cannot be empty")

    # Get all existing brand names from DB
    existing = db.query(Brand.name).all()
    existing_names = [row.name for row in existing]

    result = check_conflict(name.strip(), existing_names)

    return {
        "name":              name.strip(),
        "available":         not result["conflict"],
        "conflict":          result["conflict"],
        "conflicting_brand": result.get("conflicting_brand"),
        "similarity":        result.get("similarity"),
        "reason":            result.get("reason"),
        "message":           result["message"],
    }



# ─────────────────────────────────────────────────────────────
# POST /brands/register
# Register a new brand name for the authenticated seller
# ─────────────────────────────────────────────────────────────
@router.post("/register")
async def register_brand(
    body:   BrandRegisterRequest,
    seller: Seller = Depends(get_current_seller),
    db:     Session = Depends(get_db)
):
    """
    Register a new brand name.
    Steps:
    1. Clean and validate the name
    2. Check it doesn't already exist (exact match)
    3. Run fuzzy conflict check against all existing brands
    4. If clear → save to DB with basic badge
    5. If conflict → return conflict info so frontend shows claim option
    """
    brand_name = body.name.strip()

    if not brand_name:
        raise HTTPException(status_code=400, detail="Brand name cannot be empty")

    if len(brand_name) > 100:
        raise HTTPException(status_code=400, detail="Brand name too long (max 100 characters)")

    # ── Check exact match first ──
    exact_match = db.query(Brand).filter(
        Brand.name.ilike(brand_name)   # case-insensitive
    ).first()

    if exact_match:
        if str(exact_match.seller_id) == str(seller.id):
            raise HTTPException(
                status_code=400,
                detail=f"You have already registered '{brand_name}'."
            )
        else:
            raise HTTPException(
                status_code=409,
                detail={
                    "error":             "brand_taken",
                    "message":           f"'{brand_name}' is already registered by another seller.",
                    "can_claim":         True,
                    "conflicting_brand": brand_name,
                }
            )

    # ── Run fuzzy conflict check ──
    existing_names = [row.name for row in db.query(Brand.name).all()]
    conflict = check_conflict(brand_name, existing_names)

    if conflict["conflict"]:
        raise HTTPException(
            status_code=409,
            detail={
                "error":             "brand_conflict",
                "message":           conflict["message"],
                "can_claim":         True,
                "conflicting_brand": conflict["conflicting_brand"],
                "similarity":        conflict.get("similarity"),
            }
        )

    # ── All clear — register the brand ──
    new_brand = Brand(
        name      = brand_name,
        seller_id = seller.id,
        verified  = False,
        badge_type= "basic",
    )
    db.add(new_brand)
    db.commit()
    db.refresh(new_brand)

    print(f"[Brands] Registered '{brand_name}' for seller: {seller.shop_name} ({seller.shopify_store_id})")

    return {
        "success":    True,
        "message":    f"'{brand_name}' has been registered successfully!",
        "brand": {
            "id":            str(new_brand.id),
            "name":          new_brand.name,
            "verified":      new_brand.verified,
            "badge_type":    new_brand.badge_type,
            "registered_at": str(new_brand.registered_at),
        }
    }


# ─────────────────────────────────────────────────────────────
# GET /brands/mine
# List all brands registered by the authenticated seller
# ─────────────────────────────────────────────────────────────
@router.get("/mine")
async def get_my_brands(
    seller: Seller = Depends(get_current_seller),
    db:     Session = Depends(get_db)
):
    """Return all brands owned by this seller."""
    brands = db.query(Brand).filter(Brand.seller_id == seller.id).all()

    return {
        "seller":      seller.shop_name,
        "total_brands": len(brands),
        "brands": [
            {
                "id":            str(b.id),
                "name":          b.name,
                "verified":      b.verified,
                "badge_type":    b.badge_type,
                "registered_at": str(b.registered_at),
            }
            for b in brands
        ]
    }


# ─────────────────────────────────────────────────────────────
# DELETE /brands/{brand_id}
# Delete a brand (only the owner can delete their own brand)
# ─────────────────────────────────────────────────────────────
@router.delete("/{brand_id}")
async def delete_brand(
    brand_id: str,
    seller:   Seller = Depends(get_current_seller),
    db:       Session = Depends(get_db)
):
    """Delete a brand. Seller can only delete their own brands."""
    try:
        brand_uuid = uuid.UUID(brand_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid brand ID format")

    brand = db.query(Brand).filter(Brand.id == brand_uuid).first()

    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    if str(brand.seller_id) != str(seller.id):
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own brands"
        )

    db.delete(brand)
    db.commit()

    print(f"[Brands] Deleted '{brand.name}' by seller: {seller.shop_name}")

    return {
        "success": True,
        "message": f"Brand '{brand.name}' has been deleted."
    }