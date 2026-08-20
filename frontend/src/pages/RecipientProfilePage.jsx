import { Pencil, Plus, Search, Sparkles, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { extractRecipient } from "../api/recipients";
import EmptyState from "../components/common/EmptyState";
import Modal from "../components/common/Modal";
import { useAppData } from "../context/appData";
import {
  countries,
  getRecipientToneLabel,
  normalizeRecipientTone,
  recipientToneOptions,
} from "../data/referenceData";
import "./PageStyles.css";

const emptyRecipient = {
  name: "",
  company: "",
  position: "",
  country: "",
  tone: "polite_concise",
  traits: "",
};

const extractionFieldLabels = {
  name: "이름",
  company: "소속",
  role: "직책",
  country: "국가",
  tone_style: "어조",
  communication_preferences: "커뮤니케이션 특성",
};

export default function RecipientProfilePage() {
  const {
    recipients,
    addRecipient,
    updateRecipient,
    deleteRecipient,
    refreshRecipients,
    recipientsLoading,
    recipientsError,
  } = useAppData();
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [form, setForm] = useState(emptyRecipient);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [extractingOpen, setExtractingOpen] = useState(false);
  const [extractionText, setExtractionText] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [extractionError, setExtractionError] = useState("");
  const [extractionEvidence, setExtractionEvidence] = useState({});
  const [extractionNotice, setExtractionNotice] = useState("");

  const filteredRecipients = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return recipients;
    return recipients.filter((recipient) =>
      `${recipient.name} ${recipient.company} ${recipient.position} ${recipient.country}`.toLowerCase().includes(query),
    );
  }, [recipients, search]);

  function openCreate() {
    setEditing("new");
    setForm(emptyRecipient);
    setError("");
    setExtractionEvidence({});
    setExtractionNotice("");
  }

  function openEdit(recipient) {
    setEditing(recipient.id);
    setForm({
      name: recipient.name,
      company: recipient.company,
      position: recipient.position,
      country: recipient.country,
      tone: normalizeRecipientTone(recipient.tone),
      traits: recipient.traits,
    });
    setError("");
    setExtractionEvidence({});
    setExtractionNotice("");
  }

  async function handleExtractRecipient() {
    if (extractionText.trim().length < 10) {
      setExtractionError("상대 정보가 포함된 대화나 이메일을 10자 이상 입력해 주세요.");
      return;
    }
    setExtracting(true);
    setExtractionError("");
    try {
      const result = await extractRecipient(extractionText);
      const candidate = result.candidate;
      const existing = candidate.name
        ? recipients.find((item) => item.name.trim().toLowerCase() === candidate.name.trim().toLowerCase())
        : null;
      setEditing(existing?.id || "new");
      setForm({
        name: candidate.name || existing?.name || "",
        company: candidate.company || existing?.company || "",
        position: candidate.role || existing?.position || "",
        country: candidate.country || existing?.country || "",
        tone: normalizeRecipientTone(candidate.tone_style || existing?.tone),
        traits: candidate.communication_preferences || existing?.traits || "",
      });
      setExtractionEvidence(result.evidence || {});
      setExtractionNotice(existing
        ? "같은 이름의 프로필이 있어 기존 정보를 수정합니다. AI가 채운 내용을 확인해 주세요."
        : "AI가 찾은 후보입니다. 내용을 확인하고 필요한 부분을 수정한 뒤 저장해 주세요.");
      setExtractingOpen(false);
      setExtractionText("");
    } catch (extractError) {
      setExtractionError(extractError instanceof Error ? extractError.message : "상대 정보를 추출하지 못했습니다.");
    } finally {
      setExtracting(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!form.name.trim()) {
      setError("이름을 입력해 주세요.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      if (editing === "new") await addRecipient(form);
      else await updateRecipient(editing, form);
      setEditing(null);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "수신자 프로필을 저장하지 못했습니다.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteRecipient() {
    if (!deleting) return;
    setError("");
    try {
      await deleteRecipient(deleting.id);
      setDeleting(null);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "수신자 프로필을 삭제하지 못했습니다.");
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>상대 프로필</h1>
          <p>번역 수신자의 배경과 선호 어조를 관리합니다.</p>
        </div>
        <div className="page-header-actions">
          <button className="button" onClick={() => { setExtractingOpen(true); setExtractionError(""); }}><Sparkles size={18} /> 대화에서 자동 추출</button>
          <button className="button primary" onClick={openCreate}><Plus size={18} /> 프로필 등록</button>
        </div>
      </header>

      <div className="toolbar">
        <label className="filter-search">
          <Search size={18} />
          <input className="search-field" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="이름, 소속, 직책 검색" />
        </label>
        <span className="field-hint">총 {filteredRecipients.length}명</span>
      </div>

      {recipientsError && <div className="document-error"><span>{recipientsError}</span><button onClick={refreshRecipients}>다시 시도</button></div>}
      {recipientsLoading && <p className="field-hint">수신자 프로필을 불러오는 중입니다.</p>}

      {filteredRecipients.length ? (
        <div className="content-grid">
          {filteredRecipients.map((recipient) => (
            <article className="profile-card" key={recipient.id}>
              <header className="profile-card-header">
                <div className="avatar">{recipient.name.slice(0, 1).toUpperCase()}</div>
                <div className="profile-identity">
                  <h2>{recipient.name}</h2>
                  <p>{[recipient.company, recipient.position].filter(Boolean).join(" · ") || "소속·직책 미입력"}</p>
                </div>
                <div className="card-actions">
                  <button className="icon-button" onClick={() => openEdit(recipient)} title="수정" aria-label={`${recipient.name} 수정`}><Pencil size={16} /></button>
                  <button className="icon-button" onClick={() => { setError(""); setDeleting(recipient); }} title="삭제" aria-label={`${recipient.name} 삭제`}><Trash2 size={16} /></button>
                </div>
              </header>
              <dl className="detail-list">
                <div className="detail-row"><dt>국적</dt><dd>{recipient.country || "미입력"}</dd></div>
                <div className="detail-row"><dt>어조</dt><dd>{getRecipientToneLabel(recipient.tone)}</dd></div>
                <div className="detail-row"><dt>추가 특성</dt><dd>{recipient.traits || "등록된 특성이 없습니다."}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      ) : <section className="surface"><EmptyState title="상대 프로필이 없습니다" description="번역할 상대의 정보를 등록해 보세요." /></section>}

      {extractingOpen && (
        <Modal
          title="대화에서 상대 정보 추출"
          onClose={() => { if (!extracting) setExtractingOpen(false); }}
          footer={<><button className="button" onClick={() => setExtractingOpen(false)} disabled={extracting}>취소</button><button className="button primary" onClick={handleExtractRecipient} disabled={extracting}>{extracting ? "분석 중" : "정보 추출"}</button></>}
        >
          <div className="field">
            <label htmlFor="recipientConversation">대화 또는 이메일</label>
            <textarea
              id="recipientConversation"
              className="textarea-field extraction-textarea"
              value={extractionText}
              onChange={(event) => setExtractionText(event.target.value)}
              placeholder="서명과 상대의 말투가 포함된 이메일이나 대화를 붙여넣어 주세요."
              disabled={extracting}
            />
            <span className="field-hint">입력한 원문은 프로필에 저장되지 않으며, 추출 결과는 저장 전에 수정할 수 있습니다.</span>
          </div>
          {extractionError && <p className="form-error">{extractionError}</p>}
        </Modal>
      )}

      {editing && (
        <Modal
          title={editing === "new" ? "상대 프로필 등록" : "상대 프로필 수정"}
          onClose={() => setEditing(null)}
          footer={<><button className="button" onClick={() => setEditing(null)} disabled={saving}>취소</button><button className="button primary" onClick={handleSubmit} disabled={saving}>{saving ? "저장 중" : "저장"}</button></>}
        >
          <form onSubmit={handleSubmit} className="form-grid">
            {extractionNotice && <div className="extraction-review full"><strong>{extractionNotice}</strong>{Object.keys(extractionEvidence).length > 0 && <ul>{Object.entries(extractionEvidence).map(([field, evidence]) => <li key={field}><b>{extractionFieldLabels[field] || field}</b>: {evidence}</li>)}</ul>}</div>}
            <div className="field"><label htmlFor="recipientName">이름</label><input id="recipientName" className="text-field" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} /></div>
            <div className="field"><label htmlFor="recipientPosition">직책</label><input id="recipientPosition" className="text-field" value={form.position} onChange={(event) => setForm((current) => ({ ...current, position: event.target.value }))} /></div>
            <div className="field"><label htmlFor="recipientCompany">소속</label><input id="recipientCompany" className="text-field" value={form.company} onChange={(event) => setForm((current) => ({ ...current, company: event.target.value }))} /></div>
            <div className="field"><label htmlFor="recipientCountry">국적</label><select id="recipientCountry" className="select-field" value={form.country} onChange={(event) => setForm((current) => ({ ...current, country: event.target.value }))}><option value="">선택 안 함</option>{countries.map((country) => <option key={country}>{country}</option>)}</select></div>
            <div className="field full"><label htmlFor="recipientTone">어조 설정</label><select id="recipientTone" className="select-field" value={form.tone} onChange={(event) => setForm((current) => ({ ...current, tone: event.target.value }))}>{recipientToneOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></div>
            <div className="field full"><label htmlFor="recipientTraits">이외 특성</label><textarea id="recipientTraits" className="textarea-field" value={form.traits} onChange={(event) => setForm((current) => ({ ...current, traits: event.target.value }))} placeholder="호칭, 관심사, 커뮤니케이션 선호 등을 입력하세요." /></div>
            {error && <p className="form-error full">{error}</p>}
          </form>
        </Modal>
      )}

      {deleting && (
        <Modal
          title="상대 프로필 삭제"
          onClose={() => setDeleting(null)}
          footer={<><button className="button" onClick={() => setDeleting(null)}>취소</button><button className="button danger" onClick={handleDeleteRecipient}>삭제</button></>}
        >
          <p><strong>{deleting.name}</strong>님의 프로필을 삭제할까요? 기존 히스토리의 수신자 이름은 유지됩니다.</p>
          {error && <p className="form-error">{error}</p>}
        </Modal>
      )}
    </div>
  );
}
