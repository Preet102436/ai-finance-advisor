// Static financial-literacy content for the Finance Knowledge Hub + quiz on
// the Chat page. Deliberately plain, offline content (no AI/API calls) so it
// always works regardless of network conditions.

export const KNOWLEDGE_TOPICS = [
  {
    id: "budgeting-basics",
    title: "Budgeting basics",
    icon: "📊",
    summary: "The 50/30/20 rule and how to build a simple monthly budget.",
    aiPrompt: "How does the 50/30/20 budgeting rule apply to my own income and spending?",
    content: [
      "A budget is just a plan for where your money goes before you spend it, instead of finding out afterwards.",
      "A common starting point is the 50/30/20 rule: about 50% of after-tax income on needs (rent, groceries, bills), 30% on wants (dining out, entertainment), and 20% on savings or paying down debt.",
      "You don't need to hit these numbers exactly - they're a sanity check. If \"wants\" is closer to 50%, that's useful to know, not a failure.",
    ],
  },
  {
    id: "emergency-fund",
    title: "Emergency funds",
    icon: "🪑",
    summary: "Why having 3-6 months of expenses saved matters.",
    aiPrompt: "Based on my spending, how big should my emergency fund be, and how long would it take me to build one?",
    content: [
      "An emergency fund is money set aside purely for the unexpected: a lost job, a medical bill, an urgent repair.",
      "A common target is 3-6 months of essential expenses, kept somewhere accessible rather than invested.",
      "Even a small buffer (one month's rent, say) meaningfully reduces the chance of going into debt over a surprise bill.",
    ],
  },
  {
    id: "compound-interest",
    title: "Compound interest",
    icon: "📈",
    summary: "Why starting early matters more than how much you start with.",
    aiPrompt: "If I started saving an extra $100 a month, roughly how much could that grow to over 5 and 10 years?",
    content: [
      "Compound interest means you earn returns not just on what you put in, but on the returns you've already earned.",
      "The earlier money is invested or saved, the more time it has to compound - which is why starting small early often beats starting big late.",
      "The same effect works against you with debt: interest on unpaid balances compounds too, which is why carrying high-interest debt is expensive over time.",
    ],
  },
  {
    id: "credit-scores",
    title: "Credit scores",
    icon: "💳",
    summary: "What actually moves your score, and what doesn't.",
    aiPrompt: "What should I keep in mind about credit scores given my current spending and any debt-like categories?",
    content: [
      "Credit scores are mostly driven by payment history (paying on time) and credit utilisation (how much of your available credit you're using).",
      "Length of credit history, the mix of credit types, and new credit applications matter too, but less.",
      "Checking your own score (a \"soft\" check) doesn't hurt it - it's hard credit applications, like a new loan, that can cause a small, temporary dip.",
    ],
  },
  {
    id: "needs-vs-wants",
    title: "Needs vs. wants",
    icon: "🧭",
    summary: "A quick way to sort spending before deciding where to cut.",
    aiPrompt: "Looking at my spending, which categories are needs vs wants, and where could I realistically cut back?",
    content: [
      "A \"need\" keeps you housed, fed, safe, employed, or healthy. Everything else is a \"want\" - even things that feel essential in the moment.",
      "This isn't about guilt - wants are a normal and healthy part of a budget. It's just a useful first filter when deciding what to trim.",
      "When a category is over budget, checking whether the overspend was mostly needs or wants tells you whether the fix is cutting back, or finding more income.",
    ],
  },
];

export const KNOWLEDGE_QUIZ = [
  {
    question: "In the 50/30/20 rule, what does the 20% usually represent?",
    options: ["Wants", "Needs", "Savings or debt repayment", "Taxes"],
    correctIndex: 2,
  },
  {
    question: "What is an emergency fund mainly used for?",
    options: [
      "Everyday groceries",
      "Unexpected costs like medical bills or job loss",
      "Investing in stocks",
      "Paying rent every month",
    ],
    correctIndex: 1,
  },
  {
    question: "Why does starting to save early matter so much?",
    options: [
      "It doesn't really matter when you start",
      "Early savings avoid all taxes",
      "Compound interest has more time to grow your money",
      "Banks give better rates to younger savers",
    ],
    correctIndex: 2,
  },
  {
    question: "What has the biggest impact on your credit score?",
    options: ["Your income", "Payment history and credit utilisation", "Your age", "Your bank's name"],
    correctIndex: 1,
  },
  {
    question: "Which of these is typically a \"want\" rather than a \"need\"?",
    options: ["Rent", "Groceries", "Streaming subscriptions", "Electricity bill"],
    correctIndex: 2,
  },
];


// Simple, explainable rules (no LLM call needed) that pick 1-2 topics worth
// surfacing first based on the user's real numbers from /insights/summary -
// e.g. a low/negative savings rate points at "Emergency funds" before
// anything else. Returns [] when there's not enough data yet (a brand new
// account), so the Hub just shows the plain topic list in that case.
export function recommendTopics(summary) {
  if (!summary || !summary.transaction_count) return [];

  const picks = [];

  if (typeof summary.savings_rate === "number" && summary.savings_rate < 10) {
    picks.push("emergency-fund");
  }

  if (Array.isArray(summary.category_vs_budget) && summary.category_vs_budget.some((c) => c.over_budget)) {
    picks.push("needs-vs-wants");
  }

  if (typeof summary.health_score === "number" && summary.health_score < 50 && !picks.includes("budgeting-basics")) {
    picks.push("budgeting-basics");
  }

  if (picks.length === 0) {
    picks.push("compound-interest");
  }

  return [...new Set(picks)].slice(0, 2);
}
