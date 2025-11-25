/* --------------------------------------------
   API BASE URL
---------------------------------------------*/

// If NEXT_PUBLIC_API_URL is set → use real backend.
// Otherwise default to http://localhost:8000 for dev.
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* --------------------------------------------
   AUTHENTICATION HELPERS
---------------------------------------------*/

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auth_token");
}

export function setAuthToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("auth_token", token);
}

export function removeAuthToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("auth_token");
}

export function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  const headers: HeadersInit = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/* --------------------------------------------
   Helpers: parse JSON safely and extract backend message
---------------------------------------------*/
async function parseJsonSafe(resp: Response) {
  const text = await resp.text();
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return text || null;
  }
}

function extractErrorMessage(parsedBody: any): string {
  if (!parsedBody) return "Unknown error";
  if (typeof parsedBody === "string") return parsedBody;
  if (parsedBody.detail) return parsedBody.detail;
  if (parsedBody.error) return parsedBody.error;
  if (parsedBody.message) return parsedBody.message;
  return JSON.stringify(parsedBody);
}

/* --------------------------------------------
   Authentication API
---------------------------------------------*/

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  membership_status?: string;
  detections_used?: number;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

/** Login against backend auth. Stores token in localStorage on success. */
export async function login(credentials: LoginRequest): Promise<AuthResponse> {
  const resp = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });

  const parsed = await parseJsonSafe(resp);
  if (!resp.ok) {
    throw new Error(extractErrorMessage(parsed) || "Login failed");
  }

  const data = parsed as AuthResponse;
  if (!data?.access_token) {
    throw new Error("Login succeeded but server returned no access_token");
  }
  setAuthToken(data.access_token);
  return data;
}

/** Register a new local user (optional if you keep registration server-side) */
export async function register(userData: RegisterRequest): Promise<User> {
  const resp = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(userData),
  });

  const parsed = await parseJsonSafe(resp);
  if (!resp.ok) {
    throw new Error(extractErrorMessage(parsed) || "Registration failed");
  }

  return parsed as User;
}

/** Return current user object (requires logged-in token) */
export async function getCurrentUser(): Promise<User> {
  const resp = await fetch(`${API_BASE}/api/auth/me`, {
    headers: getAuthHeaders(),
  });

  const parsed = await parseJsonSafe(resp);
  if (!resp.ok) {
    // If unauthorized, remove stale token proactively
    if (resp.status === 401) {
      removeAuthToken();
    }
    throw new Error(extractErrorMessage(parsed) || "Not authenticated");
  }

  // backend returns { user: {...} } in some setups; accept both shapes
  if (parsed && parsed.user) return parsed.user as User;
  return parsed as User;
}

export async function updateUser(data: { full_name?: string; email?: string }): Promise<User> {
  const resp = await fetch(`${API_BASE}/api/auth/me`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    } as HeadersInit,
    body: JSON.stringify(data),
  });

  const parsed = await parseJsonSafe(resp);
  if (!resp.ok) {
    throw new Error(extractErrorMessage(parsed) || "Failed to update profile");
  }

  return parsed as User;
}

export function logout(): void {
  removeAuthToken();
}

/* --------------------------------------------
   Upload Image → POST /upload
   Requires a valid backend token.
   Returns: { jobId: number }
---------------------------------------------*/

export async function uploadImage(file: File): Promise<{ jobId: number }> {
  const token = getAuthToken();
  if (!token) {
    throw new Error("Please log in to upload images");
  }

  const form = new FormData();
  form.append("file", file);

  // Do NOT set Content-Type when using FormData — browser sets proper boundary.
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s

  try {
    const resp = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: form,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    const parsed = await parseJsonSafe(resp);
    if (!resp.ok) {
      if (resp.status === 401) {
        // clear stale token and provide actionable message
        removeAuthToken();
        throw new Error(extractErrorMessage(parsed) || "Please log in to upload images");
      }
      throw new Error(extractErrorMessage(parsed) || "Upload failed");
    }

    return parsed as { jobId: number };
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err?.name === "AbortError") {
      throw new Error("Upload timeout - please try again");
    }
    throw err;
  }
}

/* --------------------------------------------
   Get Job Result → GET /jobs/:id
---------------------------------------------*/

export async function getJob(jobId: number) {
  const resp = await fetch(`${API_BASE}/jobs/${jobId}`, {
    headers: getAuthHeaders(),
  });

  const parsed = await parseJsonSafe(resp);
  if (!resp.ok) {
    if (resp.status === 401) {
      removeAuthToken();
    }
    throw new Error(extractErrorMessage(parsed) || "Job not found");
  }

  return parsed;
}

/* --------------------------------------------
   Get Dashboard (Recent Jobs) → GET /dashboard
---------------------------------------------*/

export async function getDashboard() {
  const resp = await fetch(`${API_BASE}/dashboard`, {
    headers: getAuthHeaders(),
  });

  const parsed = await parseJsonSafe(resp);
  if (!resp.ok) {
    if (resp.status === 401) removeAuthToken();
    throw new Error(extractErrorMessage(parsed) || "Failed to load dashboard");
  }

  return parsed;
}

/* --------------------------------------------
   SWR Fetcher (auto-prepends API_BASE)
---------------------------------------------*/

export const fetcher = (path: string) =>
  fetch(`${API_BASE}${path}`, {
    headers: getAuthHeaders(),
  }).then(async (res) => {
    const parsed = await parseJsonSafe(res);
    if (!res.ok) throw new Error(extractErrorMessage(parsed) || "API Error");
    return parsed;
  });
