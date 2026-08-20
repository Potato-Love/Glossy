import { ArrowLeft, ArrowRight, UsersRound } from "lucide-react";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/authContext";
import { countries } from "../data/referenceData";
import "./OnboardingPage.css";

export default function OnboardingPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const inviteFromLink = searchParams.get("invite") || "";
  const profileStep = 0;
  const teamStep = 1;
  const [step, setStep] = useState(auth.user.profile_completed ? teamStep : profileStep);
  const [profile, setProfile] = useState({
    name: auth.user.name || "",
    nickname: auth.user.nickname || "",
    organization: auth.user.organization || "",
    position: auth.user.position || "",
    country: auth.user.country || "",
  });
  const [teamMode, setTeamMode] = useState(inviteFromLink ? "join" : "create");
  const [teamName, setTeamName] = useState("");
  const [inviteCode, setInviteCode] = useState(inviteFromLink);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function updateProfile(event) {
    const { name, value } = event.target;
    setProfile((current) => ({ ...current, [name]: value }));
  }

  async function handleProfileNext(event) {
    event.preventDefault();
    if (Object.values(profile).some((value) => !value.trim())) {
      setError("모든 프로필 정보를 입력해 주세요.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await auth.saveProfile(profile);
      setStep(teamStep);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "프로필을 저장하지 못했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTeamComplete(event) {
    event.preventDefault();
    const value = teamMode === "create" ? teamName.trim() : inviteCode.trim();
    if (!value) {
      setError(teamMode === "create" ? "팀 이름을 입력해 주세요." : "초대 코드를 입력해 주세요.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      if (teamMode === "create") await auth.createTeam(value);
      else await auth.joinTeam(value);
      navigate("/translate", { replace: true });
    } catch (teamError) {
      setError(teamError instanceof Error ? teamError.message : "팀 설정을 완료하지 못했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  if (step === profileStep) {
    return (
      <main className="onboarding-page setup-page"><div className="setup-shell">
        <div className="setup-progress"><span style={{ width: "50%" }} /></div>
        <div className="setup-heading"><span>1 / 2</span><h1>프로필을 설정해 주세요</h1><p>팀원과 번역 기록에 표시되는 정보입니다.</p></div>
        <form onSubmit={handleProfileNext}>
          <div className="form-grid">
            <div className="field"><label htmlFor="name">이름</label><input id="name" className="text-field" name="name" value={profile.name} onChange={updateProfile} /></div>
            <div className="field"><label htmlFor="nickname">닉네임</label><input id="nickname" className="text-field" name="nickname" value={profile.nickname} onChange={updateProfile} maxLength={20} /></div>
            <div className="field"><label htmlFor="organization">소속</label><input id="organization" className="text-field" name="organization" value={profile.organization} onChange={updateProfile} /></div>
            <div className="field"><label htmlFor="position">직책</label><input id="position" className="text-field" name="position" value={profile.position} onChange={updateProfile} /></div>
            <div className="field full"><label htmlFor="country">국가</label><select id="country" className="select-field" name="country" value={profile.country} onChange={updateProfile}><option value="" disabled>국가를 선택해 주세요</option>{countries.map((country) => <option key={country}>{country}</option>)}</select></div>
          </div>
          {error && <p className="form-error setup-error">{error}</p>}
          <div className="setup-actions end"><button className="button primary" disabled={submitting}>{submitting ? "저장 중..." : "팀 설정으로"} <ArrowRight size={18} /></button></div>
        </form>
      </div></main>
    );
  }

  return (
    <main className="onboarding-page setup-page"><div className="setup-shell">
      <div className="setup-progress"><span style={{ width: "100%" }} /></div>
      <div className="setup-heading"><span>2 / 2</span><h1>사용할 팀을 선택해 주세요</h1><p>새 팀을 만들거나 받은 초대 코드로 참여할 수 있습니다.</p></div>
      <div className="team-mode-options two-column">
        <button className={teamMode === "create" ? "selected" : ""} type="button" onClick={() => { setTeamMode("create"); setError(""); }}><UsersRound size={23} /><span><strong>새 팀 만들기</strong><small>새로운 팀 공간을 시작합니다.</small></span></button>
        <button className={teamMode === "join" ? "selected" : ""} type="button" onClick={() => { setTeamMode("join"); setError(""); }}><UsersRound size={23} /><span><strong>초대받은 팀 가입</strong><small>초대 코드로 기존 팀에 참여합니다.</small></span></button>
      </div>
      <form onSubmit={handleTeamComplete} className="team-setup-form">
        {teamMode === "create" ? <div className="field"><label htmlFor="teamName">팀 이름</label><input id="teamName" className="text-field" value={teamName} onChange={(event) => setTeamName(event.target.value)} maxLength={50} /></div> : <div className="field"><label htmlFor="inviteCode">초대 코드</label><input id="inviteCode" className="text-field invite-code-input" value={inviteCode} onChange={(event) => setInviteCode(event.target.value.toUpperCase())} maxLength={40} /></div>}
        {error && <p className="form-error setup-error">{error}</p>}
        <div className="setup-actions">{!auth.user.profile_completed && <button type="button" className="button" onClick={() => setStep(profileStep)}><ArrowLeft size={18} /> 이전</button>}<button className="button primary team-submit" disabled={submitting}>{submitting ? "처리 중..." : teamMode === "create" ? "팀 만들고 시작하기" : "팀 가입하고 시작하기"} <ArrowRight size={18} /></button></div>
      </form>
    </div></main>
  );
}
