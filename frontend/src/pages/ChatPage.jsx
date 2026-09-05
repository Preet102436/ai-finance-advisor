import { useEffect, useRef, useState } from "react";
import { sendChatMessage } from "../lib/chat";
import SavingsSuggestionsPanel from "../components/SavingsSuggestionsPanel";

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function handleSubmit(e) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || sending) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setQuestion("");
    setSending(true);

    try {
      const result = await sendChatMessage(trimmed);
      setMessages((prev) => [...prev, { role: "assistant", content: result.answer }]);
    } catch (err) {
      const message = err.message || "Something went wrong. Please try asking again.";
      setMessages((prev) => [...prev, { role: "assistant", content: message, isError: true }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Chat</h1>
      </div>

      <div className="chat-layout">
        <div className="chat-panel">
          <div className="chat-messages" role="log" aria-live="polite" aria-label="Conversation">
            {messages.length === 0 && (
              <p className="empty-state">
                Ask about your spending - for example, "Am I over budget on dining?" or "How much
                did I spend on groceries this month?"
              </p>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  "chat-bubble chat-bubble-" + m.role + (m.isError ? " chat-bubble-error" : "")
                }
              >
                <div className="chat-bubble-role">{m.role === "user" ? "You" : "Assistant"}</div>
                <div className="chat-bubble-content">{m.content}</div>
              </div>
            ))}
            {sending && (
              <div className="chat-bubble chat-bubble-assistant chat-bubble-pending">
                <div className="chat-bubble-role">Assistant</div>
                <div className="chat-bubble-content">Thinking...</div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className="chat-input-form" onSubmit={handleSubmit}>
            <label htmlFor="chat-question" className="sr-only">
              Type a question about your spending
            </label>
            <input
              id="chat-question"
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about your spending..."
              disabled={sending}
            />
            <button type="submit" className="btn" disabled={sending || !question.trim()}>
              {sending ? "Sending..." : "Send"}
            </button>
          </form>
        </div>

        <aside className="chat-sidebar">
          <SavingsSuggestionsPanel />
        </aside>
      </div>
    </div>
  );
}
