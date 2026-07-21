# Requirements

## Intent

Turn unstructured English work text into auditable skill mentions, public concept links, ten-category research mappings, and bundle-level summaries.

## Functional requirements

1. Keep source taxonomy and analytical taxonomy as separate, versioned fields.
2. Provide a transparent dictionary baseline with exact/normalized/longest-match behavior.
3. Provide SkillSpan BIO parsing and strict/overlap evaluation.
4. Preserve span offsets, source, confidence, mapping method, dictionary/model version, and review status.
5. Allow unknown concepts to remain NIL rather than forcing a category.
6. Provide breadth, diversity, concentration, rarity, pair support, and NPMI association measures.
7. Serve a local live extractor without requiring a hosted API or proprietary model.

