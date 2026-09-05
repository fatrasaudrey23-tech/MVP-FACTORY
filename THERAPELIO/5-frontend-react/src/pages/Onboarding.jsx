import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Onboarding() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [prenom, setPrenom] = useState("");
  const [poste, setPoste] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!code.trim() || !prenom.trim()) return;

    setLoading(true);
    try {
      const recoveryCode = await register(code.trim(), prenom.trim(), poste.trim());
      navigate("/inscription/code", { state: { code: recoveryCode, prenom: prenom.trim() } });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-center justify-center flex-1 text-center p-4 sm:p-6">
      <div className="w-16 h-16 bg-thera-confiance rounded-full flex items-center justify-center text-3xl mb-5">👋</div>
      <h2 className="text-2xl font-bold font-serif text-thera-stabilite mb-2">Bienvenue sur Thérapelio</h2>
      <p className="text-thera-stabilite/70 mb-8 max-w-sm">
        Je suis Thera, ton assistant IA pour ta santé mentale au travail. Ton entreprise t'a fourni un code
        d'accès — entre-le pour créer ton profil.
      </p>

      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-3">
        <input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Code entreprise"
          maxLength={30}
          className="w-full p-3.5 rounded-xl border border-thera-stabilite/10 text-sm focus:outline-none focus:border-thera-energie"
        />
        <input
          value={prenom}
          onChange={(e) => setPrenom(e.target.value)}
          placeholder="Ton prénom"
          maxLength={40}
          className="w-full p-3.5 rounded-xl border border-thera-stabilite/10 text-sm focus:outline-none focus:border-thera-energie"
        />
        <input
          value={poste}
          onChange={(e) => setPoste(e.target.value)}
          placeholder="Ton poste (optionnel)"
          maxLength={60}
          className="w-full p-3.5 rounded-xl border border-thera-stabilite/10 text-sm focus:outline-none focus:border-thera-energie"
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-thera-energie hover:bg-[#c26224] text-white py-3.5 rounded-xl font-semibold shadow-md transition-all disabled:opacity-50"
        >
          {loading ? "Un instant..." : "Continuer"}
        </button>
      </form>

      {error && <p className="text-xs text-thera-technologie mt-3">{error}</p>}

      <p className="text-xs text-thera-stabilite/40 mt-5 max-w-sm">
        Aucune information personnelle (email, nom de famille) n'est demandée : ton profil reste pseudonyme.
      </p>

      <Link to="/recuperer" className="text-xs text-thera-stabilite/50 hover:text-thera-stabilite underline mt-4">
        J'ai déjà un profil
      </Link>
    </div>
  );
}
