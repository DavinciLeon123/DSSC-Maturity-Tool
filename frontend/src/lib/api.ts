import axios from "axios";
import { authStore } from "./auth";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1",
});

api.interceptors.request.use((config) => {
  const token = authStore.getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error.response?.status;
    if (status === 401) {
      authStore.clearToken();
      window.location.href = "/login?session=expired";
    }
    // 5xx and network errors: propagate via Promise.reject.
    // TanStack Query captures them as isError state. No additional handling here.
    return Promise.reject(error);
  }
);
