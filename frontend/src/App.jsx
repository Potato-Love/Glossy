import Sidebar from "./components/layout/Sidebar";
import TranslatePage from "./pages/TranslatePage";

function App() {
  return (
    <>
      <Sidebar />

      <main
        style={{
          marginLeft: "var(--sidebar-width)",
        }}
      >
        <TranslatePage />
      </main>
    </>
  );
}

export default App;