# Subject seed-data schema

One JSON file per paper/subject under `backend/app/data/subjects/`, loaded by
`app/seed_content.py`. File name = subject slug, e.g. `gs1.json`,
`public-administration.json`.

```json
{
  "paper": "GS1",
  "optional_subject": null,
  "syllabus_nodes": [
    {"title": "Modern Indian History", "parent_title": null, "tags": ["history", "modern-india"]},
    {"title": "1857 Revolt", "parent_title": "Modern Indian History", "tags": ["history"]}
  ],
  "pyqs": [
    {
      "year": 2023,
      "marks": 15,
      "question_text": "Exact or close paraphrase of a real UPSC PYQ.",
      "node_titles": ["1857 Revolt"],
      "options": null,
      "correct_option": null,
      "marking_scheme": "Your own examiner-style marking scheme, 2-4 sentences: what intro/body/conclusion must cover, word limit."
    },
    {
      "year": 2022,
      "marks": 2,
      "question_text": "An MCQ stem.",
      "node_titles": ["1857 Revolt"],
      "options": [{"label": "A", "text": "..."}, {"label": "B", "text": "..."}, {"label": "C", "text": "..."}, {"label": "D", "text": "..."}],
      "correct_option": "B",
      "marking_scheme": null
    }
  ],
  "content_items": [
    {
      "title": "The 1857 Revolt — Causes and Consequences",
      "body": "300-500 words, YOUR OWN WORDING — a platform-authored summary, never copy-pasted from any book or site.",
      "source_type": "derived_summary",
      "source_url": null,
      "node_titles": ["1857 Revolt"],
      "tags": ["history"],
      "is_current_affairs": false
    }
  ]
}
```

## Rules

- **`paper`**: one of `GS1`, `GS2`, `GS3`, `GS4`, `CSAT`, `ESSAY`, `OPTIONAL`.
  `optional_subject` is set (exact subject name, e.g. `"Public Administration"`)
  only when `paper` is `OPTIONAL`, else `null`.
- **`syllabus_nodes`**: 15-30 nodes, up to 2 levels deep (`parent_title` refers
  to another node's `title` in the SAME file, or `null` for a top-level node).
  Base these on the real official UPSC syllabus for that paper/subject — it's
  a public government document, safe to restructure as topic/subtopic titles.
- **`pyqs`**: 8-15 entries per file, a mix of MCQs (GS1/CSAT papers only —
  `options` + `correct_option` set, `marking_scheme` null) and descriptive
  entries (GS2-4/Essay/Optional papers — `options`/`correct_option` null,
  `marking_scheme` set). Real UPSC previous-year question text is fine to
  quote (widely published for aspirant reference); `marking_scheme` must be
  your own written rubric, not copied from any answer key or coaching
  material.
- **`content_items`**: 8-15 reading-material entries per file. `body` must be
  ORIGINAL PROSE — a summary you write, never verbatim text from NCERT,
  Laxmikanth, Spectrum, Wikipedia, or any other source. Use `source_type:
  "ncert"` only if you are certain the passage is your own paraphrase of
  NCERT-level material; default to `"derived_summary"` otherwise.
- Every `node_titles` entry (in `pyqs` and `content_items`) MUST exactly
  match a `title` from this same file's `syllabus_nodes`.
- Validate the file parses with `python -m json.tool <file>` before you
  finish.
