import { FileText, UploadCloud, X } from "lucide-react";
import { useId, useState } from "react";

export default function FileDropzone({
  title,
  description,
  accept,
  files = [],
  multiple = false,
  onFiles,
  onRemove,
  disabled = false,
}) {
  const inputId = useId();
  const [dragging, setDragging] = useState(false);

  function selectFiles(fileList) {
    if (!disabled && fileList?.length) onFiles(Array.from(fileList));
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragging(false);
    selectFiles(event.dataTransfer.files);
  }

  return (
    <div>
      <label
        className={`file-dropzone${dragging ? " dragging" : ""}${disabled ? " disabled" : ""}`}
        htmlFor={inputId}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <UploadCloud size={30} strokeWidth={1.6} />
        <strong>{title}</strong>
        <span>{description}</span>
        <span className="file-picker-button">파일 선택</span>
        <input
          id={inputId}
          type="file"
          accept={accept}
          multiple={multiple}
          disabled={disabled}
          onChange={(event) => {
            selectFiles(event.target.files);
            event.target.value = "";
          }}
          hidden
        />
      </label>

      {files.length > 0 && (
        <div className="selected-files">
          {files.map((file, index) => (
            <div className="selected-file" key={`${file.name}-${file.lastModified}-${index}`}>
              <FileText size={18} />
              <span><strong>{file.name}</strong><small>{(file.size / 1024).toFixed(1)} KB</small></span>
              <button type="button" onClick={() => onRemove ? onRemove(index) : onFiles(files.filter((_, fileIndex) => fileIndex !== index))} disabled={disabled} aria-label={`${file.name} 제거`} title="파일 제거"><X size={17} /></button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
