import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

export default function GuideSteps({ title, description, steps, onFinish }) {
  const [index, setIndex] = useState(0);
  const isLast = index === steps.length - 1;

  return (
    <div>
      <h3 className="text-2xl font-bold font-serif text-thera-stabilite mb-1">{title}</h3>
      <p className="text-thera-stabilite/60 text-xs mb-6">{description}</p>

      <div className="relative bg-thera-confiance/40 rounded-2xl p-6 mb-6 min-h-[120px] flex items-center justify-center text-center overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.p
            key={index}
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -16 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="text-thera-stabilite font-medium leading-relaxed"
          >
            {steps[index]}
          </motion.p>
        </AnimatePresence>
      </div>

      <div className="flex items-center justify-between gap-3">
        <button
          onClick={() => setIndex((i) => Math.max(0, i - 1))}
          disabled={index === 0}
          className="text-thera-stabilite/70 hover:text-thera-stabilite text-sm font-semibold disabled:opacity-0 disabled:pointer-events-none transition-opacity"
        >
          ← Précédent
        </button>
        <div className="flex gap-1.5">
          {steps.map((_, i) => (
            <motion.span
              key={i}
              animate={{ width: i === index ? 18 : 8, backgroundColor: i === index ? "var(--color-thera-energie)" : "var(--color-thera-stabilite)" }}
              transition={{ duration: 0.2 }}
              className="h-2 rounded-full"
              style={{ opacity: i === index ? 1 : 0.15 }}
            />
          ))}
        </div>
        {isLast ? (
          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={onFinish}
            className="bg-thera-stabilite hover:bg-thera-reflexion text-white px-5 py-2.5 rounded-xl font-semibold text-sm transition-colors"
          >
            Terminer
          </motion.button>
        ) : (
          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={() => setIndex((i) => Math.min(steps.length - 1, i + 1))}
            className="bg-thera-energie hover:bg-[#c26224] text-white px-5 py-2.5 rounded-xl font-semibold text-sm transition-colors"
          >
            Suivant →
          </motion.button>
        )}
      </div>
    </div>
  );
}
