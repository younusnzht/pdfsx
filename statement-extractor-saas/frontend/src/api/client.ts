import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8010/api/v1",
});

// TODO: attach access token from auth store, and a response interceptor
// that refreshes on 401 using the refresh token — see backend app/core/security.py
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
