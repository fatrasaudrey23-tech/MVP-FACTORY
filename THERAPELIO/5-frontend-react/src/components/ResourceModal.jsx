export default function ResourceModal({ onClose, children }) {
  return (
    <div
      className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-[2rem] shadow-xl max-w-lg w-full max-h-[85vh] overflow-y-auto p-6 sm:p-8 relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 w-8 h-8 rounded-full bg-thera-confiance hover:bg-thera-stabilite/10 flex items-center justify-center text-thera-stabilite/60 hover:text-thera-stabilite transition-colors"
          aria-label="Fermer"
        >
          ✕
        </button>
        {children}
      </div>
    </div>
  );
}
