# is a dependency function in FastAPI
# it runs before your API endpoint
# it identifies who is making the request (which seller)


from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Seller


async def get_current_seller(
    x_shopify_shop_domain: str = Header(..., description="Shopify store domain"),
    db: Session = Depends(get_db)
) -> Seller:
    """
    Dependency — identifies which seller is making the API request.

    Every request from the Shopify frontend includes the header:
        X-Shopify-Shop-Domain: phantom-intelligence.myshopify.com

    We use this to look up the seller in our DB and return their record.
    If the shop is not found (not installed), we return 401.

    Usage in any route:
        seller: Seller = Depends(get_current_seller)
    """
    seller = db.query(Seller).filter(
        Seller.shopify_store_id == x_shopify_shop_domain,
        Seller.is_active == True
    ).first()

    if not seller:
        raise HTTPException(
            status_code=401,
            detail=f"Shop '{x_shopify_shop_domain}' is not registered. Please install the app first."
        )

    return seller