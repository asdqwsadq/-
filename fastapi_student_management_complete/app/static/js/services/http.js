import { clearToken, getToken } from "./auth.js";

export function formatErrorDetail(detail) {
  if (!detail) return "请求失败";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        const loc = Array.isArray(item.loc) ? item.loc.join(".") : "";
        return `${loc} ${item.msg || ""}`.trim();
      })
      .join("; ");
  }
  if (typeof detail === "object") {
    return detail.message || JSON.stringify(detail);
  }
  return String(detail);
}

export async function apiFetch(url, options = {}, onAuthExpired) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  const handleAuthError = options.handleAuthError !== false;
  if (token) {
    headers.Authorization = `Bearer ${token}`;
    headers["X-Token"] = token;
  }
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401 && handleAuthError) {
    clearToken();
    if (typeof onAuthExpired === "function") onAuthExpired();
    throw new Error("登录已失效，请重新登录");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(formatErrorDetail(err.detail));
  }
  if (res.status === 204) return null;
  return res.json();
}
