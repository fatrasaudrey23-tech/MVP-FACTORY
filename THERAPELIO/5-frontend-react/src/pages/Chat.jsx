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
        {sending && <TypingIndicator />}
      </div>

      <div className="mt-4 pt-4 border-t border-thera-stabilite/10 px-2 flex gap-3 items-end">
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={sending}
          placeholder="Écrivez votre message..."
          className="flex-1 bg-thera-confiance/40 border border-thera-stabilite/10 p-3.5 rounded-xl focus:outline-none focus:border-thera-energie focus:bg-white transition-all text-sm resize-none max-h-36 disabled:opacity-60"
        />
        <button
          onClick={handleSend}
          disabled={sending}
          className="bg-thera-energie hover:bg-[#c26224] text-white px-6 py-3.5 rounded-xl font-semibold shadow-md hover:-translate-y-0.5 transition-all text-sm shrink-0 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
        >
          Envoyer
        </button>
      </div>
    </div>
  );
}
