import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import { useAuth } from "./context/authContext";
import AuthPage from "./pages/AuthPage";
import GlossaryPage from "./pages/GlossaryPage";
import HistoryPage from "./pages/HistoryPage";
import MyPage from "./pages/MyPage";
import OnboardingPage from "./pages/OnboardingPage";
import RecipientProfilePage from "./pages/RecipientProfilePage";
import TeamPage from "./pages/TeamPage";
import TranslatePage from "./pages/TranslatePage";
import "./App.css";

function LoadingScreen() {
  return <main className="route-loading"><span className="onboarding-brand">Glossy.</span><p>로그인 정보를 확인하는 중입니다.</p></main>;
}

function ProtectedLayout() {
  const auth = useAuth();
  const location = useLocation();
  if (auth.status === "loading") return <LoadingScreen />;
  if (auth.status !== "authenticated") {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  if (!auth.user.profile_completed || !auth.currentTeam) {
    return <Navigate to="/onboarding" replace />;
  }
  return <AppLayout />;
}

function OnboardingRoute() {
  const auth = useAuth();
  if (auth.status === "loading") return <LoadingScreen />;
  if (auth.status !== "authenticated") return <Navigate to="/signup" replace />;
  return <OnboardingPage />;
}

function JoinRoute() {
  const auth = useAuth();
  const location = useLocation();
  const code = location.pathname.split("/").pop();
  if (auth.status === "loading") return <LoadingScreen />;
  if (auth.status !== "authenticated") {
    return <Navigate to={`/login?invite=${encodeURIComponent(code)}`} replace />;
  }
  return <Navigate to={`/onboarding?invite=${encodeURIComponent(code)}`} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/signup" element={<AuthPage mode="signup" />} />
      <Route path="/onboarding" element={<OnboardingRoute />} />
      <Route path="/join/:inviteCode" element={<JoinRoute />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/translate" element={<TranslatePage />} />
        <Route path="/glossary" element={<GlossaryPage />} />
        <Route path="/recipients" element={<RecipientProfilePage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/team" element={<TeamPage />} />
        <Route path="/my" element={<MyPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/translate" replace />} />
    </Routes>
  );
}
