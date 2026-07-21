from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .dictionary import extract
from .metrics import bundle_metrics


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SkillBundle · Explainable Skill Explorer</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #09111f;
      --surface: #111d31;
      --surface-2: #162640;
      --text: #eef5ff;
      --muted: #a5b5cb;
      --line: rgba(193, 215, 245, 0.16);
      --blue: #6ea8ff;
      --cyan: #55d6c2;
      --violet: #b49aff;
      --amber: #ffc76b;
      --shadow: 0 20px 60px rgba(0, 0, 0, 0.24);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-width: 320px;
      color: var(--text);
      background:
        radial-gradient(circle at 8% 0%, rgba(66, 133, 255, 0.23), transparent 34rem),
        radial-gradient(circle at 92% 14%, rgba(180, 154, 255, 0.13), transparent 30rem),
        var(--bg);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }
    .shell { width: min(1180px, calc(100% - 40px)); margin: 0 auto; padding: 34px 0 64px; }
    .topbar, .hero, .section-head, .toolbar, .metric-row, .tag-head, .footer-row {
      display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-mark {
      width: 38px; height: 38px; border-radius: 12px;
      background: linear-gradient(135deg, var(--violet), var(--cyan));
      box-shadow: 0 8px 22px rgba(180, 154, 255, 0.25);
      position: relative;
    }
    .brand-mark::after { content: ""; position: absolute; inset: 10px; border: 2px solid #081322; border-radius: 50%; }
    .brand-name { font-weight: 700; letter-spacing: -0.02em; }
    .eyebrow, .label, .micro { color: var(--muted); font-size: 0.74rem; letter-spacing: 0.08em; text-transform: uppercase; }
    .eyebrow { color: var(--cyan); font-weight: 700; }
    h1, h2, h3, p { margin-top: 0; }
    h1 { max-width: 800px; margin-bottom: 12px; font-size: clamp(2.1rem, 5vw, 4.45rem); line-height: 1.02; letter-spacing: -0.055em; }
    h2 { font-size: clamp(1.35rem, 2.5vw, 2rem); letter-spacing: -0.035em; margin-bottom: 8px; }
    h3 { margin-bottom: 6px; font-size: 1.05rem; }
    .hero { align-items: end; padding: 74px 0 44px; }
    .hero-copy { max-width: 820px; }
    .hero-copy > p { max-width: 690px; color: var(--muted); font-size: 1.08rem; }
    .hero-badge {
      display: inline-flex; gap: 8px; align-items: center; margin-bottom: 18px;
      color: var(--cyan); background: rgba(85, 214, 194, 0.1); border: 1px solid rgba(85, 214, 194, 0.25);
      border-radius: 999px; padding: 7px 11px; font-size: 0.78rem; font-weight: 700;
    }
    .hero-badge::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--cyan); box-shadow: 0 0 14px var(--cyan); }
    .panel, .meaning, .metric {
      background: linear-gradient(145deg, rgba(27, 48, 80, 0.92), rgba(13, 27, 48, 0.88));
      border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow);
    }
    .panel { padding: 24px; }
    .section { margin-top: 28px; }
    .section-head { align-items: end; margin-bottom: 14px; }
    .section-head p { max-width: 650px; margin-bottom: 0; color: var(--muted); }
    .toolbar { justify-content: flex-start; margin-bottom: 12px; }
    textarea {
      width: 100%; min-height: 152px; resize: vertical; padding: 15px;
      color: var(--text); background: rgba(8, 18, 33, 0.72); border: 1px solid var(--line);
      border-radius: 12px; font: inherit; line-height: 1.6; outline: none;
    }
    textarea:focus { border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(85, 214, 194, 0.16); }
    button {
      font: inherit; color: #071323; background: var(--blue); border: 1px solid transparent;
      border-radius: 10px; padding: 9px 14px; cursor: pointer; font-weight: 700;
    }
    button.secondary { color: var(--text); background: transparent; border-color: var(--line); }
    button:focus { border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(85, 214, 194, 0.16); outline: none; }
    .workspace { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(270px, 0.75fr); gap: 18px; align-items: start; }
    .signal-title { margin: 22px 0 9px; }
    .highlighted {
      min-height: 90px; padding: 15px; border: 1px solid var(--line); border-radius: 12px;
      background: rgba(8, 18, 33, 0.55); line-height: 2;
    }
    .skill-mark { border-radius: 6px; padding: 3px 6px; color: #071323; font-weight: 700; white-space: nowrap; }
    .skill-mark[data-category="specific_software_skill"] { background: var(--blue); }
    .skill-mark[data-category="social_skill"] { background: var(--cyan); }
    .skill-mark[data-category="ai_skill"] { background: var(--violet); }
    .skill-mark[data-category="customer_project_management_skill"] { background: var(--amber); }
    .chart-svg { display: block; width: 100%; height: auto; min-height: 250px; overflow: visible; }
    .bar { transition: width 360ms ease; }
    .bar-label { fill: var(--text); font-size: 12px; }
    .bar-count { fill: var(--muted); font-size: 12px; }
    .metric-row { align-items: stretch; margin-top: 16px; }
    .metric { flex: 1 1 120px; padding: 15px; box-shadow: none; background: rgba(17, 29, 49, 0.72); }
    .metric-value { display: block; margin: 7px 0 2px; font-size: 1.6rem; font-weight: 700; letter-spacing: -0.04em; }
    .metric-note { color: var(--muted); font-size: 0.78rem; }
    .tag-list { display: grid; gap: 0; margin-top: 14px; }
    .tag-row { padding: 12px 0; border-bottom: 1px solid var(--line); }
    .tag-name { font-weight: 700; }
    .tag-meta { color: var(--muted); font-size: 0.8rem; }
    .meaning-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .meaning { padding: 19px; box-shadow: none; background: rgba(17, 29, 49, 0.72); }
    .meaning p { margin-bottom: 0; color: var(--muted); font-size: 0.9rem; }
    .footnote { margin-top: 17px; color: var(--muted); font-size: 0.82rem; }
    .footer-row { margin-top: 42px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--muted); font-size: 0.8rem; }
    @media (max-width: 880px) { .workspace { grid-template-columns: 1fr; } }
    @media (max-width: 620px) { .shell { width: min(100% - 26px, 1180px); } .hero { padding-top: 48px; } .meaning-grid { grid-template-columns: 1fr; } .panel { padding: 17px; } }
    @media (prefers-reduced-motion: reduce) { .bar { transition: none; } }
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div class="brand"><span class="brand-mark" aria-hidden="true"></span><span class="brand-name">SkillBundle</span></div>
      <span class="micro">Explainable baseline · v0.1.0</span>
    </header>
    <section class="hero">
      <div class="hero-copy">
        <div class="hero-badge">Text → skills → task mix</div>
        <h1>Make the skill bundle visible.</h1>
        <p>Paste a job description or task sentence. SkillBundle shows what the transparent dictionary baseline found, how those skills map into analytical categories, and what the resulting mix means.</p>
      </div>
    </section>
    <section class="section">
      <div class="section-head">
        <div><span class="eyebrow">Live extractor</span><h2>See the evidence before the metric</h2></div>
        <p>Every highlighted span keeps its source text, canonical label, category, method, and confidence visible.</p>
      </div>
      <div class="panel">
        <div class="toolbar">
          <button id="extract-button" type="button">Extract skills / 提取技能</button>
          <button id="clear-button" class="secondary" type="button">Clear</button>
          <span id="status" class="micro" aria-live="polite">Dictionary baseline ready</span>
        </div>
        <textarea id="skill-text" aria-label="Job text">Build Python and SQL pipelines, communicate with customers, and manage AI projects.</textarea>
        <div class="workspace">
          <div>
            <h3 class="signal-title">Detected spans / 识别到的文本证据</h3>
            <div id="highlighted" class="highlighted" aria-live="polite"></div>
            <div id="tag-list" class="tag-list"></div>
          </div>
          <div>
            <h3 class="signal-title">Category mix / 技能类别结构</h3>
            <svg class="chart-svg" viewBox="0 0 430 270" role="img" aria-labelledby="skill-chart-title skill-chart-desc">
              <title id="skill-chart-title">Detected skill category mix</title>
              <desc id="skill-chart-desc">Horizontal bars show the count of detected skill mentions by analytical category.</desc>
              <g id="bars"></g>
              <text class="bar-count" x="224" y="258" text-anchor="middle">mentions / 提及次数</text>
            </svg>
            <div class="metric-row">
              <div class="metric"><span class="label">技能数 / skills</span><strong id="metric-skills" class="metric-value">0</strong><span class="metric-note">unique concepts</span></div>
              <div class="metric"><span class="label">广度 / breadth</span><strong id="metric-breadth" class="metric-value">0</strong><span class="metric-note">skill domains</span></div>
              <div class="metric"><span class="label">集中度 / HHI</span><strong id="metric-hhi" class="metric-value">0.00</strong><span class="metric-note">task mix concentration</span></div>
            </div>
          </div>
        </div>
        <p id="readout" class="footnote"></p>
      </div>
    </section>
    <section class="section">
      <div class="section-head"><div><span class="eyebrow">Economic meaning</span><h2>What does a skill bundle tell us?</h2></div></div>
      <div class="meaning-grid">
        <article class="meaning"><h3>Breadth is optionality</h3><p>A broader mix means the text mentions more distinct skill domains. It can signal a wider task portfolio, but it is not a direct measure of worker productivity.</p></article>
        <article class="meaning"><h3>HHI is concentration</h3><p>A high HHI means mentions are concentrated in fewer categories; a lower HHI means the bundle is more diversified. It describes structure, not job quality.</p></article>
        <article class="meaning"><h3>Evidence comes first</h3><p>The baseline does not infer hidden skills silently. Unmatched phrases remain unmatched, while every result records its method and review status.</p></article>
      </div>
    </section>
    <footer class="footer-row"><span>Transparent extraction before semantic ambition.</span><span>Baseline outputs are not formal human-reviewed annotations.</span></footer>
  </main>
  <script>
    (function () {
      const textInput = document.getElementById("skill-text");
      const extractButton = document.getElementById("extract-button");
      const clearButton = document.getElementById("clear-button");
      const highlighted = document.getElementById("highlighted");
      const tagList = document.getElementById("tag-list");
      const bars = document.getElementById("bars");
      const status = document.getElementById("status");
      const readout = document.getElementById("readout");
      const metricSkills = document.getElementById("metric-skills");
      const metricBreadth = document.getElementById("metric-breadth");
      const metricHhi = document.getElementById("metric-hhi");
      const labels = {
        specific_software_skill: "Specific software / 专用软件",
        social_skill: "Social skill / 社交技能",
        ai_skill: "AI skill / AI 技能",
        customer_project_management_skill: "Project & customer / 项目与客户"
      };
      const colors = {
        specific_software_skill: "var(--blue)",
        social_skill: "var(--cyan)",
        ai_skill: "var(--violet)",
        customer_project_management_skill: "var(--amber)"
      };
      const ns = "http://www.w3.org/2000/svg";
      const make = function (tag, attrs, text) {
        const node = document.createElementNS(ns, tag);
        Object.keys(attrs || {}).forEach(function (key) { node.setAttribute(key, attrs[key]); });
        if (text != null) node.textContent = text;
        return node;
      };
      const escapeText = function (value) { return String(value == null ? "" : value); };
      function render(payload) {
        const items = payload.extractions || [];
        const metrics = payload.metrics || {};
        highlighted.innerHTML = "";
        let cursor = 0;
        items.forEach(function (item) {
          highlighted.appendChild(document.createTextNode(textInput.value.slice(cursor, item.start)));
          const mark = document.createElement("span");
          mark.className = "skill-mark";
          mark.dataset.category = item.analysis_category_code || "";
          mark.textContent = item.text;
          mark.setAttribute("data-tooltip", escapeText(item.canonical) + " · " + escapeText(labels[item.analysis_category_code] || item.analysis_category_code));
          highlighted.appendChild(mark);
          cursor = item.end;
        });
        highlighted.appendChild(document.createTextNode(textInput.value.slice(cursor) || "No transparent dictionary matches yet."));
        const counts = metrics.category_counts || {};
        const categories = Object.keys(counts);
        const max = Math.max(1, ...categories.map(function (category) { return Number(counts[category] || 0); }));
        bars.innerHTML = "";
        categories.forEach(function (category, index) {
          const y = 24 + index * 53;
          const width = 178 * Number(counts[category] || 0) / max;
          bars.appendChild(make("text", { class: "bar-label", x: 0, y: y + 15 }, labels[category] || category));
          bars.appendChild(make("rect", { class: "bar", x: 220, y: y, width: width, height: 22, rx: 6, fill: colors[category] || "var(--blue)" }));
          bars.appendChild(make("text", { class: "bar-count", x: 208 + width, y: y + 15 }, String(counts[category] || 0)));
        });
        tagList.innerHTML = "";
        items.forEach(function (item) {
          const row = document.createElement("div");
          row.className = "tag-row";
          const head = document.createElement("div");
          head.className = "tag-head";
          const name = document.createElement("span");
          name.className = "tag-name";
          name.textContent = item.canonical || item.text;
          const confidence = document.createElement("span");
          confidence.className = "tag-meta";
          confidence.textContent = "confidence " + Number(item.confidence || 0).toFixed(2);
          head.append(name, confidence);
          const meta = document.createElement("div");
          meta.className = "tag-meta";
          meta.textContent = (labels[item.analysis_category_code] || item.analysis_category_code || "Unmapped") + " · " + (item.mapping_method || "unknown method") + " · " + (item.review_status || "review status unavailable");
          row.append(head, meta);
          tagList.appendChild(row);
        });
        metricSkills.textContent = String(metrics.unique_skill_count || 0);
        metricBreadth.textContent = String(metrics.breadth || 0);
        metricHhi.textContent = Number(metrics.category_hhi || 0).toFixed(2);
        if (items.length) {
          readout.textContent = "Economic reading: this text contains " + items.length + " detected mentions across " + (metrics.breadth || 0) + " skill domains. A lower HHI suggests a more diversified task mix; neither measure predicts wages, employment, or automation.";
          status.textContent = "Updated · " + items.length + " transparent matches";
        } else {
          readout.textContent = "Economic reading: no baseline matches were found. The system leaves unmatched language visible instead of inventing a skill label.";
          status.textContent = "No dictionary matches";
        }
      }
      async function extractText() {
        status.textContent = "Extracting…";
        try {
          const response = await fetch("/api/extract?text=" + encodeURIComponent(textInput.value));
          render(await response.json());
        } catch (error) {
          status.textContent = "The local extractor is unavailable";
          readout.textContent = "Start the local SkillBundle server and try again.";
        }
      }
      extractButton.addEventListener("click", extractText);
      textInput.addEventListener("input", extractText);
      clearButton.addEventListener("click", function () { textInput.value = ""; extractText(); });
      extractText();
    }());
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/extract":
            text = parse_qs(parsed.query).get("text", [""])[0]
            items = extract(text)
            payload = {
                "text": text,
                "extractions": items,
                "metrics": bundle_metrics(items),
            }
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(host: str = "127.0.0.1", port: int = 8766):
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"SkillBundle running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
