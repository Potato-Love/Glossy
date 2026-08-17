import {
  ArrowLeftRight,
  BookOpenCheck,
  Check,
  ChevronDown,
  Clipboard,
  LoaderCircle,
  Pencil,
  RotateCcw,
  UserRound,
} from "lucide-react";
import { useRef, useState } from "react";
import DocumentWorkspace from "../components/translate/DocumentWorkspace";
import ImageTranslationPanel from "../components/translate/ImageTranslationPanel";
import ModeTabs from "../components/translate/ModeTabs";
import TermSuggestionCard from "../components/translate/TermSuggestionCard";
import { useAppData } from "../context/appData";
import { countryLanguageMap, languages } from "../data/mockData";
import "./TranslatePage.css";

const initialText = "안녕하세요, 저희는 풍차돌리기 팀 입니다.";
const initialTarget = "Poongchadoligi";

function formatNow() {
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date());
}

export default function TranslatePage() {
  const { currentUser, recipients, terms, addTerm, saveTranslation } = useAppData();
  const [mode, setMode] = useState("text");
  const [sourceLanguage, setSourceLanguage] = useState("ko");
  const [targetLanguage, setTargetLanguage] = useState("en");
  const [selectedRecipientId, setSelectedRecipientId] = useState(recipients[0]?.id ?? "");
  const [glossaryEnabled, setGlossaryEnabled] = useState(true);
  const [text, setText] = useState(initialText);
  const [result, setResult] = useState(`Hello, we are team “${initialTarget}”.`);
  const [highlightTerm, setHighlightTerm] = useState({
    source: "풍차돌리기",
    target: initialTarget,
    strategy: "발음대로 번역",
  });
  const [suggestion, setSuggestion] = useState({ source: "풍차돌리기", target: initialTarget });
  const [loading, setLoading] = useState(false);
  const savedRef = useRef(false);
  const [notice, setNotice] = useState("");
  const [editingResult, setEditingResult] = useState(false);

  const selectedRecipient = recipients.find((recipient) => recipient.id === selectedRecipientId);

  function handleRecipientChange(event) {
    const id = event.target.value;
    const recipient = recipients.find((item) => item.id === id);
    setSelectedRecipientId(id);
    if (recipient && countryLanguageMap[recipient.country]) {
      setTargetLanguage(countryLanguageMap[recipient.country]);
      setNotice(`${recipient.name}님의 국적에 맞춰 번역 언어를 자동 설정했습니다.`);
    }
  }

  function handleSwapLanguages() {
    setSourceLanguage(targetLanguage);
    setTargetLanguage(sourceLanguage);
  }

  function saveToHistory(finalResult, appliedTerms = []) {
    if (savedRef.current) return;
    saveTranslation({
      sourceText: text,
      translatedText: finalResult,
      executorId: currentUser.id,
      executor: currentUser.nickname,
      recipient: selectedRecipient?.name ?? "기본 톤",
      createdAt: formatNow(),
      appliedTerms,
    });
    savedRef.current = true;
    setNotice("최종 번역을 히스토리에 저장했습니다.");
  }

  function buildMockTranslation() {
    const existingTerm = glossaryEnabled
      ? terms.find((term) => text.includes(term.source))
      : null;

    if (text.includes("풍차돌리기")) {
      const savedTerm = terms.find((term) => term.source === "풍차돌리기");
      if (glossaryEnabled && savedTerm) {
        const finalText = `Hello, we are team “${savedTerm.target}”.`;
        setResult(finalText);
        setHighlightTerm(savedTerm);
        setSuggestion(null);
        saveToHistory(finalText, [`${savedTerm.source} → ${savedTerm.target}`]);
        return;
      }

      setResult(`Hello, we are team “${initialTarget}”.`);
      setHighlightTerm({ source: "풍차돌리기", target: initialTarget, strategy: "발음대로 번역" });
      setSuggestion({ source: "풍차돌리기", target: initialTarget });
      return;
    }

    const translated = existingTerm
      ? `Glossy translation: ${text.replace(existingTerm.source, existingTerm.target)}`
      : `Glossy translation: ${text}`;
    setResult(translated);
    setHighlightTerm(existingTerm);
    setSuggestion(null);
    saveToHistory(translated, existingTerm ? [`${existingTerm.source} → ${existingTerm.target}`] : []);
  }

  function handleTranslate() {
    if (!text.trim() || loading) return;
    setLoading(true);
    savedRef.current = false;
    setNotice("");
    window.setTimeout(() => {
      buildMockTranslation();
      setLoading(false);
    }, 650);
  }

  function handleApproveSuggestion() {
    const target = suggestion?.target.trim();
    if (!suggestion || !target) {
      setNotice("추천 번역을 입력해 주세요.");
      return;
    }

    const finalResult = `Hello, we are team “${target}”.`;
    const exists = terms.some((term) => term.scope === "team" && term.source === suggestion.source);
    if (!exists) {
      addTerm({
        scope: "team",
        source: suggestion.source,
        target,
        strategy: "translate",
        memo: "번역 화면 AI 후보에서 승인",
        creator: currentUser.nickname,
        createdAt: new Intl.DateTimeFormat("ko-KR").format(new Date()),
      });
    }
    setResult(finalResult);
    setHighlightTerm({ source: suggestion.source, target, strategy: "발음대로 번역" });
    setSuggestion(null);
    saveToHistory(finalResult, [`${suggestion.source} → ${target}`]);
  }

  function handleRejectSuggestion() {
    const generalResult = "Hello, we are the Windmill Spinning team.";
    setResult(generalResult);
    setHighlightTerm(null);
    setSuggestion(null);
    saveToHistory(generalResult, []);
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(result);
      setNotice("번역 결과를 복사했습니다.");
    } catch {
      setNotice("클립보드에 접근할 수 없습니다.");
    }
  }

  function handleAddDetectedTerm(candidate) {
    const exists = terms.some(
      (term) => term.scope === "team" && term.source.trim().toLowerCase() === candidate.source.trim().toLowerCase(),
    );
    if (exists) return "exists";

    addTerm({
      scope: "team",
      source: candidate.source.trim(),
      target: candidate.strategy === "preserve" ? candidate.source.trim() : candidate.target.trim(),
      strategy: candidate.strategy,
      memo: candidate.kind,
      creator: currentUser.nickname,
      createdAt: new Intl.DateTimeFormat("ko-KR").format(new Date()),
    });
    return "added";
  }

  function renderResult() {
    if (!highlightTerm?.target || !result.includes(highlightTerm.target)) return result;
    const [before, after] = result.split(highlightTerm.target);
    return (
      <>{before}<mark className="applied-term" title={`원문: ${highlightTerm.source} · 처리: ${highlightTerm.strategy ?? "지정 번역"}`}>{highlightTerm.target}</mark>{after}</>
    );
  }

  return (
    <div className={`translate-page${mode === "text" ? "" : " workspace-mode"}`}>
      <div className="translate-container">
        <div className="translate-toolbar">
          <ModeTabs mode={mode} onChange={(nextMode) => { setMode(nextMode); setNotice(""); }} />
          <label className="recipient-selector">
            <UserRound size={19} />
            <select value={selectedRecipientId} onChange={handleRecipientChange} aria-label="번역 수신자 선택">
              <option value="">기본 톤</option>
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
            <span>{selectedRecipient.tone}</span>
          </div>
        )}

        {mode === "text" && <>
          <section className="translation-box">
          <div className="language-header">
            <select value={sourceLanguage} onChange={(event) => setSourceLanguage(event.target.value)} aria-label="원문 언어">
              {languages.map((language) => <option key={language.code} value={language.code}>{language.label}</option>)}
            </select>
            <button className="swap-button" onClick={handleSwapLanguages} aria-label="언어 방향 전환" title="언어 방향 전환">
              <ArrowLeftRight size={22} />
            </button>
            <div className="target-language">
              <select value={targetLanguage} onChange={(event) => setTargetLanguage(event.target.value)} aria-label="번역 언어">
                {languages.map((language) => <option key={language.code} value={language.code}>{language.label}</option>)}
              </select>
              <label className="glossary-toggle">
                <span><BookOpenCheck size={16} /> 용어집</span>
                <input type="checkbox" checked={glossaryEnabled} onChange={(event) => setGlossaryEnabled(event.target.checked)} />
                <i aria-hidden="true" />
              </label>
            </div>
          </div>

          <div className="translation-content">
            <div className="source-panel">
              <textarea value={text} maxLength={3000} onChange={(event) => setText(event.target.value)} placeholder="번역할 내용을 입력하세요." />
              <span className="character-count">{text.length.toLocaleString()} / 3,000</span>
            </div>
            <div className="result-panel">
              {loading ? (
                <div className="translation-loading"><LoaderCircle size={25} className="spin" /> Glossy가 문맥을 확인하고 있습니다.</div>
              ) : editingResult ? (
                <textarea value={result} onChange={(event) => setResult(event.target.value)} aria-label="번역 결과 수정" />
              ) : (
                <p>{result ? renderResult() : <span className="result-placeholder">번역 결과가 여기에 표시됩니다.</span>}</p>
              )}
              {result && !loading && (
                <div className="result-actions">
                  <button onClick={handleCopy} title="복사"><Clipboard size={17} /><span>복사</span></button>
                  <button onClick={handleTranslate} title="재번역"><RotateCcw size={17} /><span>재번역</span></button>
                  <button onClick={() => setEditingResult((value) => !value)} title="결과 수정">
                    {editingResult ? <Check size={17} /> : <Pencil size={17} />}<span>{editingResult ? "완료" : "수정"}</span>
                  </button>
                </div>
              )}
            </div>
          </div>
          </section>

          <div className="translation-footer">
            <span className="translation-notice">{notice}</span>
            <button className="button primary translate-button" onClick={handleTranslate} disabled={!text.trim() || loading}>
              {loading ? <><LoaderCircle size={18} className="spin" /> 번역 중</> : "번역하기"}
            </button>
          </div>

          {suggestion && (
            <TermSuggestionCard
              suggestion={suggestion}
              onChange={(target) => {
                setSuggestion((current) => ({ ...current, target }));
                setResult(`Hello, we are team “${target}”.`);
                setHighlightTerm((current) => ({ ...current, target }));
              }}
              onApprove={handleApproveSuggestion}
              onReject={handleRejectSuggestion}
            />
          )}
        </>}

        {mode === "document" && (
          <DocumentWorkspace
            options={{ sourceLanguage, targetLanguage, recipientId: selectedRecipientId, glossaryEnabled }}
            settingsProps={{
              sourceLanguage,
              targetLanguage,
              glossaryEnabled,
              onSourceLanguageChange: setSourceLanguage,
              onTargetLanguageChange: setTargetLanguage,
              onSwapLanguages: handleSwapLanguages,
              onGlossaryChange: setGlossaryEnabled,
            }}
            onAddTerm={handleAddDetectedTerm}
          />
        )}

        {mode === "image" && (
          <ImageTranslationPanel
            options={{ sourceLanguage, targetLanguage, recipientId: selectedRecipientId, glossaryEnabled }}
            settingsProps={{
              sourceLanguage,
              targetLanguage,
              glossaryEnabled,
              onSourceLanguageChange: setSourceLanguage,
              onTargetLanguageChange: setTargetLanguage,
              onSwapLanguages: handleSwapLanguages,
              onGlossaryChange: setGlossaryEnabled,
            }}
            onAddTerm={handleAddDetectedTerm}
          />
        )}
      </div>
    </div>
  );
}
