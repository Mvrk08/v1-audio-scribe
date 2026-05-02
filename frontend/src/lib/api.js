import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;

export const getToken = () => localStorage.getItem("medical-token");

export const setToken = (token) => localStorage.setItem("medical-token", token);

export const clearToken = () => localStorage.removeItem("medical-token");

const client = axios.create({ baseURL: API_BASE });

client.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const api = {
  health: () => client.get("/health"),
  login: (email, password) => client.post("/auth/login", { email, password }),
  logout: () => client.post("/auth/logout"),
  session: () => client.get("/auth/session"),
  createSession: (source_language, target_language) => client.post("/v1/sessions", { source_language, target_language }),
  uploadAudio: (sessionId, file, durationSeconds) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("duration_seconds", String(durationSeconds || 0));
    return client.post(`/v1/sessions/${sessionId}/audio`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  processSession: (sessionId) => client.post(`/v1/sessions/${sessionId}/process`),
  getStatus: (sessionId) => client.get(`/v1/sessions/${sessionId}/status`),
  getResult: (sessionId) => client.get(`/v1/sessions/${sessionId}/result`),
  updateResult: (sessionId, payload) => client.patch(`/v1/sessions/${sessionId}/result`, payload),
  listSessions: () => client.get("/v1/sessions"),
  deleteSession: (sessionId) => client.delete(`/v1/sessions/${sessionId}`),
};
