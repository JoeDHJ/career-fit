"use strict";
const $ = (id) => document.getElementById(id);
const node = (tag, text, cls) => {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = String(text);
  if (cls) n.className = cls;
  return n;
};
const num = (v) =>
  Number(v).toLocaleString("en-US", { maximumFractionDigits: 2 });
function table(id, head, rows) {
  const t = node("table"),
    h = node("thead"),
    hr = node("tr");
  head.forEach((s) => hr.append(node("th", s)));
  h.append(hr);
  t.append(h);
  const b = node("tbody");
  rows.forEach((r) => {
    const tr = node("tr");
    r.forEach((s) => tr.append(node("td", s)));
    b.append(tr);
  });
  t.append(b);
  $(id).replaceChildren(t);
}
function metric(id, title, value, note) {
  const c = node("div", undefined, "metric");
  c.append(node("span", title), node("strong", value), node("small", note));
  $(id).append(c);
}
function bars(id, rows, max) {
  $(id).replaceChildren();
  rows.forEach(([label, value]) => {
    const row = node("div", undefined, "bar-row"),
      track = node("div", undefined, "bar-track"),
      bar = node("div", undefined, "bar-fill");
    bar.style.width = (100 * value) / max + "%";
    track.append(bar);
    row.append(node("span", label), track, node("span", num(value)));
    $(id).append(row);
  });
}
async function start() {
  const [research, measurement, cases] = await Promise.all(
    ["research", "measurement", "decision-cases"].map((p) =>
      fetch("/api/" + p).then((r) => {
        if (!r.ok) throw new Error("Packaged evidence unavailable");
        return r.json();
      }),
    ),
  );
  $("research-note").textContent = research.interpretation;
  metric(
    "research-metrics",
    "Employer descriptions",
    research.sample_size,
    "Purposive, mixed seniority and geography",
  );
  metric(
    "research-metrics",
    "Employers",
    research.employers,
    "Archived and indexed sources identified",
  );
  metric(
    "research-metrics",
    "Official learning resources",
    research.learning_resources.length,
    "Missing duration is distinct from zero",
  );
  bars(
    "skill-chart",
    research.results.skill_mentions.map((r) => [r.label, r.descriptions]),
    research.sample_size,
  );
  table(
    "jobs",
    ["Employer", "Role", "Geography / seniority", "Qualification gate"],
    research.jobs.map((j) => [
      j.employer,
      j.title,
      j.geography + " / " + j.seniority,
      j.qualification_notes ||
        j.qualification_gate ||
        "Inspect employer criteria",
    ]),
  );
  research.sources.forEach((s) => {
    const p = node("p", undefined, "muted"),
      a = node("a", s.source_id);
    a.href = s.source_url;
    a.target = "_blank";
    a.rel = "noopener";
    p.append(
      a,
      node("span", ` · ${s.access_state} · checked ${s.retrieved_at}`),
    );
    $("job-sources").append(p);
  });
  $("sql-query").textContent = research.queries.skill_mentions;
  const test = measurement.results.filter((r) => r.split === "test");
  table(
    "measurement-table",
    [
      "Target",
      "Extractor",
      "Exact precision",
      "Exact recall",
      "Exact F1",
      "Overlap F1",
    ],
    test.map((r) => {
      const x = r.metrics || r;
      return [
        r.target,
        r.method || r.engine,
        ...[
          x.micro_strict.precision,
          x.micro_strict.recall,
          x.micro_strict.f1,
          x.micro_overlap.f1,
        ].map((v) => Number(v).toFixed(3)),
      ];
    }),
  );
  $("measurement-protocol").textContent =
    typeof measurement.protocol === "string"
      ? measurement.protocol
      : JSON.stringify(measurement.protocol);
  const business = cases.business,
    best = business.scenarios.hybrid;
  metric(
    "business-metrics",
    "Filled positions",
    best.filled + " / 12",
    "Priority units: " + best.filled_priority + " / 24",
  );
  metric(
    "business-metrics",
    "Incremental economic cost",
    num(best.economic_cost) + " USD",
    "Includes vacancy and backfill costs",
  );
  metric(
    "business-metrics",
    "Cash / release hours",
    num(best.cash_cost) + " / " + best.hours,
    "Budget 35,000 USD / 120 hours",
  );
  table(
    "business-table",
    [
      "Route",
      "Filled",
      "Priority units",
      "Cash",
      "Economic cost",
      "Release hours",
    ],
    Object.entries(business.scenarios).map(([name, s]) => [
      name.replaceAll("_", " "),
      s.filled,
      s.filled_priority,
      num(s.cash_cost),
      num(s.economic_cost),
      s.hours,
    ]),
  );
  const costs = {};
  best.assignments.forEach((a) =>
    Object.entries(a.cost_components).forEach(
      ([k, v]) => (costs[k] = (costs[k] || 0) + v),
    ),
  );
  bars(
    "cost-components",
    Object.entries(costs).map(([k, v]) => [k.replaceAll("_", " "), v]),
    Math.max(1, ...Object.values(costs)),
  );
  $("business-note").textContent =
    `Hybrid fills ${business.comparison.additional_positions_filled} additional positions versus no training. Coverage differs, so the ${num(Math.abs(business.comparison.economic_cost_difference))} USD cost difference is not a like-for-like saving.`;
  const sensitivity = () =>
    table(
      "sensitivity-table",
      [
        "Input value",
        "Filled",
        "Priority units",
        "Economic cost",
        "Used hours",
      ],
      cases.business_sensitivity
        .filter((r) => r.changed_input === $("sensitivity-choice").value)
        .map((r) => [
          r.value,
          r.hybrid.filled,
          r.hybrid.filled_priority,
          num(r.hybrid.economic_cost),
          r.hybrid.hours,
        ]),
    );
  $("sensitivity-choice").onchange = sensitivity;
  sensitivity();
}
start().catch((e) => {
  $("research-note").textContent = e.message;
});
