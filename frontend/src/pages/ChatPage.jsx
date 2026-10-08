import { useEffect, useRef, useState } from "react";
import { sendChatMessage, rateChatMessage } from "../lib/chat";
import SavingsSuggestionsPanel from "../components/SavingsSuggestionsPanel";

const QUICK_PROMPTS = [
  "Am I over budget this month?",
  "How much did I spend on dining?",
  "What can I do to save money?",
  "What's my balance forecast?",
];

const FOLLOW_UPS = [
  "What's driving this?",
  "How can I reduce this?",
  "Show my budget status",
];

function ChatBubble({ message, onRate, onCopy, copiedId }) {
  const isAssistant = message.role === "assistant" && !message.isError;

  return (
    <div
      className={"chat-bubble chat-bubble-" + message.role + (message.isError ? " chat-bubble-error" : "")}
    >
      <div className="chat-bubble-role">{message.role === "user" ? "You" : "Assistant"}</div>
      <div className="chat-bubble-content">{message.content}</div>
      {isAssistant && (
        <div className="chat-bubble-actions">
          <button
            type="button"
            className="chat-action-btn"
            onClick={() => onCopy(message)}
            title="Copy response"
          >
            {copiedId === message.message_id ? "Copied" : "Copy"}
          </button>
          <button
            type="button"
            className={"chat-action-btn" + (message.rating === "up" ? " chat-action-active" : "")}
            onClick={() => onRate(message, "up")}
            title="Good response"
            aria-label="Rate this response positively"
          >
            👍
          </button>
          <button
            type="button"
            className={"chat-action-btn" + (message.rating === "down" ? " chat-action-active" : "")}
            onClick={() => onRate(message, "down")}
            title="Not helpful"
            aria-label="Rate this response negatively"
          >
            👎
          </button>
        </div>
      )}
    </div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function sendQuestion(text) {
    const trimmed = text.trim();
    if (!trimmed || sending) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setQuestion("");
    setSending(true);

    try {
      const result = await sendChatMessage(trimmed);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.answer, message_id: result.message_id, rating: null },
      ]);
    } catch (err) {
      const message = err.message || "Something went wrong. Please try asking again.";
      setMessages((prev) => [...prev, { role: "assistant", content: message, isError: true }]);
    } finally {
      setSending(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    sendQuestion(question);
  }

  function handleClearChat() {
    setMessages([]);
  }

  async function handleCopy(message) {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedId(message.message_id);
      setTimeout(() => setCopiedId((current) => (current === message.message_id ? null : current)), 1500);
    } catch {
      // Clipboard access can fail (e.g. insecure context, denied permission) -
      // the button simply won't show "Copied", no need to surface an error
      // for a non-critical convenience action.
    }
  }

  async function handleRate(message, rating) {
    const nextRating = message.rating === rating ? null : rating;
    setMessages((prev) =>
      prev.map((m) => (m.message_id === message.message_id ? { ...m, rating: nextRating } : m))
    );
    if (nextRating) {
      try {
        await rateChatMessage(message.message_id, nextRating);
      } catch {
        // Non-critical - if it fails, the next page load just won't remember
        // the rating; no need to interrupt the conversation with an error.
      }
    }
  }

  const lastMessage = messages[messages.length - 1];
  const showFollowUps =
    !sending && lastMessage && lastMessage.role === "assistant" && !lastMessage.isError;

  return (
    <div>
      <div className="page-header">
        <h1>Chat</h1>
        {messages.length > 0 && (
          <button className="btn btn-secondary btn-sm" onClick={handleClearChat}>
            Clear chat
          </button>
        )}
      </div>

      <div className="chat-layout">
        <div className="chat-panel">
          <div className="chat-messages" role="log" aria-live="polite" aria-label="Conversation">
            {messages.length === 0 && (
              <div className="chat-empty-state">
                <div className="chat-empty-icon" aria-hidden="true">
                  💬
                </div>
                <p className="empty-state">
                  Ask about your spending - for example, "Am I over budget on dining?" or "How much
                  did I spend on groceries this month?"
                </p>
                <div className="quick-prompts">
                  {QUICK_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      className="quick-prompt-chip"
                      onClick={() => sendQuestion(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <ChatBubble key={i} message={m} onRate={handleRate} onCopy={handleCopy} copiedId={copiedId} />
            ))}
            {sending && (
              <div className="chat-bubble chat-bubble-assistant chat-bubble-pending">
                <div className="chat-bubble-role">Assistant</div>
                <div className="chat-bubble-content">Thinking...</div>
              </div>
            )}
            {showFollowUps && (
              <div className="quick-prompts follow-up-prompts">
                {FOLLOW_UPS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className="quick-prompt-chip"
                    onClick={() => sendQuestion(prompt)}
                  >
                    {prompt}
                  </button>
                ))}
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
