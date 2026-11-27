// Small fetch wrapper for the FastAPI backend (proxied at /api in dev).
export async function api(path, { method = "GET", body, token, screenToken } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (screenToken) headers["X-Screen-Token"] = screenToken;

  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const detail = Array.isArray(data.detail) ? data.detail[0].msg : data.detail;
    const error = new Error(detail || `Request failed (${res.status})`);
    error.status = res.status;
    throw error;
  }
  return res.status === 204 ? null : res.json();
}

// The backend stores times in UTC without a "Z", so add it before parsing.
export const fromUtc = (text) => new Date(text.endsWith("Z") ? text : `${text}Z`);
