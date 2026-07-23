# Career Fit example

Run from the repository root:

~~~powershell
career-fit analyze --job-file examples\single_job\people_analytics_job.txt --candidate-file examples\single_job\candidate_profile.txt --evidence-file examples\single_job\evidence.json
career-fit analyze --job-file examples\single_job\people_analytics_job.txt --candidate-file examples\single_job\candidate_profile.txt --evidence-file examples\single_job\evidence.json --review-file examples\single_job\role_review.json
~~~

The example deliberately leaves SQL and HR data without direct structured evidence. The report should show the difference between transferable analytical capability and proof of the exact tool or domain requirement. The candidate text also says that direct HR-data and production-SQL experience is not yet available; those negated mentions should be retained for auditability but excluded from matching. The degree and sponsorship language demonstrates why hard constraints are reported separately.

The first command deliberately returns a review-required checklist with hidden scores. After the user confirms the role requirements, run again with a review object such as `{"scope":"role_requirements","applied":true}`. The reviewed report contains Evidence Fit, Capability Signal, Proof Signal, Application Readiness, explicit evidence and eligibility coverage, and a ranked action plan. It does not contain an Information Confidence score.
