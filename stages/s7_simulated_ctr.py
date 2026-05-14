import json
import paths
import llm_client


def run():
    variants_data = json.loads(paths.COPY_VARIANTS.read_text())
    audit_data = json.loads(paths.COMPLIANCE_AUDIT.read_text())
    scores_data = json.loads(paths.VARIANT_SCORES.read_text())

    audit = {a["variant_id"]: a for a in audit_data["audit"]}
    headlines = [v for v in variants_data["variants"] if v["variant_type"] == "headline"]
    headlines_desc = "\n".join(
        f'- {h["variant_id"]} ({h["angle"]}): "{h["text"]}"' for h in headlines
    )

    prompt = f"""You are simulating 5 distinct user archetypes rating marketing headlines for a no-code automated trading bot.

HEADLINES TO RATE:
{headlines_desc}

Create 5 meaningfully distinct user archetypes — vary experience level, attitude toward automation, and trading background.
For each archetype, rate every headline 1-5 (1=very unlikely to click, 5=very likely to click) with a brief reason.

Return JSON:
{{
  "archetypes": [
    {{
      "name": "The Skeptic",
      "description": "brief archetype description",
      "ratings": [
        {{"variant_id": "headline_empowerment", "rating": 3, "reason": "brief reason"}}
      ]
    }}
  ]
}}

Each archetype must rate all {len(headlines)} headlines."""

    result = llm_client.call(
        stage="simulated_ctr",
        prompt=prompt,
        input_artifacts=[
            "artifacts/stage_3/copy_variants.json",
            "artifacts/stage_4/variant_scores.json",
            "artifacts/stage_5/compliance_audit.json",
        ],
        output_artifact="artifacts/stage_7/simulated_ctr.json",
    )

    archetypes = result.get("archetypes", [])

    # Aggregate CTR ratings deterministically
    ctr_totals = {h["variant_id"]: 0 for h in headlines}
    for archetype in archetypes:
        for r in archetype.get("ratings", []):
            if r["variant_id"] in ctr_totals:
                ctr_totals[r["variant_id"]] += r["rating"]
    ctr_rank = sorted(ctr_totals.items(), key=lambda x: (-x[1], x[0]))

    # Rubric rank: average total_weighted_score across personas
    rubric_totals: dict[str, float] = {}
    rubric_counts: dict[str, int] = {}
    for s in scores_data["scores"]:
        vid = s["variant_id"]
        if vid in ctr_totals:
            rubric_totals[vid] = rubric_totals.get(vid, 0.0) + s["total_weighted_score"]
            rubric_counts[vid] = rubric_counts.get(vid, 0) + 1
    rubric_avg = {vid: rubric_totals[vid] / rubric_counts[vid] for vid in rubric_totals}
    rubric_rank = sorted(rubric_avg.items(), key=lambda x: (-x[1], x[0]))

    ctr_winner = ctr_rank[0][0] if ctr_rank else None
    rubric_winner = rubric_rank[0][0] if rubric_rank else None
    match = ctr_winner == rubric_winner

    discrepancy_note = None
    if not match:
        discrepancy_note = (
            f"CTR winner ({ctr_winner}) differs from rubric winner ({rubric_winner}). "
            f"CTR reflects immediate emotional appeal across archetypes; "
            f"the rubric captures deeper persona fit and compliance alignment."
        )

    output = {
        "archetypes": archetypes,
        "ctr_rank": [{"variant_id": vid, "total_rating": total} for vid, total in ctr_rank],
        "rubric_rank": [{"variant_id": vid, "avg_score": round(avg, 4)} for vid, avg in rubric_rank],
        "winners_match": match,
        "discrepancy_note": discrepancy_note,
    }

    paths.SIMULATED_CTR.parent.mkdir(parents=True, exist_ok=True)
    paths.SIMULATED_CTR.write_text(json.dumps(output, indent=2))
    print(f"  CTR winner: {ctr_winner} | Rubric winner: {rubric_winner} | Match: {match}")
