import { Check, Pencil, Sparkles, X } from "lucide-react";

export default function TermSuggestionCard({ suggestion, onChange, onApprove, onReject }) {
  return (
    <section className="term-suggestion" aria-label="AI 감지 용어">
      <div className="suggestion-label"><Sparkles size={17} /> AI 감지 단어</div>
      <div className="suggestion-content">
        <div className="suggestion-mapping">
          <div>
            <strong>{suggestion.source}</strong>
            <span className="suggestion-tag">고유명사(팀명)</span>
          </div>
          <span className="mapping-arrow">→</span>
          <div>
            <label className="editable-target">
              <Pencil size={16} aria-hidden="true" />
              <input
                value={suggestion.target}
                onChange={(event) => onChange(event.target.value)}
                aria-label="추천 번역 수정"
              />
            </label>
            <span className="suggestion-tag">발음대로 번역</span>
          </div>
        </div>
        <div className="suggestion-actions">
          <button className="suggestion-button approve" onClick={onApprove} title="용어집에 추가">
            <Check size={24} /> <span>승인</span>
          </button>
          <button className="suggestion-button reject" onClick={onReject} title="추천 거절">
            <X size={24} /> <span>거절</span>
          </button>
        </div>
      </div>
    </section>
  );
}
