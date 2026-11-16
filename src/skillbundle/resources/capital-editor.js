"use strict";
// Plain-language editors share the same input object as the advanced import.
const originalFill = fill,
  originalRequest = requestInput,
  originalPersonal = personal,
  originalWorkforce = workforce;
const legacyCase =
  new URLSearchParams(location.search).get("case") === "legacy";
let editorEpoch = 0;
function currentInput() {
  return JSON.parse($("input-json").value);
}
function draftInput() {
  const data = currentInput();
  data.budget = Number($("budget").value);
  if (mode === "personal") {
    data.hours = Number($("hours").value);
    data.weekly_hours = Number($("weekly").value);
    data.hourly_value =
      $("hourly").value === "" ? null : Number($("hourly").value);
    data.occupation_id = $("occupation").value;
    data.geography = $("geography").value;
    if ($("benefit").value !== "")
      data.benefits = {
        annual_benefit: Number($("benefit").value),
        years: Number($("years").value),
        discount_rate: Number($("discount").value),
        basis: $("basis").value,
      };
    else delete data.benefits;
  } else data.hours_budget = Number($("hours").value);
  return data;
}
function savePlanContext() {
  sessionStorage.setItem(
    "career-fit-plan-context",
    JSON.stringify(draftInput()),
  );
}
function changeInput(path, value, unreviewRole = false) {
  const data = currentInput();
  let parent = data;
  path.slice(0, -1).forEach((k) => {
    parent = parent[k];
  });
  parent[path.at(-1)] = value;
  if (unreviewRole)
    data.analysis_input.review = {
      ...data.analysis_input.review,
      applied: false,
    };
  $("input-json").value = JSON.stringify(data, null, 2);
  $("review").checked = false;
  invalidate();
}
function field(parent, caption, value, path, options = {}) {
  const label = el("label", "", caption);
  const input = el(
    options.choices ? "select" : options.multiline ? "textarea" : "input",
  );
  if (options.choices)
    options.choices.forEach((v) => {
      const o = el("option", "", v);
      o.value = v;
      input.append(o);
    });
  else if (options.number) {
    input.type = "number";
    input.min = options.min ?? 0;
    input.step = options.step ?? "any";
  }
  if (options.multiline) input.rows = 3;
  input.value = value ?? "";
  input.setAttribute("aria-label", caption);
  input.oninput = () =>
    changeInput(
      path,
      options.number
        ? input.value === "" && options.nullable
          ? null
          : Number(input.value)
        : input.value,
      options.unreviewRole,
    );
  label.append(input);
  parent.append(label);
  return input;
}
function link(parent, title, url) {
  if (!/^https?:\/\//.test(url || "")) return;
  const a = el("a", "", title);
  a.href = url;
  a.target = "_blank";
  a.rel = "noopener";
  parent.append(a);
}
function card(title, note, open = false) {
  const d = el("details", "editor-card");
  d.open = open;
  d.append(el("summary", "", title));
  if (note) d.append(el("p", "muted", note));
  return d;
}
function renderRole(data) {
  $("role-editor").replaceChildren();
  if (mode !== "personal") return;
  const box = card(
    "Role and experience · review before planning",
    data.input_status,
    false,
  );
  field(
    box,
    "Role description",
    data.analysis_input.job_text,
    ["analysis_input", "job_text"],
    { multiline: true, unreviewRole: true },
  );
  field(
    box,
    "Experience and existing work",
    data.analysis_input.candidate_text,
    ["analysis_input", "candidate_text"],
    { multiline: true, unreviewRole: true },
  );
  const button = el("button", "secondary", "Review role and evidence");
  button.onclick = () => {
    const input = currentInput().analysis_input;
    input.review = { ...input.review, applied: false };
    savePlanContext();
    sessionStorage.setItem("career-fit-review-input", JSON.stringify(input));
    location.href = "/";
  };
  box.append(
    el(
      "p",
      "muted",
      "Editing either text requires a fresh evidence review. Use the review workspace, then choose Plan training from this evidence.",
    ),
    button,
  );
  if (data.jd_source)
    link(
      box,
      "Employer source · check full criteria",
      data.jd_source.source_url,
    );
  $("role-editor").append(box);
}
catalog = function (data) {
  $("catalog-table").replaceChildren();
  if (mode !== "personal") return;
  (data.courses || []).forEach((course, i) => {
    const box = card(
      course.title,
      course.outcome_status ||
        "Self-directed work sample with supplied planning assumptions",
    );
    const facts = course.provider
      ? `${course.provider} · provider duration: ${course.provider_hours ?? "not stated"} h · content fee: ${course.provider_fee ?? "not stated"}. ${course.provider_fee_scope || ""}`
      : "Practice effort and fees are planning assumptions. Completion must be assessed.";
    box.append(el("p", "muted", facts));
    if (course.source) link(box, "Provider details", course.source.source_url);
    if (course.caution) box.append(el("p", "notice", course.caution));
    const controls = el("div", "controls");
    field(
      controls,
      "Planned hours · " + course.title,
      course.hours,
      ["courses", i, "hours"],
      { number: true },
    );
    field(
      controls,
      "Fee · " + course.title,
      course.fee,
      ["courses", i, "fee"],
      { number: true },
    );
    field(
      controls,
      "Eligibility · " + course.title,
      course.eligibility,
      ["courses", i, "eligibility"],
      { choices: ["unknown", "met", "not_met"] },
    );
    box.append(controls);
    box.append(
      el(
        "p",
        "muted",
        `Entry conditions: ${course.entry_conditions || "Check the task prerequisites"}. Learning/practice allocation: ${course.learning_hours_assumption ?? "not specified"} / ${course.practice_hours_assumption ?? "not specified"} hours.`,
      ),
    );
    field(
      box,
      "Artifact · " + course.title,
      course.artifact,
      ["courses", i, "artifact"],
      { multiline: true },
    );
    field(
      box,
      "Completion check · " + course.title,
      course.completion_criterion,
      ["courses", i, "completion_criterion"],
      { multiline: true },
    );
    const mapping = el("p", "muted");
    mapping.textContent =
      "Skill targets: " +
      course.skills.map((s) => course.skill_labels?.[s] || s).join(", ") +
      ". Prerequisites: " +
      (course.prerequisites.join(", ") || "none supplied");
    box.append(mapping);
    if (data.reviewed_requirements) {
      const choices = card("Map this task to reviewed role skills");
      data.reviewed_requirements
        .filter((r) => !r.hard_constraint && r.skill_id)
        .forEach((r) => {
          const label = el("label", "confirm"),
            check = el("input");
          check.type = "checkbox";
          check.checked = course.skills.includes(r.skill_id);
          check.setAttribute(
            "aria-label",
            course.id + " targets " + r.canonical_skill,
          );
          check.oninput = () => {
            const input = currentInput(),
              item = input.courses[i];
            item.skills = item.skills.filter((s) => s !== r.skill_id);
            if (check.checked) item.skills.push(r.skill_id);
            item.skill_labels = {
              ...item.skill_labels,
              [r.skill_id]: r.canonical_skill,
            };
            $("input-json").value = JSON.stringify(input, null, 2);
            $("review").checked = false;
            invalidate();
          };
          label.append(check, el("span", "", r.canonical_skill));
          choices.append(label);
        });
      box.append(choices);
    }
    $("catalog-table").append(box);
  });
};
function workforceEditor(data) {
  const target = $("workforce-editor");
  target.hidden = mode !== "workforce";
  target.replaceChildren();
  if (mode !== "workforce") return;
  target.append(
    el("h3", "", "Business assumptions"),
    el(
      "p",
      "muted",
      "Use pseudonymous IDs. Levels and thresholds use a scenario 0–1 scale. Unknown consent or eligibility excludes internal moves. Expand each record to adjust it without editing JSON.",
    ),
  );
  const controls = el("div", "controls");
  field(
    controls,
    "Planning horizon · days",
    data.horizon_days ?? 90,
    ["horizon_days"],
    { number: true, min: 1, step: 1 },
  );
  field(
    controls,
    "Learning effect multiplier",
    data.training_effect_multiplier ?? 1,
    ["training_effect_multiplier"],
    { number: true, step: 0.05 },
  );
  field(controls, "Solver", data.solver ?? "exact", ["solver"], {
    choices: ["exact", "milp"],
  });
  target.append(controls);
  const labelById = {
    "2.A.1.e": "Mathematics",
    "2.A.2.a": "Critical thinking",
    "2.A.1.d": "Speaking",
    "2.B.4.h": "Systems evaluation",
  };
  const skillName = (s) => labelById[s] || s;
  const roles = card(
    `Roles · ${data.roles.reduce((s, r) => s + r.positions, 0)} positions`,
    "Role priorities define the first objective; a high-priority role can take precedence over more lower-priority positions.",
    true,
  );
  data.roles.forEach((role, i) => {
    const box = card(role.title);
    const c = el("div", "controls");
    [
      ["positions", "Positions", 1],
      ["priority", "Priority units", 0.01],
      ["external_cost", "External hiring cash cost", 0],
      ["vacancy_daily_cost", "Vacancy cost per day", 0],
      ["internal_lead_days", "Internal lead days", 0],
      ["external_lead_days", "Hiring lead days", 0],
    ].forEach(([key, title, min]) =>
      field(
        c,
        title + " · " + role.id,
        role[key] ?? (key === "priority" ? 1 : 0),
        ["roles", i, key],
        { number: true, min },
      ),
    );
    field(
      c,
      "External eligibility · " + role.id,
      role.external_eligible,
      ["roles", i, "external_eligible"],
      { choices: ["unknown", "met", "not_met"] },
    );
    box.append(c);
    Object.entries(role.requirements).forEach(([s, r]) => {
      const row = el("div", "controls");
      field(
        row,
        "Minimum " + skillName(s) + " · " + role.id,
        r.minimum,
        ["roles", i, "requirements", s, "minimum"],
        { number: true, step: 0.05 },
      );
      field(
        row,
        "Importance " + skillName(s) + " · " + role.id,
        r.weight,
        ["roles", i, "requirements", s, "weight"],
        { number: true },
      );
      box.append(row);
    });
    roles.append(box);
  });
  target.append(roles);
  const staff = card(
    `Employees · ${data.employees.length} pseudonymous records`,
    "Backfill is charged once for an employee assigned internally, including a direct move. Released hours count training time only.",
  );
  data.employees.forEach((employee, i) => {
    const box = card(employee.id);
    const c = el("div", "controls");
    field(
      c,
      "Hourly released-time cost · " + employee.id,
      employee.hourly_cost,
      ["employees", i, "hourly_cost"],
      { number: true },
    );
    field(
      c,
      "Backfill cash cost · " + employee.id,
      employee.backfill_cost ?? 0,
      ["employees", i, "backfill_cost"],
      { number: true },
    );
    field(
      c,
      "Consent · " + employee.id,
      employee.consent ?? "unknown",
      ["employees", i, "consent"],
      { choices: ["unknown", "met", "not_met"] },
    );
    Object.entries(employee.skills).forEach(([s, v]) =>
      field(
        c,
        skillName(s) + " · " + employee.id,
        v,
        ["employees", i, "skills", s],
        { number: true, step: 0.05 },
      ),
    );
    data.roles.forEach((r) =>
      field(
        c,
        "Eligibility " + r.id + " · " + employee.id,
        employee.eligibility[r.id] ?? "unknown",
        ["employees", i, "eligibility", r.id],
        { choices: ["unknown", "met", "not_met"] },
      ),
    );
    box.append(c);
    staff.append(box);
  });
  target.append(staff);
  const training = card(
    `Training · ${data.training.length} packages`,
    "Outcomes describe assumed attainable levels. The effect multiplier changes gains above current levels; it does not multiply existing competence.",
  );
  data.training.forEach((course, i) => {
    const box = card(course.title),
      c = el("div", "controls");
    [
      ["hours", "Release hours"],
      ["fee", "Cash fee"],
      ["capacity", "Seats"],
      ["lead_days", "Calendar lead days"],
    ].forEach(([key, title]) =>
      field(
        c,
        title + " · " + course.id,
        course[key] ?? 0,
        ["training", i, key],
        { number: true },
      ),
    );
    field(
      c,
      "Eligibility · " + course.id,
      course.eligibility,
      ["training", i, "eligibility"],
      { choices: ["unknown", "met", "not_met"] },
    );
    box.append(c);
    ["outcomes", "prerequisites"].forEach((key) =>
      Object.entries(course[key]).forEach(([s, v]) =>
        field(
          box,
          (key === "outcomes" ? "Target " : "Prerequisite ") +
            skillName(s) +
            " · " +
            course.id,
          v,
          ["training", i, key, s],
          { number: true, step: 0.05 },
        ),
      ),
    );
    field(
      box,
      "Assessment artifact · " + course.id,
      course.artifact,
      ["training", i, "artifact"],
      { multiline: true },
    );
    field(
      box,
      "Assessment criterion · " + course.id,
      course.completion_criterion,
      ["training", i, "completion_criterion"],
      { multiline: true },
    );
    training.append(box);
  });
  target.append(training);
}
const rubricText = {
  correctness: "Correctness: totals reconcile and checks pass",
  reproducibility: "Reproducibility: another person can review or run it",
  interpretation: "Interpretation: units, assumptions and decisions explained",
  independence: "Independence: can explain and adapt the work",
};
function progressEditor(data) {
  const target = $("progress-editor");
  target.replaceChildren();
  if (mode !== "personal") return;
  const box = card(
    "Track work and assess the artifact",
    "Records stay in this browser session until exported or explicitly transferred. Passing requires completed work, an artifact, review notes and all four rubric levels at least 2.",
  );
  if (!data.progress?.length) {
    data.progress = (data.courses || []).map((c) => ({
      course_id: c.id,
      status: "planned",
      assessment: "not_reviewed",
      actual_hours: null,
      artifact: "",
      review_note: "",
      rubric: {
        correctness: 0,
        reproducibility: 0,
        interpretation: 0,
        independence: 0,
      },
    }));
    $("input-json").value = JSON.stringify(data, null, 2);
  }
  data.progress.forEach((record, i) => {
    const title =
      data.courses.find((c) => c.id === record.course_id)?.title ||
      record.course_id;
    const item = card(title),
      c = el("div", "controls");
    field(c, "Status · " + title, record.status, ["progress", i, "status"], {
      choices: ["planned", "in_progress", "completed", "paused"],
    });
    field(
      c,
      "Assessment · " + title,
      record.assessment,
      ["progress", i, "assessment"],
      { choices: ["not_reviewed", "revise", "passed"] },
    );
    field(
      c,
      "Actual hours · " + title,
      record.actual_hours,
      ["progress", i, "actual_hours"],
      { number: true, nullable: true },
    );
    item.append(c);
    field(item, "Artifact location · " + title, record.artifact, [
      "progress",
      i,
      "artifact",
    ]);
    field(
      item,
      "Review notes · " + title,
      record.review_note,
      ["progress", i, "review_note"],
      { multiline: true },
    );
    const levels = el("div", "controls");
    Object.entries(rubricText).forEach(([key, label]) =>
      field(
        levels,
        label + " · " + title,
        record.rubric[key] ?? 0,
        ["progress", i, "rubric", key],
        { number: true, min: 0, step: 1 },
      ),
    );
    item.append(
      levels,
      el(
        "p",
        "muted",
        "Levels: 0 unchecked; 1 incomplete or material errors; 2 core criterion met; 3 independently handles a new variation. A user-entered pass is not independent verification.",
      ),
    );
    box.append(item);
  });
  const button = el(
    "button",
    "secondary",
    "Transfer assessed artifacts to evidence review",
  );
  button.id = "transfer-progress";
  button.onclick = async () => {
    try {
      const input = requestInput();
      input.confirm_evidence_transfer = true;
      const response = await fetch("/api/progress-evidence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Transfer failed");
      savePlanContext();
      sessionStorage.setItem(
        "career-fit-review-input",
        JSON.stringify(payload.analysis_input),
      );
      location.href = "/";
    } catch (e) {
      $("status").textContent = e.message;
      $("status").scrollIntoView({ block: "center" });
    }
  };
  box.append(
    el(
      "p",
      "muted",
      "Review notes should name the reviewer or state self-assessment. Evidence is transferred only after you choose this action; scores remain hidden until you confirm the role review.",
    ),
    button,
  );
  target.append(box);
}
fill = function (data) {
  originalFill(data);
  if (data.benefits) {
    $("benefit").value = data.benefits.annual_benefit;
    $("basis").value = data.benefits.basis;
    $("years").value = data.benefits.years;
    $("discount").value = data.benefits.discount_rate;
  }
  renderRole(data);
  workforceEditor(data);
  progressEditor(data);
};
loadDemo = async function () {
  const epoch = ++editorEpoch,
    selected = mode;
  const query = new URLSearchParams(location.search);
  const caseName = legacyCase
    ? "legacy"
    : selected === "personal"
      ? "analyst"
      : query.get("case") === "business"
        ? "business"
        : "legacy";
  const response = await fetch(
    `/api/capital-demo?mode=${selected}&case=${caseName}`,
  );
  const data = await response.json();
  if (epoch !== editorEpoch || selected !== mode) return;
  if (!response.ok) throw new Error(data.detail || "Case unavailable");
  fill(data);
  $("case-note").textContent =
    caseName === "analyst"
      ? "Archived actual NHS analyst role, five official learning resources and two assessed practice options. Learner B is fictional. Free content excludes software, equipment and exams; unknown duration is a planning assumption."
      : caseName === "business"
        ? "30 synthetic employees, 12 positions and three training packages. Consent, priorities, backfill, vacancy losses, lead times and training effects are scenario assumptions. Medium allocation needs the optimization extra installed."
        : selected === "workforce"
          ? "Six synthetic employees and four positions; actual O*NET importance weights. All employee levels, thresholds and costs are supplied scenarios."
          : "Legacy senior-role case. Candidate A and training options are fictional; experience gates remain unresolved.";
};
requestInput = function () {
  const data = originalRequest();
  return data;
};
personal = function () {
  originalPersonal();
  $("evidence")
    .querySelectorAll(".progress-summary")
    .forEach((n) => n.remove());
  if (result.progress) {
    const completed = new Set(
      result.progress.records
        .filter((r) => r.status === "completed")
        .map((r) => r.course_id),
    );
    const unfinished = (result.best_plan?.selected_courses || [])
      .filter((c) => !completed.has(c.id))
      .reduce((s, c) => s + c.hours, 0);
    const note = el(
      "p",
      "muted progress-summary",
      `Progress: ${result.progress.passed_records} user-assessed pass(es); ${result.progress.reported_actual_hours} reported actual hours. Selected unfinished tasks retain ${unfinished} planned hours plus preparation. The portfolio cost describes the current planning inputs. Before planning the next stage, update available cash and hours to your remaining budget; actual hours are not automatically deducted. Transfer assessed work for review to update the skill evidence.`,
    );
    $("evidence").append(note);
  }
};
workforce = function () {
  originalWorkforce();
  const best = result.scenarios.hybrid;
  $("metrics").querySelectorAll(".metric small")[2].textContent =
    "Fees, release time, backfill and vacancy costs";
  $("decision-copy").textContent =
    result.objective +
    ` Horizon: ${result.horizon_days} days. Filled priority: ${best.filled_priority}.`;
  table(
    "comparison-table",
    [
      "Scenario",
      "Filled / unfilled",
      "Priority units",
      "Cash cost",
      "Economic cost",
      "Release hours",
    ],
    Object.entries(result.scenarios).map(([k, s]) => [
      labels[k],
      s.filled + " / " + s.unfilled,
      s.filled_priority,
      money(s.cash_cost),
      money(s.economic_cost),
      fmt(s.hours),
    ]),
  );
  table(
    "evidence-table",
    [
      "Employee",
      "Role",
      "Eligibility",
      "Consent",
      "Weighted coverage",
      "Gaps on scenario scale",
    ],
    result.matrix.map((e) => [
      e.employee_id,
      e.role_id,
      e.eligibility,
      e.consent,
      fmt(e.weighted_coverage * 100) + "%",
      e.gap_details
        .filter((g) => g.gap > 0)
        .map((g) => g.label + ": " + g.gap)
        .join("; ") || "None",
    ]),
  );
};
$("input-json").addEventListener("change", () => {
  try {
    const data = currentInput();
    renderRole(data);
    workforceEditor(data);
    progressEditor(data);
  } catch (e) {
    $("status").textContent = e.message;
  }
});
// Transfer keeps exact reviewed IDs but uses explicit effort assumptions, with access unchecked.
initialize = async function () {
  if (new URLSearchParams(location.search).get("case") === "business")
    await switchMode("workforce");
  else await loadDemo();
  const transferred = sessionStorage.getItem("career-fit-investment");
  if (!transferred) return;
  sessionStorage.removeItem("career-fit-investment");
  try {
    const data = currentInput(),
      loaded = JSON.parse(transferred);
    const incoming = loaded.analysis_input || loaded;
    const cached = sessionStorage.getItem("career-fit-plan-context");
    if (cached) {
      sessionStorage.removeItem("career-fit-plan-context");
      const previous = JSON.parse(cached);
      if (
        previous.analysis_input.job_text === incoming.job_text &&
        previous.analysis_input.candidate_text === incoming.candidate_text
      ) {
        previous.analysis_input = incoming;
        previous.reviewed_requirements = loaded.requirements || [];
        previous.courses.forEach((course) => {
          ["skills", "prerequisites"].forEach((key) => {
            course[key] = course[key].map((s) => {
              if (!s.startsWith("user.custom.")) return s;
              const match = previous.reviewed_requirements.find(
                (r) =>
                  r.canonical_skill === course.skill_labels?.[s] &&
                  !r.hard_constraint,
              );
              if (match) {
                course.skill_labels[match.skill_id] = match.canonical_skill;
                return match.skill_id;
              }
              course.eligibility = "unknown";
              return "history.unmapped." + course.id;
            });
          });
        });
        fill(previous);
        $("case-note").textContent =
          "Reviewed evidence updated. Your resource catalog, costs and learning progress are preserved for this browser session. Custom task targets are remapped by reviewed label; removed targets require a new mapping.";
        return;
      }
    }
    data.analysis_input = incoming;
    data.reviewed_requirements = loaded.requirements || [];
    data.occupation_id = "";
    data.geography = "";
    data.confirmed_prerequisites = [];
    delete data.progress;
    data.courses = (loaded.requirements || [])
      .filter((r) => !r.hard_constraint && r.status !== "direct" && r.skill_id)
      .slice(0, 8)
      .map((r, i) => ({
        id: "proof-" + (i + 1),
        title: "Build evidence for " + r.canonical_skill,
        hours: /sql|python|excel/i.test(r.canonical_skill) ? 16 : 8,
        fee: 0,
        skills: [r.skill_id],
        skill_labels: { [r.skill_id]: r.canonical_skill },
        prerequisites: [],
        eligibility: "unknown",
        artifact:
          "One role-specific work sample demonstrating " + r.canonical_skill,
        completion_criterion:
          "A reviewer reproduces the work, reconciles its outputs and asks for an independent variation",
        outcome_status:
          "Assumed effort: 16 hours for a named software task, 8 otherwise. Zero fee excludes software/equipment. Confirm access and task scope.",
      }));
    data.input_status =
      "User-reviewed role and evidence; self-directed task effort and fee are assumptions";
    fill(data);
    $("case-note").textContent =
      "Your exact current skill IDs are loaded. Review task scope, effort and access eligibility below. Occupation and geography need separate confirmation.";
  } catch (e) {
    $("status").textContent = e.message;
  }
};
$("load-demo").onclick = () =>
  loadDemo().catch((e) => ($("status").textContent = e.message));
$("save-plan").onclick = () => {
  try {
    const data = draftInput();
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
    );
    const a = el("a");
    a.href = url;
    a.download = "career-fit-inputs-and-progress.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    $("status").textContent =
      "Saved locally. This file includes your input text, artifacts and progress; choose where to keep it.";
  } catch (e) {
    $("status").textContent = e.message;
  }
};
$("restore-plan").onchange = async (event) => {
  try {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 320000)
      throw new Error("Plan file must be at most 320,000 bytes");
    const data = JSON.parse(await file.text());
    if (!data || Array.isArray(data) || typeof data !== "object")
      throw new Error("Plan file must contain an input object");
    const next = data.analysis_input
      ? "personal"
      : Array.isArray(data.employees)
        ? "workforce"
        : null;
    if (!next)
      throw new Error(
        "Use the saved inputs file, rather than a result-only export",
      );
    if (next !== mode) await switchMode(next);
    fill(data);
    $("case-note").textContent =
      "Restored local draft. Review the source, remaining budgets, eligibility and assessment records before comparing.";
  } catch (e) {
    $("status").textContent = e.message;
  } finally {
    event.target.value = "";
  }
};
initialize().catch((e) => ($("status").textContent = e.message));
