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
    <div className="bg-thera-confiance text-thera-stabilite font-sans h-screen flex overflow-hidden">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <main className="flex-1 flex flex-col h-full overflow-hidden min-w-0">
        <Header title={title} onMenuClick={() => setSidebarOpen((v) => !v)} />
        <div className="flex-1 p-3 sm:p-6 md:p-10 overflow-y-auto">
          <div className="relative max-w-4xl mx-auto bg-white p-4 sm:p-6 md:p-8 rounded-3xl shadow-sm border border-thera-stabilite/8 min-h-[550px] flex flex-col overflow-hidden">
            {/* mode="wait" bloquait l'animation à opacité 0 sur les redirections immédiates
                (ex. "/" -> "/inscription"). "popLayout" sort l'écran sortant du flux normal
                pendant son animation, ce qui évite aussi le chevauchement visuel avec l'entrant. */}
            <AnimatePresence initial={false} mode="popLayout">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.16, ease: "easeOut" }}
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
