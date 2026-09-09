import { motion } from "framer-motion";
import { Link, Navigate } from "react-router-dom";
import { BookIcon, CalendarPlusIcon, ChatIcon, CheckCircleIcon, RdvIcon, ShieldIcon } from "../components/icons";
import { useAuth } from "../context/AuthContext";

const TRUST_STRIP = [
  { Icon: ShieldIcon, label: "Anonyme & confidentiel" },
  { Icon: CheckCircleIcon, label: "Professionnels certifiés" },
];

const CARDS = [
  { to: "/chat", Icon: ChatIcon, title: "Discuter avec Thera", desc: "Un espace pour poser des mots sur ce que tu vis, à ton rythme." },
  { to: "/rdv", Icon: RdvIcon, title: "Prendre rendez-vous", desc: "Passe directement à un échange avec un professionnel, sous 72h." },
  { to: "/ressources", Icon: BookIcon, title: "Boîte à outils", desc: "Respiration, méditation, étirements : des exercices rapides à faire seul(e)." },
];

export default function Accueil() {
  const { hasProfile, prenom, logout } = useAuth();

  if (!hasProfile) return <Navigate to="/inscription" replace />;

  return (
    <div className="flex-1 flex flex-col p-2 sm:p-4">
      <motion.h2 initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="text-2xl font-bold font-serif text-thera-stabilite mb-1">
        Bonjour {prenom}
      </motion.h2>
      <p className="text-thera-stabilite/70 mb-4">Comment veux-tu commencer aujourd'hui ?</p>

      <div className="flex items-center gap-5 mb-8">
        {TRUST_STRIP.map(({ Icon, label }) => (
          <div key={label} className="flex items-center gap-1.5 text-thera-stabilite/45">
            <Icon className="w-3.5 h-3.5" />
            <span className="text-xs font-medium">{label}</span>
          </div>
        ))}
      </div>

      {/* Prochain rendez-vous : état honnête tant que le suivi des réservations
          n'est pas relié à un profil (aucune donnée fictive affichée). */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="flex items-center gap-4 bg-thera-confiance/60 border border-thera-stabilite/8 rounded-2xl p-5 mb-6"
      >
        <div className="w-11 h-11 rounded-xl bg-white flex items-center justify-center text-thera-stabilite/40 shrink-0">
          <CalendarPlusIcon className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-thera-stabilite text-sm">Aucun rendez-vous prévu</p>
          <p className="text-thera-stabilite/50 text-xs">Tu peux en planifier un à tout moment, sous 72h.</p>
        </div>
        <Link
          to="/rdv"
          className="shrink-0 text-xs font-bold text-thera-energie bg-white border border-thera-energie/30 hover:border-thera-energie px-3 py-2 rounded-lg transition-colors"
        >
          Planifier
        </Link>
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {CARDS.map((card, i) => (
          <motion.div key={card.to} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.05 }}>
            <Link
              to={card.to}
              className="flex flex-col items-start block bg-white border border-thera-stabilite/10 hover:border-thera-energie/40 rounded-2xl p-5 text-left transition-colors shadow-sm hover:shadow-md h-full"
            >
              <div className="w-10 h-10 rounded-xl bg-thera-confiance flex items-center justify-center text-thera-energie mb-3">
                <card.Icon className="w-4.5 h-4.5" />
              </div>
              <h3 className="font-bold text-thera-stabilite mb-1">{card.title}</h3>
              <p className="text-sm text-thera-stabilite/60">{card.desc}</p>
            </Link>
          </motion.div>
        ))}
      </div>

      <button onClick={logout} className="text-xs text-thera-stabilite/40 hover:text-thera-stabilite/70 underline mt-6 self-center">
        Ce n'est pas toi ? Changer de profil
      </button>
    </div>
  );
}
