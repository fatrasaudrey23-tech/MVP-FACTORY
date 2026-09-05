export function NetworkErrorBubble({ text }) {
  return (
    <div className="text-red-500 text-xs text-center py-2 bg-red-50 rounded-xl border border-red-100">{text}</div>
  );
}

export function UserBubble({ content, time }) {
  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex justify-end items-end gap-2">
        <div className="bg-thera-stabilite text-white p-4 rounded-2xl rounded-tr-none max-w-[80%] shadow-sm text-sm leading-relaxed whitespace-pre-wrap">
          {content}
        </div>
      </div>
      <span className="text-[10px] text-thera-stabilite/40 pr-1">{time}</span>
    </div>
  );
}

export function AssistantBubble({ content, time, isError, isGreeting, prenom }) {
  return (
    <div className="flex flex-col items-start gap-1">
      <div className="flex justify-start items-start gap-3">
        <div
          className={`w-9 h-9 rounded-full ${
            isError ? "bg-thera-technologie" : "bg-thera-stabilite"
          } text-white flex items-center justify-center font-bold text-sm shrink-0 shadow-sm`}
        >
          T
        </div>
        <div
          className={`${
            isError
              ? "bg-red-50 text-thera-technologie border border-thera-technologie/20"
              : "bg-thera-confiance text-thera-stabilite border border-thera-stabilite/5"
          } p-4 rounded-2xl rounded-tl-none max-w-[80%] shadow-sm text-sm leading-relaxed whitespace-pre-wrap`}
        >
          {isGreeting ? (
            <>
              <p className="font-bold mb-1">{prenom ? `Bonjour ${prenom} 👋` : "Bonjour 👋"}</p>
              <p>Je suis Thera, ton assistant IA pour ta santé mentale au travail. En quoi puis-je t'accompagner aujourd'hui ?</p>
            </>
          ) : (
            content
          )}
        </div>
      </div>
      <span className="text-[10px] text-thera-stabilite/40 pl-12">{time}</span>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex justify-start items-start gap-3">
      <div className="w-9 h-9 rounded-full bg-thera-stabilite text-white flex items-center justify-center font-bold text-sm shrink-0 shadow-sm">
        T
      </div>
      <div className="bg-thera-confiance p-4 rounded-2xl rounded-tl-none shadow-sm border border-thera-stabilite/5 flex gap-1.5 items-center">
        <span className="w-2 h-2 bg-thera-stabilite/40 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
        <span className="w-2 h-2 bg-thera-stabilite/40 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
        <span className="w-2 h-2 bg-thera-stabilite/40 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
      </div>
    </div>
  );
}
