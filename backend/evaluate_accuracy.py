from conversation_rag import ask_question, clear_conversation
import csv
from datetime import datetime

# Parallel questions (same meaning in both languages)
TEST_QUESTIONS = [
    {
        "id": 1,
        "sinhala": "කොහොඹ හාවිතා කරන්නේ කුමක් සඳහාද?",
        "english": "What is neem used for?",
        "expected_plant": "Neem / කොහොඹ"
    },
    {
        "id": 2,
        "sinhala": "සමේ රෝග සඳහා කොහොඹ හාවිතා කරන්නේ කෙසේද?",
        "english": "How to prepare neem for skin diseases?",
        "expected_plant": "Neem / කොහොඹ"
    },
    {
        "id": 3,
        "sinhala": "ඉඟුරු හාවිතා කරන්නේ කුමක් සඳහාද?",
        "english": "What is ginger used for?",
        "expected_plant": "Ginger / ඉඟුරු"
    },
    {
        "id": 4,
        "sinhala": "කහ හාවිතා කරන්නේ කුමක් සඳහාද?",
        "english": "What is turmeric used for?",
        "expected_plant": "Turmeric / කහ"
    },
    {
        "id": 5,
        "sinhala": "ගොටුකොල මතකයට හොඳද?",
        "english": "Is gotukola good for memory?",
        "expected_plant": "Gotukola / ගොටුකොල"
    },
    {
        "id": 6,
        "sinhala": "කෝමාරිකා හාවිතා කරන්නේ කුමක් සඳහාද?",
        "english": "What is aloe vera used for?",
        "expected_plant": "Aloe vera / කෝමාරිකා"
    },
]

def run_evaluation():
    print("=" * 70)
    print("  AYURVEDIC RAG - ACCURACY EVALUATION")
    print("  Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    results = []

    for test in TEST_QUESTIONS:
        print(f"\n\n{'='*70}")
        print(f"TEST ID: {test['id']}  |  Expected Plant: {test['expected_plant']}")
        print(f"{'='*70}")

        # Clear conversation for each pair so history does not interfere
        clear_conversation("eval_si")
        clear_conversation("eval_en")

        # Sinhala
        print("\n[SINHALA QUESTION]")
        print("Q:", test["sinhala"])
        si_result = ask_question(test["sinhala"], session_id="eval_si")
        print("\nA:", si_result["answer"])
        print("Sources:", si_result["sources"])
        print("Safety mentioned:", si_result["safety_context_available"])

        # English 
        print("\n[ENGLISH QUESTION]")
        print("Q:", test["english"])
        en_result = ask_question(test["english"], session_id="eval_en")
        print("\nA:", en_result["answer"])
        print("Sources:", en_result["sources"])
        print("Safety mentioned:", en_result["safety_context_available"])

        results.append({
            "id": test["id"],
            "expected_plant": test["expected_plant"],
            "sinhala_q": test["sinhala"],
            "sinhala_a": si_result["answer"],
            "sinhala_sources": str(si_result["sources"]),
            "sinhala_safety": si_result["safety_context_available"],
            "english_q": test["english"],
            "english_a": en_result["answer"],
            "english_sources": str(en_result["sources"]),
            "english_safety": en_result["safety_context_available"],
        })

    # Save detailed text report 
    with open("evaluation_results.txt", "w", encoding="utf-8") as f:
        f.write("AYURVEDIC RAG - ACCURACY EVALUATION REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        for r in results:
            f.write(f"TEST ID: {r['id']}\n")
            f.write(f"Expected Plant: {r['expected_plant']}\n")
            f.write("-" * 60 + "\n")
            f.write(f"SINHALA Q: {r['sinhala_q']}\n")
            f.write(f"SINHALA A:\n{r['sinhala_a']}\n")
            f.write(f"Sources: {r['sinhala_sources']} | Safety: {r['sinhala_safety']}\n\n")
            f.write(f"ENGLISH Q: {r['english_q']}\n")
            f.write(f"ENGLISH A:\n{r['english_a']}\n")
            f.write(f"Sources: {r['english_sources']} | Safety: {r['english_safety']}\n")
            f.write("=" * 80 + "\n\n")

    # Save CSV for easy scoring 
    with open("evaluation_scores.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ID", "Expected Plant",
            "Sinhala Question", "Sinhala Answer (first 150 chars)", "Sinhala Safety",
            "English Question", "English Answer (first 150 chars)", "English Safety",
            "Correct Plant (SI)", "Correct Plant (EN)",
            "Factual Accuracy (SI)", "Factual Accuracy (EN)",
            "Consistency (SI vs EN)", "Notes"
        ])

        for r in results:
            writer.writerow([
                r["id"],
                r["expected_plant"],
                r["sinhala_q"],
                r["sinhala_a"][:150].replace("\n", " "),
                r["sinhala_safety"],
                r["english_q"],
                r["english_a"][:150].replace("\n", " "),
                r["english_safety"],
                "",  
                "",
                "",
                "",
                "",
                ""
            ])

    print("\n\n" + "=" * 70)
    print("EVALUATION FINISHED")
    print("Detailed answers saved to : evaluation_results.txt")
    print("Scoring sheet saved to    : evaluation_scores.csv")
    print("=" * 70)
    print("\nNext step: Open evaluation_scores.csv and fill the scoring columns")
    print("using the criteria (0, 1, or 2) we discussed earlier.")


if __name__ == "__main__":
    run_evaluation()