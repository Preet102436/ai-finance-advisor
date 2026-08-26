# Chatbot & Savings Recommendation Subsystem — Design Notes

**Owner:** Thiwanka Kaushalya Nagasanga (Conversational Chatbot / Savings Recommendation)
**Status:** RAG architecture defined; prototype retrieval + prompt flow implemented
(see `backend/chatbot-savings/`). Real `POST /chat/messages` now retrieves the
current user's actual transactions/budgets, builds the grounded prompt, and logs
the exchange to `chat_messages` (see `backend/api/routers/chat.py`).

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
- [ ] Replace simple filtering retrieval with vector-similarity retrieval over a larger
      transaction history
- [ ] No `OPENAI_API_KEY` configured in the dev environment, so `/chat/messages` is
      exercised end-to-end but always through `call_llm()`'s offline fallback path
      (returns a preview of the prompt instead of a real model response)
- [ ] `GET /chat/messages` (chat history) still TODO

## Next Steps
- Evaluate prototype responses against a small set of test questions for accuracy and
  tone before Week 9.
- Add guardrails so responses are clearly framed as suggestions, not financial advice.
- Set a real `OPENAI_API_KEY` in a deployed environment and verify actual model output.
