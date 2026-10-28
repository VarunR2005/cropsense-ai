// All communication with the FastAPI backend lives here.
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TOKEN_KEY = "cropsense_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

let onUnauthorized = null;
export const setUnauthorizedHandler = (fn) => {
  onUnauthorized = fn;
};

// FastAPI errors are either a string or a list of {loc, msg} objects.
function formatDetail(detail) {
  if (!detail) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => `${(d.loc || []).slice(1).join(".") || "input"}: ${d.msg}`)
      .join("; ");
  }
  return JSON.stringify(detail);
}

async function request(path, { method = "GET", body, form, params, raw = false } = {}) {
  const url = new URL(BASE + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
  }
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = new URLSearchParams(form);
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(url, { method, headers, body: payload });
  } catch {
    throw new ApiError(`Cannot reach the server at ${BASE}. Is the backend running?`, 0);
  }

  if (res.status === 401 && token && onUnauthorized) onUnauthorized();
  if (!res.ok) {
    let detail;
    try {
      detail = (await res.json()).detail;
    } catch {
      /* no JSON body */
    }
    throw new ApiError(formatDetail(detail), res.status);
  }
  if (raw) return res;
  if (res.status === 204) return null;
  return res.json();
}

export async function downloadReport(kind, params, format) {
  const res = await request(`/api/reports/${kind}`, { params: { ...params, format }, raw: true });
  const blob = await res.blob();
  const stamp = new Date().toISOString().slice(0, 10);
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${kind}_report_${stamp}.${format}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
}

export const api = {
  register: (body) => request("/api/auth/register", { method: "POST", body }),
  login: (email, password) =>
    request("/api/auth/login", { method: "POST", form: { username: email, password } }),
  me: () => request("/api/auth/me"),
  updateMe: (body) => request("/api/auth/me", { method: "PATCH", body }),
  changePassword: (body) => request("/api/auth/change-password", { method: "POST", body }),

  yieldOptions: () => request("/api/predictions/options"),
  predictYield: (body) => request("/api/predictions/yield", { method: "POST", body }),

  recommendCrops: (body) => request("/api/recommendations/crops", { method: "POST", body }),
  fertilizerCrops: () => request("/api/recommendations/fertilizer/crops"),
  recommendFertilizer: (body) =>
    request("/api/recommendations/fertilizer", { method: "POST", body }),

  weather: (city) => request("/api/weather/forecast", { params: { city } }),

  irrigationCrops: () => request("/api/irrigation/crops"),
  planIrrigation: (body) => request("/api/irrigation/recommend", { method: "POST", body }),

  dashboard: (city) => request("/api/dashboard/summary", { params: { city } }),
  report: (kind, params) => request(`/api/reports/${kind}`, { params: { ...params, format: "json" } }),
};
