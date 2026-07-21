from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .career import analyze_fit


DEFAULT_JOB = (
    "People Analytics Analyst. Must have Python and SQL. Strongly preferred: "
    "causal inference and data visualization. Excellent stakeholder communication "
    "is required. Experience with HR data is a plus. Bachelor's degree required. "
    "No visa sponsorship is available."
)
DEFAULT_CANDIDATE = (
    "Labor economist with a PhD. Built Python pipelines and panel datasets, used "
    "causal inference for research, communicated findings to academic and policy "
    "audiences, and created data visualizations. Completed applied research "
    "projects but have not yet worked directly with HR data or production SQL."
)


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Career Fit · Explainable Job Fit Explorer</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #08111f;
      --surface: #111f35;
      --surface-2: #172945;
      --surface-3: #1e3658;
      --text: #f1f6ff;
      --muted: #a7b7cc;
      --line: rgba(193, 215, 245, 0.16);
      --blue: #70a9ff;
      --cyan: #56d6c1;
      --violet: #b59cff;
      --amber: #ffc96d;
      --red: #ff8d91;
      --green: #77ddb5;
      --shadow: 0 22px 70px rgba(0, 0, 0, 0.25);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-width: 320px;
      color: var(--text);
      background:
        radial-gradient(circle at 8% 0%, rgba(66, 133, 255, 0.24), transparent 34rem),
        radial-gradient(circle at 94% 10%, rgba(181, 156, 255, 0.14), transparent 32rem),
        var(--bg);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }
    .shell { width: min(1240px, calc(100% - 40px)); margin: 0 auto; padding: 32px 0 68px; }
    .topbar, .hero, .section-head, .toolbar, .summary-grid, .footer-row {
      display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-mark {
      width: 39px; height: 39px; border-radius: 12px;
      background: linear-gradient(135deg, var(--violet), var(--cyan));
      box-shadow: 0 8px 24px rgba(181, 156, 255, 0.25); position: relative;
    }
    .brand-mark::after { content: ""; position: absolute; inset: 10px; border: 2px solid #071321; border-radius: 50%; }
    .brand-name { font-weight: 750; letter-spacing: -0.025em; }
    .micro, .label, .eyebrow { color: var(--muted); font-size: 0.74rem; letter-spacing: 0.08em; text-transform: uppercase; }
    .eyebrow { color: var(--cyan); font-weight: 750; }
    h1, h2, h3, p { margin-top: 0; }
    h1 { max-width: 800px; margin-bottom: 14px; font-size: clamp(2.35rem, 5.6vw, 5rem); line-height: 1.02; letter-spacing: -0.06em; }
    h2 { margin-bottom: 8px; font-size: clamp(1.45rem, 2.7vw, 2.1rem); letter-spacing: -0.04em; }
    h3 { margin-bottom: 7px; font-size: 1.04rem; }
    .hero { align-items: end; padding: 76px 0 48px; }
    .hero-copy { max-width: 850px; }
    .hero-copy > p { max-width: 720px; color: var(--muted); font-size: 1.08rem; }
    .hero-badge {
      display: inline-flex; gap: 8px; align-items: center; margin-bottom: 19px; padding: 7px 12px;
      color: var(--cyan); background: rgba(86, 214, 193, 0.1); border: 1px solid rgba(86, 214, 193, 0.26);
      border-radius: 999px; font-size: 0.78rem; font-weight: 750;
    }
    .hero-badge::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--cyan); box-shadow: 0 0 14px var(--cyan); }
    .hero-note { max-width: 330px; color: var(--muted); font-size: 0.85rem; }
    .panel, .summary-card, .meaning, .gap-card, .detail-card {
      background: linear-gradient(145deg, rgba(28, 50, 83, 0.94), rgba(13, 27, 48, 0.9));
      border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow);
    }
    .panel { padding: 24px; }
    .section { margin-top: 30px; }
    .section-head { align-items: end; margin-bottom: 15px; }
    .section-head p { max-width: 680px; margin-bottom: 0; color: var(--muted); }
    .input-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
    .input-label { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 8px; color: var(--text); font-weight: 700; }
    .input-label span { color: var(--muted); font-size: 0.76rem; font-weight: 400; }
    textarea {
      width: 100%; min-height: 185px; resize: vertical; padding: 15px;
      color: var(--text); background: rgba(7, 17, 31, 0.74); border: 1px solid var(--line);
      border-radius: 12px; font: inherit; line-height: 1.6; outline: none;
    }
    textarea:focus { border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(86, 214, 193, 0.16); }
    .toolbar { justify-content: flex-start; margin-bottom: 16px; }
    button {
      font: inherit; color: #071321; background: var(--blue); border: 1px solid transparent;
      border-radius: 10px; padding: 10px 14px; cursor: pointer; font-weight: 750;
    }
    button.secondary { color: var(--text); background: transparent; border-color: var(--line); }
    button:focus { outline: none; border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(86, 214, 193, 0.16); }
    .status { color: var(--muted); font-size: 0.78rem; }
    .summary-grid { align-items: stretch; margin-top: 16px; }
    .summary-card { flex: 1 1 190px; min-height: 128px; padding: 18px; box-shadow: none; }
    .summary-value { display: block; margin: 8px 0 4px; font-size: clamp(1.55rem, 3vw, 2.3rem); font-weight: 750; letter-spacing: -0.05em; }
    .summary-note { color: var(--muted); font-size: 0.82rem; }
    .result-grid { display: grid; grid-template-columns: minmax(0, 1.42fr) minmax(285px, 0.58fr); gap: 18px; align-items: start; }
    .matrix { display: grid; gap: 7px; }
    .matrix-row {
      display: grid; grid-template-columns: minmax(150px, 1.2fr) 122px 118px 80px; gap: 10px; align-items: center;
      width: 100%; padding: 13px 14px; color: var(--text); text-align: left; background: rgba(7, 17, 31, 0.36);
      border: 1px solid transparent; border-radius: 12px; cursor: pointer;
    }
    .matrix-row:hover, .matrix-row.selected { background: rgba(86, 214, 193, 0.08); border-color: rgba(86, 214, 193, 0.32); }
    .matrix-row > *, .matrix-head > * { min-width: 0; }
    .matrix-head { display: grid; grid-template-columns: minmax(150px, 1.2fr) 122px 118px 80px; gap: 10px; padding: 0 14px 6px; color: var(--muted); font-size: 0.72rem; letter-spacing: 0.07em; text-transform: uppercase; }
    .requirement-name { font-weight: 700; }
    .requirement-type { display: block; margin-top: 2px; color: var(--muted); font-size: 0.74rem; }
    .badge { display: inline-flex; width: fit-content; max-width: 100%; padding: 4px 7px; border-radius: 7px; font-size: 0.72rem; line-height: 1.2; text-align: center; white-space: normal; }
    .badge.direct, .badge.met { color: #052016; background: var(--green); }
    .badge.transferable { color: #191124; background: var(--violet); }
    .badge.direct_weak, .badge.unknown { color: #2b2108; background: var(--amber); }
    .badge.missing, .badge.not_met { color: #2b0b0e; background: var(--red); }
    .score-bar { height: 8px; overflow: hidden; background: rgba(167, 183, 204, 0.16); border-radius: 999px; }
    .score-fill { height: 100%; background: linear-gradient(90deg, var(--blue), var(--cyan)); border-radius: inherit; transition: width 420ms ease; }
    .score-number { color: var(--muted); font-size: 0.78rem; text-align: right; }
    .detail-card { min-height: 330px; padding: 21px; box-shadow: none; }
    .detail-title { margin: 9px 0 5px; font-size: 1.35rem; }
    .detail-list { display: grid; gap: 10px; margin: 22px 0; }
    .detail-line { display: flex; justify-content: space-between; gap: 12px; padding-bottom: 9px; border-bottom: 1px solid var(--line); }
    .detail-line strong { text-align: right; }
    .detail-copy { color: var(--muted); font-size: 0.88rem; }
    .chart-svg { display: block; width: 100%; height: auto; min-height: 290px; }
    .chart-axis { stroke: var(--line); stroke-width: 1; }
    .chart-label { fill: var(--muted); font-size: 11px; }
    .chart-value { fill: var(--text); font-size: 11px; font-weight: 700; }
    .chart-bar { fill: var(--blue); transition: width 420ms ease; }
    .gap-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .gap-card { padding: 18px; box-shadow: none; }
    .gap-card.high { border-color: rgba(255, 141, 145, 0.45); }
    .gap-card.medium { border-color: rgba(255, 201, 109, 0.4); }
    .gap-card.low { border-color: rgba(112, 169, 255, 0.36); }
    .gap-meta { display: flex; justify-content: space-between; gap: 10px; color: var(--muted); font-size: 0.75rem; }
    .gap-action { margin: 12px 0 0; color: var(--text); font-size: 0.91rem; }
    .meaning-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .meaning { padding: 19px; box-shadow: none; background: rgba(17, 31, 53, 0.72); }
    .meaning p { margin-bottom: 0; color: var(--muted); font-size: 0.9rem; }
    .source-note { margin-top: 20px; color: var(--muted); font-size: 0.82rem; }
    .footer-row { margin-top: 44px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--muted); font-size: 0.8rem; }
    @media (max-width: 900px) { .result-grid { grid-template-columns: 1fr; } .gap-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 700px) { .shell { width: min(100% - 26px, 1240px); } .hero { padding-top: 48px; } .input-grid, .meaning-grid, .gap-grid { grid-template-columns: 1fr; } .panel { padding: 17px; } .matrix-row, .matrix-head { grid-template-columns: minmax(125px, 1fr) 96px 72px; } .matrix-row > :nth-child(3), .matrix-head > :nth-child(3) { display: none; } }
    @media (prefers-reduced-motion: reduce) { .score-fill, .chart-bar { transition: none; } }
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div class="brand"><span class="brand-mark" aria-hidden="true"></span><span class="brand-name">Career Fit</span></div>
      <span class="micro">Local-first · explainable baseline · v0.1.0</span>
    </header>
    <section class="hero">
      <div class="hero-copy">
        <div class="hero-badge">岗位要求 → 能力证据 → 下一步行动</div>
        <h1>求职匹配，先看证据。</h1>
        <p>Career Fit maps job requirements to your experience evidence. It separates direct evidence, transferable skills, missing requirements, and hard constraints—so you can improve an application without pretending to predict a hiring decision.</p>
      </div>
      <p class="hero-note">这是可解释的准备度分析，不是录用概率、ATS 通过率或招聘决策工具。</p>
    </section>

    <section class="section">
      <div class="section-head">
        <div><span class="eyebrow">Single job fit / 单岗位匹配</span><h2>把岗位描述和个人经历放在同一张图上</h2></div>
        <p>先识别岗位到底要求什么，再检查你的经历是否提供了可信证据。你可以点击任意要求查看计算依据。</p>
      </div>
      <div class="panel">
        <div class="toolbar">
          <button id="analyze-button" type="button">Analyze fit / 分析匹配</button>
          <button id="example-button" class="secondary" type="button">Load example / 加载示例</button>
          <button id="clear-button" class="secondary" type="button">Clear / 清空</button>
          <span id="status" class="status" aria-live="polite">Local baseline ready / 本地基线已就绪</span>
        </div>
        <div class="input-grid">
          <div>
            <label class="input-label" for="job-input">Job description <span>岗位描述</span></label>
            <textarea id="job-input" aria-label="Job description / 岗位描述"></textarea>
          </div>
          <div>
            <label class="input-label" for="candidate-input">Candidate profile <span>个人经历</span></label>
            <textarea id="candidate-input" aria-label="Candidate profile / 个人经历"></textarea>
          </div>
        </div>
        <div class="summary-grid" aria-live="polite">
          <article class="summary-card"><span class="label">Role Fit / 岗位匹配</span><strong id="fit-score" class="summary-value">—</strong><span class="summary-note">requirement coverage, not hiring probability</span></article>
          <article class="summary-card"><span class="label">Confidence / 判断置信度</span><strong id="confidence-score" class="summary-value">—</strong><span class="summary-note">text completeness and evidence strength</span></article>
          <article class="summary-card"><span class="label">Requirements / 要求数量</span><strong id="requirement-count" class="summary-value">—</strong><span class="summary-note">skills plus admission constraints</span></article>
          <article class="summary-card"><span class="label">Blocked / 准入限制</span><strong id="blocked-count" class="summary-value">—</strong><span class="summary-note">must verify before applying</span></article>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-head"><div><span class="eyebrow">Requirement–Evidence Matrix</span><h2>每个要求，都要有证据或明确缺口</h2></div><p id="decision-label">Run an analysis to see the decision trace / 运行分析以查看判断依据。</p></div>
      <div class="result-grid">
        <div class="panel">
          <div class="matrix matrix-head" aria-hidden="true"><div>Requirement / 要求</div><div>Status / 状态</div><div>Importance / 重要性</div><div>Score</div></div>
          <div id="matrix" class="matrix" aria-live="polite"></div>
        </div>
        <aside id="detail" class="detail-card">
          <span class="eyebrow">Selected requirement / 当前要求</span>
          <h3 class="detail-title">等待分析</h3>
          <p class="detail-copy">点击左侧任意岗位要求，可以看到原文、证据来源、匹配方式和下一步解释。</p>
        </aside>
      </div>
    </section>

    <section class="section">
      <div class="section-head"><div><span class="eyebrow">Fit profile</span><h2>匹配不是一个孤立的总分</h2></div><p>这张图展示每项要求的相对匹配程度；高分不代表录用，低分也不代表没有职业可能。</p></div>
      <div class="panel"><svg id="fit-chart" class="chart-svg" viewBox="0 0 900 340" role="img" aria-label="Requirement match profile / 岗位要求匹配画像"></svg></div>
    </section>

    <section class="section">
      <div class="section-head"><div><span class="eyebrow">Gap → Action</span><h2>把缺口转成下一步行动</h2></div><p>建议按照岗位重要性、证据不足程度和准备成本排序。它是透明的准备建议，不是预测录用效果。</p></div>
      <div id="gap-list" class="gap-grid" aria-live="polite"></div>
    </section>

    <section class="section">
      <div class="section-head"><div><span class="eyebrow">Economic meaning</span><h2>如何理解这些数字</h2></div></div>
      <div class="meaning-grid">
        <article class="meaning"><h3>匹配度 ≠ 录用概率</h3><p>Role Fit Score 只是岗位要求与现有证据的加权覆盖程度。没有真实招聘结果数据，系统不会声称估计企业的录用决定。</p></article>
        <article class="meaning"><h3>证据比关键词更重要</h3><p>简历提到一个技能，不等于已经证明能力。项目、任务、应用场景、时间和可量化结果会提高证据强度。</p></article>
        <article class="meaning"><h3>硬约束单独处理</h3><p>执照、工作许可、强制学历和地点等准入条件不能被软技能高分抵消；缺失时先核实，而不是直接给出乐观结论。</p></article>
      </div>
      <p class="source-note">Career Fit v0.1 使用可复现的技能字典和分析分类。所有评分权重在代码和文档中公开；本地输入不会被服务器永久保存。</p>
    </section>
    <footer class="footer-row"><span>Career Fit · evidence before confidence</span><span>透明的求职准备分析，不是招聘决策系统。</span></footer>
  </main>
  <script>
    (function () {
      const DEFAULT_JOB = __DEFAULT_JOB__;
      const DEFAULT_CANDIDATE = __DEFAULT_CANDIDATE__;
      const jobInput = document.getElementById("job-input");
      const candidateInput = document.getElementById("candidate-input");
      const analyzeButton = document.getElementById("analyze-button");
      const exampleButton = document.getElementById("example-button");
      const clearButton = document.getElementById("clear-button");
      const status = document.getElementById("status");
      const matrix = document.getElementById("matrix");
      const detail = document.getElementById("detail");
      const gapList = document.getElementById("gap-list");
      const fitChart = document.getElementById("fit-chart");
      const decisionLabel = document.getElementById("decision-label");
      const fitScore = document.getElementById("fit-score");
      const confidenceScore = document.getElementById("confidence-score");
      const requirementCount = document.getElementById("requirement-count");
      const blockedCount = document.getElementById("blocked-count");
      const statusLabels = {
        direct: "Direct / 直接",
        direct_weak: "Weak evidence / 证据较弱",
        transferable: "Transferable / 可迁移",
        missing: "Missing / 缺口",
        met: "Met / 已满足",
        not_met: "Not met / 不满足",
        unknown: "Verify / 待核实"
      };
      const importanceLabels = {
        must: "Must / 必需",
        strongly_preferred: "Strongly preferred / 强烈优先",
        preferred: "Preferred / 优先",
        inferred: "Inferred / 职责推断"
      };
      let latest = null;

      function make(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text != null) node.textContent = text;
        return node;
      }
      function svgNode(tag, attrs, text) {
        const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
        Object.keys(attrs || {}).forEach(function (key) { node.setAttribute(key, attrs[key]); });
        if (text != null) node.textContent = text;
        return node;
      }
      function clearNode(node) { while (node.firstChild) node.removeChild(node.firstChild); }
      function setText(node, value) { node.textContent = value == null ? "—" : String(value); }
      function percent(value) { return Math.round(Number(value || 0)) + "/100"; }
      function renderDetail(item) {
        clearNode(detail);
        detail.appendChild(make("span", "eyebrow", "Selected requirement / 当前要求"));
        detail.appendChild(make("h3", "detail-title", item.canonical_skill || item.original_text));
        detail.appendChild(make("span", "badge " + (item.status || "unknown"), statusLabels[item.status] || item.status));
        const list = make("div", "detail-list");
        [["Original text / 原文", item.original_text], ["Type / 类型", item.requirement_type], ["Importance / 重要性", importanceLabels[item.importance_level] || item.importance_level], ["Match / 匹配度", percent(item.match_score * 100)], ["Evidence / 证据", (item.evidence_ids || []).length ? item.evidence_ids.join(", ") : "No linked evidence / 没有对应证据"]].forEach(function (pair) {
          const row = make("div", "detail-line"); row.append(make("span", "detail-copy", pair[0]), make("strong", "", pair[1])); list.appendChild(row);
        });
        detail.appendChild(list);
        const copy = item.status === "direct" ? "已有直接证据。下一步应优化表达和结果量化，而不是盲目重复学习。" : item.status === "transferable" ? "现有技能属于相邻领域。建议用一个小项目证明迁移关系。" : item.status === "direct_weak" ? "文本提到了该技能，但证据强度较低。补充任务、场景和结果。" : item.hard_constraint ? "这是准入条件，不能被软匹配度抵消；请先核实。" : "当前个人文本中没有找到可靠证据，先区分表达缺口和结构性缺口。";
        detail.appendChild(make("p", "detail-copy", copy));
        if (item.source_context) detail.appendChild(make("p", "detail-copy", "Job context / 岗位语境：" + item.source_context));
      }
      function renderMatrix(items) {
        clearNode(matrix);
        if (!items.length) { matrix.appendChild(make("p", "detail-copy", "暂无结果。请先运行分析。")); return; }
        items.forEach(function (item, index) {
          const row = make("button", "matrix-row" + (index === 0 ? " selected" : ""));
          row.type = "button";
          const name = make("span", ""); name.append(make("span", "requirement-name", item.canonical_skill || item.original_text), make("span", "requirement-type", item.requirement_type === "skill" ? "Skill / 技能" : "Admission constraint / 准入条件"));
          const badge = make("span", "badge " + (item.status || "unknown"), statusLabels[item.status] || item.status);
          const importance = make("span", "detail-copy", importanceLabels[item.importance_level] || item.importance_level);
          const score = make("span", "score-number", item.hard_constraint ? (item.status === "met" ? "Met" : "Verify") : percent(item.match_score * 100));
          row.append(name, badge, importance, score);
          row.addEventListener("click", function () { matrix.querySelectorAll(".matrix-row").forEach(function (other) { other.classList.remove("selected"); }); row.classList.add("selected"); renderDetail(item); });
          matrix.appendChild(row);
        });
        renderDetail(items[0]);
      }
      function renderChart(items) {
        clearNode(fitChart);
        const visible = items.slice(0, 8);
        if (!visible.length) return;
        const left = 232; const max = 100; const barWidth = 590;
        fitChart.appendChild(svgNode("line", { class: "chart-axis", x1: left, y1: 18, x2: left, y2: 320 }));
        visible.forEach(function (item, index) {
          const y = 25 + index * 37;
          const value = item.hard_constraint ? (item.status === "met" ? 100 : 0) : Math.max(0, Math.min(100, Number(item.match_score || 0) * 100));
          fitChart.appendChild(svgNode("text", { class: "chart-label", x: 0, y: y + 13 }, String(item.canonical_skill || item.original_text).slice(0, 30)));
          fitChart.appendChild(svgNode("rect", { class: "score-bar", x: left, y: y + 3, width: barWidth, height: 17, rx: 6, fill: "rgba(167,183,204,0.16)" }));
          fitChart.appendChild(svgNode("rect", { class: "chart-bar", x: left, y: y + 3, width: barWidth * value / max, height: 17, rx: 6 }));
          fitChart.appendChild(svgNode("text", { class: "chart-value", x: left + barWidth + 12, y: y + 16 }, item.hard_constraint ? (item.status === "met" ? "met" : "verify") : Math.round(value) + "%"));
        });
        fitChart.appendChild(svgNode("text", { class: "chart-label", x: left, y: 338 }, "0"));
        fitChart.appendChild(svgNode("text", { class: "chart-label", x: left + barWidth, y: 338, "text-anchor": "end" }, "100"));
      }
      function renderGaps(gaps) {
        clearNode(gapList);
        if (!gaps.length) { gapList.appendChild(make("article", "gap-card low", "No priority gaps found / 暂无优先缺口")); return; }
        gaps.slice(0, 6).forEach(function (gap) {
          const card = make("article", "gap-card " + (gap.priority || "medium"));
          const meta = make("div", "gap-meta"); meta.append(make("span", "", (gap.gap_type || "gap").replaceAll("_", " ")), make("span", "", (gap.priority || "medium") + " priority"));
          card.append(meta, make("h3", "", gap.canonical_skill));
          card.append(make("p", "gap-action", gap.action));
          card.append(make("p", "detail-copy", "时间：" + gap.time_horizon + "。" + gap.basis));
          gapList.appendChild(card);
        });
      }
      function render(payload) {
        latest = payload;
        const summary = payload.summary || {};
        setText(fitScore, percent(summary.role_fit_score));
        setText(confidenceScore, percent(summary.assessment_confidence));
        setText(requirementCount, summary.requirement_count);
        setText(blockedCount, summary.blocking_constraint_count);
        setText(decisionLabel, summary.decision_label);
        renderMatrix(payload.requirements || []);
        renderChart(payload.requirements || []);
        renderGaps(payload.gaps || []);
        status.textContent = "Updated / 已更新 · " + (summary.requirement_count || 0) + " requirements / 项要求";
      }
      async function analyze() {
        if (!jobInput.value.trim() || !candidateInput.value.trim()) { status.textContent = "Both texts are required / 请输入岗位和个人经历"; return; }
        status.textContent = "Analyzing locally… / 正在本地分析…";
        try {
          const response = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ job_text: jobInput.value, candidate_text: candidateInput.value }) });
          if (!response.ok) throw new Error("request failed");
          render(await response.json());
        } catch (error) { status.textContent = "Local analyzer unavailable / 本地分析器不可用"; }
      }
      exampleButton.addEventListener("click", function () { jobInput.value = DEFAULT_JOB; candidateInput.value = DEFAULT_CANDIDATE; analyze(); });
      analyzeButton.addEventListener("click", analyze);
      clearButton.addEventListener("click", function () { jobInput.value = ""; candidateInput.value = ""; clearNode(matrix); clearNode(gapList); clearNode(fitChart); detail.querySelector(".detail-title").textContent = "等待分析"; [fitScore, confidenceScore, requirementCount, blockedCount].forEach(function (node) { node.textContent = "—"; }); decisionLabel.textContent = "Run an analysis to see the decision trace / 运行分析以查看判断依据。"; status.textContent = "Cleared / 已清空"; });
      jobInput.value = DEFAULT_JOB;
      candidateInput.value = DEFAULT_CANDIDATE;
      analyze();
    }());
  </script>
</body>
</html>
"""


def _json_literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def render_page() -> str:
    return HTML.replace("__DEFAULT_JOB__", _json_literal(DEFAULT_JOB)).replace(
        "__DEFAULT_CANDIDATE__", _json_literal(DEFAULT_CANDIDATE)
    )


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_page(self) -> None:
        body = render_page().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/analyze":
            self._send_json({"error": "not_found"}, status=404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = analyze_fit(
                str(payload.get("job_text", "")),
                str(payload.get("candidate_text", "")),
                payload.get("evidence"),
            )
            self._send_json(result)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": "invalid_request", "detail": str(error)}, status=400)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/analyze":
            query = parse_qs(parsed.query)
            self._send_json(
                analyze_fit(
                    query.get("job", [""])[0], query.get("candidate", [""])[0]
                )
            )
            return
        self._send_page()


def serve(host: str = "127.0.0.1", port: int = 8766):
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Career Fit running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
