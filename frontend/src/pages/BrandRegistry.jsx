import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Page, Card, TextField, Button, Banner, Badge, DataTable,
  EmptyState, Spinner, BlockStack, InlineStack, Text, Divider,
} from '@shopify/polaris';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';

function getBadgeProps(badgeType) {
  switch (badgeType) {
    case 'verified': return { tone: 'info', label: 'Verified Seller' };
    case 'official': return { tone: 'success', label: 'Official Brand ✓' };
    default: return { tone: undefined, label: 'Registered Seller' };
  }
}

export default function BrandRegistry() {
  const navigate = useNavigate();
  const [brandName, setBrandName] = useState('');
  const [checkStatus, setCheckStatus] = useState(null); // null | 'checking' | 'available' | 'conflict'
  const [checkMessage, setCheckMessage] = useState('');
  const [conflictData, setConflictData] = useState(null);
  const [registering, setRegistering] = useState(false);
  const [registerSuccess, setRegisterSuccess] = useState(null);
  const [registerError, setRegisterError] = useState(null);
  const [brands, setBrands] = useState([]);
  const [loadingBrands, setLoadingBrands] = useState(true);
  const debounceRef = useRef(null);

  // Load registered brands on mount
  useEffect(() => {
    loadBrands();
  }, []);

  async function loadBrands() {
    setLoadingBrands(true);
    try {
      const res = await api.get('/brands/mine');
      setBrands(res.data.brands || []);
    } catch {
      setBrands([]);
    } finally {
      setLoadingBrands(false);
    }
  }

  // Live conflict check debounced 500ms
  const handleBrandNameChange = useCallback((value) => {
    setBrandName(value);
    setRegisterSuccess(null);
    setRegisterError(null);
    setConflictData(null);

    if (!value.trim()) {
      setCheckStatus(null);
      setCheckMessage('');
      return;
    }

    setCheckStatus('checking');
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await api.get(`/brands/check?name=${encodeURIComponent(value.trim())}`);
        const data = res.data;
        if (data.available) {
          setCheckStatus('available');
          setCheckMessage(data.message || `'${value}' is available`);
        } else {
          setCheckStatus('conflict');
          setCheckMessage(data.message || `'${value}' is not available`);
          setConflictData(data);
        }
      } catch {
        setCheckStatus(null);
        setCheckMessage('');
      }
    }, 500);
  }, []);

  async function handleRegister() {
    if (!brandName.trim()) return;
    setRegistering(true);
    setRegisterSuccess(null);
    setRegisterError(null);
    try {
      const res = await api.post('/brands/register', { name: brandName.trim() });
      setRegisterSuccess(res.data.message || 'Brand registered successfully!');
      setBrandName('');
      setCheckStatus(null);
      setCheckMessage('');
      loadBrands();
    } catch (error) {
      if (error.response?.status === 409) {
        const detail = error.response.data.detail;
        setConflictData(detail);
        setCheckStatus('conflict');
        setCheckMessage(detail?.message || 'Brand conflict detected.');
      } else {
        setRegisterError(error.response?.data?.detail?.message || 'Registration failed. Please try again.');
      }
    } finally {
      setRegistering(false);
    }
  }

  async function handleDelete(brandId) {
    if (!confirm('Delete this brand?')) return;
    try {
      await api.delete(`/brands/${brandId}`);
      loadBrands();
    } catch {
      alert('Failed to delete brand.');
    }
  }

  function handleClaimOwnership() {
    const brandId = conflictData?.conflicting_brand_id || '';
    navigate(`/claims/new?brand_id=${brandId}&brand_name=${encodeURIComponent(conflictData?.conflicting_brand || '')}`);
  }

  // Suffix for the text field
  let suffix = null;
  if (checkStatus === 'checking') suffix = <Spinner size="small" />;
  else if (checkStatus === 'available') suffix = <span style={{ color: '#198754', fontWeight: 600 }}>✅ Available</span>;
  else if (checkStatus === 'conflict') suffix = <span style={{ color: '#dc3545', fontWeight: 600 }}>❌ Conflict</span>;

  const tableRows = brands.map((b) => {
    const { label, tone } = getBadgeProps(b.badge_type);
    return [
      <Text as="span" fontWeight="bold">{b.name}</Text>,
      <Badge tone={tone}>{label}</Badge>,
      b.verified ? '✅' : '❌',
      b.registered_at
        ? new Date(b.registered_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
        : '—',
      !b.verified ? (
        <Button size="slim" tone="critical" onClick={() => handleDelete(b.id)}>Delete</Button>
      ) : <Text tone="subdued">—</Text>,
    ];
  });

  return (
    <Page title="Brand Registry" subtitle="Register and manage your brand names">
      <BlockStack gap="500">

        {/* Register Form */}
        <Card>
          <BlockStack gap="400">
            <Text variant="headingMd" as="h2">Register a New Brand</Text>

            {registerSuccess && (
              <Banner tone="success" onDismiss={() => setRegisterSuccess(null)}>
                {registerSuccess}
              </Banner>
            )}
            {registerError && (
              <Banner tone="critical" onDismiss={() => setRegisterError(null)}>
                {registerError}
              </Banner>
            )}
            {checkStatus === 'conflict' && checkMessage && (
              <Banner tone="warning">
                <BlockStack gap="200">
                  <Text>{checkMessage}</Text>
                  {conflictData?.can_claim && (
                    <Button onClick={handleClaimOwnership} variant="plain">
                      Claim Official Ownership →
                    </Button>
                  )}
                </BlockStack>
              </Banner>
            )}
            {checkStatus === 'available' && checkMessage && (
              <Banner tone="success">
                <Text>{checkMessage}</Text>
              </Banner>
            )}

            <TextField
              label="Brand Name"
              value={brandName}
              onChange={handleBrandNameChange}
              placeholder="e.g. Nike"
              autoComplete="off"
              suffix={suffix}
              helpText="We'll check for conflicts in real-time as you type."
            />

            <InlineStack gap="300">
              <Button
                variant="primary"
                onClick={handleRegister}
                loading={registering}
                disabled={checkStatus === 'conflict' || !brandName.trim() || checkStatus === 'checking'}
              >
                Register Brand
              </Button>
            </InlineStack>
          </BlockStack>
        </Card>

        <Divider />

        {/* Registered Brands Table */}
        <Card>
          <BlockStack gap="400">
            <Text variant="headingMd" as="h2">Your Registered Brands</Text>
            {loadingBrands ? (
              <InlineStack align="center"><Spinner size="large" /></InlineStack>
            ) : brands.length === 0 ? (
              <EmptyState
                heading="No brands registered yet"
                image="https://cdn.shopify.com/s/files/1/0262/4071/2726/files/emptystate-files.png"
              >
                <p>Register your first brand name above to get started.</p>
              </EmptyState>
            ) : (
              <DataTable
                columnContentTypes={['text', 'text', 'text', 'text', 'text']}
                headings={['Brand Name', 'Badge', 'Verified', 'Registered', 'Actions']}
                rows={tableRows}
              />
            )}
          </BlockStack>
        </Card>

      </BlockStack>
    </Page>
  );
}