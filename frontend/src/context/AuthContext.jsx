import { useCallback, useEffect, useState } from "react";
import {
  fetchMe,
  login as loginRequest,
  logout as logoutRequest,
  signup as signupRequest,
  updateMyProfile,
} from "../api/auth";
import { CURRENT_TEAM_KEY, SESSION_TOKEN_KEY } from "../api/client";
import {
  createTeam as createTeamRequest,
  fetchTeamMembers,
  joinTeam as joinTeamRequest,
  rotateInviteCode as rotateInviteCodeRequest,
  updateTeam as updateTeamRequest,
} from "../api/teams";
import { AuthContext } from "./authContext";

function selectTeam(teams) {
  const savedId = localStorage.getItem(CURRENT_TEAM_KEY);
  return teams.find((team) => team.id === savedId) || teams[0] || null;
}

export function AuthProvider({ children }) {
  const [status, setStatus] = useState("loading");
  const [user, setUser] = useState(null);
  const [teams, setTeams] = useState([]);
  const [currentTeam, setCurrentTeam] = useState(null);

  const applyAccount = useCallback((account) => {
    setUser(account.user);
    setTeams(account.teams || []);
    const nextTeam = selectTeam(account.teams || []);
    setCurrentTeam(nextTeam);
    if (nextTeam) localStorage.setItem(CURRENT_TEAM_KEY, nextTeam.id);
    else localStorage.removeItem(CURRENT_TEAM_KEY);
    setStatus("authenticated");
  }, []);

  const clearSession = useCallback(() => {
    localStorage.removeItem(SESSION_TOKEN_KEY);
    localStorage.removeItem(CURRENT_TEAM_KEY);
    setUser(null);
    setTeams([]);
    setCurrentTeam(null);
    setStatus("anonymous");
  }, []);

  const refreshAccount = useCallback(async () => {
    const account = await fetchMe();
    applyAccount(account);
    return account;
  }, [applyAccount]);

  useEffect(() => {
    const token = localStorage.getItem(SESSION_TOKEN_KEY);
    if (!token) {
      setStatus("anonymous");
      return;
    }
    refreshAccount().catch(clearSession);
  }, [clearSession, refreshAccount]);

  useEffect(() => {
    window.addEventListener("glossy:session-expired", clearSession);
    return () => window.removeEventListener("glossy:session-expired", clearSession);
  }, [clearSession]);

  async function startSession(request, nickname) {
    const session = await request(nickname.trim());
    localStorage.setItem(SESSION_TOKEN_KEY, session.token);
    applyAccount(session);
    return session;
  }

  async function logout() {
    try {
      await logoutRequest();
    } finally {
      clearSession();
    }
  }

  async function saveProfile(profile) {
    const updated = await updateMyProfile(profile);
    setUser(updated);
    return updated;
  }

  function addAndSelectTeam(team) {
    setTeams((current) => [...current.filter((item) => item.id !== team.id), team]);
    setCurrentTeam(team);
    localStorage.setItem(CURRENT_TEAM_KEY, team.id);
    return team;
  }

  async function createTeam(name) {
    return addAndSelectTeam(await createTeamRequest(name.trim()));
  }

  async function joinTeam(code) {
    return addAndSelectTeam(await joinTeamRequest(code.trim().toUpperCase()));
  }

  function switchTeam(teamId) {
    const team = teams.find((item) => item.id === teamId);
    if (!team) return;
    setCurrentTeam(team);
    localStorage.setItem(CURRENT_TEAM_KEY, team.id);
  }

  async function updateTeam(name) {
    const updated = await updateTeamRequest(currentTeam.id, name.trim());
    addAndSelectTeam(updated);
    return updated;
  }

  async function rotateInviteCode() {
    const updated = await rotateInviteCodeRequest(currentTeam.id);
    addAndSelectTeam(updated);
    return updated;
  }

  const value = {
    status,
    user,
    teams,
    currentTeam,
    login: (nickname) => startSession(loginRequest, nickname),
    signup: (nickname) => startSession(signupRequest, nickname),
    logout,
    saveProfile,
    refreshAccount,
    createTeam,
    joinTeam,
    switchTeam,
    updateTeam,
    rotateInviteCode,
    fetchTeamMembers,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
