import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { createBooking, fetchSlots } from "../api/client";
import { BadgeIcon, CheckCircleIcon, ClockIcon } from "../components/icons";

const EVENT_TYPE_ID = 6851496; // Identifiant fonctionnel du compte Cal.com

export default function Praticiens() {
  const [step, setStep] = useState("idle"); // idle | loading | slots | confirm | booking | success | error
  const [slotsByDate, setSlotsByDate] = useState({});
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  async function loadSlots() {
    setStep("loading");
    try {
      const { ok, data } = await fetchSlots(EVENT_TYPE_ID);
      if (ok && data?.data?.slots) {
        setSlotsByDate(data.data.slots);
        setStep("slots");
      } else {
        setErrorMsg("Erreur lors de la lecture des créneaux.");
        setStep("error");
      }
    } catch {
      setErrorMsg("Erreur de connexion au serveur de réservation.");
      setStep("error");
    }
  }

  function pickSlot(time) {
    setSelectedSlot(time);
    setStep("confirm");
  }

  async function confirmBooking() {
    if (!name.trim() || !email.trim()) {
      alert("Merci de remplir votre prénom et votre e-mail.");
      return;
    }
    setStep("booking");
    try {
      const { ok } = await createBooking({ eventTypeId: EVENT_TYPE_ID, start: selectedSlot, name: name.trim(), email: email.trim() });
      if (ok) {
        setStep("success");
      } else {
        setErrorMsg("Le créneau n'est plus disponible ou une erreur est survenue.");
        setStep("error");
      }
    } catch {
      setErrorMsg("Erreur réseau lors de la réservation.");
      setStep("error");
    }
  }

  const dates = Object.keys(slotsByDate);

  return (
    <div className="p-2">
      <div className="flex items-center justify-between mb-6">
        <p className="text-thera-stabilite/70 font-medium">Sélectionnez un praticien pour planifier une consultation confidentielle.</p>
        <span className="shrink-0 text-xs font-bold text-thera-stabilite/40 bg-thera-confiance px-2.5 py-1 rounded-full">1 praticien disponible</span>
      </div>

      <div className="bg-white border border-thera-stabilite/10 rounded-2xl shadow-sm max-w-2xl overflow-hidden">
        <div className="p-6 border-b border-thera-stabilite/8">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 bg-thera-confiance rounded-full flex items-center justify-center text-2xl font-bold text-thera-stabilite border border-thera-stabilite/5 shrink-0">
              SL
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-bold text-lg text-thera-stabilite">Dr. Sarah Lemoine</h3>
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-thera-energie bg-thera-energie/10 px-2 py-0.5 rounded-full">
                  <CheckCircleIcon className="w-3 h-3" /> Vérifié
                </span>
              </div>
              <p className="text-thera-energie font-medium text-sm mt-0.5">Psychologue du travail & QVT</p>
              <div className="flex items-center gap-1.5 text-thera-stabilite/50 mt-2">
                <BadgeIcon className="w-3.5 h-3.5" />
                <span className="text-xs">Psychologue clinicienne diplômée</span>
              </div>
            </div>
          </div>
        </div>

        <div className="p-6">
          {step === "idle" && (
            <motion.button
              whileTap={{ scale: 0.98 }}
              onClick={loadSlots}
              className="w-full py-3 bg-thera-stabilite hover:bg-thera-reflexion text-white rounded-xl font-semibold transition-colors shadow-sm flex items-center justify-center gap-2"
            >
              <ClockIcon className="w-4 h-4" /> Voir les disponibilités (72h)
            </motion.button>
          )}

          {step === "loading" && (
            <div className="text-thera-energie animate-pulse text-center py-4 font-medium">Recherche des créneaux en cours...</div>
          )}

          {step === "slots" &&
            (dates.length === 0 ? (
              <div className="text-center py-4 text-thera-stabilite/70">Aucune disponibilité sur les prochains jours.</div>
            ) : (
              <div className="space-y-4 max-h-72 overflow-y-auto pr-1">
                {dates.map((date, di) => (
                  <div key={date}>
                    <p className="text-xs font-bold uppercase tracking-wide text-thera-stabilite/40 mb-2">
                      {new Date(slotsByDate[date][0].time).toLocaleDateString("fr-FR", {
                        weekday: "long",
                        day: "numeric",
                        month: "long",
                      })}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {slotsByDate[date].map((slot, i) => {
                        const time = new Date(slot.time).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
                        return (
                          <motion.button
                            key={slot.time}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: Math.min((di * 4 + i) * 0.02, 0.3) }}
                            whileTap={{ scale: 0.96 }}
                            onClick={() => pickSlot(slot.time)}
                            className="py-2 px-4 bg-thera-confiance border border-thera-stabilite/10 rounded-lg hover:border-thera-energie hover:bg-white transition-colors text-sm font-bold text-thera-stabilite"
                          >
                            {time}
                          </motion.button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            ))}

          <AnimatePresence>
            {(step === "confirm" || step === "booking") && selectedSlot && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-4 p-5 bg-thera-confiance/60 border border-thera-stabilite/10 rounded-xl overflow-hidden"
              >
                <p className="font-bold text-thera-stabilite mb-1">Confirmer la réservation</p>
                <p className="text-sm text-thera-energie font-semibold mb-4">
                  {new Date(selectedSlot).toLocaleString("fr-FR", {
                    weekday: "long",
                    day: "numeric",
                    month: "long",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Votre prénom"
                  className="w-full mb-3 p-3 rounded-xl border border-thera-stabilite/10 text-sm focus:outline-none focus:border-thera-energie"
                />
                <input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  type="email"
                  placeholder="Votre e-mail professionnel"
                  className="w-full mb-4 p-3 rounded-xl border border-thera-stabilite/10 text-sm focus:outline-none focus:border-thera-energie"
                />
                <div className="flex gap-2">
                  <motion.button
                    whileTap={{ scale: 0.97 }}
                    onClick={confirmBooking}
                    disabled={step === "booking"}
                    className="flex-1 bg-thera-stabilite hover:bg-thera-reflexion text-white py-3 rounded-xl font-bold text-sm transition-colors shadow-sm disabled:opacity-60"
                  >
                    {step === "booking" ? "Réservation en cours..." : "Valider le RDV"}
                  </motion.button>
                  <button
                    onClick={loadSlots}
                    className="flex-1 bg-white border border-thera-stabilite/10 hover:bg-gray-50 text-thera-stabilite py-3 rounded-xl font-bold text-sm transition-colors"
                  >
                    Annuler
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {step === "success" && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-4 p-6 bg-green-50 border border-green-200 rounded-xl text-center"
            >
              <div className="w-10 h-10 rounded-full bg-green-100 text-green-700 flex items-center justify-center mx-auto mb-3">
                <CheckCircleIcon className="w-5 h-5" />
              </div>
              <p className="font-bold text-green-800 mb-2">Rendez-vous confirmé pour {name} !</p>
              <p className="text-sm text-green-700">
                Le lien de la visioconférence a été envoyé à <b>{email}</b>.
              </p>
            </motion.div>
          )}

          {step === "error" && <div className="text-red-500 font-bold text-center mt-4">{errorMsg}</div>}
        </div>
      </div>
    </div>
  );
}
