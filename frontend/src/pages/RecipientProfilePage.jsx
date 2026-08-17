import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import EmptyState from "../components/common/EmptyState";
import Modal from "../components/common/Modal";
import { useAppData } from "../context/appData";
import { countries } from "../data/mockData";
import "./PageStyles.css";

const emptyRecipient = {
  name: "",
  company: "",
  position: "",
  country: "대한민국",
  tone: "정중하고 간결하게",
  traits: "",
};

export default function RecipientProfilePage() {
  const { recipients, addRecipient, updateRecipient, deleteRecipient } = useAppData();
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [form, setForm] = useState(emptyRecipient);
  const [error, setError] = useState("");

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
  }

  function openEdit(recipient) {
    setEditing(recipient.id);
    setForm({
      name: recipient.name,
      company: recipient.company,
      position: recipient.position,
      country: recipient.country,
      tone: recipient.tone,
      traits: recipient.traits,
    });
    setError("");
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (!form.name.trim() || !form.company.trim() || !form.position.trim()) {
      setError("이름, 소속, 직책을 입력해 주세요.");
      return;
    }
    if (editing === "new") addRecipient(form);
    else updateRecipient(editing, form);
    setEditing(null);
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>상대 프로필</h1>
          <p>번역 수신자의 배경과 선호 어조를 관리합니다.</p>
        </div>
        <button className="button primary" onClick={openCreate}><Plus size={18} /> 프로필 등록</button>
      </header>

      <div className="toolbar">
        <label className="filter-search">
          <Search size={18} />
          <input className="search-field" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="이름, 소속, 직책 검색" />
        </label>
        <span className="field-hint">총 {filteredRecipients.length}명</span>
      </div>

      {filteredRecipients.length ? (
        <div className="content-grid">
          {filteredRecipients.map((recipient) => (
            <article className="profile-card" key={recipient.id}>
              <header className="profile-card-header">
                <div className="avatar">{recipient.name.slice(0, 1).toUpperCase()}</div>
                <div className="profile-identity">
                  <h2>{recipient.name}</h2>
                  <p>{recipient.company} · {recipient.position}</p>
                </div>
                <div className="card-actions">
                  <button className="icon-button" onClick={() => openEdit(recipient)} title="수정" aria-label={`${recipient.name} 수정`}><Pencil size={16} /></button>
                  <button className="icon-button" onClick={() => setDeleting(recipient)} title="삭제" aria-label={`${recipient.name} 삭제`}><Trash2 size={16} /></button>
                </div>
              </header>
              <dl className="detail-list">
                <div className="detail-row"><dt>국적</dt><dd>{recipient.country}</dd></div>
                <div className="detail-row"><dt>어조</dt><dd>{recipient.tone}</dd></div>
                <div className="detail-row"><dt>추가 특성</dt><dd>{recipient.traits || "등록된 특성이 없습니다."}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      ) : <section className="surface"><EmptyState title="상대 프로필이 없습니다" description="번역할 상대의 정보를 등록해 보세요." /></section>}

      {editing && (
        <Modal
          title={editing === "new" ? "상대 프로필 등록" : "상대 프로필 수정"}
          onClose={() => setEditing(null)}
          footer={<><button className="button" onClick={() => setEditing(null)}>취소</button><button className="button primary" onClick={handleSubmit}>저장</button></>}
        >
          <form onSubmit={handleSubmit} className="form-grid">
            <div className="field"><label htmlFor="recipientName">이름</label><input id="recipientName" className="text-field" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} /></div>
            <div className="field"><label htmlFor="recipientPosition">직책</label><input id="recipientPosition" className="text-field" value={form.position} onChange={(event) => setForm((current) => ({ ...current, position: event.target.value }))} /></div>
            <div className="field"><label htmlFor="recipientCompany">소속</label><input id="recipientCompany" className="text-field" value={form.company} onChange={(event) => setForm((current) => ({ ...current, company: event.target.value }))} /></div>
            <div className="field"><label htmlFor="recipientCountry">국적</label><select id="recipientCountry" className="select-field" value={form.country} onChange={(event) => setForm((current) => ({ ...current, country: event.target.value }))}>{countries.map((country) => <option key={country}>{country}</option>)}</select></div>
            <div className="field full"><label htmlFor="recipientTone">어조 설정</label><select id="recipientTone" className="select-field" value={form.tone} onChange={(event) => setForm((current) => ({ ...current, tone: event.target.value }))}><option>정중하고 간결하게</option><option>친근하고 전문적으로</option><option>격식 있고 공식적으로</option><option>부드럽고 설득력 있게</option></select></div>
            <div className="field full"><label htmlFor="recipientTraits">이외 특성</label><textarea id="recipientTraits" className="textarea-field" value={form.traits} onChange={(event) => setForm((current) => ({ ...current, traits: event.target.value }))} placeholder="호칭, 관심사, 커뮤니케이션 선호 등을 입력하세요." /></div>
            {error && <p className="form-error full">{error}</p>}
          </form>
        </Modal>
      )}

      {deleting && (
        <Modal
          title="상대 프로필 삭제"
          onClose={() => setDeleting(null)}
          footer={<><button className="button" onClick={() => setDeleting(null)}>취소</button><button className="button danger" onClick={() => { deleteRecipient(deleting.id); setDeleting(null); }}>삭제</button></>}
        >
          <p><strong>{deleting.name}</strong>님의 프로필을 삭제할까요? 기존 히스토리의 수신자 이름은 유지됩니다.</p>
        </Modal>
      )}
    </div>
  );
}
