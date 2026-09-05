import { useState } from "react";
import BreathingExercise from "../components/BreathingExercise";
import GuideSteps from "../components/GuideSteps";
import { ArrowIcon } from "../components/icons";
import ResourceModal from "../components/ResourceModal";
import { DEFUSION_ARTICLE, ETIREMENTS_STEPS, MEDITATION_STEPS } from "../data/guides";

const CARDS = [
  {
    id: "coherence",
    icon: "🫁",
    title: "Cohérence cardiaque",
    desc: "Exercice de respiration guidé pour réduire instantanément le stress et l'anxiété.",
    cta: "Lancer l'exercice",
  },
  {
    id: "meditation",
    icon: "🎧",
    title: "Méditation express",
    desc: "Un guide pas-à-pas de quelques minutes pour se recentrer avant une réunion ou après un coup de stress.",
    cta: "Suivre le guide",
  },
  {
    id: "etirements",
    icon: "🧘",
    title: "Étirements au bureau",
    desc: "Quelques mouvements simples pour relâcher les tensions physiques accumulées devant l'écran.",
    cta: "Voir les postures",
  },
  {
    id: "defusion",
    icon: "🧭",
    title: "Défusion cognitive",
    desc: "Apprenez à prendre de la distance avec vos pensées parasites grâce aux outils de la méthode ACT.",
    cta: "Lire l'article",
  },
];

export default function Ressources() {
  const [openId, setOpenId] = useState(null);

  return (
    <div className="p-2">
      <p className="text-thera-stabilite/70 mb-8 font-medium">
        Des ressources pratiques et rapides pour vous apaiser au quotidien, accessibles en un clic.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {CARDS.map((card) => (
          <div
            key={card.id}
            onClick={() => setOpenId(card.id)}
            className="bg-white border border-thera-stabilite/10 p-6 rounded-2xl shadow-sm hover:border-thera-energie/30 transition-all group cursor-pointer"
          >
            <div className="w-12 h-12 bg-thera-confiance rounded-xl flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">
              {card.icon}
            </div>
            <h3 className="font-bold text-lg text-thera-stabilite mb-2">{card.title}</h3>
            <p className="text-thera-stabilite/70 text-sm mb-4">{card.desc}</p>
            <span className="text-thera-energie font-bold text-sm flex items-center gap-1 group-hover:translate-x-1 transition-transform">
              {card.cta} <ArrowIcon />
            </span>
          </div>
        ))}
      </div>

      {openId && (
        <ResourceModal onClose={() => setOpenId(null)}>
          {openId === "coherence" && <BreathingExercise />}
          {openId === "meditation" && (
            <GuideSteps
              title="Méditation express"
              description="Guide pas-à-pas, prends le temps qu'il te faut à chaque étape."
              steps={MEDITATION_STEPS}
              onFinish={() => setOpenId(null)}
            />
          )}
          {openId === "etirements" && (
            <GuideSteps
              title="Étirements au bureau"
              description="Fais chaque mouvement en douceur, sans forcer."
              steps={ETIREMENTS_STEPS}
              onFinish={() => setOpenId(null)}
            />
          )}
          {openId === "defusion" && (
            <div>
              <h3 className="text-2xl font-bold font-serif text-thera-stabilite mb-4">Défusion cognitive</h3>
              <div className="text-sm text-thera-stabilite/80 space-y-4 leading-relaxed">
                {DEFUSION_ARTICLE.map((p, i) => (
                  <p key={i} className={p.muted ? "text-thera-stabilite/60 text-xs pt-2" : ""}>
                    {p.lead && <strong className="text-thera-stabilite">{p.lead}</strong>}
                    {p.text}
                  </p>
                ))}
              </div>
            </div>
          )}
        </ResourceModal>
      )}
    </div>
  );
}
