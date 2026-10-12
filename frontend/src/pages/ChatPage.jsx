import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { sendChatMessage } from "../lib/chat";
import SavingsSuggestionsPanel from "../components/SavingsSuggestionsPanel";
import MoneyRadarPanel from "../components/MoneyRadarPanel";
import FinancialSnapshotBar from "../components/FinancialSnapshotBar";
import KnowledgeHub from "../components/KnowledgeHub";

const DEFAULT_PROMPTS = [
  "Analyse my spending",
  "How can I save more?",
  "Create a budget for next month",
  "Where am I spending too much?",
];

function Avatar({ role }) {
  return (
    <div className={"chat-avatar chat-avatar-" + role} aria-hidden="true">
      {role === "user" ? "Y" : "A"}
    </div>
  );
}

function MessageControls({ message, onCopy, onFeedback, onRegenerate }) {
  return (
    <div className="chat-message-controls">
      <button type="button" className="chat-control-btn" onClick={() => onCopy(message.content)} title="Copy">
        Copy
      </button>
      {message.canRegenerate && (
        <button type="button" className="chat-control-btn" onClick={onRegenerate} title="Regenerate">
          Regenerate
        </button>
      )}
      <span className="chat-control-divider" aria-hidden="true" />
      <button
        type="button"
        className={"chat-control-btn chat-feedback-btn" + (message.feedback === "up" ? " chat-feedback-active" : "")}
        onClick={() => onFeedback("up")}
        aria-label="Good response"
        title="Good response"
      >
        {"👍"}
      </button>
      <button
        type="button"
        className={"chat-control-btn chat-feedback-btn" + (message.feedback === "down" ? " chat-feedback-active" : "")}
        onClick={() => onFeedback("down")}
        aria-label="Not helpful"
        title="Not helpful"
      >
        {"👎"}
      </button>
    </div>
  );
}

export default function ChatPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [openSourcesFor, setOpenSourcesFor] = useState(null);
  const [showKnowledgeHub, setShowKnowledgeHub] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const messagesEndRef = useRef(null);
  const prefilledRef = useRef(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  // A "Ask AI about this transaction" link from the Transactions page, or a
  // Money Radar / AI Insights card, lands here with ?q=... - ask it once on
  // arrival instead of making the user retype it.
  useEffect(() => {
    if (prefilledRef.current) return;
    const prefilled = searchParams.get("q");
    if (prefilled) {
      prefilledRef.current = true;
      ask(prefilled);
      setSearchParams((params) => {
        params.delete("q");
        return params;
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  async function ask(trimmed) {
    if (!trimmed || sending) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: trimmed },
    ]);
    setQuestion("");
    setSending(true);

    try {
      const result = await sendChatMessage(trimmed);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.answer,
          retrievedContext: result.retrieved_context,
          sources: result.sources || [],
          suggestedFollowups: result.suggested_followups || [],
          canRegenerate: true,
          sourceQuestion: trimmed,
          feedback: null,
        },
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
    ask(question.trim());
  }

  function handlePromptClick(prompt) {
    ask(prompt);
  }

  function handleRegenerate(sourceQuestion) {
    ask(sourceQuestion);
  }

  function handleCopy(content, index) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(content).catch(() => {});
    }
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex((i) => (i === index ? null : i)), 1500);
  }

  function handleFeedback(index, value) {
    setMessages((prev) =>
      prev.map((m, i) => (i === index ? { ...m, feedback: m.feedback === value ? null : value } : m))
    );
  }

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant" && !m.isError);
  const quickPrompts =
    lastAssistant && lastAssistant.suggestedFollowups && lastAssistant.suggestedFollowups.length > 0
      ? lastAssistant.suggestedFollowups
      : DEFAULT_PROMPTS;

  return (
    <div>
      <div className="page-header">
        <h1>AI Advisor</h1>
        <div className="page-header-actions">
          <button type="button" className="btn btn-secondary" onClick={() => setShowKnowledgeHub(true)}>
            Finance Knowledge Hub
          </button>
        </div>
      </div>

      <FinancialSnapshotBar />

      <section className="dashboard-section">
        <h2 className="section-title">Quick actions</h2>
        <div className="quick-action-tiles">
          <button type="button" className="quick-action-tile" onClick={() => ask("Analyse my spending")}>
            <span className="quick-action-icon quick-action-icon-blue" aria-hidden="true">
              {"\uD83D\uDCCA"}
            </span>
            <span>
              <span className="quick-action-title">Analyse spending</span>
              <span className="quick-action-subtitle">Get a complete overview</span>
            </span>
          </button>
          <button type="button" className="quick-action-tile" onClick={() => ask("Where am I spending too much right now?")}>
            <span className="quick-action-icon quick-action-icon-red" aria-hidden="true">
              {"\uD83D\uDCE1"}
            </span>
            <span>
              <span className="quick-action-title">Money Radar</span>
              <span className="quick-action-subtitle">Find unusual activity</span>
            </span>
          </button>
          <button type="button" className="quick-action-tile" onClick={() => ask("How can I save more?")}>
            <span className="quick-action-icon quick-action-icon-amber" aria-hidden="true">
              {"\uD83D\uDCA1"}
            </span>
            <span>
              <span className="quick-action-title">Find savings</span>
              <span className="quick-action-subtitle">Discover saving opportunities</span>
            </span>
          </button>
          <button type="button" className="quick-action-tile" onClick={() => setShowKnowledgeHub(true)}>
            <span className="quick-action-icon quick-action-icon-purple" aria-hidden="true">
              {"\uD83C\uDF93"}
            </span>
            <span>
              <span className="quick-action-title">Learn finance</span>
              <span className="quick-action-subtitle">Get financial knowledge</span>
            </span>
          </button>
          <button
            type="button"
            className="quick-action-tile"
            onClick={() => navigate("/ai-insights")}
          >
            <span className="quick-action-icon quick-action-icon-green" aria-hidden="true">
              {"\u2728"}
            </span>
            <span>
              <span className="quick-action-title">AI Statement Insights</span>
              <span className="quick-action-subtitle">Analyse any period with AI</span>
            </span>
          </button>
        </div>
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Money Radar</h2>
        <MoneyRadarPanel onAskAI={ask} />
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Ask the AI Advisor</h2>

        <div className="chat-layout">
          <div className="chat-panel">
            <div className="chat-panel-header">
              <div className="chat-avatar chat-avatar-assistant" aria-hidden="true">A</div>
              <div>
                <div className="chat-panel-title">AI Finance Assistant</div>
                <div className="chat-panel-subtitle">Grounded in your real income, expenses and budgets</div>
              </div>
            </div>

            <div className="chat-messages" role="log" aria-live="polite" aria-label="Conversation">
              {messages.length === 0 && (
                <p className="empty-state">
                  Ask about your spending - for example, "How can I save more?", "Where am I
                  spending too much?", "Can I afford a $200 purchase?", or "Give me a monthly
                  saving plan".
                </p>
              )}
              {messages.map((m, i) => (
                <div key={i} className={"chat-row chat-row-" + m.role}>
                  <Avatar role={m.role} />
                  <div
                    className={
                      "chat-bubble chat-bubble-" + m.role + (m.isError ? " chat-bubble-error" : "")
                    }
                  >
                    <div className="chat-bubble-role">{m.role === "user" ? "You" : "Assistant"}</div>
                    <div className="chat-bubble-content">{m.content}</div>

                    {m.sources && m.sources.length > 0 && (
                      <>
                        <button
                          type="button"
                          className="chat-context-toggle"
                          onClick={() => setOpenSourcesFor(openSourcesFor === i ? null : i)}
                        >
                          {"📚"} {openSourcesFor === i ? "Hide sources" : `Sources used (${m.sources.length})`}
                        </button>
                        {openSourcesFor === i && (
                          <ol className="chat-sources-list">
                            {m.sources.map((s, si) => (
                              <li key={si}>{s}</li>
                            ))}
                          </ol>
                        )}
                      </>
                    )}

                    {m.role === "assistant" && !m.isError && (
                      <MessageControls
                        message={m}
                        onCopy={(content) => handleCopy(content, i)}
                        onFeedback={(value) => handleFeedback(i, value)}
                        onRegenerate={() => handleRegenerate(m.sourceQuestion)}
                      />
                    )}
                    {copiedIndex === i && <span className="chat-copied-hint">Copied</span>}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="chat-row chat-row-assistant">
                  <Avatar role="assistant" />
                  <div className="chat-bubble chat-bubble-assistant chat-bubble-pending">
                    <div className="chat-bubble-role">Assistant</div>
                    <div className="chat-bubble-content chat-typing">
                      <span></span><span></span><span></span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="chat-quick-prompts">
              {quickPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="chat-quick-prompt"
                  onClick={() => handlePromptClick(prompt)}
                  disabled={sending}
                >
                  {prompt}
                </button>
              ))}
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
            <SavingsSuggestionsPanel onAskAI={ask} title="AI Insights" />
          </aside>
        </div>
      </section>

      <KnowledgeHub open={showKnowledgeHub} onClose={() => setShowKnowledgeHub(false)} onAskAI={ask} />
    </div>
  );
}
