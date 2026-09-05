import { Link } from "react-router-dom";
import { PhoneIcon } from "../components/icons";

export default function Urgence() {
  return (
    <div className="p-8 text-center max-w-lg mx-auto my-auto">
      <div className="w-16 h-16 bg-thera-technologie/10 text-thera-technologie rounded-full flex items-center justify-center mx-auto mb-4">
        <PhoneIcon className="w-7 h-7" />
      </div>
      <h3 className="text-2xl font-bold text-thera-technologie mb-3 font-serif">Tu traverses un moment difficile ?</h3>
      <p className="text-thera-stabilite/80 mb-2 leading-relaxed">
        Le <strong>31 14</strong> est le numéro national de prévention du suicide. C'est gratuit, confidentiel, et des
        professionnels y répondent 24h/24, 7j/7 — pas un robot, pas ton entreprise.
      </p>
      <p className="text-thera-stabilite/50 text-sm mb-6">En cliquant ci-dessous, ton téléphone composera directement ce numéro.</p>
      <a
        href="tel:3114"
        className="inline-block w-full py-4 bg-thera-technologie text-white font-bold text-lg rounded-xl shadow-lg hover:bg-red-600 transition-all mb-4"
      >
        📞 Appeler le 31 14
      </a>
      <Link to="/chat" className="text-thera-stabilite/60 hover:text-thera-stabilite text-sm font-medium underline">
        Tu préfères d'abord en parler à Thera ?
      </Link>
    </div>
  );
}
