import { AnimatePresence, motion } from "framer-motion";
import { Link } from "react-router-dom";
import { PhoneIcon, ShieldIcon, TheraMark } from "./icons";

export default function Header({ title }) {
  return (
    <header className="h-16 md:h-20 bg-thera-confiance flex items-center justify-between px-4 sm:px-10 border-b border-thera-stabilite/8 z-10 shrink-0">
      <div className="flex items-center gap-2.5 min-w-0">
        <div className="md:hidden w-8 h-8 rounded-lg bg-thera-stabilite text-white flex items-center justify-center shrink-0">
          <TheraMark className="w-4 h-4" />
        </div>
        <AnimatePresence mode="wait">
          <motion.h2
            key={title}
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.12 }}
            className="text-base sm:text-2xl font-bold font-serif text-thera-stabilite truncate"
          >
            {title}
          </motion.h2>
        </AnimatePresence>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white border border-thera-stabilite/10 text-thera-stabilite/60">
          <ShieldIcon className="w-3.5 h-3.5" />
          <span className="text-xs font-semibold">Échange confidentiel</span>
        </div>
        <Link
          to="/urgence"
          className="md:hidden flex items-center justify-center w-9 h-9 rounded-full bg-thera-technologie/10 text-thera-technologie"
          aria-label="Urgence"
        >
          <PhoneIcon className="w-4 h-4" />
        </Link>
      </div>
    </header>
  );
}
