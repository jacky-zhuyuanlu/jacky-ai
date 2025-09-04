import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/retell', // 后端API地址
  timeout: 5000,
});

export const healthCheck = () => api.get('/health');
export const login = (username, password) => api.post('/login', { username, password });
export const register = (username, password) => api.post('/register', { username, password });

export default api; 