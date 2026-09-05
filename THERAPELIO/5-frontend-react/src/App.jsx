import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { AuthProvider } from "./context/AuthContext";
import Accueil from "./pages/Accueil";
import Bilans from "./pages/Bilans";
import Chat from "./pages/Chat";
import Onboarding from "./pages/Onboarding";
import Praticiens from "./pages/Praticiens";
import Recover from "./pages/Recover";
import RecoveryCode from "./pages/RecoveryCode";
import Ressources from "./pages/Ressources";
import Urgence from "./pages/Urgence";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Accueil />} />
            <Route path="/inscription" element={<Onboarding />} />
            <Route path="/inscription/code" element={<RecoveryCode />} />
            <Route path="/recuperer" element={<Recover />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/rdv" element={<Praticiens />} />
            <Route path="/ressources" element={<Ressources />} />
            <Route path="/bilans" element={<Bilans />} />
            <Route path="/urgence" element={<Urgence />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
