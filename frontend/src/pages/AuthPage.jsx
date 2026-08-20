import { BookMarked, Languages, LogIn, Sparkles, UserPlus } from "lucide-react";
import { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/authContext";
import "./OnboardingPage.css";

export default function AuthPage({ mode }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [nickname, setNickname] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const inviteCode = searchParams.get("invite") || "";
  const isSignup = mode === "signup";

  if (auth.status === "loading") {
    return <main className="route-loading"><span className="onboarding-brand">Glossy.</span><p>로그인 정보를 확인하는 중입니다.</p></main>;
  }

  if (auth.status === "authenticated") {
    if (!auth.user.profile_completed || !auth.currentTeam || inviteCode) {
      const query = inviteCode ? `?invite=${encodeURIComponent(inviteCode)}` : "";
      return <Navigate to={`/onboarding${query}`} replace />;
    }
    return <Navigate to="/translate" replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (nickname.trim().length < 2) {
      setError("닉네임을 2자 이상 입력해 주세요.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const session = isSignup
        ? await auth.signup(nickname)
        : await auth.login(nickname);
      const query = inviteCode ? `?invite=${encodeURIComponent(inviteCode)}` : "";
      if (isSignup || !session.user.profile_completed || !session.teams.length || inviteCode) {
        navigate(`/onboarding${query}`, { replace: true });
      } else {
        navigate("/translate", { replace: true });
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "요청을 처리하지 못했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  const otherQuery = inviteCode ? `?invite=${encodeURIComponent(inviteCode)}` : "";
  const introFeatures = [
    { icon: Languages, title: "팀 용어를 하나로", description: "팀 용어집을 반영해 누구나 같은 표현으로 번역합니다." },
    { icon: BookMarked, title: "승인한 표현을 기억", description: "한 번 정한 번역은 다음 문장에서도 일관되게 재사용합니다." },
    { icon: Sparkles, title: "수신자에 맞는 문장", description: "상대의 소속과 선호 어조까지 번역 맥락에 반영합니다." },
  ];

  return (
    <main className="onboarding-page auth-page">
      <header className="auth-page-header">
        <Link className="onboarding-brand auth-brand" to="/login">Glossy.</Link>
      </header>
      <section className="auth-layout">
        <div className="intro-copy auth-intro">
          <h1>번역할 수록,<br />팀을 더 잘 아는 번역기.</h1>
          <p>용어집과 수신자 정보를 반영해 팀의 모든 메시지를 더 정확하고 일관되게 번역하세요.</p>
          <div className="auth-feature-list">
            {introFeatures.map(({ icon: Icon, title, description }) => (
              <div className="auth-feature" key={title}>
                <span><Icon size={18} strokeWidth={1.8} /></span>
                <div><strong>{title}</strong><small>{description}</small></div>
              </div>
            ))}
          </div>
        </div>

        <div className="auth-shell">
        <div className="setup-heading auth-heading">
          <span>{isSignup ? "회원가입" : "다시 만나서 반가워요"}</span>
          <h1>{isSignup ? "닉네임으로 시작하기" : "로그인"}</h1>
          <p>{isSignup ? "팀에서 사용할 닉네임을 먼저 만들어 주세요." : "가입할 때 사용한 닉네임을 입력해 주세요."}</p>
        </div>
        {inviteCode && <p className="invite-notice">로그인 후 초대받은 팀에 가입할 수 있습니다.</p>}
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="authNickname">닉네임</label>
            <input
              id="authNickname"
              className="text-field"
              value={nickname}
              onChange={(event) => setNickname(event.target.value)}
              maxLength={20}
              autoFocus
              autoComplete="username"
              placeholder="2~20자"
            />
          </div>
          {error && <p className="form-error setup-error">{error}</p>}
          <button className="button primary auth-submit" disabled={submitting}>
            {isSignup ? <UserPlus size={18} /> : <LogIn size={18} />}
            {submitting ? "처리 중..." : isSignup ? "회원가입" : "로그인"}
          </button>
        </form>
        <p className="auth-switch">
          {isSignup ? "이미 계정이 있나요?" : "아직 계정이 없나요?"}{" "}
          <Link to={`${isSignup ? "/login" : "/signup"}${otherQuery}`}>
            {isSignup ? "로그인" : "회원가입"}
          </Link>
        </p>
        <p className="auth-caution">해커톤 데모용 계정입니다. 비밀번호 없이 닉네임만으로 로그인됩니다.</p>
        </div>
      </section>
    </main>
  );
}
