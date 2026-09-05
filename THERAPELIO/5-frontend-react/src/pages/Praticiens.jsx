import { useState } from "react";
import { createBooking, fetchSlots } from "../api/client";

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
      <p className="text-thera-stabilite/70 mb-8 font-medium">Sélectionnez un praticien pour planifier une consultation confidentielle.</p>
      <div className="bg-white border border-thera-stabilite/10 p-6 rounded-2xl shadow-sm max-w-xl">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 bg-thera-confiance rounded-full flex items-center justify-center text-3xl border border-thera-stabilite/5">
            👩‍⚕️
          </div>
          <div>
            <h3 className="font-bold text-lg text-thera-stabilite">Dr. Sarah Lemoine</h3>
            <p className="text-thera-energie font-medium text-sm">Psychologue du travail & QVT</p>
          </div>
        </div>

        {step === "idle" && (
          <button
            onClick={loadSlots}
            className="w-full py-3 bg-thera-stabilite hover:bg-thera-reflexion text-white rounded-xl font-semibold transition-all shadow-sm"
          >
            Voir les disponibilités (72h)
          </button>
        )}

        {step === "loading" && (
          <div className="text-thera-energie animate-pulse text-center py-4 font-medium">Recherche des créneaux en cours...</div>
        )}

        {step === "slots" &&
          (dates.length === 0 ? (
            <div className="text-center py-4 text-thera-stabilite/70">Aucune disponibilité sur les prochains jours.</div>
          ) : (
            <div className="grid grid-cols-2 gap-2 mt-3 max-h-60 overflow-y-auto p-1">
              {dates.flatMap((date) =>
                slotsByDate[date].map((slot) => {
                  const time = new Date(slot.time).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
                  const day = new Date(slot.time).toLocaleDateString("fr-FR", { weekday: "short", day: "numeric" });
                  return (
                    <button
                      key={slot.time}
                      onClick={() => pickSlot(slot.time)}
                      className="py-2.5 px-3 bg-thera-confiance border border-thera-stabilite/10 rounded-xl hover:border-thera-energie hover:bg-white transition text-xs font-bold text-thera-stabilite flex items-center justify-between"
                    >
                      <span>{day}</span> <span className="text-thera-energie font-extrabold">{time}</span>
                    </button>
                  );
                })
              )}
            </div>
          ))}

        {(step === "confirm" || step === "booking") && selectedSlot && (
          <div className="mt-4 p-5 bg-thera-confiance/30 border border-thera-stabilite/10 rounded-xl shadow-inner">
            <p className="font-bold text-thera-stabilite mb-1">Confirmer la réservation</p>
            <p className="text-sm text-thera-energie font-semibold mb-4">
              📅{" "}
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
              <button
                onClick={confirmBooking}
                disabled={step === "booking"}
                className="flex-1 bg-thera-stabilite hover:bg-thera-reflexion text-white py-3 rounded-xl font-bold text-sm transition-all shadow-sm disabled:opacity-60"
              >
                {step === "booking" ? "Réservation en cours..." : "Valider le RDV"}
              </button>
              <button
                onClick={loadSlots}
                className="flex-1 bg-white border border-thera-stabilite/10 hover:bg-gray-50 text-thera-stabilite py-3 rounded-xl font-bold text-sm transition-all"
              >
                Annuler
              </button>
            </div>
          </div>
        )}

        {step === "success" && (
          <div className="mt-4 p-6 bg-green-50 border border-green-200 rounded-xl text-center">
            <div className="text-3xl mb-2">✅</div>
            <p className="font-bold text-green-800 mb-2">Rendez-vous confirmé pour {name} !</p>
            <p className="text-sm text-green-700">
              Le lien de la visioconférence a été envoyé à <b>{email}</b>.
            </p>
          </div>
        )}

        {step === "error" && <div className="text-red-500 font-bold text-center mt-4">❌ {errorMsg}</div>}
      </div>
    </div>
  );
}
