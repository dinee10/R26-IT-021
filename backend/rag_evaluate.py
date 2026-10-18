"""Fixed, auditable evaluation for the CURRENT Herbal Knowledge RAG backend.

Run from the backend folder, with the virtual environment activated:
    python rag_evaluate.py retrieval
    python rag_evaluate.py answers
    python rag_evaluate.py score

"""

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import conversation_rag_bilingual_test as rag

OUT = Path('rag_evaluation')

# Each species is verified as present in the user's English + Sinhala datasets.
# These are intentionally varied questions, NOT auto-generated from model answers.
RETRIEVAL_CASES = [
    ('R01', 'EN', 'neem', 'azadirachta indica', 'What precautions apply to Neem oil?'),
    ('R02', 'SI', 'neem', 'azadirachta indica', 'කොහොඹ තෙල් භාවිතයේ අවදානම් මොනවාද?'),
    ('R03', 'EN', 'ginger', 'zingiber officinale', 'Is there clinical evidence that Ginger helps with nausea?'),
    ('R04', 'SI', 'ginger', 'zingiber officinale', 'ඉඟුරු ඔක්කාරය අඩු කිරීමට උපකාරී වන බවට ඇති සාක්ෂි මොනවාද?'),
    ('R05', 'EN', 'gotukola', 'centella asiatica', 'Does Gotukola improve memory according to human trials?'),
    ('R06', 'SI', 'gotukola', 'centella asiatica', 'ගොටුකොල මතකය වැඩි කිරීමට උපකාරී වන බවට ඇති සාක්ෂි මොනවාද?'),
    ('R07', 'EN', 'polpala', 'aerva lanata', 'What is Polpala traditionally used for in urinary problems?'),
    ('R08', 'SI', 'polpala', 'aerva lanata', 'පොල්පලා මුත්‍රා ආශ්‍රිත ගැටලු සඳහා සාම්ප්‍රදායිකව භාවිතා කරන්නේ කෙසේද?'),
    ('R09', 'EN', 'aloe vera', 'aloe barbadensis miller', 'What is the evidence for Aloe vera in wound care?'),
    ('R10', 'SI', 'aloe vera', 'aloe barbadensis miller', 'කෝමාරිකා තුවාල සඳහා භාවිතා කිරීමේ සාක්ෂි මොනවාද?'),
    ('R11', 'EN', 'turmeric', 'curcuma longa', 'What are the traditional medicinal uses of Turmeric?'),
    ('R12', 'SI', 'turmeric', 'curcuma longa', 'කහ ශාකයේ සාම්ප්‍රදායික ඖෂධීය භාවිත මොනවාද?'),
    ('R13', 'EN', 'ranawara', 'cassia auriculata', 'What are the reported uses and limitations of Ranawara tea?'),
    ('R14', 'SI', 'ranawara', 'cassia auriculata', 'රණවරා තේ භාවිතය සහ එහි සීමාවන් මොනවාද?'),
    ('R15', 'EN', 'iramusu', 'hemidesmus indicus', 'What is Iramusu traditionally prepared for?'),
    ('R16', 'SI', 'iramusu', 'hemidesmus indicus', 'ඉරමුසු සාම්ප්‍රදායිකව සකස් කරන්නේ කුමක් සඳහාද?'),
    ('R17', 'EN', 'hathawariya', 'asparagus racemosus', 'What precautions apply to Hathawariya?'),
    ('R18', 'SI', 'hathawariya', 'asparagus racemosus', 'හතාවාරිය භාවිතයේදී සැලකිලිමත් විය යුතු කරුණු මොනවාද?'),
    ('R19', 'EN', 'kikiridiya', 'eclipta prostrata', 'What is Kikiridiya traditionally used for?'),
    ('R20', 'SI', 'kikiridiya', 'eclipta prostrata', 'කිකිරිදිය ශාකයේ සාම්ප්‍රදායික ඖෂධීය භාවිත මොනවාද?'),
]

# Manual faithfulness review is performed against the ACTUAL context captured
# from the model prompt, not just source filenames. Deliberately includes
# English, Sinhala, abstention, disease integration and persona requests.
ANSWER_CASES = [
    ('A01', 'EN', 'scientific name', 'general_public', 'What is the scientific name of Ginger?', 'Name should be Zingiber officinale; answer briefly.'),
    ('A02', 'SI', 'supported plant', 'general_public', 'ගොටුකොල සාම්ප්‍රදායිකව භාවිතා කරන්නේ කුමක් සඳහාද?', 'Traditional uses; avoid unsupported clinical claims.'),
    ('A03', 'EN', 'evidence', 'researcher', 'What does clinical research say about Gotukola and memory?', 'Cognitive benefit is not confirmed by the recorded trials.'),
    ('A04', 'EN', 'evidence', 'student', 'What is the evidence for Ginger helping nausea?', 'Evidence qualification and limitations must be grounded.'),
    ('A05', 'EN', 'precaution', 'practitioner', 'What are the precautions and contraindications for Neem oil?', 'Toxicity particularly for children; avoid invented dosage.'),
    ('A06', 'SI', 'precaution', 'student', 'පොල්පලා භාවිතයේ අවදානම් මොනවාද?', 'Review Sinhala phrasing and documented precautions.'),
    ('A07', 'EN', 'unsupported', 'general_public', 'What is dragon fruit used for?', 'Should refuse; no unrelated medicinal plant details.'),
    ('A08', 'EN', 'unsupported', 'student', 'What are the medicinal uses of Ashwagandha?', 'Should refuse; no Hathawariya or Asamodagam details.'),
    ('A09', 'SI', 'unsupported', 'student', 'අශ්වගන්ධ ශාකයේ ඖෂධීය භාවිත මොනවාද?', 'Should refuse in Sinhala; no unrelated plant details.'),
    ('A10', 'EN', 'disease integration', 'general_public', 'More Information About Murraya Koenigii Insect Damage', 'Should explain verified curry leaf pest symptoms.'),
    ('A11', 'EN', 'disease integration', 'general_public', 'More Information About Centella Asiatica WormCreep', 'Should explain caterpillar damage, not medicinal uses.'),
    ('A12', 'SI', 'evidence', 'researcher', 'ගොටුකොල මතකය වැඩි කරන බවට ඇති විද්‍යාත්මක සාක්ෂි පර්යේෂකයෙකු ලෙස පැහැදිලි කරන්න.', 'Verify language, researcher persona, evidence and references.'),
]


def scientific_identity(doc):
    """Returns species identity from a medicinal record, or empty for disease records."""
    text = doc.page_content
    if re.search(r'^Disease Name:', text, flags=re.MULTILINE):
        return ''
    m = re.search(r'^Scientific Name:\s*(.*?)\s*$', text, flags=re.MULTILINE)
    return ' '.join(m.group(1).casefold().split()) if m else ''


def write_csv(path, fieldnames, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def retrieval(limit):
    OUT.mkdir(exist_ok=True)
    rows = []
    cases = RETRIEVAL_CASES[:limit] if limit else RETRIEVAL_CASES
    for i, (case_id, lang, plant, expected, question) in enumerate(cases, 1):
        print(f'[{i}/{len(cases)}] {case_id} {lang} — {plant}', flush=True)
        row = {
            'id': case_id, 'language': lang, 'plant': plant, 'expected_species': expected,
            'question': question, 'query_used': '', 'top1_species': '',
            'top1_correct': 0, 'hit_at_3': 0, 'hit_at_5': 0,
            'relevant_count_in_top5': 0, 'retrieved_count': 0,
            'retrieved_species_in_order': '', 'error': '',
        }
        try:
            # Same query-rewriting and retrieval/filtering functions as the backend.
            query = rag._build_search_query(question, [])
            row['query_used'] = query
            docs = rag._retrieve(query)
            if docs:
                docs = rag._filter_to_named_plants(query, docs)
            if docs:
                docs = rag._filter_by_question_topic(query, docs)
            species = [scientific_identity(doc) for doc, _ in docs]
            row['retrieved_count'] = len(species)
            row['retrieved_species_in_order'] = ' | '.join(species)
            row['top1_species'] = species[0] if species else ''
            row['top1_correct'] = int(bool(species) and species[0] == expected)
            row['hit_at_3'] = int(expected in species[:3])
            row['hit_at_5'] = int(expected in species[:5])
            row['relevant_count_in_top5'] = sum(s == expected for s in species[:5])
        except Exception as exc:
            row['error'] = f'{type(exc).__name__}: {exc}'
            print('  ERROR:', row['error'], flush=True)
        rows.append(row)
        write_csv(OUT / 'retrieval_results.csv', list(rows[0]), rows)
        print(f"  Top-1: {row['top1_correct']} | Hit@5: {row['hit_at_5']} | "
              f"Top result: {row['top1_species'] or '(none)'}", flush=True)

    print('\nRETRIEVAL SUMMARY — current run only')
    for lang in ('EN', 'SI', 'ALL'):
        subset = [r for r in rows if lang == 'ALL' or r['language'] == lang]
        valid = [r for r in subset if not r['error']]
        if not valid:
            continue
        n = len(valid)
        print(f'{lang}: N={n}, Top-1 plant identification = '
              f"{sum(r['top1_correct'] for r in valid)}/{n} "
              f"({sum(r['top1_correct'] for r in valid)/n:.1%}); "
              f"Hit@5 = {sum(r['hit_at_5'] for r in valid)}/{n} "
              f"({sum(r['hit_at_5'] for r in valid)/n:.1%})")
    print('Saved:', OUT / 'retrieval_results.csv')
    print('NOTE: These measure correct plant identity in retrieved records, NOT clinical accuracy or answer faithfulness.')


class CaptureAnswerPrompt:
    """Transparent pass-through wrapper to save exactly the evidence sent to GPT.

    Only used by this standalone test. It does not alter model arguments,
    responses, or the production backend source file.
    """

    def __init__(self, wrapped, captured):
        self.wrapped = wrapped
        self.captured = captured

    def invoke(self, messages, *args, **kwargs):
        for message in messages:
            content = getattr(message, 'content', '')
            if isinstance(content, str) and '**Context:**\n' in content:
                self.captured['context'] = content.split('**Context:**\n', 1)[1]
        result = self.wrapped.invoke(messages, *args, **kwargs)
        self.captured['finish_reason'] = (result.response_metadata or {}).get('finish_reason', '')
        self.captured['output_tokens'] = (result.usage_metadata or {}).get('output_tokens', '')
        return result


def answers(limit):
    OUT.mkdir(exist_ok=True)
    cases = ANSWER_CASES[:limit] if limit else ANSWER_CASES
    records = []
    for i, (case_id, lang, kind, persona, question, expected) in enumerate(cases, 1):
        print(f'[{i}/{len(cases)}] {case_id}: {kind} / {lang} / {persona}', flush=True)
        captured = {}
        old_llm, old_si = rag.llm, rag.llm_sinhala
        rag.llm = CaptureAnswerPrompt(old_llm, captured)
        rag.llm_sinhala = CaptureAnswerPrompt(old_si, captured)
        session_id = 'viva_eval_' + case_id
        try:
            rag.clear_conversation(session_id)
            result = rag.ask_question(question, session_id=session_id,
                                      user_context={'default_type': persona, 'user_type': 'auto'})
            record = {
                'id': case_id, 'language': lang, 'test_type': kind,
                'default_persona': persona, 'question': question,
                'expected_check': expected, 'answer': result.get('answer', ''),
                'personas_used': result.get('user_types', []),
                'source_files': result.get('sources', []),
                'retrieved_context_sent_to_model': captured.get('context', ''),
                'finish_reason': captured.get('finish_reason', ''),
                'output_tokens': captured.get('output_tokens', ''),
                'error': '', 'tested_at': datetime.now().isoformat(timespec='seconds'),
            }
        except Exception as exc:
            record = {
                'id': case_id, 'language': lang, 'test_type': kind,
                'default_persona': persona, 'question': question,
                'expected_check': expected, 'answer': '', 'personas_used': [],
                'source_files': [], 'retrieved_context_sent_to_model': captured.get('context', ''),
                'finish_reason': '', 'output_tokens': '',
                'error': f'{type(exc).__name__}: {exc}',
                'tested_at': datetime.now().isoformat(timespec='seconds'),
            }
            print('  ERROR:', record['error'], flush=True)
        finally:
            rag.llm, rag.llm_sinhala = old_llm, old_si
        records.append(record)
        with (OUT / 'answer_evidence.jsonl').open('w', encoding='utf-8') as f:
            for item in records:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        print('  Answer:', record['answer'][:160].replace('\n', ' '), flush=True)

    review_fields = [
        'id', 'language', 'test_type', 'default_persona', 'question', 'expected_check',
        'answer', 'source_files', 'persona_returned', 'finish_reason',
        'supported_claims', 'unsupported_claims', 'unverifiable_claims',
        'relevance_1_to_5', 'persona_correct_yes_no', 'safe_wording_yes_no',
        'abstained_correctly_yes_no', 'reviewer_notes'
    ]
    review_rows = [{
        'id': r['id'], 'language': r['language'], 'test_type': r['test_type'],
        'default_persona': r['default_persona'], 'question': r['question'],
        'expected_check': r['expected_check'], 'answer': r['answer'],
        'source_files': '; '.join(r['source_files']),
        'persona_returned': '; '.join(r['personas_used']),
        'finish_reason': r['finish_reason'],
    } for r in records]
    write_csv(OUT / 'answer_review_TO_FILL.csv', review_fields, review_rows)
    print('Saved:', OUT / 'answer_evidence.jsonl')
    print('Saved:', OUT / 'answer_review_TO_FILL.csv')
    print('MANUAL REVIEW REQUIRED: compare each factual claim to retrieved_context_sent_to_model.')
    print('Do not report a faithfulness percentage until the review cells have been filled.')


def score():
    review_path = OUT / 'answer_review_TO_FILL.csv'
    if not review_path.exists():
        print('First run: python rag_viva_evaluate.py answers')
        return
    with review_path.open('r', encoding='utf-8-sig', newline='') as f:
        data = list(csv.DictReader(f))
    eligible = []
    for r in data:
        keys = ('supported_claims', 'unsupported_claims', 'unverifiable_claims')
        vals = [r.get(k, '').strip() for k in keys]
        if any(not v for v in vals):
            continue
        try:
            s, u, unknown = map(int, vals)
        except ValueError:
            print('Invalid claim counts for test', r['id'])
            continue
        if min(s, u, unknown) < 0 or s + u + unknown == 0:
            # 0-claim correct refusals are evaluated separately, not 0% faithful.
            continue
        eligible.append((r['id'], s, u, unknown))
    if not eligible:
        print('No claim-level faithfulness scores yet. Fill the three claim-count columns.')
        return
    supported = sum(r[1] for r in eligible)
    all_claims = sum(r[1] + r[2] + r[3] for r in eligible)
    print('Evaluated answers with factual claims:', len(eligible))
    print('Supported factual claims:', supported)
    print('Total assessed factual claims (including unsupported/unverifiable):', all_claims)
    print(f'Claim-level evidence faithfulness: {supported}/{all_claims} = {supported/all_claims:.1%}')
    print('These figures require manual claim labels; they are NOT clinical expert validation.')


def main():
    parser = argparse.ArgumentParser(description='Fixed RAG evaluation for viva / thesis')
    parser.add_argument('phase', choices=['retrieval', 'answers', 'score'])
    parser.add_argument('--limit', type=int, default=0, help='Use first N fixed cases for a smoke test')
    args = parser.parse_args()
    if args.limit < 0:
        parser.error('--limit must be nonnegative')
    if args.phase == 'retrieval':
        retrieval(args.limit)
    elif args.phase == 'answers':
        answers(args.limit)
    else:
        score()


if __name__ == '__main__':
    main()
