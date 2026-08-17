import { Check, Pencil, RotateCcw } from "lucide-react";
import { useState } from "react";

export default function DetectedTermCard({ candidate, onAdd }) {
  const [target, setTarget] = useState(candidate.target);
  const [strategy, setStrategy] = useState(candidate.recommendedStrategy);
  const [editing, setEditing] = useState(false);
  const [status, setStatus] = useState("");

  function handlePreserve() {
    setStrategy("preserve");
    setTarget(candidate.source);
    setEditing(false);
  }

  function handleEdit() {
    setStrategy("translate");
    setEditing(true);
  }

  function handleAdd() {
    if (!target.trim()) return;
    const result = onAdd({
      source: candidate.source,
      target: strategy === "preserve" ? candidate.source : target.trim(),
      strategy,
      kind: candidate.kind,
    });
    setStatus(result === "exists" ? "이미 등록됨" : "추가 완료");
  }

  return (
    <article className="detected-term-card">
      <div className="detected-term-copy">
        <strong>{candidate.source}</strong>
        <span>{candidate.kind}</span>
        {editing && (
          <label>
            <span className="sr-only">지정 번역</span>
            <input value={target} onChange={(event) => setTarget(event.target.value)} autoFocus />
          </label>
        )}
        {!editing && strategy === "translate" && target !== candidate.source && <small>추천 번역: {target}</small>}
      </div>
      <div className="detected-term-actions">
        <button type="button" className={strategy === "preserve" ? "active" : ""} onClick={handlePreserve}><RotateCcw size={16} /> 원문 유지</button>
        <button type="button" className={editing ? "active" : ""} onClick={handleEdit}><Pencil size={16} /> 수정</button>
        <button type="button" className="add-term-button" onClick={handleAdd} disabled={status === "추가 완료" || status === "이미 등록됨"}><Check size={16} /> {status || "용어집 추가"}</button>
      </div>
    </article>
  );
}
