import { motion } from "framer-motion";
import { NavLink, useLocation } from "react-router-dom";
import { BookIcon, ChartIcon, ChatIcon, PhoneIcon, RdvIcon, ShieldIcon } from "./icons";

const NAV_ITEMS = [
  { to: "/chat", label: "Discuter avec Thera", Icon: ChatIcon },
  { to: "/rdv", label: "Prendre RDV", Icon: RdvIcon },
  { to: "/ressources", label: "Boîte à outils", Icon: BookIcon },
  { to: "/bilans", label: "Mes Bilans", Icon: ChartIcon },
];

export default function Sidebar({ isOpen, onClose }) {
  const location = useLocation();

  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 bg-thera-stabilite/30 z-20 md:hidden transition-opacity ${
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      />
      <aside
        className={`w-72 bg-white border-r border-thera-stabilite/8 flex flex-col z-30 justify-between shrink-0 fixed md:static inset-y-0 left-0 transition-transform duration-250 ease-in-out md:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="p-8 pb-4">
          <img src="/logo-principal_web.png" alt="Logo Thérapelio" className="w-52 mb-1 object-contain" />
          <div className="flex items-center gap-1.5 text-thera-stabilite/40 mb-6 pl-0.5">
            <ShieldIcon className="w-3 h-3" />
            <span className="text-[11px] font-semibold tracking-wide uppercase">Anonyme &amp; sécurisé</span>
          </div>

          <nav className="space-y-1" onClick={onClose}>
            {NAV_ITEMS.map(({ to, label, Icon }) => {
              const isActive = location.pathname === to;
              return (
                <NavLink
                  key={to}
                  to={to}
                  className="relative w-full text-left px-4 py-3 rounded-xl font-medium flex items-center gap-3 transition-colors"
                >
                  {isActive && (
                    <motion.div
                      layoutId="nav-active-pill"
                      className="absolute inset-0 bg-thera-confiance rounded-xl"
                      transition={{ type: "spring", stiffness: 420, damping: 34 }}
                    />
                  )}
                  <span
                    className={`relative z-10 flex items-center gap-3 ${
                      isActive ? "text-thera-energie font-semibold" : "text-thera-stabilite/70"
                    }`}
                  >
                    <Icon />
                    {label}
                  </span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        <div className="p-4 mb-4">
          <NavLink
            to="/urgence"
            onClick={onClose}
            className="w-full bg-white hover:bg-thera-technologie/5 border border-thera-technologie/20 hover:border-thera-technologie/40 px-4 py-3.5 rounded-xl transition-colors flex items-center gap-3 text-left group"
          >
            <div className="w-9 h-9 rounded-full bg-thera-technologie/10 flex items-center justify-center shrink-0">
              <PhoneIcon className="w-4 h-4 text-thera-technologie" />
            </div>
            <div className="min-w-0">
              <p className="font-bold text-sm text-thera-technologie">Urgence</p>
              <p className="text-xs text-thera-stabilite/50">Ligne d'écoute 3114 · Gratuit, 24h/24</p>
            </div>
          </NavLink>
        </div>
      </aside>
    </>
  );
}
