import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { previewTermStrategy } from "../api/suggestions";
import {
  deleteStrategyPreference,
  fetchStrategyPreferences,
  saveStrategyPreference,
} from "../api/strategyPreferences";
import EmptyState from "../components/common/EmptyState";
import Modal from "../components/common/Modal";
import { useAppData } from "../context/appData";
import {
  getTermCategoryLabel,
  getTranslationStrategyLabel,
  languages,
  termCategories,
  translationStrategies,
} from "../data/referenceData";
import "./PageStyles.css";

function createEmptyForm(scope = "team") {
  return {
    source: "",
    target: "",
    strategy: "translate",
    translationStrategy: "custom",
    termCategory: "other",
    memo: "",
    sourceLanguage: "ko",
    targetLanguage: "en",
    rememberPreference: false,
    preferenceScope: scope,
    creationMethod: "manual",
  };
}

export default function GlossaryPage() {
  const {
    currentUser,
    team,
    terms,
    createTeamTerm,
    createPersonalTerm,
    updateTeamTerm,
    deleteTeamTerm,
    refreshTeamTerms,
    teamTermsLoading,
    teamTermsError,
  } = useAppData();
  const [scope, setScope] = useState("team");
  const [search, setSearch] = useState("");
  const [strategy, setStrategy] = useState("all");
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [form, setForm] = useState(() => createEmptyForm());
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [preferences, setPreferences] = useState([]);
  const [preferenceError, setPreferenceError] = useState("");

  const filteredTerms = useMemo(() => terms.filter((term) => {
    const matchesScope = term.scope === scope;
    const query = search.trim().toLowerCase();
    const matchesSearch = !query || `${term.source} ${term.target} ${term.memo}`.toLowerCase().includes(query);
    const matchesStrategy = strategy === "all" || term.translationStrategy === strategy;
    return matchesScope && matchesSearch && matchesStrategy;
  }), [terms, scope, search, strategy]);

  const visiblePreferences = preferences.filter((preference) => preference.scope === scope);

  const refreshPreferences = useCallback(async function refreshPreferences() {
    if (!team.id || !currentUser.id) return;
    try {
      setPreferences(await fetchStrategyPreferences({ teamKey: team.id, userKey: currentUser.id }));
      setPreferenceError("");
    } catch (loadError) {
      setPreferenceError(loadError instanceof Error ? loadError.message : "번역 기본값을 불러오지 못했습니다.");
    }
  }, [currentUser.id, team.id]);

  useEffect(() => {
    refreshPreferences();
  }, [refreshPreferences]);

  function openCreate() {
    setEditing("new");
    setForm(createEmptyForm(scope));
    setError("");
  }

  function openEdit(term) {
    setEditing(term.id);
    setForm({
      source: term.source,
      target: term.target,
      strategy: term.strategy,
      translationStrategy: term.translationStrategy || (term.strategy === "preserve" ? "preserve" : "custom"),
      termCategory: term.termCategory || "other",
      memo: term.memo,
      sourceLanguage: term.sourceLanguage || "ko",
      targetLanguage: term.targetLanguage || "en",
      rememberPreference: false,
      preferenceScope: term.scope || scope,
      creationMethod: term.creationMethod || "manual",
    });
    setError("");
  }

  async function handleTranslationStrategy(nextStrategy) {
    setError("");
    if (nextStrategy === "preserve") {
      setForm((current) => ({
        ...current,
        strategy: "preserve",
        translationStrategy: "preserve",
        target: "",
        creationMethod: "manual",
      }));
      return;
    }
    if (nextStrategy === "custom") {
      setForm((current) => ({
        ...current,
        strategy: "translate",
        translationStrategy: "custom",
        rememberPreference: false,
        creationMethod: "direct_edit",
      }));
      return;
    }
    if (!form.source.trim()) {
      setError("먼저 원문을 입력해 주세요.");
      return;
    }

    setPreviewing(true);
    try {
      const preview = await previewTermStrategy({
        source: form.source.trim(),
        source_language: form.sourceLanguage,
        target_language: form.targetLanguage,
        strategy: nextStrategy,
        context: form.memo.trim() || null,
      });
      setForm((current) => ({
        ...current,
        strategy: "translate",
        translationStrategy: nextStrategy,
        target: preview.target,
        creationMethod: nextStrategy,
      }));
    } catch (previewError) {
      setError(previewError instanceof Error ? previewError.message : "번역 후보를 만들지 못했습니다.");
    } finally {
      setPreviewing(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!form.source.trim() || (form.strategy === "translate" && !form.target.trim())) {
      setError("원문과 번역 결과를 입력해 주세요.");
      return;
    }
    if (form.rememberPreference && (form.translationStrategy === "custom" || form.termCategory === "other")) {
      setError("직접 입력 또는 기타 분류는 기본 방식으로 기억할 수 없습니다.");
      return;
    }
    const duplicate = terms.some((term) =>
      term.scope === scope
      && term.sourceLanguage === form.sourceLanguage
      && term.targetLanguage === form.targetLanguage
      && term.source.trim().toLowerCase() === form.source.trim().toLowerCase()
      && term.id !== editing,
    );
    if (duplicate) {
      setError("같은 용어집에 이미 등록된 원문입니다.");
      return;
    }

    const values = {
      ...form,
      target: form.strategy === "preserve" ? form.source.trim() : form.target.trim(),
      source: form.source.trim(),
    };
    setSaving(true);
    setError("");
    try {
      if (scope === "team") {
        if (editing === "new") await createTeamTerm(values);
        else await updateTeamTerm(editing, values);
      } else if (editing === "new") {
        await createPersonalTerm(values);
      } else {
        await updateTeamTerm(editing, values);
      }

      if (editing !== "new" && form.rememberPreference) {
        await saveStrategyPreference({
          team_key: team.id,
          scope: form.preferenceScope,
          owner_key: form.preferenceScope === "personal" ? currentUser.id : null,
          term_category: form.termCategory,
          source_language: form.sourceLanguage,
          target_language: form.targetLanguage,
          preferred_strategy: form.translationStrategy,
          created_by_key: currentUser.id,
          created_by_name: currentUser.nickname,
        });
      }
      await refreshPreferences();
      setEditing(null);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "용어를 저장하지 못했습니다.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!deleting) return;
    setDeleteError("");
    try {
      await deleteTeamTerm(deleting.id);
      setDeleting(null);
    } catch (removeError) {
      setDeleteError(removeError instanceof Error ? removeError.message : "용어를 삭제하지 못했습니다.");
    }
  }

  async function handlePreferenceChange(preference, preferredStrategy) {
    try {
      await saveStrategyPreference({
        team_key: preference.team_key,
        scope: preference.scope,
        owner_key: preference.owner_key,
        term_category: preference.term_category,
        source_language: preference.source_language,
        target_language: preference.target_language,
        preferred_strategy: preferredStrategy,
        created_by_key: currentUser.id,
        created_by_name: currentUser.nickname,
      });
      await refreshPreferences();
    } catch (updateError) {
      setPreferenceError(updateError instanceof Error ? updateError.message : "번역 기본값을 수정하지 못했습니다.");
    }
  }

  async function handlePreferenceDelete(preference) {
    try {
      await deleteStrategyPreference(preference.id, { teamKey: team.id, userKey: currentUser.id });
      await refreshPreferences();
    } catch (removeError) {
      setPreferenceError(removeError instanceof Error ? removeError.message : "번역 기본값을 삭제하지 못했습니다.");
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <div><h1>용어집</h1><p>팀과 개인 번역에 사용할 표현과 상황별 기본 방식을 관리합니다.</p></div>
        <button className="button primary" onClick={openCreate}><Plus size={18} /> 용어 등록</button>
      </header>

      <div className="toolbar">
        <div className="segmented-control">
          <button className={scope === "team" ? "active" : ""} onClick={() => setScope("team")}>팀 공유</button>
          <button className={scope === "personal" ? "active" : ""} onClick={() => setScope("personal")}>개인</button>
        </div>
        <div className="toolbar-group">
          <label className="filter-search"><Search size={18} /><input className="search-field" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="용어 검색" /></label>
          <select className="select-field" value={strategy} onChange={(event) => setStrategy(event.target.value)} aria-label="처리 방식 필터">
            <option value="all">전체 방식</option>
            {translationStrategies.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </div>
      </div>

      {scope === "team" && teamTermsError && <div className="document-error"><span>{teamTermsError}</span><button onClick={refreshTeamTerms}>다시 시도</button></div>}

      <section className="surface data-table-wrap">
        {scope === "team" && teamTermsLoading ? (
          <EmptyState title="팀 용어집을 불러오는 중입니다" description="잠시만 기다려 주세요." />
        ) : filteredTerms.length ? (
          <table className="data-table">
            <thead><tr><th>원문</th><th>지정 번역</th><th>용어 분류</th><th>번역 방식</th><th>등록자</th><th>등록일</th><th aria-label="관리" /></tr></thead>
            <tbody>{filteredTerms.map((term) => (
              <tr key={term.id}>
                <td><strong>{term.source}</strong></td><td>{term.target}</td>
                <td>{getTermCategoryLabel(term.termCategory)}</td>
                <td><span className={`badge${term.translationStrategy === "preserve" ? " neutral" : ""}`}>{getTranslationStrategyLabel(term.translationStrategy)}</span></td>
                <td>{term.creator}</td><td>{term.createdAt}</td>
                <td><div className="table-actions">
                  <button className="icon-button" onClick={() => openEdit(term)} title="수정" aria-label={`${term.source} 수정`}><Pencil size={16} /></button>
                  <button className="icon-button" onClick={() => setDeleting(term)} title="삭제" aria-label={`${term.source} 삭제`}><Trash2 size={16} /></button>
                </div></td>
              </tr>
            ))}</tbody>
          </table>
        ) : <EmptyState title="조건에 맞는 용어가 없습니다" description="검색 조건을 바꾸거나 새 용어를 등록해 보세요." />}
      </section>

      <section className="settings-section strategy-preferences-section">
        <div className="section-heading"><div><h2>상황별 번역 기본값</h2><p>사용자가 기억하도록 선택한 방식이 다음 번역과 AI 추천에 우선 적용됩니다.</p></div></div>
        {preferenceError && <div className="document-error"><span>{preferenceError}</span><button onClick={refreshPreferences}>다시 시도</button></div>}
        {visiblePreferences.length ? (
          <div className="data-table-wrap"><table className="data-table">
            <thead><tr><th>상황</th><th>언어</th><th>기본 방식</th><th>등록자</th><th aria-label="삭제" /></tr></thead>
            <tbody>{visiblePreferences.map((preference) => (
              <tr key={preference.id}>
                <td><strong>{getTermCategoryLabel(preference.term_category)}</strong></td>
                <td>{preference.source_language} → {preference.target_language}</td>
                <td><select className="select-field" value={preference.preferred_strategy} onChange={(event) => handlePreferenceChange(preference, event.target.value)}>
                  {translationStrategies.filter((item) => item.value !== "custom").map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select></td>
                <td>{preference.created_by_name}</td>
                <td><button className="icon-button" onClick={() => handlePreferenceDelete(preference)} title="기본값 삭제"><Trash2 size={16} /></button></td>
              </tr>
            ))}</tbody>
          </table></div>
        ) : <EmptyState title="기억된 번역 기본값이 없습니다" description="AI 추천을 승인할 때 상황별 기본값으로 기억할 수 있습니다." />}
      </section>

      {editing && (
        <Modal title={editing === "new" ? "용어 등록" : "용어 수정"} onClose={() => setEditing(null)} footer={<><button className="button" onClick={() => setEditing(null)} disabled={saving}>취소</button><button className="button primary" onClick={handleSubmit} disabled={saving || previewing}>{saving ? "저장 중" : "저장"}</button></>}>
          <form onSubmit={handleSubmit} className="form-grid">
            <div className="field full"><label htmlFor="termSource">원문</label><input id="termSource" className="text-field" value={form.source} onChange={(event) => setForm((current) => ({ ...current, source: event.target.value }))} /></div>
            <div className="field"><label htmlFor="termSourceLanguage">원문 언어</label><select id="termSourceLanguage" className="select-field" value={form.sourceLanguage} onChange={(event) => setForm((current) => ({ ...current, sourceLanguage: event.target.value }))}>{languages.map((language) => <option key={language.code} value={language.code}>{language.label}</option>)}</select></div>
            <div className="field"><label htmlFor="termTargetLanguage">번역 언어</label><select id="termTargetLanguage" className="select-field" value={form.targetLanguage} onChange={(event) => setForm((current) => ({ ...current, targetLanguage: event.target.value }))}>{languages.map((language) => <option key={language.code} value={language.code}>{language.label}</option>)}</select></div>
            <div className="field full"><label htmlFor="termCategory">용어 분류</label><select id="termCategory" className="select-field" value={form.termCategory} onChange={(event) => setForm((current) => ({ ...current, termCategory: event.target.value, rememberPreference: event.target.value === "other" ? false : current.rememberPreference }))}>{termCategories.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></div>
            <div className="field full"><span className="field-label">번역 방식</span><div className="segmented-control term-strategy-control">
              {translationStrategies.map((item) => <button type="button" key={item.value} className={form.translationStrategy === item.value ? "active" : ""} onClick={() => handleTranslationStrategy(item.value)} disabled={previewing}>{previewing && (item.value === "transliteration" || item.value === "semantic_translation") ? "생성 중" : item.label}</button>)}
            </div></div>
            <div className="field full"><label htmlFor="termTarget">번역 결과</label><input id="termTarget" className="text-field" value={form.target} disabled={form.translationStrategy === "preserve"} placeholder={form.translationStrategy === "preserve" ? "원문이 그대로 사용됩니다" : "번역 표현"} onChange={(event) => setForm((current) => ({ ...current, target: event.target.value, strategy: "translate", translationStrategy: "custom", creationMethod: "direct_edit", rememberPreference: false }))} /></div>
            <div className="field full"><label htmlFor="termMemo">메모</label><textarea id="termMemo" className="textarea-field" value={form.memo} onChange={(event) => setForm((current) => ({ ...current, memo: event.target.value }))} /></div>
            <div className="field full preference-form-row"><label><input type="checkbox" checked={form.rememberPreference} disabled={form.translationStrategy === "custom" || form.termCategory === "other"} onChange={(event) => setForm((current) => ({ ...current, rememberPreference: event.target.checked }))} /> 이 방식을 상황별 기본값으로 기억</label>{form.rememberPreference && <select className="select-field" value={form.preferenceScope} onChange={(event) => setForm((current) => ({ ...current, preferenceScope: event.target.value }))}><option value="team">팀 기본</option><option value="personal">내 기본</option></select>}</div>
            {error && <p className="form-error full">{error}</p>}
          </form>
        </Modal>
      )}

      {deleting && <Modal title="용어 삭제" onClose={() => { setDeleting(null); setDeleteError(""); }} footer={<><button className="button" onClick={() => setDeleting(null)}>취소</button><button className="button danger" onClick={handleDelete}>삭제</button></>}><p><strong>{deleting.source}</strong> 용어를 삭제할까요? 이후 번역부터 적용되지 않습니다.</p>{deleteError && <p className="form-error">{deleteError}</p>}</Modal>}
    </div>
  );
}
