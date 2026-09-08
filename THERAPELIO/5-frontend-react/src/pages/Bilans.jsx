import { ChartIcon } from "../components/icons";

export default function Bilans() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
      <div className="w-14 h-14 bg-thera-confiance rounded-2xl flex items-center justify-center text-thera-stabilite/40 mb-4">
        <ChartIcon className="w-6 h-6" />
      </div>
      <p className="text-thera-stabilite font-semibold mb-1">Bientôt disponible</p>
      <p className="text-thera-stabilite/50 text-sm max-w-xs">
        Le suivi de ton état de forme et l'historique de tes échanges arriveront dans une prochaine version.
      </p>
    </div>
  );
}
