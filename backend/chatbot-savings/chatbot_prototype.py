"""
Chatbot & Savings Recommendation Subsystem - RAG Prototype
Owner: Thiwanka Kaushalya Nagasanga

Prototype of the Retrieval-Augmented Generation flow: given a user question, retrieve
relevant sample transactions, build a grounded prompt, and (optionally) call an LLM API.
The retrieval step here uses simple keyword/date filtering; this will be upgraded to
vector-similarity retrieval once there is enough transaction volume to justify it.

To actually call an LLM, set an API key as an environment variable and install the
OpenAI SDK: pip install openai --break-system-packages
This script runs fully offline (prints the constructed prompt) if no API key is set,
which is enough to test and demonstrate the retrieval + prompt-construction logic.

backend/api/routers/chat.py wires this retrieval/prompt/LLM logic into a real
POST /chat/messages endpoint, swapping SAMPLE_TRANSACTIONS/SAMPLE_BUDGETS for
the current user's real transactions/budgets from the database.
"""

import os
import re
from datetime import datetime

SAMPLE_TRANSACTIONS = [
    {"date": "2026-07-14", "category": "dining", "amount": -125.00, "merchant": "Rustic Kitchen"},
    {"date": "2026-07-11", "category": "dining", "amount": -11.40, "merchant": "Corner Cafe"},
    {"date": "2026-07-08", "category": "dining", "amount": -14.20, "merchant": "Corner Cafe"},
    {"date": "2026-07-05", "category": "dining", "amount": -15.30, "merchant": "Noodle House"},
    {"date": "2026-07-02", "category": "dining", "amount": -12.50, "merchant": "Corner Cafe"},
    {"date": "2026-07-20", "category": "groceries", "amount": -55.80, "merchant": "Woolworths"},
]

SAMPLE_BUDGETS = {
    "dining": 100.00,
    "groceries": 250.00,
}


def retrieve_relevant_transactions(question, transactions=SAMPLE_TRANSACTIONS, known_categories=None):
    """Prototype retrieval: filters by any category name mentioned in the question.
    Falls back to returning the most recent transactions if no category matches.

    `known_categories` defaults to the sample budget categories (unchanged
    standalone behaviour); callers with real data pass in the user's actual
    budget/category names instead."""
    question_lower = question.lower()
    categories_to_match = known_categories if known_categories is not None else SAMPLE_BUDGETS.keys()
    matched_categories = [c for c in categories_to_match if c in question_lower]

    if matched_categories:
        results = [t for t in transactions if t["category"] in matched_categories]
    else:
        results = sorted(transactions, key=lambda t: t["date"], reverse=True)[:5]
    return results


def build_context_block(transactions):
    lines = [f"- {t['date']} | {t['category']} | {t['merchant']} | {t['amount']:.2f}"
             for t in transactions]
    return "\n".join(lines)


def category_totals_for(transactions):
    totals = {}
    for t in transactions:
        totals[t["category"]] = totals.get(t["category"], 0) + t["amount"]
    return totals


def detect_over_budget_categories(category_totals, budgets=SAMPLE_BUDGETS):
    """Returns {category: overspend_amount} for categories where actual spend exceeds
    the recommended budget."""
    over_budget = {}
    for cat, total in category_totals.items():
        budget = budgets.get(cat)
        spent = abs(total)
        if budget is not None and spent > budget:
            over_budget[cat] = round(spent - budget, 2)
    return over_budget


def top_merchant_in_category(transactions, category):
    """Finds the merchant driving the most spend in a category, so suggestions can
    name a specific merchant instead of a generic 'spend less' message."""
    merchant_totals = {}
    merchant_counts = {}
    for t in transactions:
        if t["category"] != category:
            continue
        merchant_totals[t["merchant"]] = merchant_totals.get(t["merchant"], 0) + abs(t["amount"])
        merchant_counts[t["merchant"]] = merchant_counts.get(t["merchant"], 0) + 1

    if not merchant_totals:
        return None
    top_merchant = max(merchant_totals, key=merchant_totals.get)
    return {
        "merchant": top_merchant,
        "total_spent": round(merchant_totals[top_merchant], 2),
        "visit_count": merchant_counts[top_merchant],
    }


def generate_savings_suggestions(transactions, budgets=SAMPLE_BUDGETS):
    """Generates a specific, actionable savings suggestion for each category that is
    over budget - naming the merchant driving the overspend and recommending either
    cutting back on visit frequency or switching to a cheaper alternative, rather than
    a generic 'spend less' message."""
    over_budget = detect_over_budget_categories(category_totals_for(transactions), budgets)

    suggestions = []
    for cat, overspend in over_budget.items():
        top_merchant = top_merchant_in_category(transactions, cat)
        if top_merchant is None:
            suggestions.append(f"You're ${overspend:.2f} over your {cat} budget this month.")
        elif top_merchant["visit_count"] > 1:
            suggestions.append(
                f"You're ${overspend:.2f} over your {cat} budget this month, largely driven by "
                f"{top_merchant['visit_count']} visits to {top_merchant['merchant']} "
                f"(${top_merchant['total_spent']:.2f} total). Consider cutting back to fewer "
                f"visits a week, or switching to a cheaper alternative nearby."
            )
        else:
            suggestions.append(
                f"You're ${overspend:.2f} over your {cat} budget this month, largely driven by "
                f"a single ${top_merchant['total_spent']:.2f} transaction at "
                f"{top_merchant['merchant']}. Worth checking whether that was a one-off or a "
                f"pattern to budget for going forward."
            )
    return suggestions


def build_prompt(question, retrieved, budgets=SAMPLE_BUDGETS):
    context = build_context_block(retrieved)
    category_totals = category_totals_for(retrieved)

    budget_lines = []
    for cat, total in category_totals.items():
        budget = budgets.get(cat)
        if budget:
            budget_lines.append(f"- {cat}: spent {abs(total):.2f} of a {budget:.2f} budget")

    suggestion_lines = generate_savings_suggestions(retrieved, budgets)

    prompt = f"""You are a helpful personal finance assistant. Answer the user's question
using ONLY the transaction data provided below. Be specific and concise, and clearly
frame any suggestion as a suggestion, not financial advice.

User's recent relevant transactions:
{context}

Budget comparison:
{chr(10).join(budget_lines) if budget_lines else "No matching budget data."}

Savings suggestions:
{chr(10).join(f"- {s}" for s in suggestion_lines) if suggestion_lines else "No categories currently over budget."}

User question: {question}
"""
    return prompt


def call_llm(prompt):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[No OPENAI_API_KEY set - printing the constructed prompt instead of "
              "calling the LLM. Set the env var to test a real response.]\n")
        print(prompt)
        return None

    try:
        import openai
    except ImportError:
        raise RuntimeError("Run: pip install openai --break-system-packages")

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def ask(question):
    retrieved = retrieve_relevant_transactions(question)
    prompt = build_prompt(question, retrieved)
    answer = call_llm(prompt)
    if answer:
        print("Assistant:", answer)
    return {"retrieved": retrieved, "prompt": prompt, "answer": answer}


TEST_QUESTIONS = [
    "Why did I overspend on dining this month?",
    "How much did I spend on groceries this month?",
    "Am I over budget on dining?",
    "What can I do to save money this month?",
]


if __name__ == "__main__":
    for test_question in TEST_QUESTIONS:
        print(f"{'=' * 60}\nTest question: {test_question}\n{'=' * 60}")
        ask(test_question)
        print()
