import { useState } from "react";

export default function GuideSteps({ title, description, steps, onFinish }) {
  const [index, setIndex] = useState(0);
  const isLast = index === steps.length - 1;

  return (
    <div>
      <h3 className="text-2xl font-bold font-serif text-thera-stabilite mb-1">{title}</h3>
      <p className="text-thera-stabilite/60 text-xs mb-6">{description}</p>
      <div className="bg-thera-confiance/40 rounded-2xl p-6 mb-6 min-h-[120px] flex items-center justify-center text-center">
        <p className="text-thera-stabilite font-medium leading-relaxed">{steps[index]}</p>
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
            <span key={i} className={`w-2 h-2 rounded-full ${i === index ? "bg-thera-energie" : "bg-thera-stabilite/15"}`} />
          ))}
        </div>
        {isLast ? (
          <button
            onClick={onFinish}
            className="bg-thera-stabilite hover:bg-thera-reflexion text-white px-5 py-2.5 rounded-xl font-semibold text-sm transition-all"
          >
            Terminer
          </button>
        ) : (
          <button
            onClick={() => setIndex((i) => Math.min(steps.length - 1, i + 1))}
            className="bg-thera-energie hover:bg-[#c26224] text-white px-5 py-2.5 rounded-xl font-semibold text-sm transition-all"
          >
            Suivant →
          </button>
        )}
      </div>
    </div>
  );
}
