import { motion } from "framer-motion";
import { Link, Navigate } from "react-router-dom";
import { ChatIcon, CheckCircleIcon, RdvIcon, ShieldIcon } from "../components/icons";
import { useAuth } from "../context/AuthContext";

const TRUST_STRIP = [
  { Icon: ShieldIcon, label: "Anonyme & confidentiel" },
  { Icon: CheckCircleIcon, label: "Professionnels certifiés" },
];

export default function Accueil() {
  const { hasProfile, prenom, logout } = useAuth();

  if (!hasProfile) return <Navigate to="/inscription" replace />;

  return (
    <div className="flex flex-col items-center justify-center flex-1 text-center p-4 sm:p-6">
      <motion.h2
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-2xl font-bold font-serif text-thera-stabilite mb-2"
      >
        Bonjour {prenom}
      </motion.h2>
      <p className="text-thera-stabilite/70 mb-6">Comment veux-tu commencer aujourd'hui ?</p>

      <div className="flex items-center gap-5 mb-10">
        {TRUST_STRIP.map(({ Icon, label }) => (
          <div key={label} className="flex items-center gap-1.5 text-thera-stabilite/45">
            <Icon className="w-3.5 h-3.5" />
            <span className="text-xs font-medium">{label}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 w-full max-w-xl">
        {[
          { to: "/chat", Icon: ChatIcon, title: "Discuter avec Thera", desc: "Un espace pour poser des mots sur ce que tu vis, à ton rythme." },
          { to: "/rdv", Icon: RdvIcon, title: "Prendre rendez-vous", desc: "Passe directement à un échange avec un professionnel, sous 72h." },
        ].map((card, i) => (
          <motion.div
            key={card.to}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.06 }}
          >
            <Link
              to={card.to}
              className="flex flex-col items-start block bg-white border border-thera-stabilite/10 hover:border-thera-energie/40 rounded-2xl p-6 text-left transition-colors shadow-sm hover:shadow-md h-full"
            >
              <div className="w-11 h-11 rounded-xl bg-thera-confiance flex items-center justify-center text-thera-energie mb-4">
                <card.Icon className="w-5 h-5" />
              </div>
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
