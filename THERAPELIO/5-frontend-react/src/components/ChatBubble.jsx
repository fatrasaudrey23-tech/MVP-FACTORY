import { motion } from "framer-motion";

const bubbleMotion = {
  initial: { opacity: 0, y: 12, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  transition: { duration: 0.25, ease: "easeOut" },
};

export function NetworkErrorBubble({ text }) {
  return (
    <motion.div {...bubbleMotion} className="text-red-500 text-xs text-center py-2 bg-red-50 rounded-xl border border-red-100">
      {text}
    </motion.div>
  );
}

export function UserBubble({ content, time }) {
  return (
    <motion.div {...bubbleMotion} className="flex flex-col items-end gap-1">
      <div className="flex justify-end items-end gap-2">
        <div className="bg-gradient-to-br from-thera-stabilite to-thera-reflexion text-white p-4 rounded-2xl rounded-tr-md max-w-[80%] shadow-md shadow-thera-stabilite/10 text-sm leading-relaxed whitespace-pre-wrap">
          {content}
        </div>
      </div>
      <span className="text-[10px] text-thera-stabilite/40 pr-1">{time}</span>
    </motion.div>
  );
}

export function AssistantBubble({ content, time, isError, isGreeting, prenom }) {
  return (
    <motion.div {...bubbleMotion} className="flex flex-col items-start gap-1">
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
              : "bg-white text-thera-stabilite border border-thera-stabilite/5 shadow-sm"
          } p-4 rounded-2xl rounded-tl-md max-w-[80%] text-sm leading-relaxed whitespace-pre-wrap`}
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
    </motion.div>
  );
}

export function TypingIndicator() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex justify-start items-start gap-3">
      <div className="w-9 h-9 rounded-full bg-thera-stabilite text-white flex items-center justify-center font-bold text-sm shrink-0 shadow-sm">
        T
      </div>
      <div className="bg-white p-4 rounded-2xl rounded-tl-md shadow-sm border border-thera-stabilite/5 flex gap-1.5 items-center">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="w-2 h-2 bg-thera-energie/60 rounded-full"
            animate={{ y: [0, -5, 0] }}
            transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15, ease: "easeInOut" }}
          />
        ))}
      </div>
    </motion.div>
  );
}
