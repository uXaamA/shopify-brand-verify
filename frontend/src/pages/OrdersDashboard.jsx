import React from 'react';
import { useState, useEffect } from 'react';
import {
  Page, Card, DataTable, Button, Spinner, EmptyState,
  BlockStack, InlineStack, Text, Link as PolarisLink, Modal,
} from '@shopify/polaris';
import api from '../api/client';

const BASE_URL = 'https://shopify-brand-verify-production.up.railway.app';

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  });
}

function ItemsCell({ items }) {
  if (!items || items.length === 0) return <Text tone="subdued">—</Text>;
  const first = items[0].name;
  const rest = items.length - 1;
  return (
    <Text>
      {first}{rest > 0 ? ` +${rest} more` : ''}
    </Text>
  );
}

function QRCell({ orderId, shopDomain }) {
  const [qrData, setQrData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);

  async function loadQR() {
    if (loaded) return;
    setLoading(true);
    try {
      const res = await api.get(`/orders/${orderId}/qr/base64`);
      setQrData(res.data);
    } catch {
      setQrData(null);
    } finally {
      setLoading(false);
      setLoaded(true);
    }
  }

  useEffect(() => { loadQR(); }, []);

  async function handleDownload() {
    try {
      const res = await api.get(`/orders/${orderId}/qr/image`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `qr-${orderId}.png`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      alert('Failed to download QR code.');
    }
  }

  if (loading) return <Spinner size="small" />;
  if (!qrData) return <Button size="slim" onClick={loadQR}>Load QR</Button>;

  return (
    <InlineStack gap="200" align="center">
      <img
        src={`data:image/png;base64,${qrData.qr_base64}`}
        width="72"
        height="72"
        alt="Order QR Code"
        style={{ borderRadius: '4px', border: '1px solid #e1e3e5' }}
      />
      <Button size="slim" onClick={handleDownload}>⬇ Download</Button>
    </InlineStack>
  );
}

export default function OrdersDashboard() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOrder, setModalOrder] = useState(null);

  useEffect(() => {
    loadOrders();
  }, []);

  async function loadOrders() {
    setLoading(true);
    try {
      const res = await api.get('/orders');
      setOrders(res.data.orders || []);
    } catch {
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }

  const tableRows = orders.map((order) => [
    <Text fontWeight="semibold">#{order.shopify_order_id}</Text>,
    <Text>{order.customer_name}</Text>,
    <ItemsCell items={order.items} />,
    <Text>${order.order_total} {order.currency}</Text>,
    <Text>{order.shipping_to?.city || '—'}</Text>,
    <Text>{formatDate(order.created_at)}</Text>,
    <QRCell orderId={order.shopify_order_id} />,
    order.verify_url ? (
      <a href={order.verify_url} target="_blank" rel="noreferrer">
        <Button size="slim" variant="plain">🔗 Verify</Button>
      </a>
    ) : '—',
  ]);

  return (
    <Page
      title="Orders & QR Dashboard"
      subtitle={`${orders.length} order${orders.length !== 1 ? 's' : ''} found`}
      primaryAction={{ content: '↻ Refresh', onAction: loadOrders }}
    >
      <Card>
        {loading ? (
          <InlineStack align="center" style={{ padding: '48px' }}>
            <Spinner size="large" />
          </InlineStack>
        ) : orders.length === 0 ? (
          <EmptyState
            heading="No orders found"
            image="https://cdn.shopify.com/s/files/1/0262/4071/2726/files/emptystate-files.png"
          >
            <p>Orders from your Shopify store will appear here with their QR codes.</p>
          </EmptyState>
        ) : (
          <DataTable
            columnContentTypes={['text', 'text', 'text', 'text', 'text', 'text', 'text', 'text']}
            headings={['Order #', 'Customer', 'Items', 'Total', 'City', 'Date', 'QR Code', 'Verify Link']}
            rows={tableRows}
          />
        )}
      </Card>
    </Page>
  );
}