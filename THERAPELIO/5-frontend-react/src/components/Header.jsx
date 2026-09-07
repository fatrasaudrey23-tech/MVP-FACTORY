import { AnimatePresence, motion } from "framer-motion";
import { MenuIcon } from "./icons";

export default function Header({ title, onMenuClick }) {
  return (
    <header className="h-20 bg-thera-confiance/70 backdrop-blur-xl flex items-center justify-between px-4 sm:px-10 border-b border-white/50 z-10 shrink-0">
      <div className="flex items-center gap-2 min-w-0">
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={onMenuClick}
          className="md:hidden p-2 -ml-2 rounded-lg hover:bg-white/60 text-thera-stabilite shrink-0"
          aria-label="Ouvrir le menu"
        >
          <MenuIcon />
        </motion.button>
        <AnimatePresence mode="wait">
          <motion.h2
            key={title}
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.15 }}
            className="text-lg sm:text-2xl font-bold font-serif text-thera-stabilite truncate"
          >
            {title}
          </motion.h2>
        </AnimatePresence>
      </div>
    </header>
  );
}
