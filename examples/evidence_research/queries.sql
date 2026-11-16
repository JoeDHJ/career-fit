
CREATE TABLE jobs(job_id TEXT PRIMARY KEY, employer TEXT, family TEXT, seniority TEXT, geography TEXT, access_state TEXT);
CREATE TABLE requirements(job_id TEXT, skill TEXT, label TEXT, level TEXT, PRIMARY KEY(job_id,skill), FOREIGN KEY(job_id) REFERENCES jobs(job_id));
CREATE TABLE learning(resource_id TEXT PRIMARY KEY, provider TEXT, title TEXT, provider_hours REAL, provider_fee REAL, planning_hours REAL);

-- skill_mentions
SELECT skill, label, COUNT(DISTINCT job_id) AS descriptions, SUM(level='required') AS explicitly_required, SUM(level='preferred') AS preferred FROM requirements GROUP BY skill,label ORDER BY descriptions DESC,skill;

-- family_skills
SELECT j.family, r.label, COUNT(*) AS descriptions FROM jobs j JOIN requirements r USING(job_id) GROUP BY j.family,r.label ORDER BY j.family,descriptions DESC,r.label;

-- sample_coverage
SELECT geography,access_state,COUNT(*) AS descriptions FROM jobs GROUP BY geography,access_state ORDER BY geography,access_state;

-- seniority
SELECT seniority,COUNT(*) AS descriptions FROM jobs GROUP BY seniority ORDER BY descriptions DESC,seniority;

-- resource_completeness
SELECT COUNT(*) AS resources, SUM(provider_hours IS NOT NULL) AS observed_duration, SUM(provider_hours IS NULL) AS duration_needs_assumption, SUM(provider_fee=0) AS free_content_access FROM learning;