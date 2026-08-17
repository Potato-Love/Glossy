import {
  AlertCircle,
  BookPlus,
  Check,
  CheckCircle2,
  FileCheck2,
  Files,
  LoaderCircle,
  Pencil,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { compareTranslations, translateDocument } from "../../api/documents";
import DetectedTermCard from "./DetectedTermCard";
import FileDropzone from "./FileDropzone";
import TranslationSettingsBar from "./TranslationSettingsBar";

const documentAccept = ".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain";
const supportedExtensions = ["pdf", "docx", "txt"];
const processingSteps = ["텍스트 추출", "문단 단위 분할", "용어집·상대 프로필 적용", "LLM 번역"];

function supportedFiles(files) {
  return files.filter((file) => supportedExtensions.includes(file.name.split(".").pop()?.toLowerCase()));
}

function ComparisonTermCard({ item, onAdd }) {
  const [target, setTarget] = useState(item.recommendedTarget);
  const [strategy, setStrategy] = useState(item.recommendedStrategy);
  const [editing, setEditing] = useState(false);
  const [status, setStatus] = useState("");

  function handleAdd() {
    if (!target.trim()) return;
    const result = onAdd({
      source: item.source,
      target: strategy === "preserve" ? item.source : target.trim(),
      strategy,
      kind: `${item.kind} · 번역본 비교에서 발견`,
    });
    setStatus(result === "exists" ? "이미 등록됨" : "추가 완료");
  }

  return (
    <article className="comparison-term-card">
      <header>
        <div><strong>{item.source}</strong><span>{item.kind}</span></div>
        <span className="badge neutral">번역 {item.variants.length}종</span>
      </header>
      <div className="translation-variants">
        {item.variants.map((variant) => (
          <label key={`${variant.documentName}-${variant.target}`}>
            <input
              type="radio"
              name={`variant-${item.id}`}
              checked={strategy === "translate" && target === variant.target}
              onChange={() => { setStrategy("translate"); setTarget(variant.target); setEditing(false); }}
            />
            <span><strong>{variant.target}</strong><small>{variant.documentName} · {variant.count}회</small></span>
          </label>
        ))}
      </div>
      <div className="comparison-decision">
        <button type="button" className={strategy === "preserve" ? "active" : ""} onClick={() => { setStrategy("preserve"); setTarget(item.source); setEditing(false); }}>원문 유지</button>
        <button type="button" className={editing ? "active" : ""} onClick={() => { setStrategy("translate"); setEditing(true); }}><Pencil size={15} /> 직접 수정</button>
        {editing && <input value={target} onChange={(event) => setTarget(event.target.value)} aria-label={`${item.source} 지정 번역`} autoFocus />}
        <button type="button" className="add-term-button" onClick={handleAdd} disabled={Boolean(status)}><BookPlus size={16} /> {status || "팀 용어집에 추가"}</button>
      </div>
    </article>
  );
}

export default function DocumentWorkspace({ options, settingsProps, onAddTerm }) {
  const [workflow, setWorkflow] = useState("translate");
  const [sourceFile, setSourceFile] = useState(null);
  const [translationFiles, setTranslationFiles] = useState([]);
  const [status, setStatus] = useState("idle");
  const [processingStep, setProcessingStep] = useState(0);
  const [translationResult, setTranslationResult] = useState(null);
  const [comparisonResult, setComparisonResult] = useState(null);
  const [error, setError] = useState("");

  const processing = status === "processing";

  function updateSingleFile(files) {
    if (!files.length) {
      setSourceFile(null);
      return;
    }
    const valid = supportedFiles(files);
    if (!valid.length) {
      setError("PDF, DOCX, TXT 파일만 업로드할 수 있습니다.");
      return;
    }
    setSourceFile(valid[0]);
    setError("");
  }

  function updateTranslationFiles(files) {
    const valid = supportedFiles(files);
    if (files.length && valid.length !== files.length) {
      setError("지원하지 않는 파일은 제외했습니다. PDF, DOCX, TXT만 사용할 수 있습니다.");
    } else {
      setError("");
    }
    setTranslationFiles(valid);
  }

  function appendTranslationFiles(files) {
    const valid = supportedFiles(files);
    if (valid.length !== files.length) {
      setError("지원하지 않는 파일은 제외했습니다. PDF, DOCX, TXT만 사용할 수 있습니다.");
    } else {
      setError("");
    }
    const merged = [...translationFiles, ...valid].filter(
      (file, index, all) => all.findIndex((item) => item.name === file.name && item.size === file.size) === index,
    );
    setTranslationFiles(merged);
  }

  async function runWithProgress(task) {
    setStatus("processing");
    setProcessingStep(0);
    setError("");
    const timer = window.setInterval(() => {
      setProcessingStep((current) => Math.min(current + 1, processingSteps.length - 1));
    }, 430);

    try {
      const result = await task();
      setStatus("done");
      return result;
    } catch (taskError) {
      setStatus("error");
      setError(taskError instanceof Error ? taskError.message : "문서 처리 중 오류가 발생했습니다.");
      return null;
    } finally {
      window.clearInterval(timer);
    }
  }

  async function handleTranslateDocument() {
    if (!sourceFile) {
      setError("번역할 원문 문서를 선택해 주세요.");
      return;
    }
    const result = await runWithProgress(() => translateDocument({ file: sourceFile, ...options }));
    if (result) setTranslationResult(result);
  }

  async function handleCompareDocuments() {
    if (!sourceFile) {
      setError("비교 기준이 될 원문 문서를 선택해 주세요.");
      return;
    }
    if (translationFiles.length < 2) {
      setError("번역본을 2개 이상 선택해 주세요.");
      return;
    }
    const result = await runWithProgress(() => compareTranslations({ sourceFile, translationFiles, ...options }));
    if (result) setComparisonResult(result);
  }

  function changeWorkflow(nextWorkflow) {
    if (processing) return;
    setWorkflow(nextWorkflow);
    setSourceFile(null);
    setTranslationFiles([]);
    setError("");
    setStatus("idle");
  }

  return (
    <section className="file-workspace">
      <div className="document-workflow-header">
        <div className="segmented-control">
          <button className={workflow === "translate" ? "active" : ""} onClick={() => changeWorkflow("translate")} disabled={processing}>원문 번역</button>
          <button className={workflow === "compare" ? "active" : ""} onClick={() => changeWorkflow("compare")} disabled={processing}>번역본 비교</button>
        </div>
        <p>{workflow === "translate" ? "문서의 문단과 용어 맥락을 유지해 번역합니다." : "서로 다른 번역 표현을 찾아 팀 용어로 정리합니다."}</p>
      </div>

      <TranslationSettingsBar {...settingsProps} />

      {workflow === "translate" ? (
        <div className="document-upload-section">
          <FileDropzone
            title="번역할 원문 문서를 올려주세요"
            description="PDF, DOCX, TXT · 파일 1개"
            accept={documentAccept}
            files={sourceFile ? [sourceFile] : []}
            onFiles={updateSingleFile}
            disabled={processing}
          />
          <button className="button primary document-run-button" onClick={handleTranslateDocument} disabled={!sourceFile || processing}>
            {processing ? <><LoaderCircle size={18} className="spin" /> 문서 번역 중</> : <><FileCheck2 size={18} /> 문서 번역하기</>}
          </button>
        </div>
      ) : (
        <div className="comparison-upload-grid">
          <div>
            <span className="upload-step-label">1. 원문 문서</span>
            <FileDropzone
              title="원문 문서"
              description="비교 기준 파일 1개"
              accept={documentAccept}
              files={sourceFile ? [sourceFile] : []}
              onFiles={updateSingleFile}
              disabled={processing}
            />
          </div>
          <div>
            <span className="upload-step-label">2. 번역본 문서</span>
            <FileDropzone
              title="번역본 문서"
              description="비교할 파일 2개 이상"
              accept={documentAccept}
              files={translationFiles}
              multiple
              onFiles={appendTranslationFiles}
              onRemove={(index) => updateTranslationFiles(translationFiles.filter((_, fileIndex) => fileIndex !== index))}
              disabled={processing}
            />
          </div>
          <button className="button primary document-run-button full-width" onClick={handleCompareDocuments} disabled={!sourceFile || translationFiles.length < 2 || processing}>
            {processing ? <><LoaderCircle size={18} className="spin" /> 번역본 분석 중</> : <><Files size={18} /> 번역본 비교하기</>}
          </button>
        </div>
      )}

      {error && <div className="document-error"><AlertCircle size={18} /> <span>{error}</span><button onClick={() => setError("")}>닫기</button></div>}

      {processing && (
        <div className="document-processing" aria-live="polite">
          <LoaderCircle size={27} className="spin" />
          <div><strong>{workflow === "translate" ? "문서를 번역하고 있습니다" : "번역 표현을 비교하고 있습니다"}</strong><span>문서 길이에 따라 시간이 걸릴 수 있습니다.</span></div>
          <ol>{processingSteps.map((step, index) => <li key={step} className={index < processingStep ? "complete" : index === processingStep ? "active" : ""}>{index < processingStep ? <Check size={15} /> : index + 1}<span>{step}</span></li>)}</ol>
        </div>
      )}

      {workflow === "translate" && translationResult && !processing && (
        <div className="document-result">
          <header className="document-result-heading">
            <div className="result-success-icon"><CheckCircle2 size={28} /></div>
            <div><span>문서 번역 완료</span><h2>{translationResult.document.name}</h2><p>{translationResult.document.pageCount}페이지 · {translationResult.document.wordCount.toLocaleString()}단어</p></div>
          </header>
          <div className="document-result-stats">
            <div><Check size={20} /><span><strong>팀 용어 {translationResult.appliedTermCount}개</strong> 적용</span></div>
            <div><Sparkles size={20} /><span><strong>새로운 용어 후보 {translationResult.suggestions.length}개</strong> 발견</span></div>
          </div>
          <section className="translated-document">
            <div className="document-section-heading"><h3>번역 결과</h3><span>문단별 원문과 번역문</span></div>
            {translationResult.translatedParagraphs.map((paragraph) => (
              <article key={paragraph.id}><p>{paragraph.source}</p><p>{paragraph.target}</p></article>
            ))}
          </section>
          <section className="detected-terms-section">
            <div className="document-section-heading"><h3>용어집 후보</h3><span>확인 후 팀 용어집에 추가할 수 있습니다.</span></div>
            <div className="detected-term-list">{translationResult.suggestions.map((candidate) => <DetectedTermCard key={candidate.id} candidate={candidate} onAdd={onAddTerm} />)}</div>
          </section>
        </div>
      )}

      {workflow === "compare" && comparisonResult && !processing && (
        <div className="document-result comparison-result">
          <header className="document-result-heading">
            <div className="result-success-icon"><CheckCircle2 size={28} /></div>
            <div><span>번역본 비교 완료</span><h2>서로 다르게 번역된 용어 {comparisonResult.inconsistencies.length}개</h2><p>원문 1개 · 번역본 {comparisonResult.translationDocuments.length}개 비교</p></div>
          </header>
          <section className="detected-terms-section">
            <div className="document-section-heading"><h3>번역 불일치</h3><span>팀에서 사용할 최종 표현을 선택하세요.</span></div>
            <div className="comparison-term-list">{comparisonResult.inconsistencies.map((item) => <ComparisonTermCard key={item.id} item={item} onAdd={onAddTerm} />)}</div>
          </section>
        </div>
      )}
    </section>
  );
}
