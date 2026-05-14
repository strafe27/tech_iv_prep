# Deriv Copy Testing Pipeline

A replayable multi-stage AI pipeline that ingests a product brief, co-designs a scoring rubric with operator approval, generates marketing copy variants, scores them by persona, audits for compliance, and produces a handoff-ready recommendation deck.

## Requirements

- Python 3.14+
- [uv](https://github.com/astral-sh/uv)
- A Gemini API key

## Setup

```bash
# Install dependencies
uv sync

# Create .env with your Gemini API key
echo "gemini_api=YOUR_KEY_HERE" > .env
```

## Running the pipeline

```bash
uv run python pipeline.py
```

The pipeline is resumable — if interrupted, re-running skips completed stages. To run from scratch:

```bash
rm artifacts/pipeline_state.json
uv run python pipeline.py
```

To replace the product brief, swap `product_brief.json` before running. The pipeline reads it from disk at each stage.

## Operator approval (Stage 2)

After Stage 1 generates the rubric draft, the pipeline pauses for interactive review:

- **[A]** Approve the rubric as-is
- **[E]** Edit a dimension (name, description, or weight)
- **[R]** Reject and regenerate via a new LLM call

All downstream scoring uses the approved rubric.

## Pipeline stages

| Stage | Key | Description |
|---|---|---|
| 1 | `RUBRIC_DRAFTED` | LLM designs a 5-dimension scoring rubric from the product brief |
| 2 | `RUBRIC_APPROVED` | Operator reviews and approves/edits/rejects the rubric |
| 3 | `VARIANTS_GENERATED` | LLM generates 6 headlines, 6 CTAs, 12 subheadlines (one per angle) |
| 4 | `VARIANTS_SCORED` | LLM scores all headlines and CTAs against the approved rubric for both personas |
| 5 | `COMPLIANCE_AUDITED` | LLM audits all variants against the product brief compliance constraints |
| 6 | `COPY_DECK_GENERATED` | Selects winners per persona, excludes blockers, generates full copy deck |
| 7 | `SIMULATED_CTR_DONE` | 5 user archetypes rate headlines; CTR rank compared to rubric rank |
| 8 | `IMPROVEMENT_DONE` | Lowest-scoring eligible headline is improved, re-scored, and re-audited |
| 9 | `LOCALISATION_DONE` | Top 3 headlines evaluated for Arabic and Bahasa Malaysia localisation |
| 10 | `AB_TEST_DONE` | A/B test briefs generated for top 2 persona recommendations |

## Artifacts

All outputs are written to `artifacts/` (gitignored):

```
artifacts/
  pipeline_state.json
  llm_calls.jsonl
  stage_1/rubric_draft.json
  stage_2/approved_rubric.json
  stage_3/copy_variants.json
  stage_4/variant_scores.json
  stage_5/compliance_audit.json
  stage_6/recommendation.json
  stage_6/recommendation.md        ← final copy deck
  stage_7/simulated_ctr.json
  stage_8/variant_improvement.json
  stage_9/localisation_flags.json
  stage_10/ab_test_brief.md
```

## Validation

```bash
uv run python validate.py
```

Checks artifact existence, JSON validity, rubric integrity, variant coverage, scoring correctness, compliance taxonomy, blocker exclusion, recommendation completeness, and LLM call log records.
