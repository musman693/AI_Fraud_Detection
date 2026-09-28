import axios from "axios";
import { demoApiAdapter } from "./demoApi";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
export const isDemoMode = import.meta.env.VITE_DEMO_MODE === "true" || (import.meta.env.PROD && !apiBaseUrl);

export const api = axios.create({
  baseURL: apiBaseUrl || "/api",
  adapter: isDemoMode ? demoApiAdapter : undefined,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("fraudshield_token");
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("fraudshield_token");
      localStorage.removeItem("fraudshield_user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
