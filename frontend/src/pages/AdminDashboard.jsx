import React from 'react';
import { useState, useEffect } from 'react';
import {
  Page, Card, DataTable, Button, Badge, Tabs, BlockStack,
  InlineStack, Text, Spinner, EmptyState, Modal, Banner,
} from '@shopify/polaris';
import { adminApi } from '../api/client';

function getStatusBadge(status) {
  const map = {
    pending: { tone: 'warning', label: 'Pending' },
    approved: { tone: 'success', label: 'Approved' },
    rejected: { tone: 'critical', label: 'Rejected' },
  };
  const s = map[status] || { tone: undefined, label: status };
  return <Badge tone={s.tone}>{s.label}</Badge>;
}

function formatDate(str) {
  if (!str) return '—';
  return new Date(str).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

export default function AdminDashboard() {
  const [selectedTab, setSelectedTab] = useState(0);
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionModal, setActionModal] = useState(null); // { claim, action: 'approve'|'reject' }
  const [actioning, setActioning] = useState(false);
  const [actionResult, setActionResult] = useState(null);

  const tabs = [
    { id: 'pending', content: 'Pending', statusFilter: 'pending' },
    { id: 'approved', content: 'Approved', statusFilter: 'approved' },
    { id: 'rejected', content: 'Rejected', statusFilter: 'rejected' },
    { id: 'all', content: 'All', statusFilter: '' },
  ];

  useEffect(() => {
    loadClaims();
  }, [selectedTab]);

  async function loadClaims() {
    setLoading(true);
    setActionResult(null);
    const filter = tabs[selectedTab].statusFilter;
    const params = filter ? `?status=${filter}` : '';
    try {
      const res = await adminApi.get(`/admin/claims${params}`);
      setClaims(res.data.claims || []);
    } catch {
      setClaims([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleAction(claim, action) {
    setActioning(true);
    try {
      const status = action === 'approve' ? 'approved' : 'rejected';
      await adminApi.patch(`/admin/claims/${claim.claim_id}`, { status });
      setActionModal(null);
      setActionResult({ tone: 'success', message: `Claim ${status} successfully.` });
      loadClaims();
    } catch (err) {
      setActionResult({ tone: 'critical', message: err.response?.data?.detail || `Failed to ${action} claim.` });
    } finally {
      setActioning(false);
    }
  }

  function openModal(claim, action) {
    setActionModal({ claim, action });
  }

  const tableRows = claims.map((claim) => [
    <Text>{claim.brand_name || '—'}</Text>,
    <Text fontWeight="semibold">{claim.business_name || '—'}</Text>,
    <Text>{claim.ntn_number || '—'}</Text>,
    claim.website ? (
      <a href={claim.website} target="_blank" rel="noreferrer" style={{ color: '#2563eb', fontSize: '13px' }}>
        {claim.website.replace(/^https?:\/\//, '')}
      </a>
    ) : <Text tone="subdued">—</Text>,
    claim.docs_url ? (
      <a href={claim.docs_url} target="_blank" rel="noreferrer" style={{ color: '#2563eb', fontSize: '13px' }}>
        View Doc
      </a>
    ) : <Text tone="subdued">—</Text>,
    getStatusBadge(claim.status),
    <Text>{formatDate(claim.submitted_at || claim.created_at)}</Text>,
    <InlineStack gap="200">
      {claim.status === 'pending' && (
        <>
          <Button size="slim" tone="success" onClick={() => openModal(claim, 'approve')}>Approve</Button>
          <Button size="slim" tone="critical" onClick={() => openModal(claim, 'reject')}>Reject</Button>
        </>
      )}
      {claim.status !== 'pending' && (
        <Text tone="subdued" variant="bodySm">{claim.status === 'approved' ? '✅ Done' : '❌ Done'}</Text>
      )}
    </InlineStack>,
  ]);

  return (
    <Page
      title="Admin Claims Dashboard"
      subtitle="Review and approve merchant ownership claims"
      primaryAction={{ content: '↻ Refresh', onAction: loadClaims }}
    >
      <BlockStack gap="400">
        {actionResult && (
          <Banner tone={actionResult.tone} onDismiss={() => setActionResult(null)}>
            {actionResult.message}
          </Banner>
        )}

        <Card padding="0">
          <Tabs tabs={tabs} selected={selectedTab} onSelect={setSelectedTab}>
            <div style={{ padding: '16px 0 0' }}>
              {loading ? (
                <InlineStack align="center" blockAlign="center" style={{ padding: '48px' }}>
                  <Spinner size="large" />
                </InlineStack>
              ) : claims.length === 0 ? (
                <EmptyState
                  heading={`No ${tabs[selectedTab].id !== 'all' ? tabs[selectedTab].id : ''} claims`}
                  image="https://cdn.shopify.com/s/files/1/0262/4071/2726/files/emptystate-files.png"
                >
                  <p>Ownership claims will appear here for review.</p>
                </EmptyState>
              ) : (
                <DataTable
                  columnContentTypes={['text', 'text', 'text', 'text', 'text', 'text', 'text', 'text']}
                  headings={['Brand', 'Business Name', 'NTN', 'Website', 'Document', 'Status', 'Submitted', 'Actions']}
                  rows={tableRows}
                />
              )}
            </div>
          </Tabs>
        </Card>
      </BlockStack>

      {/* Approve / Reject Confirmation Modal */}
      {actionModal && (
        <Modal
          open
          onClose={() => setActionModal(null)}
          title={`${actionModal.action === 'approve' ? 'Approve' : 'Reject'} Claim`}
          primaryAction={{
            content: actionModal.action === 'approve' ? 'Approve' : 'Reject',
            tone: actionModal.action === 'approve' ? 'success' : 'critical',
            onAction: () => handleAction(actionModal.claim, actionModal.action),
            loading: actioning,
          }}
          secondaryActions={[{ content: 'Cancel', onAction: () => setActionModal(null) }]}
        >
          <Modal.Section>
            <BlockStack gap="300">
              <Text>
                Are you sure you want to <strong>{actionModal.action}</strong> the ownership claim for brand{' '}
                <strong>"{actionModal.claim.brand_name}"</strong> by{' '}
                <strong>{actionModal.claim.business_name}</strong>?
              </Text>
              {actionModal.action === 'approve' && (
                <Banner tone="info">
                  Approving this claim will upgrade the brand's badge to "Official Brand" and notify the merchant.
                </Banner>
              )}
              {actionModal.action === 'reject' && (
                <Banner tone="warning">
                  Rejecting this claim will close the application. The merchant can resubmit with better documentation.
                </Banner>
              )}
            </BlockStack>
          </Modal.Section>
        </Modal>
      )}
    </Page>
  );
}