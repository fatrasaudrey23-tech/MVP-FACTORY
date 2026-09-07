import { motion } from "framer-motion";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Accueil() {
  const { hasProfile, prenom, logout } = useAuth();

  if (!hasProfile) return <Navigate to="/inscription" replace />;

  return (
    <div className="flex flex-col items-center justify-center flex-1 text-center p-4 sm:p-6">
      <motion.h2
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-2xl font-bold font-serif text-thera-stabilite mb-2"
      >
        Bonjour {prenom} 👋
      </motion.h2>
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="text-thera-stabilite/70 mb-10"
      >
        Comment veux-tu commencer aujourd'hui ?
      </motion.p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 w-full max-w-xl">
        {[
          { to: "/chat", icon: "💬", title: "Discuter avec Thera", desc: "Un espace pour poser des mots sur ce que tu vis, à ton rythme." },
          { to: "/rdv", icon: "📅", title: "Prendre rendez-vous", desc: "Passe directement à un échange avec un professionnel, sous 72h." },
        ].map((card, i) => (
          <motion.div
            key={card.to}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 + i * 0.08, duration: 0.3 }}
            whileHover={{ y: -4 }}
          >
            <Link
              to={card.to}
              className="block bg-white border-2 border-thera-stabilite/10 hover:border-thera-energie rounded-2xl p-6 text-left transition-colors shadow-sm hover:shadow-lg hover:shadow-thera-stabilite/5 h-full"
            >
              <div className="text-3xl mb-3">{card.icon}</div>
              <h3 className="font-bold text-lg text-thera-stabilite mb-1">{card.title}</h3>
              <p className="text-sm text-thera-stabilite/60">{card.desc}</p>
            </Link>
          </motion.div>
        ))}
      </div>

      <button onClick={logout} className="text-xs text-thera-stabilite/40 hover:text-thera-stabilite/70 underline mt-8">
        Ce n'est pas toi ? Changer de profil
      </button>
    </div>
  );
}
