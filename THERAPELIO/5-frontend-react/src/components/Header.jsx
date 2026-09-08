import { AnimatePresence, motion } from "framer-motion";
import { MenuIcon, ShieldIcon } from "./icons";

export default function Header({ title, onMenuClick }) {
  return (
    <header className="h-20 bg-thera-confiance flex items-center justify-between px-4 sm:px-10 border-b border-thera-stabilite/8 z-10 shrink-0">
      <div className="flex items-center gap-2 min-w-0">
        <button
          onClick={onMenuClick}
          className="md:hidden p-2 -ml-2 rounded-lg hover:bg-white/60 text-thera-stabilite shrink-0"
          aria-label="Ouvrir le menu"
        >
          <MenuIcon />
        </button>
        <AnimatePresence mode="wait">
          <motion.h2
            key={title}
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.12 }}
            className="text-lg sm:text-2xl font-bold font-serif text-thera-stabilite truncate"
          >
            {title}
          </motion.h2>
        </AnimatePresence>
      </div>
      <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white border border-thera-stabilite/10 text-thera-stabilite/60 shrink-0">
        <ShieldIcon className="w-3.5 h-3.5" />
        <span className="text-xs font-semibold">Échange confidentiel</span>
      </div>
    </header>
  );
}
