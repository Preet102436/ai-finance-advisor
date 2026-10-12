import { useEffect, useState } from "react";
import { KNOWLEDGE_QUIZ, KNOWLEDGE_TOPICS, recommendTopics } from "../data/knowledgeHub";
import { fetchFinancialSummary } from "../lib/insights";

export default function KnowledgeHub({ open, onClose, onAskAI }) {
  const [view, setView] = useState("topics");
  const [activeTopic, setActiveTopic] = useState(null);
  const [quizIndex, setQuizIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [score, setScore] = useState(0);
  const [recommendedIds, setRecommendedIds] = useState([]);

  // Recomputed every time the Hub opens, so recommendations stay current
  // with whatever the user's spending looks like right now - rule-based on
  // their real numbers (see recommendTopics), not an LLM call, so it's
  // instant and still correct if the AI/network is unavailable.
  useEffect(() => {
    if (!open) return;
    fetchFinancialSummary()
      .then((summary) => setRecommendedIds(recommendTopics(summary)))
      .catch(() => setRecommendedIds([]));
  }, [open]);

  if (!open) return null;

  function askAIAboutTopic(topic) {
    if (onAskAI && topic.aiPrompt) {
      onAskAI(topic.aiPrompt);
      onClose();
    }
  }

  function openTopic(topic) {
    setActiveTopic(topic);
    setView("article");
  }

  function startQuiz() {
    setQuizIndex(0);
    setScore(0);
    setSelectedAnswer(null);
    setView("quiz");
  }

  function backToTopics() {
    setActiveTopic(null);
    setView("topics");
  }

  function answerQuiz(optionIndex) {
    if (selectedAnswer !== null) return;
    setSelectedAnswer(optionIndex);
    if (optionIndex === KNOWLEDGE_QUIZ[quizIndex].correctIndex) {
      setScore((s) => s + 1);
    }
  }

  function nextQuizQuestion() {
    if (quizIndex + 1 >= KNOWLEDGE_QUIZ.length) {
      setView("results");
      return;
    }
    setQuizIndex((i) => i + 1);
    setSelectedAnswer(null);
  }

  return (
    <div className="knowledge-hub-overlay" role="dialog" aria-modal="true" aria-label="Finance Knowledge Hub">
      <div className="knowledge-hub-panel">
        <div className="knowledge-hub-header">
          <h2>Finance Knowledge Hub</h2>
          <button type="button" className="knowledge-hub-close" onClick={onClose} aria-label="Close">
            &times;
          </button>
        </div>

        {view === "topics" && (
          <div className="knowledge-hub-body">
            <p className="knowledge-hub-intro">
              A few short, practical topics - and a quick quiz to check what stuck.
            </p>
            <div className="knowledge-topic-grid">
              {KNOWLEDGE_TOPICS.map((t) => (
                <button key={t.id} type="button" className="knowledge-topic-card" onClick={() => openTopic(t)}>
                  {recommendedIds.includes(t.id) && (
                    <span className="knowledge-topic-badge">Recommended for you</span>
                  )}
                  <span className="knowledge-topic-icon" aria-hidden="true">{t.icon}</span>
                  <span className="knowledge-topic-title">{t.title}</span>
                  <span className="knowledge-topic-summary">{t.summary}</span>
                </button>
              ))}
            </div>
            <button type="button" className="btn" onClick={startQuiz}>
              Take the quiz
            </button>
          </div>
        )}

        {view === "article" && activeTopic && (
          <div className="knowledge-hub-body">
            <button type="button" className="knowledge-hub-back" onClick={backToTopics}>
              &larr; Back to topics
            </button>
            <h3>
              <span aria-hidden="true">{activeTopic.icon}</span> {activeTopic.title}
            </h3>
            {activeTopic.content.map((para, i) => (
              <p key={i}>{para}</p>
            ))}
            <div className="form-row">
              <button type="button" className="btn" onClick={startQuiz}>
                Take the quiz
              </button>
              {onAskAI && activeTopic.aiPrompt && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => askAIAboutTopic(activeTopic)}
                >
                  {"\u2728"} Ask the AI Advisor about this
                </button>
              )}
            </div>
          </div>
        )}

        {view === "quiz" && (
          <div className="knowledge-hub-body">
            <div className="quiz-progress">
              Question {quizIndex + 1} of {KNOWLEDGE_QUIZ.length}
            </div>
            <h3 className="quiz-question">{KNOWLEDGE_QUIZ[quizIndex].question}</h3>
            <div className="quiz-options">
              {KNOWLEDGE_QUIZ[quizIndex].options.map((option, i) => {
                const isCorrect = i === KNOWLEDGE_QUIZ[quizIndex].correctIndex;
                const isSelected = selectedAnswer === i;
                let className = "quiz-option";
                if (selectedAnswer !== null) {
                  if (isCorrect) className += " quiz-option-correct";
                  else if (isSelected) className += " quiz-option-wrong";
                }
                return (
                  <button
                    key={i}
                    type="button"
                    className={className}
                    onClick={() => answerQuiz(i)}
                    disabled={selectedAnswer !== null}
                  >
                    {option}
                  </button>
                );
              })}
            </div>
            {selectedAnswer !== null && (
              <button type="button" className="btn" onClick={nextQuizQuestion}>
                {quizIndex + 1 >= KNOWLEDGE_QUIZ.length ? "See results" : "Next question"}
              </button>
            )}
          </div>
        )}

        {view === "results" && (
          <div className="knowledge-hub-body">
            <h3>
              You scored {score} / {KNOWLEDGE_QUIZ.length}
            </h3>
            <p>
              {score === KNOWLEDGE_QUIZ.length
                ? "Perfect score - nice work."
                : score >= KNOWLEDGE_QUIZ.length / 2
                ? "Solid result - review the topics above to fill in the gaps."
                : "Worth a re-read of the topics above before trying again."}
            </p>
            <div className="form-row">
              <button type="button" className="btn" onClick={startQuiz}>
                Retake quiz
              </button>
              <button type="button" className="btn btn-secondary" onClick={backToTopics}>
                Back to topics
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
