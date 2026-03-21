import React from 'react';
import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { publicApi } from '../api/client';

const styles = `
  * { box-sizing: border-box; margin: 0; padding: 0; }

  body { background: #0f0f0f; color: #f0f0f0; }

  .verify-root {
    min-height: 100vh;
    background: #0f0f0f;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0 0 40px 0;
  }

  .status-banner {
    width: 100%;
    padding: 28px 24px 24px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }
  .status-banner.verified { background: linear-gradient(135deg, #0d6e3d, #198754); }
  .status-banner.invalid { background: linear-gradient(135deg, #7f1d1d, #dc2626); }
  .status-banner.loading { background: #1a1a2e; }

  .status-icon { font-size: 52px; line-height: 1; }
  .status-title { font-size: 22px; font-weight: 800; color: #fff; letter-spacing: 1px; text-transform: uppercase; }
  .status-message { font-size: 15px; color: rgba(255,255,255,0.85); max-width: 320px; }

  .content { width: 100%; max-width: 480px; padding: 24px 16px 0; }

  .info-card {
    background: #1a1a2e;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 14px;
    border: 1px solid #2a2a4a;
  }

  .card-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #6b7280;
    font-weight: 600;
    margin-bottom: 6px;
  }

  .card-value {
    font-size: 17px;
    font-weight: 600;
    color: #f0f0f0;
    line-height: 1.3;
  }

  .card-value.large { font-size: 22px; font-weight: 800; color: #fff; }

  .badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }
  .badge.basic { background: #374151; color: #d1d5db; }
  .badge.verified { background: #1d4ed8; color: #bfdbfe; }
  .badge.official { background: #065f46; color: #6ee7b7; }

  .items-list { list-style: none; }
  .items-list li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid #2a2a4a;
    font-size: 15px;
    color: #e5e7eb;
  }
  .items-list li:last-child { border-bottom: none; }
  .item-qty {
    background: #374151;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 12px;
    color: #9ca3af;
  }

  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .loading-spinner {
    width: 40px; height: 40px;
    border: 3px solid #2a2a4a;
    border-top-color: #e94560;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 40px auto;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .footer {
    text-align: center;
    padding: 24px 16px 0;
    font-size: 12px;
    color: #4b5563;
  }
`;

function getBadgeClass(badgeType) {
  if (badgeType === 'verified') return 'verified';
  if (badgeType === 'official') return 'official';
  return 'basic';
}

function BadgeLabel({ badgeType }) {
  const labels = { basic: 'Registered Seller', verified: 'Verified Seller', official: 'Official Brand ✓' };
  return (
    <span className={`badge ${getBadgeClass(badgeType)}`}>
      {labels[badgeType] || badgeType}
    </span>
  );
}

function formatDate(str) {
  if (!str) return '—';
  return new Date(str).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

export default function VerifyPage() {
  const { hash } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function verify() {
      try {
        const res = await publicApi.get(`/verify/${hash}`);
        setData(res.data);
      } catch (err) {
        if (err.response?.status === 404) {
          setData({ verified: false, message: 'This QR code is not valid or has been tampered with.' });
        } else {
          setData({ verified: false, message: 'Could not verify this QR code. Please try again.' });
        }
      } finally {
        setLoading(false);
      }
    }
    if (hash) verify();
  }, [hash]);

  return (
    <>
      <style>{styles}</style>
      <div className="verify-root">
        {loading ? (
          <>
            <div className="status-banner loading">
              <div className="status-title">Verifying...</div>
              <div className="status-message">Please wait while we check this package.</div>
            </div>
            <div className="loading-spinner" />
          </>
        ) : !data?.verified ? (
          <>
            <div className="status-banner invalid">
              <div className="status-icon">❌</div>
              <div className="status-title">Invalid QR Code</div>
              <div className="status-message">{data?.message || 'This QR code could not be verified.'}</div>
            </div>
            <div className="content">
              <div className="info-card">
                <div className="card-label">What does this mean?</div>
                <div className="card-value" style={{ fontSize: '14px', fontWeight: 400, color: '#d1d5db' }}>
                  This QR code is either invalid, expired, or may have been tampered with.
                  If you received this package from a seller, please contact them for clarification.
                </div>
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="status-banner verified">
              <div className="status-icon">✅</div>
              <div className="status-title">Verified Authentic</div>
              <div className="status-message">{data.message || 'This package is from a registered seller.'}</div>
            </div>

            <div className="content">
              {/* Seller */}
              <div className="info-card">
                <div className="card-label">Seller</div>
                <div className="card-value large">{data.seller?.store_name || '—'}</div>
                {data.brand && (
                  <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '15px', color: '#d1d5db' }}>{data.brand.name}</span>
                    <BadgeLabel badgeType={data.brand.badge_type} />
                  </div>
                )}
              </div>

              {/* Order Info */}
              {data.order && (
                <>
                  <div className="grid-2">
                    <div className="info-card">
                      <div className="card-label">Order ID</div>
                      <div className="card-value">#{data.order.order_id}</div>
                    </div>
                    <div className="info-card">
                      <div className="card-label">Order Total</div>
                      <div className="card-value">${data.order.order_total} {data.order.currency}</div>
                    </div>
                  </div>

                  <div className="info-card">
                    <div className="card-label">Customer</div>
                    <div className="card-value">{data.order.customer_name}</div>
                  </div>

                  <div className="grid-2">
                    <div className="info-card">
                      <div className="card-label">Ship To</div>
                      <div className="card-value">
                        {data.order.shipping_to?.city || '—'}, {data.order.shipping_to?.country || ''}
                      </div>
                    </div>
                    <div className="info-card">
                      <div className="card-label">Verified At</div>
                      <div className="card-value" style={{ fontSize: '14px' }}>{formatDate(data.order.verified_at)}</div>
                    </div>
                  </div>

                  {data.order.items && data.order.items.length > 0 && (
                    <div className="info-card">
                      <div className="card-label">Products</div>
                      <ul className="items-list" style={{ marginTop: '8px' }}>
                        {data.order.items.map((item, i) => (
                          <li key={i}>
                            <span>{item.name}</span>
                            <span className="item-qty">x{item.quantity}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </div>
          </>
        )}

        <div className="footer">
          Powered by Shopify Brand Verify &nbsp;·&nbsp; phantom-intelligence.myshopify.com
        </div>
      </div>
    </>
  );
}