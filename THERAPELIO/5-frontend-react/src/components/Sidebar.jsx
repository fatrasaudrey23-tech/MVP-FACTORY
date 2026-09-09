import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { BookIcon, ChartIcon, ChatIcon, ChevronDownIcon, HomeIcon, LogOutIcon, PhoneIcon, RdvIcon, ShieldIcon } from "./icons";

const NAV_ITEMS = [
  { to: "/", label: "Accueil", Icon: HomeIcon, exact: true },
  { to: "/chat", label: "Discuter avec Thera", Icon: ChatIcon },
  { to: "/rdv", label: "Prendre RDV", Icon: RdvIcon },
  { to: "/ressources", label: "Boîte à outils", Icon: BookIcon },
  { to: "/bilans", label: "Mes Bilans", Icon: ChartIcon },
];

function UserChip() {
  const { prenom, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  if (!prenom) return null;

  function handleLogout() {
    setOpen(false);
    logout();
    navigate("/");
  }

  return (
    <div className="relative mb-4">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2.5 p-2 rounded-xl hover:bg-thera-confiance transition-colors"
      >
        <div className="w-8 h-8 rounded-full bg-thera-stabilite text-white flex items-center justify-center text-xs font-bold shrink-0">
          {prenom.slice(0, 2).toUpperCase()}
        </div>
        <span className="flex-1 text-left text-sm font-semibold text-thera-stabilite truncate">{prenom}</span>
        <ChevronDownIcon className={`w-3.5 h-3.5 text-thera-stabilite/40 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.12 }}
              className="absolute left-0 right-0 mt-1 bg-white border border-thera-stabilite/10 rounded-xl shadow-lg overflow-hidden z-20"
            >
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-4 py-3 text-sm text-thera-stabilite hover:bg-thera-confiance transition-colors"
              >
                <LogOutIcon className="w-4 h-4" /> Changer de profil
              </button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="hidden md:flex w-72 bg-white border-r border-thera-stabilite/8 flex-col justify-between shrink-0">
      <div className="p-6 pb-4">
        <img src="/logo-principal_web.png" alt="Logo Thérapelio" className="w-48 mb-1 object-contain" />
        <div className="flex items-center gap-1.5 text-thera-stabilite/40 mb-6 pl-0.5">
          <ShieldIcon className="w-3 h-3" />
          <span className="text-[11px] font-semibold tracking-wide uppercase">Anonyme &amp; sécurisé</span>
        </div>

        <UserChip />

        <nav className="space-y-1">
          {NAV_ITEMS.map(({ to, label, Icon, exact }) => {
            const isActive = exact ? location.pathname === to : location.pathname.startsWith(to);
            return (
              <NavLink key={to} to={to} className="relative w-full text-left px-4 py-3 rounded-xl font-medium flex items-center gap-3 transition-colors">
                {isActive && (
                  <motion.div
                    layoutId="nav-active-pill"
                    className="absolute inset-0 bg-thera-confiance rounded-xl"
                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                  />
                )}
                <span className={`relative z-10 flex items-center gap-3 ${isActive ? "text-thera-energie font-semibold" : "text-thera-stabilite/70"}`}>
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
  );
}
