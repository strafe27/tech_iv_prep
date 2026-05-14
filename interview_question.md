## BUILD

Build a replayable multi-stage AI copy testing engine that ingests a product brief, co-designs a scoring rubric, generates distinct marketing copy variants, scores them by persona, audits them for financial marketing compliance, simulates user response signals, and produces a handoff-ready recommendation deck.

This is not a one-shot copywriting task. The evaluator will run your pipeline from a clean checkout, may replace the product brief with an equivalent fixture, and will verify that rubric design, generation, scoring, compliance audit, and recommendation are separated into staged steps.

The pipeline must preserve intermediate artifacts, enforce operator approval, log LLM calls, and exclude blocker compliance violations from final recommendations.

---

## INPUT FILES

Your pipeline must read the product brief from disk:

- `product_brief.json`

The sample product brief below is provided for local testing. The evaluator may replace it with an equivalent product brief using the same structure. Your implementation must not depend on exact product wording or hardcoded final variants.

---

## SAMPLE `product_brief.json`

```json
{
  "product_brief": {
    "product": "Deriv Bot",
    "description": "A no-code automated trading bot builder with drag-and-drop strategy creation, historical backtesting, and 24/7 execution",
    "markets": ["Forex", "Synthetic Indices", "Cryptocurrencies"],
    "primary_audience": {
      "persona": "Retail Trader — Automation Curious",
      "traits": [
        "No programming background",
        "Has been trading manually for 6–18 months",
        "Feels overwhelmed by manual monitoring",
        "Skeptical of automation — worried about losing control"
      ]
    },
    "secondary_audience": {
      "persona": "Experienced Trader — Time Poor",
      "traits": [
        "Has tested multiple strategies",
        "Wants to scale without hiring",
        "Evaluates tools on reliability and customisability"
      ]
    },
    "tone": "Approachable, empowering, not overly technical",
    "control_headline": "Automate your trading. No coding needed.",
    "control_cta": "Start building for free",
    "control_subheadline": "Build, test, and run automated trading strategies — without writing a single line of code.",
    "compliance_constraints": [
      "Must not imply guaranteed returns or risk-free trading",
      "Must not claim superiority over competitors without substantiation",
      "Must not use urgency language that could be construed as pressure selling",
      "Must include or imply that trading involves risk if making performance claims"
    ]
  }
}
```

---

## CONTROLLED TAXONOMY

Define the creative angle taxonomy in code and validate outputs against it.

Allowed copy angles:

```text
fear_of_missing_out
social_proof
benefit_led
curiosity
empowerment
loss_aversion
```

Allowed compliance severities:

```text
blocker
warning
clear
```

Allowed recommendation statuses:

```text
eligible
excluded_compliance_blocker
needs_review
```

---

## PIPELINE STAGES

Your implementation must enforce these stages in code:

```text
INIT
 -> PRODUCT_BRIEF_LOADED
 -> RUBRIC_DRAFTED
 -> RUBRIC_APPROVED
 -> VARIANTS_GENERATED
 -> VARIANTS_SCORED
 -> COMPLIANCE_AUDITED
 -> BLOCKERS_EXCLUDED
 -> RECOMMENDATIONS_SELECTED
 -> COPY_DECK_GENERATED
 -> OPTIONAL_ANALYSES_GENERATED
 -> VALIDATION_COMPLETE
 -> RESULTS_FINALISED
```

Final recommendations must not be produced before compliance audit completion and blocker exclusion.

Variant scoring must use the operator-approved rubric, not the draft rubric.

---

## MUST COMPLETE

### 1. Rubric Design

Make a Stage 1 LLM call using the product brief.

Ask the model to design a scoring rubric for evaluating copy variants.

The rubric must include exactly 5 dimensions.

Each dimension must include:

```json
{
  "dimension_id": "string",
  "name": "string",
  "weight": 0.2,
  "scale": "0-10",
  "description_of_10": "string"
}
```

The rubric must be grounded in the product brief, audience personas, tone, and compliance constraints.

It must not be a generic marketing rubric.

Save the draft rubric to `rubric_draft.json`.

---

### 2. Operator Rubric Approval Checkpoint

After Stage 1, display the draft rubric in the terminal.

Pause for operator review.

The operator must be able to:

- approve the rubric unchanged
- edit dimension names, descriptions, or weights
- reject and regenerate the rubric

Save the approved rubric to:

```text
approved_rubric.json
```

All downstream scoring must use `approved_rubric.json`.

The checkpoint must be interactive and must affect downstream inputs.

---

### 3. Variant Generation

Make a separate Stage 2 LLM call using:

- product brief
- approved angle taxonomy
- compliance constraints
- tone guidance

Generate:

- 6 headline variants, one per angle
- 6 CTA variants, one per angle
- 2 subheadline variants per headline, 12 total

Each variant must include:

```json
{
  "variant_id": "string",
  "variant_type": "headline | cta | subheadline",
  "angle": "empowerment",
  "text": "string",
  "linked_headline_id": "string | null"
}
```

Every variant must stay grounded in the product brief.

The LLM must not introduce unsupported product features, performance promises, or claims.

Save output to `copy_variants.json`.

---

### 4. Persona-Conditional Scoring

Make a separate Stage 3 LLM call.

The call must include:

- approved rubric
- product brief
- all generated variants
- primary audience persona
- secondary audience persona

Score every headline and CTA against the approved rubric for both personas.

Each score must include:

```json
{
  "variant_id": "string",
  "persona": "string",
  "dimension_scores": [
    {
      "dimension_id": "string",
      "score": 0,
      "rationale": "string"
    }
  ],
  "total_weighted_score": 0
}
```

The same variant may score differently by persona.

Save scores into `copy_variants.json` or `variant_scores.json`.

---

### 5. Compliance Audit

Make a separate Stage 4 LLM call.

The call must include:

- product brief
- exact compliance constraints
- all generated variants

For each variant, output:

```json
{
  "variant_id": "string",
  "variant_text": "string",
  "status": "clear | warning | blocker",
  "rule_violated": "string | null",
  "severity": "clear | warning | blocker",
  "suggested_fix": "string | null"
}
```

Variants with `blocker` violations must be excluded from final recommendations in code.

Save output to `compliance_audit.json`.

---

### 6. Recommendation and Copy Deck

After scoring and compliance audit, select the winning combination for each persona.

Selection must use:

- persona-specific scores
- compliance status
- blocker exclusion
- angle labels
- subheadline compatibility with selected headline

For each persona, produce a full above-the-fold copy deck:

- headline
- subheadline
- 3 benefit bullets
- CTA
- 1-sentence social proof or trust signal
- compliance notes
- 3-5 sentence recommendation rationale

Save output to `recommendation.md`.

The final recommendation must not include any variant with a blocker compliance violation.

---

## SHOULD ATTEMPT

### 7. Simulated Click-Through Ranking

Make a Stage 5 LLM call where the model role-plays as 5 distinct user archetypes.

Each archetype must rate every headline from 1 to 5 for likelihood to click.

Each rating must include a short reason.

Aggregate ratings into a simulated CTR rank in deterministic code.

Compare simulated CTR rank to rubric-based rank.

If the winners differ, explain the discrepancy.

Save output to `simulated_ctr.json`.

---

### 8. Variant Improvement Loop

Identify the lowest-scoring eligible headline.

Make an LLM call with:

- the headline text
- its weak rubric dimensions
- persona score rationales
- compliance constraints

Ask for an improved version.

Re-score and re-audit the improved version.

Save output to `variant_improvement.json`.

Do not assume the improved version is better unless re-scoring confirms it.

---

## STRETCH

### 9. Localisation Flag

For 3 top-scoring eligible headlines, make an additional LLM call to evaluate conceptual localisation into:

- Arabic
- Bahasa Malaysia

Flag:

- idioms
- cultural assumptions
- unclear phrasing
- compliance risks introduced by translation

Save output to `localisation_flags.json`.

---

### 10. A/B Test Design

For the top 2 persona-specific recommendations, produce an A/B test brief.

Each brief must include:

- hypothesis
- control
- variant
- primary metric
- secondary metrics
- sample size estimate
- success threshold
- guardrail metrics
- compliance review requirement before launch

Save output to `ab_test_brief.md`.

---

## REQUIRED ARTIFACTS

Your repository must produce:

- `product_brief.json`
- `rubric_draft.json`
- `approved_rubric.json`
- `copy_variants.json`
- `variant_scores.json`, if scores are not embedded in `copy_variants.json`
- `compliance_audit.json`
- `recommendation.md`
- `simulated_ctr.json`, if attempted
- `variant_improvement.json`, if attempted
- `localisation_flags.json`, if attempted
- `ab_test_brief.md`, if attempted
- `llm_calls.jsonl`

---

## `llm_calls.jsonl` REQUIREMENTS

Log one JSON object per LLM call.

Each record must include:

```json
{
  "stage": "string",
  "timestamp": "ISO-8601 timestamp",
  "provider": "string",
  "model": "string",
  "prompt_hash": "string",
  "input_artifacts": ["path"],
  "output_artifact": "path"
}
```

There must be separate records for:

- rubric design
- variant generation
- persona scoring
- compliance audit
- simulated CTR, if attempted
- variant improvement, if attempted
- localisation review, if attempted
- A/B test brief, if generated by LLM

---

## VALIDATION REQUIREMENTS

The repository must include a validation command, for example:

```bash
make validate
```

or:

```bash
python validate.py
```

The validation command must check that:

- required artifacts exist
- JSON files are valid
- product brief was read from disk
- rubric has exactly 5 dimensions
- approved rubric exists before variant scoring
- operator approval checkpoint was completed
- all 6 required angles are represented
- all variants have angle labels
- scoring uses the approved rubric
- both personas receive separate scores
- compliance audit uses the exact product brief constraints
- blocker variants are excluded from recommendations
- final recommendations include headline, subheadline, bullets, CTA, trust signal, and rationale
- LLM call logs contain separate records for required stages

---

## EXECUTION REQUIREMENTS

The evaluator will run the pipeline from a clean checkout.

Generated artifacts may be deleted before evaluation.

The evaluator may replace `product_brief.json` with an equivalent file using the same structure.

Static precomputed outputs are not sufficient.

The solution must actually run the staged pipeline and regenerate required artifacts.

---

## TOOLS

Any programming language may be used.

Any LLM provider or AI tooling may be used.

---

## TECHNICAL CONSTRAINTS

- Read `product_brief.json` from disk.
- Do not hardcode generated variants or final recommendations.
- Operator approval checkpoint after Stage 1 must be interactive.
- Scoring must use the approved rubric.
- All variants must be traceable by angle label.
- Compliance audit must be a separate LLM call.
- Blocker compliance violations must be excluded from final recommendations.
- Generated copy must not imply guaranteed returns or risk-free trading.
- Generated copy must not introduce claims or features absent from the product brief.