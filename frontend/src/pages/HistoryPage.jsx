import { Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import EmptyState from "../components/common/EmptyState";
import Modal from "../components/common/Modal";
import { useAppData } from "../context/appData";
import "./PageStyles.css";

export default function HistoryPage() {
  const {
    currentUser,
    history,
    deleteHistory,
    refreshHistory,
    historyLoading,
    historyError,
  } = useAppData();
  const [scope, setScope] = useState("personal");
  const [selectedId, setSelectedId] = useState(history[0]?.id ?? "");
  const [deleting, setDeleting] = useState(null);
  const [deleteError, setDeleteError] = useState("");

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  const visibleHistory = scope === "personal"
    ? history.filter((item) => item.executorId === currentUser.id)
    : history;
  const selected = visibleHistory.find((item) => item.id === selectedId) ?? visibleHistory[0];

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>히스토리</h1>
          <p>개인과 팀의 번역 기록을 다시 확인합니다.</p>
        </div>
        <div className="segmented-control">
          <button className={scope === "personal" ? "active" : ""} onClick={() => setScope("personal")}>개인 히스토리</button>
          <button className={scope === "team" ? "active" : ""} onClick={() => setScope("team")}>팀 히스토리</button>
        </div>
      </header>

      {historyError && <div className="document-error"><span>{historyError}</span><button onClick={refreshHistory}>다시 시도</button></div>}
      {historyLoading && !history.length && <section className="surface"><p className="field-hint">번역 기록을 불러오는 중입니다.</p></section>}

      {visibleHistory.length ? (
        <section className="history-layout">
          <div className="history-list">
            {visibleHistory.map((item) => (
              <button key={item.id} className={`history-item${selected?.id === item.id ? " active" : ""}`} onClick={() => setSelectedId(item.id)}>
                <strong>{item.sourceText}</strong>
                <div className="history-meta"><span>{item.executor}</span><span>·</span><span>{item.createdAt}</span></div>
                <div className="history-meta"><span>수신자: {item.recipient}</span></div>
              </button>
            ))}
          </div>

          {selected && (
            <article className="history-detail">
              <header className="history-detail-header">
                <div><h2>{selected.executor}의 번역</h2><p>{selected.createdAt} · 수신자 {selected.recipient}</p></div>
                {selected.executorId === currentUser.id && (
                  <button className="icon-button" onClick={() => setDeleting(selected)} title="기록 삭제" aria-label="기록 삭제"><Trash2 size={17} /></button>
                )}
              </header>
              <div className="translation-detail-block"><h3>원문</h3><p>{selected.sourceText}</p></div>
              <div className="translation-detail-block"><h3>번역 결과</h3><p>{selected.translatedText}</p></div>
              <div className="translation-detail-block">
                <h3>적용 용어</h3>
                {selected.appliedTerms.length ? <div className="term-chips">{selected.appliedTerms.map((term) => <span className="badge" key={term}>{term}</span>)}</div> : <span className="field-hint">적용된 용어가 없습니다.</span>}
              </div>
            </article>
          )}
        </section>
      ) : <section className="surface"><EmptyState title="번역 기록이 없습니다" description="번역을 실행하면 이곳에 기록됩니다." /></section>}

      {deleting && (
        <Modal
          title="히스토리 삭제"
          onClose={() => setDeleting(null)}
          footer={<><button className="button" onClick={() => setDeleting(null)}>취소</button><button className="button danger" onClick={async () => {
            setDeleteError("");
            try {
              await deleteHistory(deleting.id);
              setDeleting(null);
            } catch (error) {
              setDeleteError(error instanceof Error ? error.message : "번역 기록을 삭제하지 못했습니다.");
            }
          }}>삭제</button></>}
        >
          <p>이 번역 기록을 삭제할까요? 삭제한 기록은 복구할 수 없습니다.</p>
          {deleteError && <p className="form-error">{deleteError}</p>}
        </Modal>
      )}
    </div>
  );
}
