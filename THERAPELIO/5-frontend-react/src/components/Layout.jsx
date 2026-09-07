import { AnimatePresence, motion } from "framer-motion";
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
    <div className="relative bg-thera-confiance text-thera-stabilite font-sans h-screen flex overflow-hidden">
      {/* Fond décoratif : masses de couleur douces et animées, pour donner de la profondeur */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="animate-blob absolute -top-32 -left-24 w-[32rem] h-[32rem] rounded-full bg-thera-energie/10 blur-3xl" />
        <div className="animate-blob-slow absolute top-1/3 -right-32 w-[36rem] h-[36rem] rounded-full bg-thera-reflexion/10 blur-3xl" />
        <div className="animate-blob absolute -bottom-40 left-1/4 w-[28rem] h-[28rem] rounded-full bg-thera-chaleur/10 blur-3xl" />
      </div>

      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <main className="relative flex-1 flex flex-col h-full overflow-hidden min-w-0">
        <Header title={title} onMenuClick={() => setSidebarOpen((v) => !v)} />
        <div className="flex-1 p-3 sm:p-6 md:p-10 overflow-y-auto">
          <div className="relative max-w-4xl mx-auto bg-white/80 backdrop-blur-xl p-4 sm:p-6 md:p-8 rounded-[2rem] shadow-[0_8px_40px_-12px_rgba(40,50,82,0.18)] border border-white/60 min-h-[550px] flex flex-col overflow-hidden">
            {/* mode="wait" bloquait l'animation à opacité 0 sur les redirections immédiates
                (ex. "/" -> "/inscription"). "popLayout" sort l'écran sortant du flux normal
                pendant son animation, ce qui évite aussi le chevauchement visuel avec l'entrant. */}
            <AnimatePresence initial={false} mode="popLayout">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.22, ease: "easeOut" }}
                className="flex-1 flex flex-col"
              >
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </main>
    </div>
  );
}
