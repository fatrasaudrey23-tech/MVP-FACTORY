import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Accueil() {
  const { hasProfile, prenom, logout } = useAuth();

  if (!hasProfile) return <Navigate to="/inscription" replace />;

  return (
    <div className="flex flex-col items-center justify-center flex-1 text-center p-4 sm:p-6">
      <h2 className="text-2xl font-bold font-serif text-thera-stabilite mb-2">Bonjour {prenom} 👋</h2>
      <p className="text-thera-stabilite/70 mb-10">Comment veux-tu commencer aujourd'hui ?</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 w-full max-w-xl">
        <Link
          to="/chat"
          className="bg-white border-2 border-thera-stabilite/10 hover:border-thera-energie rounded-2xl p-6 text-left transition-all"
        >
          <div className="text-3xl mb-3">💬</div>
          <h3 className="font-bold text-lg text-thera-stabilite mb-1">Discuter avec Thera</h3>
          <p className="text-sm text-thera-stabilite/60">Un espace pour poser des mots sur ce que tu vis, à ton rythme.</p>
        </Link>
        <Link
          to="/rdv"
          className="bg-white border-2 border-thera-stabilite/10 hover:border-thera-energie rounded-2xl p-6 text-left transition-all"
        >
          <div className="text-3xl mb-3">📅</div>
          <h3 className="font-bold text-lg text-thera-stabilite mb-1">Prendre rendez-vous</h3>
          <p className="text-sm text-thera-stabilite/60">Passe directement à un échange avec un professionnel, sous 72h.</p>
        </Link>
      </div>

      <button onClick={logout} className="text-xs text-thera-stabilite/40 hover:text-thera-stabilite/70 underline mt-8">
        Ce n'est pas toi ? Changer de profil
      </button>
    </div>
  );
}
