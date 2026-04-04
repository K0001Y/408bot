"""Test question_parser with real chunk data."""
import json
from app.utils.question_parser import (
    find_numbered_items,
    extract_question_by_number,
    extract_answer_by_number,
)

with open("../processed/ds_chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

ex_chunk = next(c for c in chunks if c["chunk_id"] == "ds_3.4.5")
ans_chunk = next(c for c in chunks if c["chunk_id"] == "ds_3.4.6")

print("=== Exercise chunk (ds_3.4.5) ===")
print("Title:", ex_chunk["subsection_title"])
items = find_numbered_items(ex_chunk["content"])
print("Found", len(items), "numbered items:")
for num, start, end in items:
    preview = ex_chunk["content"][start : start + 80].replace("\n", " ")
    print(f"  Q{num}: pos={start}-{end}, preview: {preview}")

print("\n=== Answer chunk (ds_3.4.6) ===")
print("Title:", ans_chunk["subsection_title"])
items = find_numbered_items(ans_chunk["content"])
print("Found", len(items), "numbered items:")
for num, start, end in items:
    preview = ans_chunk["content"][start : start + 80].replace("\n", " ")
    print(f"  A{num}: pos={start}-{end}, preview: {preview}")

print("\n=== Extract Q6 ===")
q6 = extract_question_by_number(ex_chunk["content"], 6)
print(f"Q6 ({len(q6)} chars):", q6[:200])

print("\n=== Extract A6 ===")
a6 = extract_answer_by_number(ans_chunk["content"], 6)
print(f"A6 ({len(a6)} chars):", a6[:200])

print("\n=== Extract Q1 ===")
q1 = extract_question_by_number(ex_chunk["content"], 1)
print(f"Q1 ({len(q1)} chars):", q1[:200])

print("\n=== Extract A1 ===")
a1 = extract_answer_by_number(ans_chunk["content"], 1)
print(f"A1 ({len(a1)} chars):", a1[:200])

print("\n=== Edge: Q99 (not found) ===")
q99 = extract_question_by_number(ex_chunk["content"], 99)
print(f"Q99: '{q99}'")
