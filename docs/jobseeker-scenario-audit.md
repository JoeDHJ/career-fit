# Career Fit: 50 job-seeker scenario audit

This release gate exercises the complete Career Fit flow with 50 deliberately different profiles: job posting input, candidate input, deterministic extraction, user review, structured evidence, plan generation, and role comparison where applicable. The fixture is [tests/fixtures/jobseeker_scenarios.json](../tests/fixtures/jobseeker_scenarios.json), and the repeatable runner is [tools/audit_jobseeker_scenarios.py](../tools/audit_jobseeker_scenarios.py).

## Decision

The product can form a useful, role-specific preparation plan for candidates who provide enough evidence and complete the review step. It does not claim that a score is possible for every first attempt. Sparse, language-limited, and claim-only profiles are routed to a visible evidence or guided-intake path instead of being assigned a misleading fit number.

Current audit result:

| Route | Cases | What the user receives |
| --- | ---: | --- |
| Role plan ready after checklist review | 41 | A reviewed preparation signal, requirement matrix, gaps, proof artifacts, and next actions |
| Guided intake required | 2 | No score until the user supplies a concrete example; the plan explains what to add and does not require an existing resume |
| Language-assisted manual evidence | 3 | A language coverage warning and a path to user-labeled evidence or trusted translation |
| Guided intake or manual evidence | 4 | A cautious no-score state for claim-heavy or eligibility-sensitive profiles, followed by structured evidence collection |
| **Total** | **50** | Every case has at least one next action |

The exact real review path produced `43` scored cases and `7` intentionally insufficient-information cases. When the review-panel harness added explicit user-labeled claim evidence, `49` cases could proceed to a scored preparation plan; the remaining `long_unemployed` case is the dedicated resume-free guided-intake path because it contains no role-linked evidence in the starting text. This harness is a capability check, not a claim that users supplied evidence automatically.

## Full 500-journey stress audit

The release gate also expands every maintained profile through ten controlled variants in [tools/audit_500_jobseeker_scenarios.py](../tools/audit_500_jobseeker_scenarios.py): plain text, case changes, spacing changes, added context, added result, added duration, claim language, low-information input, resume-style formatting, and an explicit review-panel evidence journey. That is `50 × 10 = 500` deterministic journeys, not 500 randomly generated people.

The completed run produced:

| Check | Result |
| --- | ---: |
| Journeys | 500 / 500 |
| Baseline `review_required` | 386 |
| Baseline `insufficient_information` | 114 |
| Applied review `scored` | 386 |
| Applied review `insufficient_information` | 114 |
| Structured or guided evidence `scored` | 486 |
| Structured or guided evidence `insufficient_information` | 14 |
| Journeys with a next action | 500 / 500 |
| Unexpected exceptions or contract issues | 0 |

The 14 cautious journeys are the intended language-limited, evidence-free, or otherwise constrained boundary. They receive the guided intake or manual-evidence route rather than a fabricated score. Every low-information variant now exercises the guided form itself: a task and context example is attached to an extracted requirement where one exists, remains `user_declared`, and unlocks scoring only after the checklist review is applied. All 20 language-review journeys retain a visible language-coverage caveat.

The full audit found no score-visibility leak, missing next action, comparison-count error, or crash. Its remaining limitations are product scope rather than hidden failures: a user may need several examples for a complex role, the English-first dictionary can still miss unfamiliar labels, and user-declared evidence is not external verification.

In addition to the 500 journeys, the runner executes a 32-case hard-gate edge matrix for experience comparison/negation, threshold wording, and post-claim follow-up sentences, historical/expired authorization and licenses, current license synonyms, future claims, unrelated future actions, and background-check wording. All 32 edge cases passed with no issue added to the release result.

The current guided-intake layout is captured in [the resume-free flow screenshot](assets/career-fit-guided-intake.png); it is an illustrative local UI capture, not a user record or performance claim.

## Scenario coverage

### Role plan ready after review — 41

`new_grad_business_analytics`, `new_grad_cs`, `teacher_to_data`, `humanities_to_ux`, `retail_to_customer_success`, `hospitality_to_project_coord`, `military_to_supply_chain`, `caregiver_return_hr`, `experienced_admin_ops`, `laid_off_engineer`, `foreign_experience_accounting`, `low_literacy`, `low_digital_literacy`, `bootcamp_data`, `self_taught_dev`, `open_source`, `freelancer`, `gig_worker`, `small_business_owner`, `phd_academic`, `postdoc_industry`, `researcher_product`, `nurse_health_data`, `social_worker_people_analytics`, `trades_to_coord`, `accommodation_request`, `communication_style`, `career_break_caregiving`, `return_after_illness`, `older_pivot`, `no_degree`, `licensed_nurse`, `remote_cross_border`, `background_check_gate`, `copywriter_ai_transition`, `creative_portfolio`, `nontraditional_pm`, `cybersecurity_transition`, `green_energy`, `apprentice_trade`, `undecided_compare`.

These cases cover early-career applicants, career changers, caregivers, immigrants, trades workers, freelancers, founders, researchers, nurses, older pivots, nontraditional candidates, accessibility needs, return-to-work cases, hard eligibility gates, creative work, AI transition, and two-role comparison. Their plans distinguish direct proof, thin proof, transferable proof, bridge work, foundation work, and gate verification.

### Guided intake required — 2

`long_unemployed` has no mapped role evidence and remains `insufficient_information`. `no_resume` can use a concrete family-business/customer example, but it is still tagged for a guided intake route because the user should not need to know resume language in advance. The input-gap action now asks for three short answers—tasks, tools or setting, and result or who benefited—rather than assuming the user has a resume.

### Language-assisted manual evidence — 3

`esl_job_seeker` has English technical terms but still needs review of language coverage. `spanish_profile` has no safe English dictionary match until the user adds labeled evidence or translates the relevant task. `chinese_profile` has some exact English tool matches inside Chinese text but remains conservative until the user confirms the mapped evidence. The UI now exposes a profile-language selector and displays the caveat in the result; it never treats language as an ability or employability judgment.

### Guided intake or manual evidence — 4

`overqualified_underemployed`, `work_authorization_gate`, `ambiguous_pm_claim`, and `executive_return` contain broad claims or an unresolved eligibility question. A user can add task, context, result, duration, and recency in the review panel. Until then, the score stays hidden or the gate remains separate. This is the intended behavior for senior applicants whose titles or claims do not themselves prove the target role's scope.

## Problems found and changes made

1. Action-oriented evidence such as archival research, inventory and shipments, test cases, budgeted expenses, visual summaries, customer issues, and coordinated launches was under-mapped. The versioned English seed dictionary now contains reviewed aliases and context phrases for these common transition patterns. They remain claim-only or thin until the user supplies reviewable proof.
2. The initial audit incorrectly passed automatically extracted evidence back as if the user had supplied it. The audit now runs the exact browser-equivalent review-only path first, then a separately labeled manual-evidence harness. This prevents false confidence in the release gate.
3. Background checks were not separated from ordinary skills. They are now hard constraints with conservative `met`, `not_met`, or `unknown` status and a verification action.
4. A fully evidenced candidate could receive an empty action list. The engine now returns a role-specific positioning action: tailor the resume, show one recent result, and prepare a concise explanation of why the role scope is appropriate.
5. Non-English profiles could fail silently as “no evidence.” The language selector, API/CLI language hint, `summary.candidate_language`, visible warning, and explicit manual-evidence route make the limitation legible.
6. The substantive-profile guard missed plain-language verbs such as tracked, scheduled, presented, moved, checked, and reviewed. It now recognizes common action and context terms while still refusing keyword-only claims.
7. A missed requirement did not have to be in the dictionary. The review panel now accepts a user-supplied soft label such as a niche workflow; it receives a `user.custom.*` ID and can only match after the user labels evidence, without being assigned a research taxonomy category. It also accepts an explicitly written missed eligibility gate, which remains a hard `unknown`/`met`/`not_met` constraint rather than being downgraded to a skill.
8. Future or conditional eligibility language could be mistaken for current proof. Hard-gate checks now keep modal, date-bound, and conditional claims such as `will`, `would`, `by 2027`, and `if approved` as `unknown`; explicit current negatives remain `not_met`, and current authorization wording is recognized without weakening the verification boundary.
9. Experience negation and historical/expired eligibility language could be swallowed by broad positive regexes. The gate parser now keeps explicit experience negation, insufficient comparisons, post-claim relevance conflicts, and tightly linked follow-up sentences as `not_met`, preserves positive threshold phrases such as `no less than five years`, treats historical-only authorization or licensure as `unknown`, marks explicit expired/revoked/inactive states as `not_met`, recognizes licensed/not-licensed and eligible/not-eligible synonyms, and treats `current` license wording as equivalent to `active` when the required license terms are present. The 500-journey runner also checks a 32-case hard-gate edge matrix.

## Full workflow findings

- Input: A full posting and a profile can be pasted or a local plain-text/Markdown resume can be loaded. A short or empty profile is not scored.
- Review: Requirements, importance, evidence type, and eligibility gates can be kept, removed, corrected, or supplemented. Scores stay hidden until the role checklist is confirmed.
- Evidence: User-added evidence is stored as declared rather than externally verified. Claim-only evidence stays weaker than work, project, portfolio, course, or certificate evidence.
- Plan: Every successful route has an action with a time horizon, effort estimate, expected artifact, and evidence prompt. Gate problems remain separate from soft skill gaps.
- Comparison: The comparison scenario confirms two roles can be compared only after candidate evidence is reviewed. Rankings are preparation priorities, not hiring odds; each selected role still needs its own checklist review.
- Occupation context: The optional AI Labor Atlas panel remains descriptive and separate from the job-specific fit result. It requires occupation confirmation and exposes source, vintage, mapping, and worker-review caveats.
- Privacy and fairness: The rule-based path is local; optional semantic review discloses its configured remote endpoint. The flow does not ask users to disclose medical details for return-to-work or accommodation scenarios, and it does not infer protected traits.
- Usability: The 390px browser regression passes for both products. Plain-language, low-literacy, resume-free, and accessibility cases retain an actionable route instead of a binary rejection.

## Remaining product boundary

The current release is an evidence-first preparation tool, not a universal multilingual resume parser, a labor-market forecast, or a hiring decision system. The guided intake supports a first concrete example, not a complete resume reconstruction: users may still need several examples, translation help, or a coach to cover a complex role. User-declared evidence remains a lead for preparation, not external verification.

## Verification commands

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
python -m compileall -q src tests tools
python tools/audit_jobseeker_scenarios.py
python tools/audit_500_jobseeker_scenarios.py
```

The same release cycle also runs the Atlas test suite and the two-product 390px browser regression before publication.
