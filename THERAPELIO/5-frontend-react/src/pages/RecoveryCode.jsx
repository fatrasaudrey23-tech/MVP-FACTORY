import { motion } from "framer-motion";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

export default function RecoveryCode() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state;

  if (!state?.code) return <Navigate to="/" replace />;

  return (
    <div className="flex flex-col items-center justify-center flex-1 text-center p-4 sm:p-6">
      <motion.div
        initial={{ scale: 0.6, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 18 }}
        className="w-16 h-16 bg-thera-confiance rounded-full flex items-center justify-center text-3xl mb-5"
      >
        🔑
      </motion.div>
      <h2 className="text-2xl font-bold font-serif text-thera-stabilite mb-2">C'est fait, {state.prenom} !</h2>
      <p className="text-thera-stabilite/70 mb-6 max-w-sm">
        Voici ton code personnel. Note-le quelque part : il te permettra de retrouver ton profil si tu changes
        d'appareil ou de navigateur. Il ne sera plus jamais réaffiché.
      </p>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="bg-thera-confiance/60 border-2 border-dashed border-thera-energie/40 rounded-2xl px-8 py-5 mb-6"
      >
        <span className="text-2xl font-bold font-mono tracking-widest text-thera-energie">{state.code}</span>
      </motion.div>
      <motion.button
        whileTap={{ scale: 0.98 }}
        onClick={() => navigate("/", { replace: true })}
        className="w-full max-w-sm bg-thera-energie hover:bg-[#c26224] text-white py-3.5 rounded-xl font-semibold shadow-md transition-colors"
      >
        J'ai noté mon code, continuer
      </motion.button>
    </div>
  );
}
