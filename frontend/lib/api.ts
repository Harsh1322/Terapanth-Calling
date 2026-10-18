export type ApiUser = {
  id: number;
  name: string;
  mobile: string;
  isAdmin: boolean;
};

async function getCsrfToken() {
  const response = await fetch("/api/csrf", { credentials: "same-origin" });
  const data: { csrfToken?: unknown; error?: string } = await response.json();
  if (!response.ok || typeof data.csrfToken !== "string") {
    throw new Error(data.error || "Could not start a secure session.");
  }
  return data.csrfToken;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    headers.set("X-CSRFToken", await getCsrfToken());
  }

  const response = await fetch(path, {
    ...options,
    method,
    headers,
    credentials: "same-origin",
  });
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : null;
  if (!response.ok) {
    throw new Error(data?.error || `Request failed (${response.status}).`);
  }
  return data as T;
}

export function initials(name: string) {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0))
    .join("")
    .toUpperCase();
}
