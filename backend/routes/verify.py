from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import OrderQR, Seller, Brand

router = APIRouter(prefix="/verify", tags=["Verify"])


@router.get("/{qr_hash}")
async def verify_order(
    qr_hash: str = Path(..., min_length=8, max_length=64),
    db: Session = Depends(get_db)
):
    """
    PUBLIC endpoint — no authentication required.
    Called when a customer scans the QR code on their package.

    Returns everything the customer needs to verify their order:
    - Seller name and store
    - Brand name and verified status
    - Order details
    - Whether this is a verified/trusted seller

    This is the CORE feature of the entire app.
    """

    # ── Look up the QR hash ──
    order = db.query(OrderQR).filter(OrderQR.qr_hash == qr_hash).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail={
                "verified":  False,
                "message":   "This QR code is not valid or has been tampered with.",
                "warning":   "Do not accept this package. Contact the seller directly.",
            }
        )

    # ── Get seller info ──
    seller = db.query(Seller).filter(Seller.id == order.seller_id).first()

    if not seller or not seller.is_active:
        raise HTTPException(
            status_code=404,
            detail={
                "verified": False,
                "message":  "This seller's account is no longer active.",
            }
        )

    # ── Get brand info (if seller has registered brands) ──
    brand = db.query(Brand).filter(Brand.seller_id == seller.id).first()

    # ── Build response ──
    return {
        "verified":     True,
        "status":       "authentic",
        "message":      "✅ This package is from a registered seller on Shopify Brand Verify.",

        "seller": {
            "store_name":  seller.shop_name,
            "store_id":    seller.shopify_store_id,
            "email":       seller.shop_email,
        },

        "brand": {
            "name":        brand.name       if brand else None,
            "verified":    brand.verified   if brand else False,
            "badge_type":  brand.badge_type if brand else None,
        } if brand else None,

        "order": {
            "order_id":        order.shopify_order_id,
            "customer_name":   order.customer_name,
            "order_total":     str(order.order_total) if order.order_total else None,
            "currency":        order.currency,
            "items":           order.line_items,
            "shipping_to":     order.shipping_address,
            "verified_at":     str(order.created_at),
        },
    }