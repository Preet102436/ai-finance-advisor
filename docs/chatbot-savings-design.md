# Chatbot & Savings Recommendation Subsystem — Design Notes

**Owner:** Thiwanka Kaushalya Nagasanga (Conversational Chatbot / Savings Recommendation)
**Status:** Complete. RAG architecture defined; prototype retrieval + prompt flow
implemented (see `backend/chatbot-savings/`). Real `POST /chat/messages` retrieves
the current user's actual transactions/budgets, builds the grounded prompt, and
logs the exchange to `chat_messages` (see `backend/api/routers/chat.py`). Real
`GET /savings/suggestions` exposes the savings-suggestion logic over real data
(see `backend/api/routers/savings.py`). Both are wired into a real Chat page and
a savings-suggestions panel on the frontend, and have had a usability/
accessibility pass (see Current Progress).

## Purpose
Provide a conversational assistant that answers questions about the user's own finances,
grounded in their real transaction/budget data (Retrieval-Augmented Generation), and
generate practical savings suggestions.

## RAG Flow (prototype stage)
1. User sends a natural-language question (e.g. "Why did I overspend on dining this
   month?").
2. Backend retrieves the most relevant rows for that user from `transactions` and
   `budgets` (prototype uses simple filtering by category/date; a vector-similarity
   retrieval step is planned once the data volume justifies it).
3. Retrieved rows are formatted into a short context block and combined with the user's
   question into a prompt sent to the LLM API.
4. The LLM's response, along with the retrieved context used, is stored in
   `chat_messages` for traceability and future evaluation.

## Savings Recommendation Logic (prototype stage)
- Compare each category's actual spend to its recommended budget (from the Budgeting
  subsystem's `budgets` table).
- For categories consistently over budget, generate a specific suggestion (e.g. reduce
  a specific merchant's frequency, switch to a cheaper alternative) rather than a
  generic "spend less" message.

## Current Progress
- [x] RAG architecture and prompt design documented
- [x] Prototype script (`chatbot_prototype.py`) built: retrieves sample transaction rows
      and sends a grounded prompt to the LLM API, tested against 4 sample questions
      covering category-specific, budget-check, and no-category-mentioned retrieval paths
- [x] Initial savings-suggestion rule set drafted for common overspend categories
- [x] Savings-suggestion logic expanded from detection-only to generating a specific
      suggestion per over-budget category (names the driving merchant and recommends
      cutting visit frequency or switching to a cheaper alternative), fed into the
      constructed prompt
- [x] `POST /chat/messages` implemented in `backend/api/routers/chat.py`: loads the
      current user's real transactions (last 90 days) and most-recent-per-category
      budgets from the database, reuses `chatbot_prototype.py`'s
      `retrieve_relevant_transactions`/`build_prompt`/`call_llm` (both retrieval and
      prompt-building were lightly parameterised to accept real data instead of
      `SAMPLE_TRANSACTIONS`/`SAMPLE_BUDGETS`, with those still the defaults so the
      script's standalone/offline behaviour is unchanged), and logs both the
      question and the answer - with the retrieved context attached to the
      assistant's row - into `chat_messages`
- [x] Integration test (`backend/api/test_chat.py`, pytest) covering the full flow
      against a real user/account/transactions/budget, asserting the retrieved
      context is the real data and that sample data never leaks into it
- [x] `generate_savings_suggestions()` split into a structured
      `generate_savings_suggestions_detailed()` (returns category, overspend,
      driving merchant + visit count, and the suggestion sentence per over-budget
      category) with the original string-list function now a thin wrapper over it,
      so `build_prompt()`/`/chat/messages` are unaffected
- [x] `GET /savings/suggestions` implemented in `backend/api/routers/savings.py`:
      compares the current user's real this-month spend per category (via the new
      shared `backend/api/finance_data.py` loaders, also now used by
      `/chat/messages`) against their most recent budget, and returns a suggestion
      per over-budget category naming the category and the merchant/visit-count
      driving it. Covered by `backend/api/test_savings.py` (names the right
      merchant/visit count; categories under budget are correctly not suggested)
- [x] Chat page built on the frontend (`frontend/src/pages/ChatPage.jsx`): a
      scrollable message list and input calling `POST /chat/messages`
      (conversation is client-side state only, since there's no chat-history GET
      yet). A reusable `SavingsSuggestionsPanel` (`frontend/src/components/`)
      calls `GET /savings/suggestions` and is shown both in the Chat page's
      sidebar and on the Dashboard
- [x] Usability/accessibility pass on the Chat, Login, and Register pages (this
      subsystem's own UI), checked and fixed against three criteria:
      - **Plain-language copy:** `/chat/messages`' no-real-answer fallback used to
        show the raw LLM prompt verbatim, plus jargon like "API key"/"LLM
        response"/"model returned an empty reply" - a real problem, since a real
        `OPENAI_API_KEY` is set locally and the model reliably returns empty
        content here (see below), so every user was seeing this. Rewritten to a
        plain sentence built from the already-human-readable `retrieved_context`
        (or a plain "no transaction history yet, try syncing" message when even
        that's empty) - never the raw prompt. Login/Register/suggestion copy was
        already jargon-free.
      - **Loading and error states:** confirmed present on every async action
        (submitting/sending/loading flags with matching button-text and disabled
        states); added `disabled={submitting}` to the Login/Register input
        fields to match the Chat page's existing pattern; removed a redundant
        second error banner on the Chat page in favour of one clear message
        surfaced where the user is looking (the reply bubble); fixed
        `apiClient.js` to format FastAPI's list-of-objects validation-error
        shape into readable text instead of risking an unreadable
        "[object Object]" message.
      - **Accessibility:** computed contrast on the chat bubbles' role labels
        ("YOU"/"ASSISTANT") - both failed WCAG AA for text this size (~3.15:1 and
        ~3.58:1 against a 4.5:1 requirement) and were fixed to clear it (~7:1 and
        ~5.1:1). Added a screen-reader-only `<label>` (new `.sr-only` utility) for
        the chat input, which previously relied on a placeholder alone. Added
        `role="log"`/`aria-live="polite"` to the message list so new replies are
        announced. Confirmed keyboard-only operation end-to-end (Tab to a field,
        type, Enter submits) on Register, Login, and the chat input - Login/
        Register's form fields were already correctly labelled via the
        wrapping-`<label>` pattern.
- [ ] Replace simple filtering retrieval with vector-similarity retrieval over a larger
      transaction history
- [ ] The real `OPENAI_API_KEY` set locally surfaced two real bugs: `call_llm()`
      passed `max_tokens` (fixed - the API now requires `max_completion_tokens`
      for this model), and the model still returns an *empty* response for our
      prompt even after that fix (root cause unknown - needs a maintainer who can
      spend real API credits investigating it). `/chat/messages` degrades
      gracefully either way via the plain-language fallback above
- [ ] `GET /chat/messages` (chat history) still TODO
- [ ] `/savings/suggestions` is read-only (no `savings_goals` table exists yet);
      goal-setting (`GET`/`POST /savings/goals`) still TODO

## Next Steps
- Evaluate prototype responses against a small set of test questions for accuracy and
  tone before Week 9.
- Add guardrails so responses are clearly framed as suggestions, not financial advice.
- Investigate the empty-response issue from the real `gpt-5` model (see above).
