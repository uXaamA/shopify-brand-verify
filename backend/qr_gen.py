import hashlib
import qrcode
import io
import base64
from datetime import datetime, timezone


def generate_qr_hash(order_id: str, seller_id: str) -> str:
    """
    Generate a unique, tamper-proof hash for an order.
    This hash is what gets encoded inside the QR code.

    Formula: SHA256(order_id + seller_id + timestamp)
    Result:  first 32 characters → short but unique enough

    Example:
        order_id  = "12345"
        seller_id = "7e151c29-9581-42f6-b734-91cbd70faeff"
        timestamp = "2026-03-20T19:00:00"
        hash      = "a3f9d2c1b8e7f4a2..."
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    raw       = f"{order_id}:{seller_id}:{timestamp}"
    full_hash = hashlib.sha256(raw.encode()).hexdigest()
    return full_hash[:32]   # 32 chars — short, unique, URL-safe


def generate_qr_image(verify_url: str) -> bytes:
    """
    Generate a QR code image that encodes the verification URL.
    Returns raw PNG bytes.

    The QR encodes:  https://yourapp.com/verify/abc123...
    Customer scans → opens browser → hits /verify/{hash} → sees seller info
    """
    qr = qrcode.QRCode(
        version        = 1,
        error_correction = qrcode.constants.ERROR_CORRECT_H,  # High error correction
        box_size       = 10,
        border         = 4,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


def generate_qr_base64(verify_url: str) -> str:
    """
    Same as generate_qr_image but returns base64 string.
    Useful for embedding QR directly in JSON API response.
    Frontend can display it as: <img src="data:image/png;base64,{result}" />
    """
    png_bytes = generate_qr_image(verify_url)
    return base64.b64encode(png_bytes).decode("utf-8")