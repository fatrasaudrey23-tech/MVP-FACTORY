import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Recover() {
  const { recover } = useAuth();
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!code.trim()) return;

    setLoading(true);
    try {
      await recover(code.trim());
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-center justify-center flex-1 text-center p-4 sm:p-6">
      <div className="w-16 h-16 bg-thera-confiance rounded-full flex items-center justify-center text-3xl mb-5">🔑</div>
      <h2 className="text-2xl font-bold font-serif text-thera-stabilite mb-2">Retrouver mon profil</h2>
      <p className="text-thera-stabilite/70 mb-8 max-w-sm">
        Entre le code personnel que tu as reçu lors de ta première connexion.
      </p>

      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-3">
        <input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Code personnel"
          maxLength={10}
          className="w-full p-3.5 rounded-xl border border-thera-stabilite/10 text-sm text-center font-mono tracking-widest uppercase focus:outline-none focus:border-thera-energie"
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-thera-energie hover:bg-[#c26224] text-white py-3.5 rounded-xl font-semibold shadow-md transition-all disabled:opacity-50"
        >
          {loading ? "Un instant..." : "Retrouver mon profil"}
        </button>
      </form>

      {error && <p className="text-xs text-thera-technologie mt-3">{error}</p>}

      <Link to="/inscription" className="text-xs text-thera-stabilite/50 hover:text-thera-stabilite underline mt-6">
        Je n'ai pas encore de profil
      </Link>
    </div>
  );
}
