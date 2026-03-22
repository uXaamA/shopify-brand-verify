from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from models import OrderQR, Seller
from dependencies import get_current_seller
from qr_gen import generate_qr_image, generate_qr_base64

router = APIRouter(prefix="/orders", tags=["Orders"])


# ─────────────────────────────────────────────────────────────
# GET /orders
# List all orders with QR codes for the authenticated seller
# Shown in the merchant dashboard
# ─────────────────────────────────────────────────────────────
@router.get("")
async def get_my_orders(
    seller: Seller = Depends(get_current_seller),
    db:     Session = Depends(get_db)
):
    """
    Returns all orders for this seller, each with its QR hash and verify URL.
    The merchant sees this list in their app dashboard.
    They can click any order to get the printable QR.
    """
    orders = db.query(OrderQR).filter(
        OrderQR.seller_id == seller.id
    ).order_by(OrderQR.created_at.desc()).all()

    return {
        "seller":       seller.shop_name,
        "total_orders": len(orders),
        "orders": [
            {
                "id":             str(o.id),
                "shopify_order_id": o.shopify_order_id,
                "customer_name":  o.customer_name,
                "customer_email": o.customer_email,
                "order_total":    str(o.order_total) if o.order_total else None,
                "currency":       o.currency,
                "items":          o.line_items,
                "shipping_to":    o.shipping_address,
                "qr_hash":        o.qr_hash,
                "verify_url": f"https://shopify-brand-verify-vercel.vercel.app/verify/{o.qr_hash}",
                "created_at":     str(o.created_at),
            }
            for o in orders
        ]
    }


# ─────────────────────────────────────────────────────────────
# GET /orders/{order_id}/qr/image
# Returns the QR code as a PNG image file
# Merchant downloads and prints this on the packing slip
# ─────────────────────────────────────────────────────────────
@router.get("/{order_id}/qr/image")
async def get_qr_image(
    order_id: str,
    seller:   Seller = Depends(get_current_seller),
    db:       Session = Depends(get_db)
):
    """
    Returns the QR code as a downloadable PNG image.
    Merchant prints this and sticks it on the package.
    """
    order = db.query(OrderQR).filter(
        OrderQR.shopify_order_id == order_id,
        OrderQR.seller_id == seller.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    verify_url = f"https://shopify-brand-verify-vercel.vercel.app/verify/{o.qr_hash}"
    png_bytes  = generate_qr_image(verify_url)

    return Response(
        content      = png_bytes,
        media_type   = "image/png",
        headers      = {"Content-Disposition": f"attachment; filename=qr-{order_id}.png"}
    )


# ─────────────────────────────────────────────────────────────
# GET /orders/{order_id}/qr/base64
# Returns QR code as base64 string
# Used by the frontend to display QR inline without a separate request
# ─────────────────────────────────────────────────────────────
@router.get("/{order_id}/qr/base64")
async def get_qr_base64(
    order_id: str,
    seller:   Seller = Depends(get_current_seller),
    db:       Session = Depends(get_db)
):
    """
    Returns the QR code as a base64 encoded PNG string.
    Frontend displays it as: <img src="data:image/png;base64,{result}" />
    """
    order = db.query(OrderQR).filter(
        OrderQR.shopify_order_id == order_id,
        OrderQR.seller_id == seller.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    verify_url = f"https://shopify-brand-verify-vercel.vercel.app/verify/{o.qr_hash}"
    b64         = generate_qr_base64(verify_url)

    return {
        "order_id":   order_id,
        "qr_hash":    order.qr_hash,
        "verify_url": verify_url,
        "qr_base64":  b64,
        "img_tag":    f'<img src="data:image/png;base64,{b64}" alt="Order QR Code" />'
    }