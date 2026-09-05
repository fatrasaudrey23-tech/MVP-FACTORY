import { NavLink } from "react-router-dom";
import { BookIcon, ChartIcon, ChatIcon, PhoneIcon, RdvIcon } from "./icons";

function navItemClass({ isActive }) {
  return `w-full text-left px-4 py-3 rounded-xl font-medium transition-all flex items-center gap-3 ${
    isActive
      ? "bg-thera-confiance text-thera-energie font-semibold shadow-sm"
      : "text-thera-stabilite/70 hover:bg-thera-confiance"
  }`;
}

export default function Sidebar({ isOpen, onClose }) {
  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 bg-black/40 z-20 md:hidden ${isOpen ? "" : "hidden"}`}
      />
      <aside
        className={`w-72 bg-white border-r border-thera-stabilite/5 shadow-sm flex flex-col z-30 justify-between shrink-0 fixed md:static inset-y-0 left-0 transition-transform duration-300 ease-in-out md:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="p-8 pb-4">
          <img src="/logo-principal_web.png" alt="Logo Thérapelio" className="w-56 mb-4 object-contain" />

          <nav className="mt-6 space-y-2" onClick={onClose}>
            <NavLink to="/chat" className={navItemClass}>
              <ChatIcon />
              Discuter avec Thera
            </NavLink>
            <NavLink to="/rdv" className={navItemClass}>
              <RdvIcon />
              Prendre RDV
            </NavLink>
            <NavLink to="/ressources" className={navItemClass}>
              <BookIcon />
              Boîte à outils
            </NavLink>
            <NavLink to="/bilans" className={navItemClass}>
              <ChartIcon />
              Mes Bilans
            </NavLink>
          </nav>
        </div>

        <div className="p-4 mb-4">
          <NavLink
            to="/urgence"
            onClick={onClose}
            className="w-full bg-white hover:bg-thera-technologie/5 border border-thera-technologie/20 hover:border-thera-technologie/40 px-4 py-3.5 rounded-xl transition-all flex items-center gap-3 text-left group"
          >
            <div className="w-9 h-9 rounded-full bg-thera-technologie/10 group-hover:bg-thera-technologie/15 flex items-center justify-center shrink-0 transition-colors">
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
