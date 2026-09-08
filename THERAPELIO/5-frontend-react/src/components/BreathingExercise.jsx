import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

export default function BreathingExercise() {
  const [running, setRunning] = useState(false);
  const [phase, setPhase] = useState("ready"); // ready | inspire | expire
  const [cycles, setCycles] = useState(0);
  const timerRef = useRef(null);
  const activeRef = useRef(false);

  useEffect(
    () => () => {
      activeRef.current = false;
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    []
  );

  function runCycle() {
    setPhase("inspire");
    timerRef.current = setTimeout(() => {
      if (!activeRef.current) return;
      setPhase("expire");
      timerRef.current = setTimeout(() => {
        if (!activeRef.current) return;
        setCycles((c) => c + 1);
        runCycle();
      }, 6000);
    }, 4000);
  }

  function start() {
    activeRef.current = true;
    setRunning(true);
    setCycles(0);
    runCycle();
  }

  function stop() {
    activeRef.current = false;
    setRunning(false);
    if (timerRef.current) clearTimeout(timerRef.current);
    setPhase("ready");
  }

  const scale = phase === "inspire" ? 1.55 : 1;
  const duration = phase === "inspire" ? 4 : phase === "expire" ? 6 : 0.5;
  const label = phase === "ready" ? "Prêt ?" : phase === "inspire" ? "Inspire..." : "Expire...";

  return (
    <div className="text-center">
      <h3 className="text-2xl font-bold font-serif text-thera-stabilite mb-2">Cohérence cardiaque</h3>
      <p className="text-thera-stabilite/70 text-sm mb-8">
        Suis le cercle : inspire quand il grandit, expire quand il rétrécit. Arrête quand tu veux.
      </p>
      <div className="flex items-center justify-center h-56 mb-6">
        <motion.div
          animate={{ scale }}
          transition={{ duration, ease: "easeInOut" }}
          className="w-28 h-28 rounded-full bg-thera-confiance border-2 border-thera-energie flex items-center justify-center"
        >
          <span className="font-bold text-thera-energie text-sm">{label}</span>
        </motion.div>
      </div>
      <p className="text-xs text-thera-stabilite/50 mb-4">{cycles} cycle(s) effectué(s)</p>
      <motion.button
        whileTap={{ scale: 0.97 }}
        onClick={running ? stop : start}
        className="bg-thera-energie hover:bg-[#c26224] text-white px-6 py-3 rounded-xl font-semibold shadow-sm transition-colors"
      >
        {running ? "Arrêter" : "Commencer"}
      </motion.button>
    </div>
  );
}
