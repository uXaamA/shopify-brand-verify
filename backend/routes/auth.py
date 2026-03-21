import hmac
import hashlib
import base64
import httpx
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import Seller

router = APIRouter(prefix="/auth", tags=["Auth"])

SHOPIFY_API_VERSION = "2026-01"


@router.get("/install")
async def install(shop: str):
    """Step 1 — Redirect merchant to Shopify consent screen."""
    shop = unquote(shop)

    if not shop.endswith(".myshopify.com"):
        raise HTTPException(status_code=400, detail="Invalid shop domain")

    scopes       = "read_orders,write_orders,read_products"
    redirect_uri = f"{settings.SHOPIFY_APP_URL}/auth/callback"

    oauth_url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={settings.SHOPIFY_API_KEY}"
        f"&scope={scopes}"
        f"&redirect_uri={redirect_uri}"
    )

    return RedirectResponse(oauth_url)


@router.get("/callback")
async def callback(shop: str, code: str, db: Session = Depends(get_db)):
    """Step 2 — Exchange code for access_token, save seller to DB."""

    # Decode URL-encoded shop name (Shopify sometimes encodes dashes)
    shop = unquote(shop)

    if not shop.endswith(".myshopify.com"):
        raise HTTPException(status_code=400, detail="Invalid shop domain")

    # ── Exchange code for permanent access_token ──
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id":     settings.SHOPIFY_API_KEY,
                "client_secret": settings.SHOPIFY_API_SECRET,
                "code":          code,
            },
            headers={"Content-Type": "application/json"}
        )

    print(f"[OAuth] Token exchange status: {response.status_code}")
    print(f"[OAuth] Response: {response.text[:200]}")

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Token exchange failed: {response.text[:300]}"
        )

    access_token = response.json().get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access_token in Shopify response")

    # ── Fetch store info ──
    shop_info = await _get_shop_info(shop, access_token)
    print(f"[OAuth] Shop: {shop_info.get('name')} / {shop_info.get('email')}")

    # ── Save or update seller in DB ──
    seller = db.query(Seller).filter(Seller.shopify_store_id == shop).first()

    if seller:
        seller.access_token = access_token
        seller.shop_email   = shop_info.get("email")
        seller.shop_name    = shop_info.get("name")
        seller.is_active    = True
        print(f"[OAuth] Updated existing seller: {shop}")
    else:
        seller = Seller(
            shopify_store_id = shop,
            access_token     = access_token,
            shop_email       = shop_info.get("email"),
            shop_name        = shop_info.get("name"),
        )
        db.add(seller)
        print(f"[OAuth] Created new seller: {shop}")

    db.commit()
    db.refresh(seller)
    print(f"[OAuth] SUCCESS — Seller saved. ID: {seller.id}")

    # ── Register webhook so we get order events ──
    await _register_order_webhook(shop, access_token)

    # ── Redirect merchant back into the app ──
    return RedirectResponse(
        f"https://{shop}/admin/apps/{settings.SHOPIFY_API_KEY}"
    )


async def _get_shop_info(shop: str, access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}/shop.json",
            headers={"X-Shopify-Access-Token": access_token}
        )
    return r.json().get("shop", {}) if r.status_code == 200 else {}


async def _register_order_webhook(shop: str, access_token: str):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}/webhooks.json",
            headers={"X-Shopify-Access-Token": access_token},
            json={"webhook": {
                "topic":   "orders/create",
                "address": f"{settings.SHOPIFY_APP_URL}/webhooks/orders/create",
                "format":  "json",
            }}
        )
    if r.status_code == 201:
        print(f"[Webhook] Registered for {shop}")
    elif r.status_code == 422:
        print(f"[Webhook] Already registered for {shop}")
    else:
        print(f"[Webhook] Warning: {r.text[:200]}")


def verify_shopify_hmac(data: bytes, hmac_header: str) -> bool:
    digest   = hmac.new(
        settings.SHOPIFY_API_SECRET.encode("utf-8"),
        data,
        hashlib.sha256
    ).digest()
    computed = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed, hmac_header)