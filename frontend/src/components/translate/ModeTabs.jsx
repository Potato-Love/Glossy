import { FileText, Image, Type } from "lucide-react";

const modes = [
  { id: "text", label: "텍스트", icon: Type },
  { id: "document", label: "문서", icon: FileText },
  { id: "image", label: "사진", icon: Image },
];

export default function ModeTabs({ mode, onChange }) {
  return (
    <div className="mode-tabs" aria-label="번역 입력 방식">
      {modes.map((item) => {
        const Icon = item.icon;
        return (
          <button
            key={item.id}
            className={`mode-tab${mode === item.id ? " active" : ""}`}
            onClick={() => onChange(item.id)}
            aria-pressed={mode === item.id}
          >
            <Icon size={18} strokeWidth={1.8} />
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
