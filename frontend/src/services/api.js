import axios from 'axios';

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
  // Los arreglos viajan como ?tipo=1&tipo=3 (lo que espera Django),
  // no como ?tipo[]=1&tipo[]=3 (el formato por defecto de axios).
  paramsSerializer: { indexes: null },
});

export default api;
