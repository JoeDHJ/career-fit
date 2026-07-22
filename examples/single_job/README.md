# Career Fit example

Run from the repository root:

~~~powershell
career-fit analyze --job-file examples\single_job\people_analytics_job.txt --candidate-file examples\single_job\candidate_profile.txt --evidence-file examples\single_job\evidence.json
~~~

The example deliberately leaves SQL and HR data without direct structured evidence. The report should show the difference between transferable analytical capability and proof of the exact tool or domain requirement. The candidate text also says that direct HR-data and production-SQL experience is not yet available; those negated mentions should be retained for auditability but excluded from matching. The degree and sponsorship language demonstrates why hard constraints are reported separately.

The expected report contains Evidence Fit, Capability Signal, Proof Signal, Application Readiness, Information Confidence, and a ranked action plan.
