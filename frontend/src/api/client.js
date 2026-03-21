import axios from 'axios';

const BASE_URL = 'https://shopify-brand-verify-production.up.railway.app';

// Get shop domain from URL query param (Shopify always appends ?shop=)
const shopDomain =
  new URLSearchParams(window.location.search).get('shop') ||
  'phantom-intelligence.myshopify.com';

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'X-Shopify-Shop-Domain': shopDomain,
    'Content-Type': 'application/json',
  },
});

export const adminApi = axios.create({
  baseURL: BASE_URL,
  headers: {
    'X-Admin-Secret': 'admin-secret-change-this-in-production',
    'Content-Type': 'application/json',
  },
});

export const publicApi = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export { shopDomain };
export default api;