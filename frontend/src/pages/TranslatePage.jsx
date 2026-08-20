import {
  AlertCircle,
  ArrowLeftRight,
  BookOpenCheck,
  Check,
  ChevronDown,
  Clipboard,
  LoaderCircle,
  Pencil,
  RotateCcw,
  Sparkles,
  UserRound,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { createHistory } from "../api/history";
import { approveSuggestion, previewTermStrategy, rejectSuggestion, toSuggestionCandidate } from "../api/suggestions";
import { translateText } from "../api/translations";
import DetectedTermCard from "../components/translate/DetectedTermCard";
import DocumentWorkspace from "../components/translate/DocumentWorkspace";
import { HighlightedText, HighlightedTextarea } from "../components/translate/HighlightedText";
import ImageTranslationPanel from "../components/translate/ImageTranslationPanel";
import ModeTabs from "../components/translate/ModeTabs";
import { useAppData } from "../context/appData";
import {
  countryLanguageMap,
  getRecipientApiTone,
  getRecipientToneLabel,
  languages,
  normalizeRecipientTone,
} from "../data/referenceData";
import "./TranslatePage.css";

function isUuid(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value || "");
}

function replaceSuggestionTarget(value, highlights, suggestionId, target) {
  const matches = highlights
    .filter((item) => item.suggestion_id === suggestionId)
    .sort((left, right) => left.start - right.start);
  if (!matches.length) return { value, highlights };

  let nextValue = "";
  let cursor = 0;
  matches.forEach((match) => {
    nextValue += value.slice(cursor, match.start) + target;
    cursor = match.end;
  });
  nextValue += value.slice(cursor);

  const nextHighlights = highlights.map((highlight) => {
    let shift = 0;
    for (const match of matches) {
      const delta = target.length - (match.end - match.start);
      if (highlight.suggestion_id === suggestionId && highlight.start === match.start) {
        return { ...highlight, start: match.start + shift, end: match.start + shift + target.length, target };
      }
      if (match.end <= highlight.start) shift += delta;
    }
    return { ...highlight, start: highlight.start + shift, end: highlight.end + shift };
  });
  return { value: nextValue, highlights: nextHighlights };
}

export default function TranslatePage() {
  const {
    currentUser,
    team,
    recipients,
    recipientsLoading,
    terms,
    createTeamTerm,
    refreshTeamTerms,
    refreshHistory,
    updateSavedHistory,
    teamTermsLoading,
  } = useAppData();
  const [mode, setMode] = useState("text");
  const [sourceLanguage, setSourceLanguage] = useState("ko");
  const [targetLanguage, setTargetLanguage] = useState("en");
  const [selectedRecipientId, setSelectedRecipientId] = useState("");
  const [teamGlossaryEnabled, setTeamGlossaryEnabled] = useState(true);
  const [personalGlossaryEnabled, setPersonalGlossaryEnabled] = useState(true);
  const [text, setText] = useState("");
  const [result, setResult] = useState("");
  const [highlights, setHighlights] = useState({ source: [], translation: [] });
  const [suggestions, setSuggestions] = useState([]);
  const [suggestionError, setSuggestionError] = useState("");
  const [suggestionChecked, setSuggestionChecked] = useState(false);
  const [loading, setLoading] = useState(false);
  const historyIdRef = useRef(null);
  const historyTimerRef = useRef(null);
  const [historySaveFailed, setHistorySaveFailed] = useState(false);
  const [notice, setNotice] = useState("");
  const [editingResult, setEditingResult] = useState(false);

  const selectedRecipient = recipients.find((recipient) => recipient.id === selectedRecipientId);

  useEffect(() => () => window.clearTimeout(historyTimerRef.current), []);

  function handleRecipientChange(event) {
    const id = event.target.value;
    const recipient = recipients.find((item) => item.id === id);
    setSelectedRecipientId(id);
    clearTranslationState();
    if (recipient && countryLanguageMap[recipient.country]) {
      setTargetLanguage(countryLanguageMap[recipient.country]);
      setNotice(`${recipient.name}님의 국적에 맞춰 번역 언어를 자동 설정했습니다.`);
    }
  }

  function handleSwapLanguages() {
    setSourceLanguage(targetLanguage);
    setTargetLanguage(sourceLanguage);
    clearTranslationState();
  }

  function clearTranslationState() {
    setResult("");
    setSuggestions([]);
    setHighlights({ source: [], translation: [] });
    setSuggestionChecked(false);
    setSuggestionError("");
    historyIdRef.current = null;
    setHistorySaveFailed(false);
  }

  async function updateCurrentHistory(finalResult, appliedTerms) {
    if (!historyIdRef.current) return;
    try {
      await updateSavedHistory(historyIdRef.current, {
        translatedText: finalResult,
        ...(appliedTerms ? { appliedTerms } : {}),
      });
      setNotice("수정한 번역을 히스토리에 반영했습니다.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "히스토리를 수정하지 못했습니다.");
    }
  }

  function scheduleCurrentHistoryUpdate(finalResult, appliedTerms) {
    window.clearTimeout(historyTimerRef.current);
    historyTimerRef.current = window.setTimeout(
      () => updateCurrentHistory(finalResult, appliedTerms),
      600,
    );
  }

  async function retryHistorySave() {
    try {
      const appliedTerms = [...new Map(
        highlights.source
          .filter((item) => item.state === "applied")
          .map((item) => [`${item.source}-${item.target}`, `${item.source} → ${item.target}`]),
      ).values()];
      const saved = await createHistory({
        mode: "text",
        source_language: sourceLanguage,
        target_language: targetLanguage,
        source_text: text.trim(),
        translated_text: result,
        recipient_id: selectedRecipient && isUuid(selectedRecipient.id) ? selectedRecipient.id : null,
        recipient_name: selectedRecipient?.name || null,
        applied_terms: appliedTerms,
      });
      historyIdRef.current = saved.id;
      setHistorySaveFailed(false);
      setNotice("번역 결과를 히스토리에 저장했습니다.");
      await refreshHistory();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "히스토리를 저장하지 못했습니다.");
    }
  }

  async function handleTranslate() {
    if (!text.trim() || loading || teamTermsLoading) return;
    setLoading(true);
    setSuggestionChecked(false);
    setSuggestionError("");
    setSuggestions([]);
    setNotice("");
    setEditingResult(false);

    const contact = selectedRecipient && !isUuid(selectedRecipient.id)
      ? {
          name: selectedRecipient.name,
          company: selectedRecipient.company || null,
          role: selectedRecipient.position || null,
          country: selectedRecipient.country || null,
          tone_style: normalizeRecipientTone(selectedRecipient.tone),
          communication_preferences: selectedRecipient.traits?.trim() || null,
        }
      : null;

    try {
      const response = await translateText({
        text: text.trim(),
        source_language: sourceLanguage,
        target_language: targetLanguage,
        tone: selectedRecipient ? getRecipientApiTone(selectedRecipient.tone) : "standard",
        purpose: "email",
        contact_id: selectedRecipient && isUuid(selectedRecipient.id) ? selectedRecipient.id : null,
        contact,
        use_memory: false,
        save_to_memory: false,
        team_key: team.id,
        user_key: currentUser.id,
        created_by_name: currentUser.nickname,
        glossary_scopes: [
          ...(teamGlossaryEnabled ? ["team"] : []),
          ...(personalGlossaryEnabled ? ["personal"] : []),
        ],
        max_suggestions: 8,
      });
      setResult(response.translation);
      setHighlights(response.highlights ?? { source: [], translation: [] });
      setSuggestions((response.suggestions ?? []).map((item, index) => toSuggestionCandidate(item, index, "text-term")));
      setSuggestionError(response.suggestion_warning || "");
      setSuggestionChecked(true);
      historyIdRef.current = response.history_id || null;
      setHistorySaveFailed(Boolean(response.history_warning));
      await refreshHistory();
      setNotice(response.history_warning || "번역 결과를 히스토리에 저장했습니다.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "번역 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(result);
      setNotice("번역 결과를 복사했습니다.");
    } catch {
      setNotice("클립보드에 접근할 수 없습니다.");
    }
  }

  async function handleToggleResultEditing() {
    if (editingResult) await updateCurrentHistory(result);
    setEditingResult((value) => !value);
  }

  async function handleAddDetectedTerm(candidate) {
    const exists = terms.some(
      (term) => term.scope === "team"
        && term.sourceLanguage === sourceLanguage
        && term.targetLanguage === targetLanguage
        && term.source.trim().toLowerCase() === candidate.source.trim().toLowerCase(),
    );
    if (exists) return "exists";

    try {
      if (isUuid(candidate.id)) {
        const approved = await approveSuggestion(candidate.id, {
          target: candidate.strategy === "preserve" ? null : candidate.target.trim(),
          mode: candidate.strategy,
          note: candidate.kind,
          created_by_key: currentUser.id,
          created_by_name: currentUser.nickname,
          scope: "team",
          creation_method: candidate.creationMethod || "manual",
          translation_strategy: candidate.translationStrategy || "custom",
          term_category: candidate.termCategory || "other",
          preference_scope: candidate.rememberPreference ? candidate.preferenceScope : null,
        });
        await refreshTeamTerms();
        setHighlights((current) => ({
          source: current.source.map((item) => item.suggestion_id === candidate.id
            ? { ...item, state: "applied", suggestion_id: null, term_id: approved.approved_term_id }
            : item),
          translation: current.translation.map((item) => item.suggestion_id === candidate.id
            ? { ...item, state: "applied", suggestion_id: null, term_id: approved.approved_term_id }
            : item),
        }));
        return "added";
      }
      await createTeamTerm({
        source: candidate.source.trim(),
        target: candidate.strategy === "preserve" ? candidate.source.trim() : candidate.target.trim(),
        strategy: candidate.strategy,
        memo: candidate.kind,
        sourceLanguage,
        targetLanguage,
        creationMethod: candidate.creationMethod || "manual",
        translationStrategy: candidate.translationStrategy || "custom",
        termCategory: candidate.termCategory || "other",
        rememberPreference: candidate.rememberPreference,
        preferenceScope: candidate.preferenceScope,
      });
      return "added";
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        await refreshTeamTerms();
        return "exists";
      }
      throw error;
    }
  }

  function handleSuggestionTargetChange(id, target, translationStrategy, creationMethod) {
    const strategy = translationStrategy === "preserve" ? "preserve" : "translate";
    setSuggestions((current) => current.map((item) => item.id === id
      ? {
          ...item,
          target,
          recommendedStrategy: strategy,
          translationStrategy,
          creationMethod: creationMethod || "direct_edit",
        }
      : item));
    const replaced = replaceSuggestionTarget(result, highlights.translation, id, target);
    setResult(replaced.value);
    setHighlights({
      source: highlights.source.map((item) => item.suggestion_id === id ? { ...item, target } : item),
      translation: replaced.highlights,
    });
    const appliedTerms = [...new Map(
      highlights.source
        .filter((item) => item.state === "applied")
        .map((item) => [`${item.source}-${item.target}`, `${item.source} → ${item.target}`]),
    ).values()];
    scheduleCurrentHistoryUpdate(replaced.value, appliedTerms);
  }

  function handlePreviewStrategy({ source, strategy }) {
    return previewTermStrategy({
      source,
      source_language: sourceLanguage,
      target_language: targetLanguage,
      strategy,
      context: text.trim().slice(0, 1000) || null,
    });
  }

  async function handleRejectSuggestion(id) {
    if (isUuid(id)) await rejectSuggestion(id);
    setSuggestions((current) => current.filter((item) => item.id !== id));
    await handleTranslate();
  }

  return (
    <div className={`translate-page${mode === "text" ? "" : " workspace-mode"}`}>
      <div className="translate-container">
        <div className="translate-toolbar">
          <ModeTabs mode={mode} onChange={(nextMode) => { setMode(nextMode); setNotice(""); }} />
          <label className="recipient-selector">
            <UserRound size={19} />
            <select value={selectedRecipientId} onChange={handleRecipientChange} aria-label="번역 수신자 선택" disabled={recipientsLoading}>
              <option value="">{recipientsLoading ? "수신자 불러오는 중" : "기본 톤"}</option>
              {recipients.map((recipient) => <option key={recipient.id} value={recipient.id}>{recipient.name}</option>)}
            </select>
            <ChevronDown size={17} />
          </label>
        </div>

        {selectedRecipient && (
          <div className="recipient-context">
            <span><strong>수신자</strong> {selectedRecipient.name}</span>
            <span>{selectedRecipient.company}</span>
            <span>{selectedRecipient.position}</span>
            <span>{selectedRecipient.country}</span>
            <span>{getRecipientToneLabel(selectedRecipient.tone)}</span>
          </div>
        )}

        {mode === "text" && <>
          <section className="translation-box">
          <div className="language-header">
            <select value={sourceLanguage} onChange={(event) => { setSourceLanguage(event.target.value); clearTranslationState(); }} aria-label="원문 언어">
              {languages.map((language) => <option key={language.code} value={language.code}>{language.label}</option>)}
            </select>
            <button className="swap-button" onClick={handleSwapLanguages} aria-label="언어 방향 전환" title="언어 방향 전환">
              <ArrowLeftRight size={22} />
            </button>
            <div className="target-language">
              <select value={targetLanguage} onChange={(event) => { setTargetLanguage(event.target.value); clearTranslationState(); }} aria-label="번역 언어">
                {languages.map((language) => <option key={language.code} value={language.code}>{language.label}</option>)}
              </select>
              <div className="glossary-toggles">
                <label className="glossary-toggle">
                  <span><BookOpenCheck size={16} /> 팀</span>
                  <input type="checkbox" checked={teamGlossaryEnabled} onChange={(event) => { setTeamGlossaryEnabled(event.target.checked); clearTranslationState(); }} />
                  <i aria-hidden="true" />
                </label>
                <label className="glossary-toggle">
                  <span>개인</span>
                  <input type="checkbox" checked={personalGlossaryEnabled} onChange={(event) => { setPersonalGlossaryEnabled(event.target.checked); clearTranslationState(); }} />
                  <i aria-hidden="true" />
                </label>
              </div>
            </div>
          </div>

          <div className="translation-content">
            <div className="source-panel">
              <HighlightedTextarea
                value={text}
                highlights={highlights.source}
                maxLength={3000}
                onChange={(event) => { setText(event.target.value); clearTranslationState(); }}
                placeholder="번역할 내용을 입력하세요."
              />
              <span className="character-count">{text.length.toLocaleString()} / 3,000</span>
            </div>
            <div className="result-panel">
              {loading ? (
                <div className="translation-loading"><LoaderCircle size={25} className="spin" /> Glossy가 문맥을 확인하고 있습니다.</div>
              ) : editingResult ? (
                <textarea value={result} onChange={(event) => setResult(event.target.value)} aria-label="번역 결과 수정" />
              ) : (
                <p>{result ? <HighlightedText text={result} highlights={highlights.translation} /> : <span className="result-placeholder">번역 결과가 여기에 표시됩니다.</span>}</p>
              )}
              {result && !loading && (
                <div className="result-actions">
                  <button onClick={handleCopy} title="복사"><Clipboard size={17} /><span>복사</span></button>
                  <button onClick={handleTranslate} title="재번역" disabled={loading}><RotateCcw size={17} /><span>재번역</span></button>
                  <button onClick={handleToggleResultEditing} title="결과 수정">
                    {editingResult ? <Check size={17} /> : <Pencil size={17} />}<span>{editingResult ? "완료" : "수정"}</span>
                  </button>
                </div>
              )}
            </div>
          </div>
          </section>

          <div className="translation-footer">
            <span className="translation-notice">{notice}{historySaveFailed && <button type="button" onClick={retryHistorySave}>저장 재시도</button>}</span>
            <button className="button primary translate-button" onClick={handleTranslate} disabled={!text.trim() || loading || teamTermsLoading}>
              {teamTermsLoading ? <><LoaderCircle size={18} className="spin" /> 용어집 준비 중</> : loading ? <><LoaderCircle size={18} className="spin" /> 번역 중</> : "번역하기"}
            </button>
          </div>

          {(loading || suggestionChecked) && (
            <section className="detected-terms-section">
              <div className="document-section-heading">
                <h3><Sparkles size={18} /> 용어집 후보</h3>
                <span>AI가 찾은 새 표현을 확인한 뒤 팀 용어집에 추가하세요.</span>
              </div>
              {loading && <div className="translation-loading"><LoaderCircle size={22} className="spin" /> 번역과 새 용어를 함께 확인하고 있습니다.</div>}
              {suggestionError && (
                <div className="document-error">
                  <AlertCircle size={18} />
                  <span>{suggestionError}</span>
                  <button onClick={handleTranslate}>다시 시도</button>
                </div>
              )}
              {!loading && !suggestionError && suggestions.length === 0 && (
                <p className="result-placeholder">새로 추천할 용어가 없습니다.</p>
              )}
              <div className="detected-term-list">
                {suggestions.map((candidate) => (
                  <DetectedTermCard
                    key={candidate.id}
                    candidate={candidate}
                    onAdd={handleAddDetectedTerm}
                    onReject={handleRejectSuggestion}
                    onResolved={(id) => setSuggestions((current) => current.filter((item) => item.id !== id))}
                    onTargetChange={handleSuggestionTargetChange}
                    onPreview={handlePreviewStrategy}
                  />
                ))}
              </div>
            </section>
          )}
        </>}

        {mode === "document" && (
          <DocumentWorkspace
            options={{
              sourceLanguage,
              targetLanguage,
              recipientId: selectedRecipientId,
              recipient: selectedRecipient,
              teamGlossaryEnabled,
              personalGlossaryEnabled,
              teamKey: team.id,
              userKey: currentUser.id,
              creatorName: currentUser.nickname,
            }}
            settingsProps={{
              sourceLanguage,
              targetLanguage,
              teamGlossaryEnabled,
              personalGlossaryEnabled,
              onSourceLanguageChange: setSourceLanguage,
              onTargetLanguageChange: setTargetLanguage,
              onSwapLanguages: handleSwapLanguages,
              onTeamGlossaryChange: setTeamGlossaryEnabled,
              onPersonalGlossaryChange: setPersonalGlossaryEnabled,
            }}
            onAddTerm={handleAddDetectedTerm}
            onPreview={handlePreviewStrategy}
            onHistorySaved={refreshHistory}
          />
        )}

        {mode === "image" && (
          <ImageTranslationPanel
            options={{
              sourceLanguage,
              targetLanguage,
              recipientId: selectedRecipientId,
              recipient: selectedRecipient,
              teamGlossaryEnabled,
              personalGlossaryEnabled,
              teamKey: team.id,
              userKey: currentUser.id,
              creatorName: currentUser.nickname,
            }}
            settingsProps={{
              sourceLanguage,
              targetLanguage,
              teamGlossaryEnabled,
              personalGlossaryEnabled,
              onSourceLanguageChange: setSourceLanguage,
              onTargetLanguageChange: setTargetLanguage,
              onSwapLanguages: handleSwapLanguages,
              onTeamGlossaryChange: setTeamGlossaryEnabled,
              onPersonalGlossaryChange: setPersonalGlossaryEnabled,
            }}
            onAddTerm={handleAddDetectedTerm}
            onPreview={handlePreviewStrategy}
            onHistorySaved={refreshHistory}
          />
        )}
      </div>
    </div>
  );
}
