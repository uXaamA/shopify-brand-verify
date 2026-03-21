import React from 'react';
import { AppProvider } from '@shopify/polaris';
import enTranslations from '@shopify/polaris/locales/en.json';
import '@shopify/polaris/build/esm/styles.css';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import BrandRegistry from './pages/BrandRegistry';
import OrdersDashboard from './pages/OrdersDashboard';
import ClaimForm from './pages/ClaimForm';
import VerifyPage from './pages/VerifyPage';
import AdminDashboard from './pages/AdminDashboard';

function NavBar() {
  const location = useLocation();
  // Don't show nav on verify page (public) or admin
  if (location.pathname.startsWith('/verify')) return null;

  const links = [
    { to: '/', label: '🏷️ Brands' },
    { to: '/orders', label: '📦 Orders & QR' },
    { to: '/admin', label: '🛡️ Admin' },
  ];

  return (
    <nav style={{
      background: '#1a1a2e',
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      height: '52px',
      borderBottom: '1px solid #16213e',
    }}>
      <span style={{ color: '#e94560', fontWeight: 700, fontSize: '15px', marginRight: '16px', letterSpacing: '0.5px' }}>
        🔮 Brand Verify
      </span>
      {links.map(({ to, label }) => (
        <Link
          key={to}
          to={to}
          style={{
            color: location.pathname === to ? '#e94560' : '#aaa',
            textDecoration: 'none',
            padding: '6px 14px',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: location.pathname === to ? 600 : 400,
            background: location.pathname === to ? 'rgba(233,69,96,0.12)' : 'transparent',
            transition: 'all 0.15s',
          }}
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}

function AppInner() {
  return (
    <>
      <NavBar />
      <Routes>
        <Route path="/" element={<BrandRegistry />} />
        <Route path="/brands" element={<BrandRegistry />} />
        <Route path="/orders" element={<OrdersDashboard />} />
        <Route path="/claims/new" element={<ClaimForm />} />
        <Route path="/verify/:hash" element={<VerifyPage />} />
        <Route path="/admin" element={<AdminDashboard />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <AppProvider i18n={enTranslations}>
      <BrowserRouter>
        <AppInner />
      </BrowserRouter>
    </AppProvider>
  );
}