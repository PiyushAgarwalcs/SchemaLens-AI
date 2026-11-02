# test_data_concierge.py

from agents.data_concierge import ask_question

history = []

QUESTIONS = [
    # Mode A — doc-only
    "Which table tracks revenue?",
    # Ambiguity trap — channel exists in two tables with different value sets
    "What does the channel column mean? Is it the same across all tables?",
    # Mode B — real data needed
    "How many customers are in each segment?",
    # Mode B — multi-table join
    "What's the refund rate by order channel?",
    # Multi-turn — references previous answer implicitly
    "Which channel has the highest refund rate?",
    # Multi-part — should produce two entries
    "What does segment mean, and how many orders were placed last month?",
    # Mode C — out of scope
    "What are our marketing campaign conversion rates?",
]


def separator(label: str):
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print('=' * 60)


for q in QUESTIONS:
    separator(f"Q: {q}")
    responses = ask_question(q, history)

    assistant_summary = []  # collect all answers for history

    for i, r in enumerate(responses):
        if len(responses) > 1:
            print(f"\n  [Part {i+1} — Mode {r['mode']}]")
        else:
            print(f"\n  [Mode {r['mode']}]")

        print(f"Answer: {r['answer']}")
        if r["sql"]:
            print(f"\nSQL:\n{r['sql']}")
        if r["results"]:
            print(f"\nResults:\n{r['results']}")

        assistant_summary.append(r["answer"])

    history.append({"role": "user", "content": q})
    history.append({"role": "assistant", "content": " | ".join(assistant_summary)})

print("\n\n✅ Done. Review output above.")