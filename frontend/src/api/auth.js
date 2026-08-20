import { apiRequest } from "./client";

const jsonHeaders = { "Content-Type": "application/json" };

export function signup(nickname) {
  return apiRequest("/auth/signup", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ nickname }),
  }, "회원가입에 실패했습니다.");
}

export function login(nickname) {
  return apiRequest("/auth/login", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ nickname }),
  }, "로그인에 실패했습니다.");
}

export function logout() {
  return apiRequest("/auth/logout", { method: "POST" }, "로그아웃 요청에 실패했습니다.");
}

export function fetchMe() {
  return apiRequest("/auth/me", {}, "로그인 정보를 불러오지 못했습니다.");
}

export function updateMyProfile(profile) {
  return apiRequest("/users/me", {
    method: "PATCH",
    headers: jsonHeaders,
    body: JSON.stringify(profile),
  }, "프로필을 저장하지 못했습니다.");
}
