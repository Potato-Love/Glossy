import { useEffect, useState } from "react";
import { demoData } from "../data/mockData";
import { AppDataContext } from "./appData";

const STORAGE_KEY = "glossy-demo-data-v1";
function makeId(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function loadInitialData() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : demoData;
  } catch {
    return demoData;
  }
}

export function AppDataProvider({ children }) {
  const [data, setData] = useState(loadInitialData);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }, [data]);

  function completeOnboarding(profile, teamSetup) {
    setData((current) => {
      const updatedUser = { ...current.currentUser, ...profile };
      const currentMember = {
        id: updatedUser.id,
        nickname: updatedUser.nickname,
        organization: updatedUser.organization,
        position: updatedUser.position,
        status: "활동 중",
      };

      return {
        ...current,
        onboardingComplete: true,
        currentUser: updatedUser,
        team: {
          ...current.team,
          name: teamSetup.mode === "create" ? teamSetup.teamName : current.team.name,
          members: [currentMember, ...current.team.members.filter((member) => member.id !== updatedUser.id)],
        },
      };
    });
  }

  function updateUser(updates) {
    setData((current) => ({
      ...current,
      currentUser: { ...current.currentUser, ...updates },
      team: {
        ...current.team,
        members: current.team.members.map((member) =>
          member.id === current.currentUser.id
            ? {
                ...member,
                nickname: updates.nickname ?? member.nickname,
                organization: updates.organization ?? member.organization,
                position: updates.position ?? member.position,
              }
            : member,
        ),
      },
      history: current.history.map((item) =>
        item.executorId === current.currentUser.id
          ? { ...item, executor: updates.nickname ?? item.executor }
          : item,
      ),
    }));
  }

  function addTerm(term) {
    const newTerm = { ...term, id: makeId("term") };
    setData((current) => ({ ...current, terms: [newTerm, ...current.terms] }));
    return newTerm;
  }

  function updateTerm(id, updates) {
    setData((current) => ({
      ...current,
      terms: current.terms.map((term) => (term.id === id ? { ...term, ...updates } : term)),
    }));
  }

  function deleteTerm(id) {
    setData((current) => ({
      ...current,
      terms: current.terms.filter((term) => term.id !== id),
    }));
  }

  function addRecipient(recipient) {
    setData((current) => ({
      ...current,
      recipients: [{ ...recipient, id: makeId("recipient") }, ...current.recipients],
    }));
  }

  function updateRecipient(id, updates) {
    setData((current) => ({
      ...current,
      recipients: current.recipients.map((recipient) =>
        recipient.id === id ? { ...recipient, ...updates } : recipient,
      ),
    }));
  }

  function deleteRecipient(id) {
    setData((current) => ({
      ...current,
      recipients: current.recipients.filter((recipient) => recipient.id !== id),
    }));
  }

  function saveTranslation(translation) {
    setData((current) => ({
      ...current,
      history: [{ ...translation, id: makeId("history") }, ...current.history],
    }));
  }

  function deleteHistory(id) {
    setData((current) => ({
      ...current,
      history: current.history.filter(
        (item) => item.id !== id || item.executorId !== current.currentUser.id,
      ),
    }));
  }

  function updateTeam(updates) {
    setData((current) => ({ ...current, team: { ...current.team, ...updates } }));
  }

  return (
    <AppDataContext.Provider
      value={{
        ...data,
        completeOnboarding,
        updateUser,
        addTerm,
        updateTerm,
        deleteTerm,
        addRecipient,
        updateRecipient,
        deleteRecipient,
        saveTranslation,
        deleteHistory,
        updateTeam,
      }}
    >
      {children}
    </AppDataContext.Provider>
  );
}
