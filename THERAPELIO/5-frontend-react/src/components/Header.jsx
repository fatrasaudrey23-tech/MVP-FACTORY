import { MenuIcon } from "./icons";

export default function Header({ title, onMenuClick }) {
  return (
    <header className="h-20 bg-thera-confiance/90 backdrop-blur-md flex items-center justify-between px-4 sm:px-10 border-b border-thera-stabilite/5 z-10 shrink-0">
      <div className="flex items-center gap-2 min-w-0">
        <button
          onClick={onMenuClick}
          className="md:hidden p-2 -ml-2 rounded-lg hover:bg-white/60 text-thera-stabilite shrink-0"
          aria-label="Ouvrir le menu"
        >
          <MenuIcon />
        </button>
        <h2 className="text-lg sm:text-2xl font-bold font-serif text-thera-stabilite truncate">{title}</h2>
      </div>
    </header>
  );
}
