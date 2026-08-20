import { AlertCircle, CheckCircle2, ImageIcon, LoaderCircle, ScanText, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { translateImage } from "../../api/documents";
import { createHistory, updateHistory } from "../../api/history";
import { rejectSuggestion } from "../../api/suggestions";
import DetectedTermCard from "./DetectedTermCard";
import FileDropzone from "./FileDropzone";
import TranslationSettingsBar from "./TranslationSettingsBar";
import { HighlightedText } from "./HighlightedText";
import { replaceSuggestionHighlights } from "./highlightUtils";

const imageAccept = ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp";
const supportedImageExtensions = ["jpg", "jpeg", "png", "webp"];

export default function ImageTranslationPanel({ options, settingsProps, onAddTerm, onPreview, onHistorySaved }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const lastHistoryTextRef = useRef("");
  const historyTimerRef = useRef(null);

  const processing = status === "processing";

  useEffect(() => {
    if (!result?.historyId || result.translatedText === lastHistoryTextRef.current) return undefined;
    window.clearTimeout(historyTimerRef.current);
    historyTimerRef.current = window.setTimeout(async () => {
      try {
        await updateHistory(result.historyId, { translatedText: result.translatedText });
        lastHistoryTextRef.current = result.translatedText;
        onHistorySaved?.();
      } catch (historyError) {
        setError(historyError instanceof Error ? historyError.message : "사진 히스토리를 수정하지 못했습니다.");
      }
    }, 600);
    return () => window.clearTimeout(historyTimerRef.current);
  }, [onHistorySaved, result]);

  useEffect(() => {
    setResult(null);
    setStatus("idle");
  }, [
    options.sourceLanguage,
    options.targetLanguage,
    options.recipientId,
    options.teamGlossaryEnabled,
    options.personalGlossaryEnabled,
  ]);

  function updateFile(files) {
    if (!files.length) {
      setFile(null);
      setPreview("");
      setResult(null);
      return;
    }

    const selected = files[0];
    const extension = selected.name.split(".").pop()?.toLowerCase();
    if (!supportedImageExtensions.includes(extension)) {
      setError("JPG, PNG, WEBP 이미지만 업로드할 수 있습니다.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => setPreview(String(reader.result));
    reader.readAsDataURL(selected);
    setFile(selected);
    setResult(null);
    setError("");
  }

  async function handleTranslateImage() {
    if (!file) {
      setError("번역할 이미지를 선택해 주세요.");
      return;
    }
    setStatus("processing");
    setError("");
    try {
      const response = await translateImage({ file, ...options });
      lastHistoryTextRef.current = response.translatedText;
      setResult(response);
      setStatus("done");
      onHistorySaved?.();
    } catch (taskError) {
      setStatus("error");
      setError(taskError instanceof Error ? taskError.message : "이미지 처리 중 오류가 발생했습니다.");
    }
  }

  async function retryHistorySave() {
    if (!result) return;
    try {
      const appliedTerms = (result.appliedTerms || []).map(
        (term) => `${term.source} → ${term.target || term.source}`,
      );
      const saved = await createHistory({
        mode: "image",
        source_language: options.sourceLanguage,
        target_language: options.targetLanguage,
        source_text: result.extractedText,
        translated_text: result.translatedText,
        recipient_id: /^[0-9a-f-]{36}$/i.test(options.recipientId) ? options.recipientId : null,
        recipient_name: options.recipient?.name || null,
        file_name: result.imageName,
        applied_terms: appliedTerms,
      });
      lastHistoryTextRef.current = result.translatedText;
      setResult((current) => ({ ...current, historyId: saved.id, historyWarning: null }));
      onHistorySaved?.();
    } catch (historyError) {
      setError(historyError instanceof Error ? historyError.message : "사진 히스토리를 저장하지 못했습니다.");
    }
  }

  function resolveSuggestion(id) {
    setResult((current) => current
      ? {
          ...current,
          suggestions: current.suggestions.filter((candidate) => candidate.id !== id),
          highlights: {
            source: (current.highlights?.source || []).map((item) => item.suggestion_id === id
              ? { ...item, state: "applied", suggestion_id: null }
              : item),
            translation: (current.highlights?.translation || []).map((item) => item.suggestion_id === id
              ? { ...item, state: "applied", suggestion_id: null }
              : item),
          },
        }
      : current);
  }

  function handleSuggestionTargetChange(id, target, translationStrategy, creationMethod) {
    const strategy = translationStrategy === "preserve" ? "preserve" : "translate";
    setResult((current) => {
      if (!current) return current;
      const replaced = replaceSuggestionHighlights(
        current.translatedText,
        current.highlights?.translation || [],
        id,
        target,
      );
      return {
        ...current,
        translatedText: replaced.value,
        suggestions: current.suggestions.map((candidate) => candidate.id === id
          ? {
              ...candidate,
              target,
              recommendedStrategy: strategy,
              translationStrategy,
              creationMethod: creationMethod || "direct_edit",
            }
          : candidate),
        highlights: {
          source: (current.highlights?.source || []).map((item) => item.suggestion_id === id
            ? { ...item, target }
            : item),
          translation: replaced.highlights,
        },
      };
    });
  }

  async function handleRejectSuggestion(id) {
    if (/^[0-9a-f-]{36}$/i.test(id)) await rejectSuggestion(id);
    await handleTranslateImage();
  }

  return (
    <section className="file-workspace image-workspace">
      <div className="document-workflow-header">
        <div><h2>사진 번역</h2><p>이미지 속 문장을 추출해 용어집과 상대 프로필을 반영합니다.</p></div>
      </div>
      <TranslationSettingsBar {...settingsProps} />

      <div className={`image-upload-layout${preview ? " has-preview" : ""}`}>
        <FileDropzone
          title="번역할 사진을 올려주세요"
          description="JPG, PNG, WEBP · 파일 1개"
          accept={imageAccept}
          files={file ? [file] : []}
          onFiles={updateFile}
          disabled={processing}
        />
        {preview && <div className="uploaded-image-preview"><img src={preview} alt="업로드한 번역 이미지" /></div>}
      </div>

      <button className="button primary document-run-button" onClick={handleTranslateImage} disabled={!file || processing}>
        {processing ? <><LoaderCircle size={18} className="spin" /> 이미지 분석 중</> : <><ScanText size={18} /> 사진 번역하기</>}
      </button>

      {error && <div className="document-error"><AlertCircle size={18} /> <span>{error}</span><button onClick={() => setError("")}>닫기</button></div>}

      {processing && (
        <div className="image-processing" aria-live="polite">
          <LoaderCircle size={28} className="spin" />
          <div><strong>이미지에서 문장을 찾고 있습니다</strong><span>문자 인식 후 번역 맥락을 적용합니다.</span></div>
        </div>
      )}

      {result && !processing && (
        <div className="document-result image-result">
          {result.historyWarning && <div className="document-error"><AlertCircle size={18} /><span>{result.historyWarning}</span><button onClick={retryHistorySave}>저장 재시도</button></div>}
          <header className="document-result-heading">
            <div className="result-success-icon"><CheckCircle2 size={28} /></div>
            <div><span>사진 번역 완료</span><h2>{result.imageName}</h2><p>문장 추출과 번역을 완료했습니다.</p></div>
          </header>
          <div className="image-translation-result">
            <article><h3><ImageIcon size={17} /> 추출한 문장</h3><p><HighlightedText text={result.extractedText} highlights={result.highlights?.source || []} /></p></article>
            <article><h3><Sparkles size={17} /> Glossy 번역</h3><p><HighlightedText text={result.translatedText} highlights={result.highlights?.translation || []} /></p></article>
          </div>
          <section className="detected-terms-section">
            <div className="document-section-heading"><h3>용어집 후보</h3><span>이미지에서 감지한 새 표현입니다.</span></div>
            {result.suggestionWarning && <div className="document-error"><AlertCircle size={18} /><span>{result.suggestionWarning}</span></div>}
            {!result.suggestionWarning && result.suggestions.length === 0 && <p className="result-placeholder">새로 추천할 용어가 없습니다.</p>}
            <div className="detected-term-list">
              {result.suggestions.map((candidate) => (
                <DetectedTermCard
                  key={candidate.id}
                  candidate={candidate}
                  onAdd={onAddTerm}
                  onReject={handleRejectSuggestion}
                  onResolved={resolveSuggestion}
                  onTargetChange={handleSuggestionTargetChange}
                  onPreview={onPreview}
                />
              ))}
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
