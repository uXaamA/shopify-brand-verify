import { useState } from 'react';
import {
  Page, Card, Form, FormLayout, TextField, Button, Banner, BlockStack, Text,
} from '@shopify/polaris';
import { useSearchParams, useNavigate } from 'react-router-dom';
import api from '../api/client';

export default function ClaimForm() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const brandId = searchParams.get('brand_id') || '';
  const brandName = searchParams.get('brand_name') || '';

  const [formData, setFormData] = useState({
    business_name: '',
    ntn_number: '',
    website: '',
    docs_url: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(null);
  const [error, setError] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  function handleChange(field) {
    return (value) => setFormData((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit() {
    if (!formData.business_name.trim() || !formData.ntn_number.trim()) {
      setError('Business Name and NTN Number are required.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        brand_id: brandId,
        business_name: formData.business_name.trim(),
        ntn_number: formData.ntn_number.trim(),
        website: formData.website.trim() || undefined,
        docs_url: formData.docs_url.trim() || undefined,
      };
      const res = await api.post('/claims/submit', payload);
      const data = res.data;
      setSuccess({
        message: data.message || 'Claim submitted successfully.',
        claimId: data.claim_id,
      });
      setSubmitted(true);
    } catch (err) {
      setError(err.response?.data?.detail?.message || err.response?.data?.detail || 'Failed to submit claim. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Page
      title="Claim Official Ownership"
      subtitle={brandName ? `Claiming ownership of "${brandName}"` : 'Submit your ownership claim'}
      backAction={{ content: 'Back to Brands', onAction: () => navigate('/') }}
    >
      <Card>
        <BlockStack gap="400">
          <Text variant="bodyMd" tone="subdued">
            Fill in your official business details to claim ownership of this brand name.
            We will review your application within 3–5 business days.
          </Text>

          {success && (
            <Banner tone="success">
              <BlockStack gap="200">
                <Text fontWeight="semibold">{success.message}</Text>
                {success.claimId && (
                  <Text tone="subdued">Your Claim ID: <strong>{success.claimId}</strong> — keep this for reference.</Text>
                )}
              </BlockStack>
            </Banner>
          )}

          {error && (
            <Banner tone="critical" onDismiss={() => setError(null)}>
              {error}
            </Banner>
          )}

          <Form onSubmit={handleSubmit}>
            <FormLayout>
              <TextField
                label="Business Name"
                value={formData.business_name}
                onChange={handleChange('business_name')}
                placeholder="e.g. Nike Inc."
                helpText="Your official registered business name."
                disabled={submitted}
                autoComplete="organization"
                requiredIndicator
              />
              <TextField
                label="NTN Number"
                value={formData.ntn_number}
                onChange={handleChange('ntn_number')}
                placeholder="e.g. 1234567-8"
                helpText="National Tax Number (Pakistan)."
                disabled={submitted}
                autoComplete="off"
                requiredIndicator
              />
              <TextField
                label="Official Website"
                value={formData.website}
                onChange={handleChange('website')}
                placeholder="https://nike.com"
                helpText="Optional — your brand's official website."
                disabled={submitted}
                type="url"
                autoComplete="url"
              />
              <TextField
                label="Document URL"
                value={formData.docs_url}
                onChange={handleChange('docs_url')}
                placeholder="https://storage.example.com/certificate.pdf"
                helpText="Optional — link to your NTN or SECP registration certificate."
                disabled={submitted}
                type="url"
                autoComplete="off"
              />

              {!submitted && (
                <Button
                  variant="primary"
                  onClick={handleSubmit}
                  loading={submitting}
                  disabled={submitting}
                >
                  Submit Ownership Claim
                </Button>
              )}
            </FormLayout>
          </Form>
        </BlockStack>
      </Card>
    </Page>
  );
}