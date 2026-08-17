import { ArrowLeftRight, BookOpenCheck } from "lucide-react";
import { languages } from "../../data/mockData";

export default function TranslationSettingsBar({
  sourceLanguage,
  targetLanguage,
  glossaryEnabled,
  onSourceLanguageChange,
  onTargetLanguageChange,
  onSwapLanguages,
  onGlossaryChange,
}) {
  return (
    <div className="file-translation-settings">
      <div className="file-language-controls">
        <select value={sourceLanguage} onChange={(event) => onSourceLanguageChange(event.target.value)} aria-label="원문 언어">
          {languages.map((language) => <option key={language.code} value={language.code}>{language.label}</option>)}
        </select>
        <button type="button" onClick={onSwapLanguages} aria-label="언어 방향 전환" title="언어 방향 전환"><ArrowLeftRight size={19} /></button>
        <select value={targetLanguage} onChange={(event) => onTargetLanguageChange(event.target.value)} aria-label="번역 언어">
          {languages.map((language) => <option key={language.code} value={language.code}>{language.label}</option>)}
        </select>
      </div>
      <label className="glossary-toggle">
        <span><BookOpenCheck size={16} /> 용어집 적용</span>
        <input type="checkbox" checked={glossaryEnabled} onChange={(event) => onGlossaryChange(event.target.checked)} />
        <i aria-hidden="true" />
      </label>
    </div>
  );
}
