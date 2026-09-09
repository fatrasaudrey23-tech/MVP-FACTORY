import { motion } from "framer-motion";
import { NavLink, useLocation } from "react-router-dom";
import { BookIcon, ChartIcon, ChatIcon, HomeIcon, RdvIcon } from "./icons";

const TABS = [
  { to: "/", label: "Accueil", Icon: HomeIcon, exact: true },
  { to: "/chat", label: "Thera", Icon: ChatIcon },
  { to: "/rdv", label: "RDV", Icon: RdvIcon },
  { to: "/ressources", label: "Outils", Icon: BookIcon },
  { to: "/bilans", label: "Bilans", Icon: ChartIcon },
];

export default function BottomNav() {
  const location = useLocation();

  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-thera-stabilite/8 flex items-stretch z-30 pb-[env(safe-area-inset-bottom)]">
      {TABS.map(({ to, label, Icon, exact }) => {
        const isActive = exact ? location.pathname === to : location.pathname.startsWith(to);
        return (
          <NavLink key={to} to={to} className="relative flex-1 flex flex-col items-center justify-center gap-0.5 py-2.5">
            {isActive && (
              <motion.div
                layoutId="bottom-nav-active"
                className="absolute top-0 inset-x-4 h-0.5 bg-thera-energie rounded-full"
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
              />
            )}
            <Icon className={`w-5 h-5 ${isActive ? "text-thera-energie" : "text-thera-stabilite/45"}`} />
            <span className={`text-[10px] font-semibold ${isActive ? "text-thera-energie" : "text-thera-stabilite/45"}`}>{label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
