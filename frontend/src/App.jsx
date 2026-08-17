import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import { useAppData } from "./context/appData";
import GlossaryPage from "./pages/GlossaryPage";
import HistoryPage from "./pages/HistoryPage";
import MyPage from "./pages/MyPage";
import OnboardingPage from "./pages/OnboardingPage";
import RecipientProfilePage from "./pages/RecipientProfilePage";
import TeamPage from "./pages/TeamPage";
import TranslatePage from "./pages/TranslatePage";
import "./App.css";

function AppRoutes() {
  const { onboardingComplete } = useAppData();

  return (
    <Routes>
      <Route
        path="/onboarding"
        element={onboardingComplete ? <Navigate to="/translate" replace /> : <OnboardingPage />}
      />
      <Route
        element={onboardingComplete ? <AppLayout /> : <Navigate to="/onboarding" replace />}
      >
        <Route path="/translate" element={<TranslatePage />} />
        <Route path="/glossary" element={<GlossaryPage />} />
        <Route path="/recipients" element={<RecipientProfilePage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/team" element={<TeamPage />} />
        <Route path="/my" element={<MyPage />} />
      </Route>
      <Route path="*" element={<Navigate to={onboardingComplete ? "/translate" : "/onboarding"} replace />} />
    </Routes>
  );
}

export default function App() {
  return <AppRoutes />;
}
