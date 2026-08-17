import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import EmptyState from "../components/common/EmptyState";
import Modal from "../components/common/Modal";
import { useAppData } from "../context/appData";
import "./PageStyles.css";

const emptyForm = {
  source: "",
  target: "",
  strategy: "translate",
  memo: "",
};

export default function GlossaryPage() {
  const { currentUser, terms, addTerm, updateTerm, deleteTerm } = useAppData();
  const [scope, setScope] = useState("team");
  const [search, setSearch] = useState("");
  const [strategy, setStrategy] = useState("all");
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");

  const filteredTerms = useMemo(() => terms.filter((term) => {
    const matchesScope = term.scope === scope;
    const query = search.trim().toLowerCase();
    const matchesSearch = !query || `${term.source} ${term.target} ${term.memo}`.toLowerCase().includes(query);
    const matchesStrategy = strategy === "all" || term.strategy === strategy;
    return matchesScope && matchesSearch && matchesStrategy;
  }), [terms, scope, search, strategy]);

  function openCreate() {
    setEditing("new");
    setForm(emptyForm);
    setError("");
  }

  function openEdit(term) {
    setEditing(term.id);
    setForm({ source: term.source, target: term.target, strategy: term.strategy, memo: term.memo });
    setError("");
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (!form.source.trim() || (form.strategy === "translate" && !form.target.trim())) {
      setError("원문과 지정 번역을 입력해 주세요.");
      return;
    }
    const duplicate = terms.some((term) =>
      term.scope === scope && term.source.trim().toLowerCase() === form.source.trim().toLowerCase() && term.id !== editing,
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
    if (editing === "new") {
      addTerm({
        ...values,
        scope,
        creator: currentUser.nickname,
        createdAt: new Intl.DateTimeFormat("ko-KR").format(new Date()),
      });
    } else {
      updateTerm(editing, values);
    }
    setEditing(null);
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>용어집</h1>
          <p>팀과 개인 번역에 사용할 표현을 관리합니다.</p>
        </div>
        <button className="button primary" onClick={openCreate}><Plus size={18} /> 용어 등록</button>
      </header>

      <div className="toolbar">
        <div className="segmented-control">
          <button className={scope === "team" ? "active" : ""} onClick={() => setScope("team")}>팀 공유</button>
          <button className={scope === "personal" ? "active" : ""} onClick={() => setScope("personal")}>개인</button>
        </div>
        <div className="toolbar-group">
          <label className="filter-search">
            <Search size={18} />
            <input className="search-field" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="용어 검색" />
          </label>
          <select className="select-field" value={strategy} onChange={(event) => setStrategy(event.target.value)} aria-label="처리 방식 필터">
            <option value="all">전체 방식</option>
            <option value="translate">지정 번역</option>
            <option value="preserve">원문 보존</option>
          </select>
        </div>
      </div>

      <section className="surface data-table-wrap">
        {filteredTerms.length ? (
          <table className="data-table">
            <thead><tr><th>원문</th><th>지정 번역</th><th>처리 방식</th><th>메모</th><th>등록자</th><th>등록일</th><th aria-label="관리" /></tr></thead>
            <tbody>
              {filteredTerms.map((term) => (
                <tr key={term.id}>
                  <td><strong>{term.source}</strong></td>
                  <td>{term.target}</td>
                  <td><span className={`badge${term.strategy === "preserve" ? " neutral" : ""}`}>{term.strategy === "preserve" ? "원문 보존" : "지정 번역"}</span></td>
                  <td>{term.memo || "-"}</td>
                  <td>{term.creator}</td>
                  <td>{term.createdAt}</td>
                  <td><div className="table-actions">
                    <button className="icon-button" onClick={() => openEdit(term)} title="수정" aria-label={`${term.source} 수정`}><Pencil size={16} /></button>
                    <button className="icon-button" onClick={() => setDeleting(term)} title="삭제" aria-label={`${term.source} 삭제`}><Trash2 size={16} /></button>
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <EmptyState title="조건에 맞는 용어가 없습니다" description="검색 조건을 바꾸거나 새 용어를 등록해 보세요." />}
      </section>

      {editing && (
        <Modal
          title={editing === "new" ? "용어 등록" : "용어 수정"}
          onClose={() => setEditing(null)}
          footer={<><button className="button" onClick={() => setEditing(null)}>취소</button><button className="button primary" onClick={handleSubmit}>저장</button></>}
        >
          <form onSubmit={handleSubmit} className="form-grid">
            <div className="field full"><label htmlFor="termSource">원문</label><input id="termSource" className="text-field" value={form.source} onChange={(event) => setForm((current) => ({ ...current, source: event.target.value }))} /></div>
            <div className="field full">
              <span className="field-label">처리 방식</span>
              <div className="segmented-control">
                <button type="button" className={form.strategy === "translate" ? "active" : ""} onClick={() => setForm((current) => ({ ...current, strategy: "translate" }))}>지정 번역</button>
                <button type="button" className={form.strategy === "preserve" ? "active" : ""} onClick={() => setForm((current) => ({ ...current, strategy: "preserve", target: "" }))}>원문 보존</button>
              </div>
            </div>
            <div className="field full"><label htmlFor="termTarget">지정 번역</label><input id="termTarget" className="text-field" value={form.target} disabled={form.strategy === "preserve"} placeholder={form.strategy === "preserve" ? "원문이 그대로 사용됩니다" : "번역 표현"} onChange={(event) => setForm((current) => ({ ...current, target: event.target.value }))} /></div>
            <div className="field full"><label htmlFor="termMemo">메모</label><textarea id="termMemo" className="textarea-field" value={form.memo} onChange={(event) => setForm((current) => ({ ...current, memo: event.target.value }))} /></div>
            {error && <p className="form-error full">{error}</p>}
          </form>
        </Modal>
      )}

      {deleting && (
        <Modal
          title="용어 삭제"
          onClose={() => setDeleting(null)}
          footer={<><button className="button" onClick={() => setDeleting(null)}>취소</button><button className="button danger" onClick={() => { deleteTerm(deleting.id); setDeleting(null); }}>삭제</button></>}
        >
          <p><strong>{deleting.source}</strong> 용어를 삭제할까요? 이후 번역부터 적용되지 않습니다.</p>
        </Modal>
      )}
    </div>
  );
}
