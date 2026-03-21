from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, brands, webhooks, verify, orders, claims

app = FastAPI(
    title="Shopify Brand Verify",
    description="Brand registry and order QR verification for Shopify",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(brands.router)
app.include_router(webhooks.router)
app.include_router(verify.router)
app.include_router(orders.router)
app.include_router(claims.router)


@app.get("/", tags=["Health"])
def health_check():
    return {
        "status":   "running",
        "app":      "Shopify Brand Verify",
        "version":  "1.0.0",
        "docs":     "/docs",
        "endpoints": {
            "auth":     "/auth/install, /auth/callback",
            "brands":   "/brands/check, /brands/register, /brands/mine",
            "orders":   "/orders, /orders/{id}/qr/image, /orders/{id}/qr/base64",
            "verify":   "/verify/{qr_hash}  ← PUBLIC",
            "claims":   "/claims/submit, /claims/status/{id}",
            "admin":    "/admin/claims  ← ADMIN ONLY",
            "webhooks": "/webhooks/orders/create  ← SHOPIFY ONLY",
        }
    }