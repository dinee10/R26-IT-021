"""
Runs your RAG pipeline against a hand-labeled test set and computes RAGAS metrics:
faithfulness, answer relevancy, context precision, context recall.

Run from the backend/ folder:
    python evaluate_rag.py
"""

import json
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall

from conversation_rag import ask_question

TEST_SET_PATH = "eval/eval_testset.json"


def load_test_set():
    with open(TEST_SET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_eval():
    test_cases = load_test_set()

    questions, answers, contexts, ground_truths = [], [], [], []

    for case in test_cases:
        print(f"Running query {case['id']}: {case['question'][:60]}...")
        result = ask_question(case["question"], session_id=f"eval_{case['id']}")

        questions.append(case["question"])
        answers.append(result["answer"])
        contexts.append(result.get("retrieved_context", []))
        ground_truths.append(case["ground_truth"])

    dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })

    print("\nRunning RAGAS evaluation (this calls the OpenAI API multiple times, may take a bit)...")
    scores = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
    )

    print("\n=== RAGAS RESULTS ===")
    print(scores)

    df = scores.to_pandas()
    df.to_csv("ragas_results.csv", index=False)
    print("\nSaved detailed per-question results to ragas_results.csv")


if __name__ == "__main__":
    run_eval()