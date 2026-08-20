export const API_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");
export const SESSION_TOKEN_KEY = "glossy-session-token-v1";
export const CURRENT_TEAM_KEY = "glossy-current-team-v1";

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readErrorMessage(response, fallbackMessage) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") return data.detail;
  } catch {
    // The backend did not return a JSON error body.
  }

  return `${fallbackMessage} (${response.status})`;
}

export async function apiRequest(path, options = {}, fallbackMessage = "요청을 처리하지 못했습니다.") {
  let response;

  const headers = new Headers(options.headers || {});
  const token = localStorage.getItem(SESSION_TOKEN_KEY);
  const teamId = localStorage.getItem(CURRENT_TEAM_KEY);
  if (token && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
  if (teamId && !headers.has("X-Team-Id")) headers.set("X-Team-Id", teamId);

  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError("백엔드에 연결할 수 없습니다. 서버 실행 상태와 API 주소를 확인해 주세요.");
  }

  if (!response.ok) {
    if (response.status === 401 && token) {
      localStorage.removeItem(SESSION_TOKEN_KEY);
      localStorage.removeItem(CURRENT_TEAM_KEY);
      window.dispatchEvent(new Event("glossy:session-expired"));
    }
    throw new ApiError(await readErrorMessage(response, fallbackMessage), response.status);
  }

  if (response.status === 204) return null;
  return response.json();
}
