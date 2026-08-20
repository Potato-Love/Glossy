import { Check, UserRound } from "lucide-react";
import { useState } from "react";
import { useAppData } from "../context/appData";
import { countries } from "../data/referenceData";
import "./PageStyles.css";

export default function MyPage() {
  const { currentUser, updateUser } = useAppData();
  const [form, setForm] = useState(currentUser);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await updateUser(form);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 1800);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "프로필을 저장하지 못했습니다.");
    } finally {
      setSaving(false);
    }
  }

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  return (
    <div className="page">
      <header className="page-header">
        <div><h1>내 정보</h1><p>프로필과 팀에 표시되는 개인 정보를 수정합니다.</p></div>
      </header>

      <section className="settings-section">
        <div className="section-heading">
          <div><h2>개인 프로필</h2><p>변경한 닉네임은 팀원 목록과 새 히스토리에 반영됩니다.</p></div>
          <div className="avatar"><UserRound size={22} /></div>
        </div>
        <form onSubmit={handleSubmit} className="form-grid">
          <div className="field"><label htmlFor="myName">이름</label><input id="myName" className="text-field" name="name" value={form.name} onChange={updateField} required /></div>
          <div className="field"><label htmlFor="myNickname">닉네임</label><input id="myNickname" className="text-field" name="nickname" value={form.nickname} onChange={updateField} required /></div>
          <div className="field"><label htmlFor="myOrganization">소속</label><input id="myOrganization" className="text-field" name="organization" value={form.organization} onChange={updateField} required /></div>
          <div className="field"><label htmlFor="myPosition">직책</label><input id="myPosition" className="text-field" name="position" value={form.position} onChange={updateField} required /></div>
          <div className="field full"><label htmlFor="myCountry">국가</label><select id="myCountry" className="select-field" name="country" value={form.country} onChange={updateField}>{countries.map((country) => <option key={country}>{country}</option>)}</select></div>
          {error && <p className="form-error full">{error}</p>}
          <div className="full toolbar-group"><button className="button primary" disabled={saving}><Check size={18} /> {saving ? "저장 중" : "저장"}</button>{saved && <span className="status-message">프로필을 저장했습니다.</span>}</div>
        </form>
      </section>
    </div>
  );
}
