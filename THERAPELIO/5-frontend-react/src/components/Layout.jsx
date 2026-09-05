import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Header from "./Header";
import Sidebar from "./Sidebar";

const TITLES = {
  "/": "Bienvenue",
  "/inscription": "Bienvenue",
  "/inscription/code": "Bienvenue",
  "/recuperer": "Bienvenue",
  "/chat": "Thera",
  "/rdv": "Prendre rendez-vous",
  "/ressources": "Boîte à outils bien-être",
  "/bilans": "Mes Bilans",
  "/urgence": "Urgence",
};

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const title = TITLES[location.pathname] || "Thérapelio";

  return (
    <div className="bg-thera-confiance text-thera-stabilite font-sans h-screen flex overflow-hidden">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <main className="flex-1 flex flex-col h-full relative overflow-hidden min-w-0">
        <Header title={title} onMenuClick={() => setSidebarOpen((v) => !v)} />
        <div className="flex-1 p-3 sm:p-6 md:p-10 overflow-y-auto">
          <div className="max-w-4xl mx-auto bg-white p-4 sm:p-6 md:p-8 rounded-[2rem] shadow-sm border border-thera-stabilite/5 min-h-[550px] flex flex-col">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}
