import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { sendChatMessage } from "../api/client";
import { AssistantBubble, NetworkErrorBubble, TypingIndicator, UserBubble } from "../components/ChatBubble";
import { useAuth } from "../context/AuthContext";
import { formatTime, generateSessionId } from "../utils/sessionId";

export default function Chat() {
  const { userId, prenom, poste } = useAuth();
  const [sessionId] = useState(generateSessionId);
  const [messages, setMessages] = useState([{ role: "assistant", isGreeting: true, time: formatTime(new Date()) }]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const historyRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (historyRef.current) historyRef.current.scrollTop = historyRef.current.scrollHeight;
  }, [messages, sending]);

  function handleInput(e) {
    setInput(e.target.value);
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 144) + "px";
    }
  }

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    const historyForApi = messages.filter((m) => !m.isGreeting).map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [...prev, { role: "user", content: trimmed, time: formatTime(new Date()) }]);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setSending(true);

    try {
      const result = await sendChatMessage({ message: trimmed, sessionId, history: historyForApi, userId, prenom, poste });
      const isError = result.status === "error";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.reply || "Erreur inconnue.", time: formatTime(new Date()), isError },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "network-error", content: "Impossible de joindre l'assistant (Erreur réseau).", time: formatTime(new Date()) },
      ]);
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-220px)] min-h-[450px]">
      <div ref={historyRef} className="flex-1 overflow-y-auto px-2 py-4 space-y-5 scroll-smooth">
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => {
            if (msg.role === "network-error") return <NetworkErrorBubble key={i} text={msg.content} />;
            if (msg.role === "user") return <UserBubble key={i} content={msg.content} time={msg.time} />;
            return (
              <AssistantBubble
                key={i}
                content={msg.content}
                time={msg.time}
                isError={msg.isError}
                isGreeting={msg.isGreeting}
                prenom={prenom}
              />
            );
          })}
          {sending && <TypingIndicator key="typing" />}
        </AnimatePresence>
      </div>

      <div className="mt-4 px-2">
        <div className="flex gap-2 items-end bg-thera-confiance/50 border border-thera-stabilite/10 rounded-2xl p-1.5 focus-within:border-thera-energie/50 focus-within:bg-white focus-within:shadow-md transition-all">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={sending}
            placeholder="Écrivez votre message..."
            className="flex-1 bg-transparent px-3 py-2.5 focus:outline-none text-sm resize-none max-h-36 disabled:opacity-60"
          />
          <motion.button
            whileTap={{ scale: sending ? 1 : 0.97 }}
            onClick={handleSend}
            disabled={sending}
            className="bg-thera-energie text-white px-6 py-3 rounded-xl font-semibold shadow-sm text-sm shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Envoyer
          </motion.button>
        </div>
      </div>
    </div>
  );
}
