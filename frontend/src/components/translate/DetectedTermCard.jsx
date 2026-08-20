import { Check, Pencil, RotateCcw, Sparkles, Volume2, X } from "lucide-react";
import { useState } from "react";
import {
  getTermCategoryLabel,
  getTranslationStrategyLabel,
  termCategories,
} from "../../data/referenceData";

export default function DetectedTermCard({
  candidate,
  onAdd,
  onReject,
  onResolved,
  onTargetChange,
  onPreview,
}) {
  const initialStrategy = candidate.translationStrategy
    || (candidate.recommendedStrategy === "preserve" ? "preserve" : "semantic_translation");
  const [target, setTarget] = useState(candidate.target || candidate.source);
  const [strategy, setStrategy] = useState(initialStrategy);
  const [termCategory, setTermCategory] = useState(candidate.termCategory || "other");
  const [editing, setEditing] = useState(initialStrategy === "custom");
  const [rememberPreference, setRememberPreference] = useState(false);
  const [preferenceScope, setPreferenceScope] = useState("team");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [previewing, setPreviewing] = useState("");

  function applyTarget(nextTarget, nextStrategy, creationMethod = nextStrategy) {
    setTarget(nextTarget);
    setStrategy(nextStrategy);
    setEditing(nextStrategy === "custom");
    onTargetChange?.(candidate.id, nextTarget, nextStrategy, creationMethod);
  }

  async function handleStrategy(nextStrategy) {
    setError("");
    if (nextStrategy === "preserve") {
      applyTarget(candidate.source, "preserve", "manual");
      return;
    }
    if (nextStrategy === "custom") {
      setStrategy("custom");
      setEditing(true);
      setRememberPreference(false);
      return;
    }
    if (nextStrategy === strategy && target.trim()) {
      setEditing(false);
      return;
    }

    setPreviewing(nextStrategy);
    try {
      const preview = await onPreview({
        source: candidate.source,
        strategy: nextStrategy,
      });
      applyTarget(preview.target, nextStrategy, nextStrategy);
    } catch (previewError) {
      setError(previewError instanceof Error ? previewError.message : "새 번역 후보를 만들지 못했습니다.");
    } finally {
      setPreviewing("");
    }
  }

  function handleTargetChange(event) {
    const nextTarget = event.target.value;
    setTarget(nextTarget);
    setStrategy("custom");
    setRememberPreference(false);
    onTargetChange?.(candidate.id, nextTarget, "custom", "direct_edit");
  }

  async function handleAdd() {
    if (strategy !== "preserve" && !target.trim()) {
      setError("번역 결과를 입력해 주세요.");
      return;
    }

    setStatus("saving");
    setError("");
    try {
      const result = await onAdd({
        id: candidate.id,
        source: candidate.source,
        target: strategy === "preserve" ? candidate.source : target.trim(),
        strategy: strategy === "preserve" ? "preserve" : "translate",
        translationStrategy: strategy,
        termCategory,
        rememberPreference,
        preferenceScope,
        kind: candidate.reason || candidate.kind,
        creationMethod: strategy === "transliteration" || strategy === "semantic_translation"
          ? strategy
          : strategy === "custom" ? "direct_edit" : "manual",
      });
      setStatus(result === "exists" ? "exists" : "added");
      if (result !== "exists") onResolved?.(candidate.id);
    } catch (addError) {
      setStatus("");
      setError(addError instanceof Error ? addError.message : "용어집에 추가하지 못했습니다.");
    }
  }

  async function handleReject() {
    if (!onReject) return;
    setStatus("rejecting");
    setError("");
    try {
      await onReject(candidate.id);
    } catch (rejectError) {
      setStatus("");
      setError(rejectError instanceof Error ? rejectError.message : "추천을 거절하지 못했습니다.");
    }
  }

  const canRemember = strategy !== "custom" && termCategory !== "other";
  const statusLabel = status === "saving"
    ? "추가 중"
    : status === "exists"
      ? "이미 등록됨"
      : status === "added"
        ? "추가 완료"
        : "용어집 추가";

  return (
    <article className="detected-term-card">
      <div className="detected-term-mapping">
        <div className="detected-term-side">
          <span>원문</span>
          <strong>{candidate.source}</strong>
        </div>
        <span className="detected-term-arrow" aria-hidden="true">→</span>
        <div className="detected-term-side target">
          <span>추천 번역</span>
          {editing ? (
            <label>
              <span className="sr-only">추천 번역 직접 입력</span>
              <input value={target} onChange={handleTargetChange} autoFocus />
            </label>
          ) : <strong>{target}</strong>}
        </div>
      </div>

      <div className="detected-term-copy">
        <span>{candidate.reason || candidate.kind}</span>
        {candidate.evidence && <small>근거: {candidate.evidence}</small>}
        {candidate.confidence !== null && candidate.confidence !== undefined && (
          <small>AI 신뢰도 {Math.round(candidate.confidence * 100)}%</small>
        )}
        <small>{getTermCategoryLabel(termCategory)} · {getTranslationStrategyLabel(strategy)}</small>
      </div>

      <div className="detected-term-classification">
        <label>
          <span>용어 분류</span>
          <select value={termCategory} onChange={(event) => {
            setTermCategory(event.target.value);
            if (event.target.value === "other") setRememberPreference(false);
          }}>
            {termCategories.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </label>
      </div>

      <div className="detected-term-actions strategy-actions">
        <button type="button" className={strategy === "preserve" ? "active" : ""} onClick={() => handleStrategy("preserve")}><RotateCcw size={16} /> 원문 그대로</button>
        <button type="button" className={strategy === "transliteration" ? "active" : ""} onClick={() => handleStrategy("transliteration")} disabled={Boolean(previewing)}><Volume2 size={16} /> {previewing === "transliteration" ? "생성 중" : "발음대로"}</button>
        <button type="button" className={strategy === "semantic_translation" ? "active" : ""} onClick={() => handleStrategy("semantic_translation")} disabled={Boolean(previewing)}><Sparkles size={16} /> {previewing === "semantic_translation" ? "생성 중" : "의미 번역"}</button>
        <button type="button" className={strategy === "custom" ? "active" : ""} onClick={() => handleStrategy("custom")}><Pencil size={16} /> 직접 입력</button>
      </div>

      <div className="preference-memory-row">
        <label>
          <input
            type="checkbox"
            checked={rememberPreference}
            disabled={!canRemember}
            onChange={(event) => setRememberPreference(event.target.checked)}
          />
          이 방식을 {getTermCategoryLabel(termCategory)} 기본값으로 기억
        </label>
        {rememberPreference && (
          <select value={preferenceScope} onChange={(event) => setPreferenceScope(event.target.value)} aria-label="기억 범위">
            <option value="team">팀 기본</option>
            <option value="personal">내 기본</option>
          </select>
        )}
      </div>

      <div className="detected-term-actions decision-actions">
        <button type="button" className="add-term-button" onClick={handleAdd} disabled={Boolean(status) || Boolean(previewing)}><Check size={16} /> {statusLabel}</button>
        {onReject && <button type="button" onClick={handleReject} disabled={Boolean(status)}><X size={16} /> {status === "rejecting" ? "재번역 중" : "거절"}</button>}
      </div>
      {error && <p className="form-error">{error}</p>}
    </article>
  );
}
