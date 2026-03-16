import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api',
  timeout: 10000,
});

export async function fetchProducts() {
  const response = await api.get('/urunler');
  return response.data.urunler;
}

export default api;
