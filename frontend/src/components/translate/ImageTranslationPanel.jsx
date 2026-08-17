import { AlertCircle, CheckCircle2, ImageIcon, LoaderCircle, ScanText, Sparkles } from "lucide-react";
import { useState } from "react";
import { translateImage } from "../../api/documents";
import DetectedTermCard from "./DetectedTermCard";
import FileDropzone from "./FileDropzone";
import TranslationSettingsBar from "./TranslationSettingsBar";

const imageAccept = ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp";
const supportedImageExtensions = ["jpg", "jpeg", "png", "webp"];

export default function ImageTranslationPanel({ options, settingsProps, onAddTerm }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const processing = status === "processing";

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
      setResult(response);
      setStatus("done");
    } catch (taskError) {
      setStatus("error");
      setError(taskError instanceof Error ? taskError.message : "이미지 처리 중 오류가 발생했습니다.");
    }
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
          <header className="document-result-heading">
            <div className="result-success-icon"><CheckCircle2 size={28} /></div>
            <div><span>사진 번역 완료</span><h2>{result.imageName}</h2><p>문장 추출과 번역을 완료했습니다.</p></div>
          </header>
          <div className="image-translation-result">
            <article><h3><ImageIcon size={17} /> 추출한 문장</h3><p>{result.extractedText}</p></article>
            <article><h3><Sparkles size={17} /> Glossy 번역</h3><p>{result.translatedText}</p></article>
          </div>
          <section className="detected-terms-section">
            <div className="document-section-heading"><h3>용어집 후보</h3><span>이미지에서 감지한 새 표현입니다.</span></div>
            <div className="detected-term-list">{result.suggestions.map((candidate) => <DetectedTermCard key={candidate.id} candidate={candidate} onAdd={onAddTerm} />)}</div>
          </section>
        </div>
      )}
    </section>
  );
}
