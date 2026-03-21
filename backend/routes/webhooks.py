import json
import hmac
import hashlib
import base64

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import Seller, OrderQR
from qr_gen import generate_qr_hash, generate_qr_base64

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def verify_shopify_hmac(body: bytes, hmac_header: str) -> bool:
    """
    Verify the webhook actually came from Shopify.
    Shopify signs every webhook with your API secret.
    If verification fails → reject the request immediately.
    """
    digest   = hmac.new(
        settings.SHOPIFY_API_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()
    computed = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed, hmac_header)


@router.post("/orders/create")
async def handle_order_created(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Shopify calls this endpoint every time an order is placed
    in any store that has our app installed.

    What we do:
    1. Verify the HMAC signature (security)
    2. Parse the order data
    3. Find the seller in our DB
    4. Generate a unique QR hash
    5. Save order + QR hash to orders_qr table
    6. Return 200 OK to Shopify (important — Shopify retries if we don't respond 200)
    """
    body        = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256", "")
    shop_domain = request.headers.get("X-Shopify-Shop-Domain", "")

    # ── Step 1: Verify HMAC ──
    if not verify_shopify_hmac(body, hmac_header):
        print(f"[Webhook] HMAC verification FAILED for shop: {shop_domain}")
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")

    # ── Step 2: Parse order data ──
    try:
        order = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    order_id       = str(order.get("id", ""))
    shopify_order_id = str(order.get("order_number", order_id))
    customer       = order.get("customer", {})
    shipping       = order.get("shipping_address", {})
    line_items     = order.get("line_items", [])

    print(f"[Webhook] Order received: #{shopify_order_id} from {shop_domain}")

    # ── Step 3: Find seller ──
    seller = db.query(Seller).filter(
        Seller.shopify_store_id == shop_domain,
        Seller.is_active == True
    ).first()

    if not seller:
        print(f"[Webhook] Seller not found for shop: {shop_domain}")
        # Return 200 anyway — Shopify doesn't need to know our internal state
        return {"status": "seller_not_found"}

    # ── Step 4: Generate unique QR hash ──
    qr_hash = generate_qr_hash(order_id, str(seller.id))

    # Build the public verification URL
    verify_url = f"{settings.SHOPIFY_APP_URL}/verify/{qr_hash}"

    # ── Step 5: Save to orders_qr table ──
    # Check if this order already has a QR (avoid duplicates on retry)
    existing = db.query(OrderQR).filter(
        OrderQR.shopify_order_id == order_id,
        OrderQR.seller_id == seller.id
    ).first()

    if existing:
        print(f"[Webhook] Order #{shopify_order_id} already has QR — skipping")
        return {"status": "already_exists", "qr_hash": existing.qr_hash}

    new_order = OrderQR(
        shopify_order_id = order_id,
        seller_id        = seller.id,
        qr_hash          = qr_hash,
        customer_name    = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
        customer_email   = customer.get("email", ""),
        order_total      = order.get("total_price"),
        currency         = order.get("currency", "PKR"),
        line_items       = [
            {
                "name":     item.get("name"),
                "quantity": item.get("quantity"),
                "price":    item.get("price"),
            }
            for item in line_items
        ],
        shipping_address = {
            "name":    shipping.get("name"),
            "address": shipping.get("address1"),
            "city":    shipping.get("city"),
            "country": shipping.get("country"),
            "zip":     shipping.get("zip"),
        } if shipping else None,
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    print(f"[Webhook] QR generated for order #{shopify_order_id} — hash: {qr_hash}")
    print(f"[Webhook] Verify URL: {verify_url}")

    # ── Step 6: Return 200 to Shopify ──
    return {
        "status":     "ok",
        "order_id":   shopify_order_id,
        "qr_hash":    qr_hash,
        "verify_url": verify_url,
    }