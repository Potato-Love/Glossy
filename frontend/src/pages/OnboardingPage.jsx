import { ArrowLeft, ArrowRight, BookMarked, Languages, Link2, Sparkles, UsersRound } from "lucide-react";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAppData } from "../context/appData";
import { countries } from "../data/mockData";
import "./OnboardingPage.css";

const introSlides = [
  {
    icon: Languages,
    eyebrow: "팀을 위한 번역",
    title: "다르게 번역되는 팀 용어를 하나로",
    description: "Glossy는 팀 용어집과 수신자 정보를 반영해 협업 문장을 일관되게 번역합니다.",
  },
  {
    icon: BookMarked,
    eyebrow: "기억하는 용어집",
    title: "한 번 승인한 표현은 다음 번역에도",
    description: "새로운 용어 후보를 확인하고 승인하면 팀원 모두가 같은 표현을 재사용할 수 있습니다.",
  },
  {
    icon: Sparkles,
    eyebrow: "맥락에 맞는 문장",
    title: "상대에 따라 언어와 어조까지 자연스럽게",
    description: "수신자의 소속, 직책, 국적, 어조 설정을 골라 더 적절한 메시지를 만듭니다.",
  },
];

export default function OnboardingPage() {
  const { currentUser, completeOnboarding } = useAppData();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const inviteFromLink = searchParams.get("invite") ?? "";
  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState(currentUser);
  const [teamSetup, setTeamSetup] = useState({
    mode: inviteFromLink ? "join" : "create",
    teamName: "Poongcha Team",
    inviteCode: inviteFromLink,
  });
  const [error, setError] = useState("");

  const introCount = introSlides.length;
  const profileStep = introCount;
  const teamStep = introCount + 1;

  function updateProfile(event) {
    const { name, value } = event.target;
    setProfile((current) => ({ ...current, [name]: value }));
  }

  function handleProfileNext(event) {
    event.preventDefault();
    const required = [profile.name, profile.nickname, profile.organization, profile.position, profile.country];
    if (required.some((value) => !value.trim())) {
      setError("모든 프로필 정보를 입력해 주세요.");
      return;
    }
    setError("");
    setStep(teamStep);
  }

  function handleComplete(event) {
    event.preventDefault();
    const valid = teamSetup.mode === "create" ? teamSetup.teamName.trim() : teamSetup.inviteCode.trim();
    if (!valid) {
      setError(teamSetup.mode === "create" ? "팀 이름을 입력해 주세요." : "초대 코드를 입력해 주세요.");
      return;
    }
    if (teamSetup.mode === "join" && teamSetup.inviteCode !== "GLOSSY-2026") {
      setError("데모 초대 코드는 GLOSSY-2026입니다.");
      return;
    }

    completeOnboarding(profile, teamSetup);
    navigate("/translate", { replace: true });
  }

  if (step < introCount) {
    const slide = introSlides[step];
    const Icon = slide.icon;
    return (
      <main className="onboarding-page">
        <div className="onboarding-brand">Glossy.</div>
        <section className="intro-layout">
          <div className="intro-copy">
            <span className="intro-eyebrow">{slide.eyebrow}</span>
            <h1>{slide.title}</h1>
            <p>{slide.description}</p>
            <div className="intro-actions">
              {step > 0 && (
                <button className="button" onClick={() => setStep(step - 1)}>
                  <ArrowLeft size={18} /> 이전
                </button>
              )}
              <button className="button primary" onClick={() => setStep(step + 1)}>
                {step === introCount - 1 ? "프로필 설정" : "다음"} <ArrowRight size={18} />
              </button>
            </div>
            <div className="step-dots" aria-label={`${step + 1} / ${introCount}`}>
              {introSlides.map((item, index) => (
                <span key={item.eyebrow} className={index === step ? "active" : ""} />
              ))}
            </div>
          </div>
          <div className="intro-visual" aria-hidden="true">
            <div className="visual-icon"><Icon size={72} strokeWidth={1.4} /></div>
            <div className="visual-line wide" />
            <div className="visual-line" />
            <div className="visual-translation">
              <span>풍차돌리기</span>
              <ArrowRight size={18} />
              <strong>Poongchadoligi</strong>
            </div>
          </div>
        </section>
      </main>
    );
  }

  if (step === profileStep) {
    return (
      <main className="onboarding-page setup-page">
        <div className="setup-shell">
          <div className="setup-progress"><span style={{ width: "50%" }} /></div>
          <div className="setup-heading">
            <span>1 / 2</span>
            <h1>프로필을 설정해 주세요</h1>
            <p>팀원과 번역 기록에 표시되는 정보입니다.</p>
          </div>
          <form onSubmit={handleProfileNext}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="name">이름</label>
                <input id="name" className="text-field" name="name" value={profile.name} onChange={updateProfile} />
              </div>
              <div className="field">
                <label htmlFor="nickname">닉네임</label>
                <input id="nickname" className="text-field" name="nickname" value={profile.nickname} onChange={updateProfile} />
              </div>
              <div className="field">
                <label htmlFor="organization">소속</label>
                <input id="organization" className="text-field" name="organization" value={profile.organization} onChange={updateProfile} />
              </div>
              <div className="field">
                <label htmlFor="position">직책</label>
                <input id="position" className="text-field" name="position" value={profile.position} onChange={updateProfile} />
              </div>
              <div className="field full">
                <label htmlFor="country">국가</label>
                <select id="country" className="select-field" name="country" value={profile.country} onChange={updateProfile}>
                  {countries.map((country) => <option key={country}>{country}</option>)}
                </select>
              </div>
            </div>
            {error && <p className="form-error setup-error">{error}</p>}
            <div className="setup-actions">
              <button type="button" className="button" onClick={() => setStep(introCount - 1)}><ArrowLeft size={18} /> 이전</button>
              <button className="button primary">팀 설정으로 <ArrowRight size={18} /></button>
            </div>
          </form>
        </div>
      </main>
    );
  }

  return (
    <main className="onboarding-page setup-page">
      <div className="setup-shell">
        <div className="setup-progress"><span style={{ width: "100%" }} /></div>
        <div className="setup-heading">
          <span>2 / 2</span>
          <h1>함께 사용할 팀을 선택하세요</h1>
          <p>새 팀을 만들거나 받은 초대로 기존 팀에 참여할 수 있습니다.</p>
        </div>
        <div className="team-mode-options">
          <button
            className={teamSetup.mode === "create" ? "selected" : ""}
            onClick={() => { setTeamSetup((current) => ({ ...current, mode: "create" })); setError(""); }}
          >
            <UsersRound size={23} /><span><strong>새 팀 만들기</strong><small>새로운 팀 공간을 시작합니다.</small></span>
          </button>
          <button
            className={teamSetup.mode === "join" ? "selected" : ""}
            onClick={() => { setTeamSetup((current) => ({ ...current, mode: "join" })); setError(""); }}
          >
            <Link2 size={23} /><span><strong>초대로 가입하기</strong><small>초대 코드나 링크를 사용합니다.</small></span>
          </button>
        </div>
        <form onSubmit={handleComplete} className="team-setup-form">
          {teamSetup.mode === "create" ? (
            <div className="field">
              <label htmlFor="teamName">팀 이름</label>
              <input id="teamName" className="text-field" value={teamSetup.teamName} onChange={(event) => setTeamSetup((current) => ({ ...current, teamName: event.target.value }))} />
            </div>
          ) : (
            <div className="field">
              <label htmlFor="inviteCode">초대 코드</label>
              <input id="inviteCode" className="text-field" placeholder="예: GLOSSY-2026" value={teamSetup.inviteCode} onChange={(event) => setTeamSetup((current) => ({ ...current, inviteCode: event.target.value }))} />
              <p className="field-hint">초대 링크로 접속한 경우 코드가 자동으로 입력됩니다.</p>
            </div>
          )}
          {error && <p className="form-error setup-error">{error}</p>}
          <div className="setup-actions">
            <button type="button" className="button" onClick={() => setStep(profileStep)}><ArrowLeft size={18} /> 이전</button>
            <button className="button primary">Glossy 시작하기 <ArrowRight size={18} /></button>
          </div>
        </form>
      </div>
    </main>
  );
}
