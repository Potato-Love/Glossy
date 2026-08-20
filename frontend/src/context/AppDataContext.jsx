import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createRecipient as createRecipientRequest,
  deleteRecipient as deleteRecipientRequest,
  fetchRecipients,
  updateRecipient as updateRecipientRequest,
} from "../api/recipients";
import {
  createTeamTerm as createTeamTermRequest,
  deleteTeamTerm as deleteTeamTermRequest,
  fetchTeamTerms,
  updateTeamTerm as updateTeamTermRequest,
} from "../api/terms";
import {
  deleteHistory as deleteHistoryRequest,
  fetchHistory,
  updateHistory as updateHistoryRequest,
} from "../api/history";
import { useAuth } from "./authContext";
import { AppDataContext } from "./appData";

const LEGACY_STORAGE_KEY = "glossy-app-data-v1";

export function AppDataProvider({ children }) {
  const auth = useAuth();
  const userId = auth.user?.id || "";
  const teamId = auth.currentTeam?.id || "";
  const [terms, setTerms] = useState([]);
  const [recipients, setRecipients] = useState([]);
  const [history, setHistory] = useState([]);
  const [teamTermsLoading, setTeamTermsLoading] = useState(false);
  const [teamTermsError, setTeamTermsError] = useState("");
  const [recipientsLoading, setRecipientsLoading] = useState(false);
  const [recipientsError, setRecipientsError] = useState("");
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");

  useEffect(() => {
    localStorage.removeItem(LEGACY_STORAGE_KEY);
    Object.keys(localStorage)
      .filter((key) => key.startsWith("glossy-history-v1:"))
      .forEach((key) => localStorage.removeItem(key));
  }, []);

  useEffect(() => {
    setTerms([]);
    setRecipients([]);
    setHistory([]);
    setTeamTermsError("");
    setRecipientsError("");
    setHistoryError("");
  }, [teamId, userId]);

  const refreshTeamTerms = useCallback(async () => {
    if (!userId || !teamId) return [];
    setTeamTermsLoading(true);
    setTeamTermsError("");
    try {
      const result = await fetchTeamTerms({ teamKey: teamId, userKey: userId });
      setTerms(result);
      return result;
    } catch (error) {
      setTeamTermsError(error instanceof Error ? error.message : "팀 용어집을 불러오지 못했습니다.");
      return null;
    } finally {
      setTeamTermsLoading(false);
    }
  }, [teamId, userId]);

  const refreshRecipients = useCallback(async () => {
    if (!userId || !teamId) return [];
    setRecipientsLoading(true);
    setRecipientsError("");
    try {
      const result = await fetchRecipients({ teamKey: teamId });
      setRecipients(result);
      return result;
    } catch (error) {
      setRecipientsError(error instanceof Error ? error.message : "수신자 프로필을 불러오지 못했습니다.");
      return null;
    } finally {
      setRecipientsLoading(false);
    }
  }, [teamId, userId]);

  const refreshHistory = useCallback(async () => {
    if (!userId || !teamId) return [];
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const result = await fetchHistory("team");
      setHistory(result);
      return result;
    } catch (error) {
      setHistoryError(error instanceof Error ? error.message : "번역 히스토리를 불러오지 못했습니다.");
      return null;
    } finally {
      setHistoryLoading(false);
    }
  }, [teamId, userId]);

  useEffect(() => {
    if (auth.status === "authenticated" && teamId) {
      refreshTeamTerms();
      refreshRecipients();
      refreshHistory();
    }
  }, [auth.status, refreshHistory, refreshRecipients, refreshTeamTerms, teamId]);

  async function updateUser(updates) {
    return auth.saveProfile({ ...auth.user, ...updates });
  }

  async function createScopedTerm(term, scope) {
    const created = await createTeamTermRequest(term, {
      teamKey: teamId,
      userKey: userId,
      creatorName: auth.user.nickname,
      scope,
    });
    setTerms((current) => [created, ...current.filter((item) => item.id !== created.id)]);
    return created;
  }

  async function updateTeamTerm(id, updates) {
    const updated = await updateTeamTermRequest(id, updates);
    setTerms((current) => current.map((term) => term.id === id ? updated : term));
    return updated;
  }

  async function deleteTeamTerm(id) {
    await deleteTeamTermRequest(id);
    setTerms((current) => current.filter((term) => term.id !== id));
  }

  async function addRecipient(recipient) {
    const created = await createRecipientRequest(recipient, {
      teamKey: teamId,
      userKey: userId,
      creatorName: auth.user.nickname,
    });
    setRecipients((current) => [created, ...current.filter((item) => item.id !== created.id)]);
    return created;
  }

  async function updateRecipient(id, updates) {
    const updated = await updateRecipientRequest(id, updates);
    setRecipients((current) => current.map((item) => item.id === id ? updated : item));
    return updated;
  }

  async function deleteRecipient(id) {
    await deleteRecipientRequest(id);
    setRecipients((current) => current.filter((item) => item.id !== id));
  }

  async function updateSavedHistory(id, updates) {
    const updated = await updateHistoryRequest(id, updates);
    setHistory((current) => current.map((item) => item.id === id ? updated : item));
    return updated;
  }

  async function deleteHistory(id) {
    await deleteHistoryRequest(id);
    setHistory((current) => current.filter((item) => item.id !== id));
  }

  const currentUser = useMemo(() => ({
    id: userId,
    name: auth.user?.name || "",
    nickname: auth.user?.nickname || "",
    organization: auth.user?.organization || "",
    position: auth.user?.position || "",
    country: auth.user?.country || "",
  }), [auth.user, userId]);

  const team = useMemo(() => ({
    id: teamId,
    name: auth.currentTeam?.name || "",
    inviteCode: auth.currentTeam?.invite_code || "",
    role: auth.currentTeam?.role || "member",
    memberCount: auth.currentTeam?.member_count || 0,
    members: [],
  }), [auth.currentTeam, teamId]);

  return (
    <AppDataContext.Provider value={{
      onboardingComplete: auth.status === "authenticated" && Boolean(auth.user?.profile_completed && teamId),
      currentUser,
      team,
      terms,
      recipients,
      history,
      updateUser,
      createTeamTerm: (term) => createScopedTerm(term, "team"),
      createPersonalTerm: (term) => createScopedTerm(term, "personal"),
      updateTeamTerm,
      deleteTeamTerm,
      refreshTeamTerms,
      teamTermsLoading,
      teamTermsError,
      refreshRecipients,
      recipientsLoading,
      recipientsError,
      addRecipient,
      updateRecipient,
      deleteRecipient,
      refreshHistory,
      historyLoading,
      historyError,
      updateSavedHistory,
      deleteHistory,
      updateTeam: auth.updateTeam,
    }}>
      {children}
    </AppDataContext.Provider>
  );
}
