import { ArrowLeftRight, BookOpenCheck } from "lucide-react";
import { languages } from "../../data/referenceData";

export default function TranslationSettingsBar({
  sourceLanguage,
  targetLanguage,
  teamGlossaryEnabled,
  personalGlossaryEnabled,
  onSourceLanguageChange,
  onTargetLanguageChange,
  onSwapLanguages,
  onTeamGlossaryChange,
  onPersonalGlossaryChange,
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
      <div className="glossary-toggles">
        <label className="glossary-toggle">
          <span><BookOpenCheck size={16} /> 팀 용어집</span>
          <input type="checkbox" checked={teamGlossaryEnabled} onChange={(event) => onTeamGlossaryChange(event.target.checked)} />
          <i aria-hidden="true" />
        </label>
        <label className="glossary-toggle">
          <span>개인 용어집</span>
          <input type="checkbox" checked={personalGlossaryEnabled} onChange={(event) => onPersonalGlossaryChange(event.target.checked)} />
          <i aria-hidden="true" />
        </label>
      </div>
    </div>
  );
}
