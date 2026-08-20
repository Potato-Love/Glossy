import { apiRequest } from "./client";

const jsonHeaders = { "Content-Type": "application/json" };

export function fetchTeams() {
  return apiRequest("/teams", {}, "팀 목록을 불러오지 못했습니다.");
}

export function createTeam(name) {
  return apiRequest("/teams", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ name }),
  }, "팀을 만들지 못했습니다.");
}

export function joinTeam(inviteCode) {
  return apiRequest("/teams/join", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ invite_code: inviteCode }),
  }, "팀에 가입하지 못했습니다.");
}

export function fetchTeamMembers(teamId) {
  return apiRequest(`/teams/${teamId}/members`, {}, "팀원 목록을 불러오지 못했습니다.");
}

export function updateTeam(teamId, name) {
  return apiRequest(`/teams/${teamId}`, {
    method: "PATCH",
    headers: jsonHeaders,
    body: JSON.stringify({ name }),
  }, "팀 정보를 저장하지 못했습니다.");
}

export function rotateInviteCode(teamId) {
  return apiRequest(`/teams/${teamId}/invite-code/rotate`, {
    method: "POST",
  }, "초대 코드를 재발급하지 못했습니다.");
}
