from __future__ import annotations

import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import ProxyHandler, Request, build_opener

from .career import analyze_fit, compare_roles
from .document_io import DocumentExtractionError, extract_import_preview
from .llm_review import LLMNotConfiguredError, LLMReviewClient, LLMReviewError
from .reports import build_markdown_plan, build_pdf_plan


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
LLM_REVIEW_CLIENT = LLMReviewClient()
ATLAS_URL = os.environ.get("CAREER_FIT_ATLAS_URL", "").rstrip("/")


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Career Fit | Evidence-first job search planner</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #07111e;
      --surface: rgba(17, 31, 53, 0.82);
      --surface-strong: #132640;
      --surface-soft: rgba(26, 49, 81, 0.62);
      --text: #f4f7fc;
      --muted: #aab9cc;
      --line: rgba(191, 215, 244, 0.16);
      --blue: #79aaff;
      --cyan: #5fe1c7;
      --violet: #c0a9ff;
      --amber: #ffd276;
      --red: #ff9098;
      --green: #7be0b6;
      --shadow: 0 24px 80px rgba(0, 0, 0, 0.28);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-width: 320px;
      color: var(--text);
      background:
        radial-gradient(circle at 8% 0%, rgba(70, 137, 255, 0.24), transparent 32rem),
        radial-gradient(circle at 92% 5%, rgba(193, 169, 255, 0.18), transparent 28rem),
        linear-gradient(180deg, #081423 0%, var(--bg) 70%);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }
    body::before {
      content: ""; position: fixed; inset: 0; pointer-events: none; opacity: 0.13;
      background-image: linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px);
      background-size: 48px 48px; mask-image: linear-gradient(to bottom, black, transparent 78%);
    }
    .shell { width: min(1240px, calc(100% - 40px)); margin: 0 auto; padding: 30px 0 70px; position: relative; }
    .topbar, .hero, .section-head, .toolbar, .summary-grid, .footer-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-mark { width: 40px; height: 40px; border-radius: 13px; background: conic-gradient(from 210deg, var(--violet), var(--cyan), var(--blue), var(--violet)); box-shadow: 0 8px 28px rgba(105, 176, 255, .24); position: relative; animation: drift 8s ease-in-out infinite; }
    .brand-mark::before { content: ""; position: absolute; inset: 9px; border: 2px solid #081423; border-radius: 50%; }
    .brand-mark::after { content: ""; position: absolute; width: 6px; height: 6px; left: 17px; top: 17px; border-radius: 50%; background: #081423; }
    .brand-name { font-weight: 800; letter-spacing: -0.03em; }
    .micro, .label, .eyebrow { color: var(--muted); font-size: .72rem; letter-spacing: .09em; text-transform: uppercase; }
    .eyebrow { color: var(--cyan); font-weight: 800; }
    h1, h2, h3, p { margin-top: 0; }
    h1 { max-width: 850px; margin-bottom: 16px; font-size: clamp(2.45rem, 6vw, 5.45rem); line-height: .98; letter-spacing: -.07em; }
    h2 { margin-bottom: 8px; font-size: clamp(1.45rem, 2.8vw, 2.2rem); letter-spacing: -.045em; }
    h3 { margin-bottom: 7px; font-size: 1.04rem; }
    .hero { align-items: end; padding: 82px 0 48px; }
    .hero-copy { max-width: 900px; }
    .hero-copy > p { max-width: 750px; color: var(--muted); font-size: 1.08rem; }
    .hero-badge { display: inline-flex; gap: 8px; align-items: center; margin-bottom: 20px; padding: 7px 12px; color: var(--cyan); background: rgba(95, 225, 199, .1); border: 1px solid rgba(95, 225, 199, .28); border-radius: 999px; font-size: .77rem; font-weight: 800; }
    .hero-badge::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--cyan); box-shadow: 0 0 16px var(--cyan); animation: pulse 2.2s ease-in-out infinite; }
    .hero-note { max-width: 335px; color: var(--muted); font-size: .86rem; }
    .panel, .summary-card, .meaning, .gap-card, .detail-card, .signal-card { background: linear-gradient(145deg, rgba(27, 51, 84, .94), rgba(10, 24, 43, .9)); border: 1px solid var(--line); border-radius: 19px; box-shadow: var(--shadow); }
    .panel { padding: 24px; }
    .section { margin-top: 32px; }
    .section-head { align-items: end; margin-bottom: 15px; }
    .section-head p { max-width: 700px; margin-bottom: 0; color: var(--muted); }
    .input-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
    .input-label { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 8px; color: var(--text); font-weight: 750; }
    .input-label span { color: var(--muted); font-size: .76rem; font-weight: 400; }
    textarea { width: 100%; min-height: 185px; resize: vertical; padding: 15px; color: var(--text); background: rgba(5, 14, 27, .78); border: 1px solid var(--line); border-radius: 12px; font: inherit; line-height: 1.6; outline: none; }
    textarea:focus { border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(95, 225, 199, .16); }
    .input-grid select { width: 100%; padding: 10px 12px; color: var(--text); background: rgba(5, 14, 27, .78); border: 1px solid var(--line); border-radius: 10px; font: inherit; }
    .input-grid select:focus { outline: none; border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(95, 225, 199, .16); }
    button { font: inherit; color: #07111e; background: var(--blue); border: 1px solid transparent; border-radius: 10px; padding: 10px 14px; cursor: pointer; font-weight: 800; transition: transform 180ms ease, filter 180ms ease; }
    button:hover { filter: brightness(1.08); transform: translateY(-1px); }
    button.secondary { color: var(--text); background: transparent; border-color: var(--line); }
    button:focus { outline: none; border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(95, 225, 199, .16); }
    .toolbar { justify-content: flex-start; margin-bottom: 16px; }
    .status { color: var(--muted); font-size: .78rem; }
    .semantic-panel { margin-top: 16px; padding: 18px; border: 1px solid var(--line); border-radius: 18px; background: var(--surface-soft); }
    .semantic-panel[hidden] { display: none; }
    .semantic-list { display: grid; gap: 10px; margin-top: 14px; }
    .semantic-item { padding: 12px 14px; border-radius: 12px; background: var(--surface); border: 1px solid var(--line); }
    .semantic-meta { display: flex; justify-content: space-between; gap: 12px; color: var(--muted); font-size: .78rem; }
    .semantic-item p { margin: 8px 0 0; color: var(--text); font-size: .86rem; line-height: 1.45; }
     .privacy-note { margin: 14px 0 0; color: var(--muted); font-size: .78rem; }
     .occupation-context-panel { margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--line); }
     .occupation-search-row { display: flex; align-items: end; gap: 10px; flex-wrap: wrap; }
     .occupation-search-row label { display: grid; gap: 7px; flex: 1 1 320px; color: var(--muted); font-size: .78rem; }
     .occupation-search-row input { width: 100%; padding: 12px 13px; color: var(--text); background: var(--surface); border: 1px solid var(--line); border-radius: 12px; font: inherit; }
     .occupation-search-row input:focus { border-color: var(--blue); outline: none; box-shadow: 0 0 0 4px rgba(0, 113, 227, .12); }
     .occupation-status, .occupation-interpretation { margin: 12px 0 0; color: var(--muted); font-size: .8rem; }
     .occupation-candidates, .occupation-reviews { display: grid; gap: 9px; margin-top: 14px; }
     .occupation-candidate, .occupation-review { padding: 13px; background: var(--surface-soft); border: 1px solid var(--line); border-radius: 13px; }
     .occupation-candidate { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
     .occupation-candidate strong { display: block; }
     .occupation-candidate span, .occupation-review-meta { color: var(--muted); font-size: .75rem; }
     .occupation-candidate-note { display: block; max-width: 620px; margin-top: 5px; line-height: 1.4; }
     .occupation-candidate button { padding: 8px 12px; font-size: .8rem; box-shadow: none; }
     .occupation-review blockquote { margin: 8px 0 0; font-size: .85rem; line-height: 1.45; }
     .occupation-review a { color: var(--blue); }
     .occupation-review-tags { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 8px; }
     .occupation-review-tag { padding: 3px 7px; color: var(--blue); background: #edf5ff; border-radius: 999px; font-size: .7rem; }
     .occupation-review-filter-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 12px; }
     .occupation-review-filter-row label { display: grid; gap: 5px; color: var(--muted); font-size: .7rem; }
     .occupation-review-filter-row select { width: 100%; min-width: 0; padding: 7px 8px; font-size: .76rem; }
     .occupation-context-empty { color: var(--muted); font-size: .82rem; }
     .market-context { display: grid; gap: 12px; margin-top: 10px; padding: 16px; background: var(--surface-soft); border: 1px solid var(--line); border-radius: 13px; }
     .market-context[hidden] { display: none; }
     .market-metrics, .market-adjacent { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
     .market-metric, .market-adjacent-card { display: grid; gap: 4px; padding: 10px; background: var(--surface); border: 1px solid var(--line); border-radius: 9px; }
     .market-metric span, .market-adjacent-card small { color: var(--muted); font-size: .7rem; }
     .market-metric strong { font-size: .95rem; }
     .market-tasks { color: var(--muted); font-size: .78rem; }
     .market-tasks ul { margin: 5px 0 0; padding-left: 18px; }
     .market-adjacent { grid-template-columns: repeat(2, minmax(0, 1fr)); }
     .market-adjacent-card strong { font-size: .82rem; }
     .occupation-disclosure { margin-top: 13px; color: var(--muted); font-size: .72rem; }
     .occupation-disclosure summary { cursor: pointer; }
     .occupation-disclosure p { max-width: 680px; margin: 8px 0 0; line-height: 1.45; }
    .compare-panel { margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--line); }
    .compare-panel .section-head { margin-bottom: 10px; }
    .compare-panel .section-head p { max-width: 620px; font-size: .84rem; }
    .compare-input { min-height: 150px; }
    .comparison-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }
    .comparison-card { padding: 17px; background: var(--surface-soft); border: 1px solid var(--line); border-radius: 15px; }
    .comparison-card:first-child { border-color: rgba(0, 113, 227, .52); box-shadow: 0 0 0 2px rgba(0, 113, 227, .08); }
    .comparison-rank { display: flex; justify-content: space-between; gap: 10px; color: var(--muted); font-size: .72rem; letter-spacing: .07em; text-transform: uppercase; }
    .comparison-card h3 { margin: 9px 0 6px; }
    .comparison-basis { min-height: 50px; color: var(--muted); font-size: .82rem; }
    .comparison-metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; margin: 14px 0; }
    .comparison-metric { padding: 9px; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; }
    .comparison-metric strong { display: block; margin-top: 2px; font-size: 1.08rem; }
    .comparison-metric span { color: var(--muted); font-size: .7rem; }
    .comparison-action { margin: 0 0 13px; color: var(--muted); font-size: .8rem; }
    .comparison-card button { width: 100%; }
    .comparison-panel[hidden] { display: none; }
    .fingerprint-panel { display: grid; gap: 16px; margin-top: 18px; padding-top: 18px; border-top: 1px solid var(--line); }
    .fingerprint-layout { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(260px, .75fr); gap: 14px; }
    .fingerprint-card, .bundle-card { padding: 16px; background: var(--surface-soft); border: 1px solid var(--line); border-radius: 15px; }
    .fingerprint-card h3, .bundle-card h3 { margin-bottom: 5px; }
    .category-profile { display: grid; gap: 12px; }
    .category-row { display: grid; gap: 6px; }
    .category-meta, .bundle-meta { display: flex; justify-content: space-between; gap: 12px; color: var(--muted); font-size: .76rem; }
    .category-name { font-weight: 700; }
    .category-track { height: 9px; overflow: hidden; background: rgba(167, 183, 204, .16); border-radius: 999px; }
    .category-fill { height: 100%; background: linear-gradient(90deg, var(--blue), var(--cyan)); border-radius: inherit; transition: width 520ms ease; }
    .category-foot { display: flex; justify-content: space-between; gap: 12px; color: var(--muted); font-size: .72rem; }
    .mismatch-list, .bundle-grid { display: grid; gap: 10px; }
    .mismatch-item { padding: 11px 0; border-bottom: 1px solid var(--line); }
    .mismatch-item:last-child { border-bottom: 0; padding-bottom: 0; }
    .mismatch-item strong { display: block; margin-bottom: 3px; }
    .bundle-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .bundle-card { box-shadow: none; }
    .bundle-card.supported { border-color: rgba(52, 199, 89, .42); }
    .bundle-card h3 { font-size: .96rem; }
    .bundle-action { margin: 10px 0 0; color: var(--text); font-size: .83rem; }
    .bundle-status { margin-top: 8px; color: var(--muted); font-size: .75rem; }
    .fingerprint-panel[hidden] { display: none; }
    .summary-grid { align-items: stretch; margin-top: 16px; }
    .summary-card { flex: 1 1 190px; min-height: 128px; padding: 18px; box-shadow: none; }
    .summary-value { display: block; margin: 8px 0 4px; font-size: clamp(1.55rem, 3vw, 2.3rem); font-weight: 800; letter-spacing: -.05em; }
    .summary-note { color: var(--muted); font-size: .82rem; }
    .signal-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
    .signal-card { display: grid; grid-template-columns: 84px minmax(0, 1fr); gap: 16px; align-items: center; padding: 18px; box-shadow: none; overflow: hidden; position: relative; }
    .signal-card::after { content: ""; position: absolute; width: 120px; height: 120px; right: -45px; bottom: -52px; border-radius: 50%; background: radial-gradient(circle, rgba(95, 225, 199, .16), transparent 68%); }
    .ring { --ring-color: var(--cyan); --ring-progress: 0deg; width: 78px; height: 78px; display: grid; place-items: center; border-radius: 50%; background: conic-gradient(var(--ring-color) 0 var(--ring-progress), rgba(170, 190, 215, .14) var(--ring-progress) 360deg); position: relative; transition: background 600ms ease; }
    .ring::before { content: ""; position: absolute; inset: 7px; border-radius: 50%; background: #10233d; border: 1px solid var(--line); }
    .ring strong { position: relative; font-size: 1.08rem; }
    .signal-card p { margin-bottom: 0; color: var(--muted); font-size: .84rem; }
    .result-grid { display: grid; grid-template-columns: minmax(0, 1.42fr) minmax(285px, .58fr); gap: 18px; align-items: start; }
    .matrix { display: grid; gap: 7px; }
    .matrix-row { display: grid; grid-template-columns: minmax(150px, 1.2fr) 142px 120px 80px; gap: 10px; align-items: center; width: 100%; padding: 13px 14px; color: var(--text); text-align: left; background: rgba(7, 17, 31, .36); border: 1px solid transparent; border-radius: 12px; cursor: pointer; }
    .matrix-row:hover, .matrix-row.selected { background: rgba(95, 225, 199, .08); border-color: rgba(95, 225, 199, .32); }
    .matrix-row > *, .matrix-head > * { min-width: 0; }
    .matrix-head { display: grid; grid-template-columns: minmax(150px, 1.2fr) 142px 120px 80px; gap: 10px; padding: 0 14px 6px; color: var(--muted); font-size: .71rem; letter-spacing: .07em; text-transform: uppercase; }
    .requirement-name { font-weight: 750; }
    .requirement-type { display: block; margin-top: 2px; color: var(--muted); font-size: .74rem; }
    .badge { display: inline-flex; width: fit-content; max-width: 100%; padding: 4px 7px; border-radius: 7px; font-size: .71rem; line-height: 1.2; text-align: center; white-space: normal; }
    .badge.direct, .badge.met { color: #052016; background: var(--green); }
    .badge.transferable { color: #191124; background: var(--violet); }
    .badge.direct_weak, .badge.unknown { color: #2b2108; background: var(--amber); }
    .badge.missing, .badge.not_met { color: #2b0b0e; background: var(--red); }
    .score-bar { height: 8px; overflow: hidden; background: rgba(167, 183, 204, .16); border-radius: 999px; }
    .score-fill { height: 100%; background: linear-gradient(90deg, var(--blue), var(--cyan)); border-radius: inherit; transition: width 520ms ease; }
    .score-number { color: var(--muted); font-size: .78rem; text-align: right; }
    .detail-card { min-height: 365px; padding: 21px; box-shadow: none; }
    .detail-title { margin: 9px 0 5px; font-size: 1.35rem; }
    .detail-list { display: grid; gap: 10px; margin: 22px 0; }
    .detail-line { display: flex; justify-content: space-between; gap: 12px; padding-bottom: 9px; border-bottom: 1px solid var(--line); }
    .detail-line strong { max-width: 60%; text-align: right; }
    .detail-copy { color: var(--muted); font-size: .88rem; }
    .chart-svg { display: block; width: 100%; height: auto; min-height: 290px; }
    .chart-axis { stroke: var(--line); stroke-width: 1; }
    .chart-label { fill: var(--muted); font-size: 11px; }
    .chart-value { fill: var(--text); font-size: 11px; font-weight: 750; }
    .chart-bar { fill: var(--blue); transition: width 520ms ease; }
    .gap-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .gap-card { padding: 18px; box-shadow: none; }
    .gap-card.high { border-color: rgba(255, 144, 152, .5); }
    .gap-card.medium { border-color: rgba(255, 210, 118, .42); }
    .gap-card.low { border-color: rgba(121, 170, 255, .38); }
    .gap-meta { display: flex; justify-content: space-between; gap: 10px; color: var(--muted); font-size: .73rem; }
    .gap-action { margin: 12px 0 0; color: var(--text); font-size: .91rem; }
    .gap-artifact { margin: 12px 0 0; padding: 10px; color: var(--muted); background: rgba(7, 17, 31, .35); border-left: 2px solid var(--cyan); font-size: .82rem; }
    .meaning-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
    .meaning { padding: 19px; box-shadow: none; background: rgba(17, 31, 53, .72); }
    .meaning p { margin-bottom: 0; color: var(--muted); font-size: .9rem; }
    .source-note { margin-top: 20px; color: var(--muted); font-size: .82rem; }
    .footer-row { margin-top: 44px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--muted); font-size: .8rem; }
    @keyframes pulse { 0%, 100% { opacity: .55; transform: scale(.86); } 50% { opacity: 1; transform: scale(1.12); } }
    @keyframes drift { 0%, 100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-3px) rotate(8deg); } }
    @media (max-width: 1020px) { .signal-grid { grid-template-columns: 1fr; } .meaning-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 900px) { .result-grid { display: block !important; } .result-grid > * { width: 100%; margin-bottom: 18px; } .gap-grid, .comparison-grid, .bundle-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .fingerprint-layout { grid-template-columns: 1fr; } }
    @media (max-width: 700px) { .shell { width: min(100% - 26px, 1240px); } .hero { padding-top: 48px; } .input-grid, .meaning-grid, .gap-grid { grid-template-columns: 1fr; } .panel { padding: 17px; } .matrix-row, .matrix-head { grid-template-columns: minmax(125px, 1fr) 106px 78px; } .matrix-row > :nth-child(3), .matrix-head > :nth-child(3) { display: none; } .signal-card { grid-template-columns: 74px minmax(0, 1fr); } .ring { width: 68px; height: 68px; } }
    @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
  </style>
  <style id="apple-inspired-overrides">
    :root {
      color-scheme: light;
      --bg: #f5f5f7;
      --surface: #ffffff;
      --surface-strong: #ffffff;
      --surface-soft: #fbfbfd;
      --text: #1d1d1f;
      --muted: #6e6e73;
      --line: #d2d2d7;
      --blue: #0071e3;
      --cyan: #0071e3;
      --violet: #0071e3;
      --amber: #ff9f0a;
      --red: #ff3b30;
      --green: #34c759;
      --shadow: 0 12px 36px rgba(0, 0, 0, .07);
    }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
      -webkit-font-smoothing: antialiased;
    }
    body::before { display: none; }
    .shell { width: min(1180px, calc(100% - 56px)); padding: 0 0 72px; }
    .topbar { min-height: 72px; border-bottom: 1px solid rgba(210, 210, 215, .72); }
    .brand { gap: 11px; }
    .brand-mark { width: 26px; height: 26px; border-radius: 8px; background: var(--text); box-shadow: none; animation: none; }
    .brand-mark::before { content: "CF"; inset: 0; display: grid; place-items: center; border: 0; border-radius: 0; color: #fff; font-size: 10px; font-weight: 750; }
    .brand-mark::after { display: none; }
    .brand-name { font-size: 16px; font-weight: 680; }
    .micro, .label, .eyebrow { color: var(--muted); font-size: 12px; letter-spacing: .04em; }
    .eyebrow { color: var(--blue); font-weight: 650; }
    h1 { max-width: 820px; margin-bottom: 22px; font-size: clamp(2.75rem, 6vw, 4.9rem); line-height: 1.03; letter-spacing: -.065em; font-weight: 720; }
    h2 { margin-bottom: 8px; font-size: clamp(1.45rem, 2.8vw, 2rem); letter-spacing: -.045em; font-weight: 680; }
    h3 { margin-bottom: 7px; font-size: 1rem; font-weight: 650; }
    .hero { display: block; padding: 78px 0 42px; }
    .hero-copy > p { max-width: 700px; color: var(--muted); font-size: 1.18rem; line-height: 1.45; letter-spacing: -.02em; }
    .hero-badge { display: inline-block; margin-bottom: 18px; padding: 0; color: var(--blue); background: transparent; border: 0; border-radius: 0; font-size: 12px; font-weight: 650; letter-spacing: .04em; }
    .hero-badge::before { display: none; }
    .hero-note { display: none; }
    .workflow { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin: 0 0 22px; padding: 0; list-style: none; }
    .workflow-step { display: grid; grid-template-columns: 28px minmax(0, 1fr); grid-template-rows: auto auto; column-gap: 9px; align-items: center; padding: 11px 13px; color: var(--muted); background: var(--surface-soft); border: 1px solid var(--line); border-radius: 12px; }
    .workflow-step span { grid-row: 1 / span 2; display: grid; place-items: center; width: 26px; height: 26px; color: var(--muted); border: 1px solid var(--line); border-radius: 50%; font-size: .78rem; font-weight: 700; }
    .workflow-step strong { color: var(--text); font-size: .82rem; font-weight: 650; }
    .workflow-step small { font-size: .72rem; }
    .workflow-step.active, .workflow-step.current { border-color: rgba(0, 113, 227, .42); background: #f4f8ff; }
    .workflow-step.active span, .workflow-step.current span { color: #fff; background: var(--blue); border-color: var(--blue); }
    #app[data-workflow-stage="intake"] .review-stage, #app[data-workflow-stage="intake"] .plan-stage { display: none; }
    #app[data-workflow-stage="review"] .intake-stage, #app[data-workflow-stage="review"] .plan-stage { display: none; }
    #app[data-workflow-stage="plan"] .intake-stage, #app[data-workflow-stage="plan"] .review-stage { display: none; }
    .file-import-row { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; margin-top: 9px; }
    .file-input-label { color: var(--blue); font-size: .78rem; font-weight: 600; cursor: pointer; }
    .file-import-row input[type="file"] { max-width: 220px; color: var(--muted); font-size: .76rem; }
    .document-preview { margin-top: 12px; padding: 12px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface-soft); }
    .document-preview textarea, #semantic-payload { width: 100%; margin-top: 7px; }
    .review-item-copy strong { overflow-wrap: anywhere; }
    .review-evidence-grid { display: grid; grid-column: 1 / -1; grid-template-columns: minmax(110px, .7fr) minmax(130px, 1fr) minmax(130px, 1fr) 92px 92px auto; gap: 7px; align-items: end; width: 100%; }
    .review-evidence-field { display: grid; gap: 4px; min-width: 0; color: var(--muted); font-size: .68rem; }
    .review-evidence-grid input, .review-evidence-grid select { min-width: 0; width: 100%; padding: 8px 9px; color: var(--text); background: var(--surface); border: 1px solid var(--line); border-radius: 8px; font: inherit; font-size: .78rem; }
    .review-evidence-grid button { white-space: nowrap; }
    .review-check { display: inline-flex; align-items: center; gap: 7px; color: var(--muted); font-size: .78rem; }
    .badge.claimed, .badge.transferable_claimed { color: #8a5a00; background: #fff5dc; }
    .panel, .summary-card, .meaning, .gap-card, .detail-card, .signal-card { background: var(--surface); border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow); }
    .panel { padding: 28px; }
    .section { margin-top: 54px; }
    .section-head { align-items: end; margin-bottom: 18px; }
    .section-head p { max-width: 700px; margin-bottom: 0; color: var(--muted); font-size: .9rem; }
    .input-grid { gap: 16px; }
    .input-label { color: var(--muted); font-size: 12px; font-weight: 600; letter-spacing: .02em; text-transform: uppercase; }
    .input-label span { color: var(--muted); font-size: 12px; }
    textarea { min-height: 185px; padding: 15px; color: var(--text); background: var(--surface); border: 1px solid var(--line); border-radius: 12px; font: inherit; line-height: 1.6; }
    textarea:focus { border-color: var(--blue); box-shadow: 0 0 0 4px rgba(0, 113, 227, .12); }
    button { color: #fff; background: var(--blue); border-radius: 12px; padding: 12px 20px; font-size: 15px; font-weight: 650; box-shadow: 0 5px 14px rgba(0, 113, 227, .2); transition: background 180ms ease, transform 180ms ease, box-shadow 180ms ease; }
    button:hover { filter: none; background: #0077ed; transform: translateY(-1px); }
    button.secondary { color: var(--text); background: transparent; border-color: var(--line); box-shadow: none; }
    button.secondary:hover { background: #f5f5f7; }
    button:focus { border-color: var(--blue); box-shadow: 0 0 0 4px rgba(0, 113, 227, .12); }
    .toolbar { justify-content: flex-start; margin-bottom: 22px; }
    .status { color: var(--muted); font-size: .8rem; }
    .privacy-note { margin: 16px 0 0; color: var(--muted); font-size: .78rem; }
    .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); align-items: stretch; margin-top: 42px; padding: 24px 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
    .summary-card { min-height: auto; padding: 0 24px; border: 0; border-left: 1px solid var(--line); border-radius: 0; box-shadow: none; }
    .summary-card:first-child { padding-left: 0; border-left: 0; }
    .summary-card:last-child { padding-right: 0; }
    .summary-card:nth-child(1) .summary-value { color: var(--blue); }
    .summary-card:nth-child(3) .summary-value { color: var(--green); }
    .summary-value { display: block; margin: 8px 0 4px; color: var(--text); font-size: clamp(1.8rem, 3vw, 2.35rem); font-weight: 680; letter-spacing: -.05em; }
    .summary-note { color: var(--muted); font-size: .78rem; }
    .coverage-panel, .review-panel { margin-top: 24px; padding: 22px; background: var(--surface-soft); border: 1px solid var(--line); border-radius: 15px; }
    .coverage-panel[hidden], .review-panel[hidden] { display: none; }
    .coverage-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .coverage-card { display: grid; gap: 5px; padding: 14px; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; }
    .coverage-card span, .coverage-card small { color: var(--muted); font-size: .76rem; }
    .coverage-card strong { font-size: 1.5rem; }
    .review-panel { background: var(--surface); }
    .review-requirements, .review-added-list { display: grid; gap: 8px; }
    .review-item { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 12px; background: var(--surface-soft); border: 1px solid var(--line); border-radius: 10px; }
    .review-item-copy { display: grid; gap: 3px; min-width: 0; }
    .review-item-copy small { color: var(--muted); }
    .review-item select, .review-evidence-input, .review-add-row input { min-width: 0; padding: 9px 10px; color: var(--text); background: var(--surface); border: 1px solid var(--line); border-radius: 8px; font: inherit; }
    .review-evidence-row, .review-add-row { display: flex; gap: 8px; align-items: end; margin-top: 12px; }
    .review-evidence-row { grid-column: 1 / -1; }
    .review-evidence-row input { flex: 1; }
    .review-add-row label { display: grid; flex: 1; gap: 5px; color: var(--muted); font-size: .78rem; }
    .review-add-row label span { font-size: .7rem; }
    .review-added-list { margin-top: 10px; color: var(--muted); font-size: .8rem; }
    .guided-intake { margin-top: 18px; padding: 16px; background: var(--surface-soft); border: 1px solid var(--line); border-radius: 12px; }
    .guided-intake[hidden] { display: none; }
    .guided-intake-copy { margin: -8px 0 14px; color: var(--muted); font-size: .82rem; }
    .guided-intake-grid { display: grid; grid-template-columns: minmax(130px, .8fr) repeat(3, minmax(140px, 1fr)) 96px 82px 82px minmax(90px, .55fr); gap: 8px; align-items: end; }
    .guided-intake-grid label { display: grid; gap: 4px; min-width: 0; color: var(--muted); font-size: .68rem; }
    .guided-intake-grid input, .guided-intake-grid select, .guided-intake-grid textarea { min-width: 0; width: 100%; padding: 8px 9px; color: var(--text); background: var(--surface); border: 1px solid var(--line); border-radius: 8px; font: inherit; font-size: .78rem; }
    .guided-intake-grid textarea { min-height: 58px; resize: vertical; }
    .guided-intake-grid button { white-space: nowrap; }
    .guided-intake-status { margin: 10px 0 0; color: var(--muted); font-size: .78rem; }
    .signal-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
    .signal-card { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 18px; align-items: center; padding: 21px; box-shadow: none; overflow: hidden; position: relative; }
    .signal-card::after { display: none; }
    .ring { --ring-color: var(--blue) !important; --ring-progress: 0%; width: 64px; height: auto; min-height: 58px; display: block; border-radius: 0; background: transparent; position: relative; transition: none; }
    .ring::before { content: ""; position: absolute; inset: auto 0 0; height: 6px; border: 0; border-radius: 999px; background: linear-gradient(90deg, var(--ring-color) 0 var(--ring-progress), #e8e8ed var(--ring-progress) 100%); }
    .ring strong { position: relative; display: block; font-size: 2rem; line-height: 1; font-weight: 680; letter-spacing: -.05em; }
    .signal-card p { margin-bottom: 0; color: var(--muted); font-size: .84rem; }
    .result-grid { gap: 18px; }
    .result-grid, .result-grid > *, .matrix, .matrix-head, .matrix-row, .detail-card { min-width: 0; }
    .matrix { gap: 0; }
    .matrix-row { grid-template-columns: minmax(150px, 1.2fr) 142px 120px 80px; padding: 15px 14px; color: var(--text); background: transparent; border: 0; border-top: 1px solid var(--line); border-radius: 0; overflow: hidden; }
    .matrix-row:hover, .matrix-row.selected { background: var(--surface-soft); border-color: var(--line); }
    .matrix-row.selected { box-shadow: inset 3px 0 0 var(--blue); }
    .matrix-head { padding-bottom: 8px; color: var(--muted); font-size: .71rem; }
    .requirement-name { font-weight: 650; }
    .badge { padding: 5px 8px; border-radius: 999px; font-size: .7rem; font-weight: 600; }
    .badge.direct, .badge.met { color: #1d6b38; background: #eaf8ef; }
    .badge.transferable { color: #155ca8; background: #eaf3ff; }
    .badge.direct_weak, .badge.unknown { color: #8a5a00; background: #fff5dc; }
    .badge.missing, .badge.not_met { color: #a32923; background: #ffebe9; }
    .score-bar { height: 6px; background: #e8e8ed; }
    .score-fill { background: var(--blue); }
    .score-number { color: var(--muted); font-size: .78rem; }
    .detail-card { min-height: 365px; padding: 21px; box-shadow: none; }
    .detail-title { margin: 9px 0 5px; font-size: 1.35rem; }
    .detail-line { padding-bottom: 9px; border-bottom: 1px solid var(--line); }
    .detail-copy { color: var(--muted); font-size: .88rem; }
    .chart-svg { min-height: 290px; }
    .chart-axis { stroke: var(--line); }
    .chart-label { fill: var(--muted); font-size: 11px; }
    .chart-value { fill: var(--text); font-size: 11px; font-weight: 650; }
    .chart-bar { fill: var(--blue); }
    .gap-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
    .gap-card { padding: 18px; box-shadow: none; border-top: 3px solid var(--blue); }
    .gap-card.high { border-color: var(--line); border-top-color: var(--red); }
    .gap-card.medium { border-color: var(--line); border-top-color: var(--amber); }
    .gap-card.low { border-color: var(--line); border-top-color: var(--blue); }
    .gap-meta { color: var(--muted); font-size: .73rem; }
    .gap-action { margin: 12px 0 0; color: var(--text); font-size: .91rem; }
    .gap-artifact { margin: 12px 0 0; padding: 10px; color: var(--muted); background: var(--surface-soft); border-left: 2px solid var(--blue); font-size: .82rem; }
    .meaning-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
    .meaning { padding: 19px; box-shadow: none; background: var(--surface); }
    .meaning p { margin-bottom: 0; color: var(--muted); font-size: .88rem; }
    .source-note { margin-top: 20px; color: var(--muted); font-size: .82rem; }
    .footer-row { margin-top: 54px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--muted); font-size: .8rem; }
    @media (max-width: 1020px) { .signal-grid { grid-template-columns: 1fr; } .meaning-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 900px) { .result-grid { display: block !important; } .result-grid > * { width: 100%; margin-bottom: 18px; } .gap-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 1020px) { .guided-intake-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
    @media (max-width: 700px) { .shell { width: min(100% - 36px, 1180px); } .hero { padding-top: 54px; } .input-grid, .meaning-grid, .gap-grid, .comparison-grid, .workflow { grid-template-columns: 1fr; } .panel { padding: 21px; } .summary-grid { grid-template-columns: 1fr 1fr; gap: 22px; } .summary-card:nth-child(3) { padding-left: 0; border-left: 0; } .summary-card:nth-child(3), .summary-card:nth-child(4) { margin-top: 0; } .matrix-row, .matrix-head { grid-template-columns: minmax(125px, 1fr) 106px 78px; } .matrix-row > :nth-child(3), .matrix-head > :nth-child(3) { display: none; } .signal-card { grid-template-columns: 64px minmax(0, 1fr); } .ring { width: 58px; } .toolbar { align-items: flex-start; } }
    @media (max-width: 700px) { .coverage-grid { grid-template-columns: 1fr; } .review-item { grid-template-columns: 1fr; } .review-evidence-row, .review-add-row { align-items: stretch; flex-direction: column; } .review-evidence-row input, .review-add-row input { width: 100%; } .review-evidence-grid, .guided-intake-grid { grid-template-columns: 1fr 1fr; } .guided-intake-grid label:nth-child(2), .guided-intake-grid label:nth-child(3), .guided-intake-grid label:nth-child(4) { grid-column: 1 / -1; } .guided-intake-grid button { width: 100%; } .review-evidence-grid button { width: 100%; } }
    @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; scroll-behavior: auto !important; } }
  </style>
  </head>
<body>
  <main id="app" class="shell" data-workflow-stage="intake">
    <header class="topbar">
      <div class="brand"><span class="brand-mark" aria-hidden="true"></span><span class="brand-name">Career Fit</span></div>
      <span class="micro">Private by default · explainable preparation</span>
    </header>

    <section class="hero">
      <div class="hero-copy">
        <div class="hero-badge">EVIDENCE-FIRST JOB SEARCH</div>
        <h1>Turn uncertainty into an application plan.</h1>
        <p>Career Fit helps every job seeker answer three practical questions: can I do this, can I prove it, and what should I do next? It translates a job posting into an evidence map without pretending to predict a hiring decision.</p>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div><span class="eyebrow">A guided, private workflow</span><h2>Make the hidden decision visible.</h2></div>
        <p>Start with a job posting and your experience. The app extracts a reviewable checklist first, then shows preparation signals only after you confirm what it found.</p>
      </div>
      <ol class="workflow" aria-label="Career Fit workflow">
        <li class="workflow-step active"><span>1</span><strong>Add inputs</strong><small>Posting and experience</small></li>
        <li class="workflow-step"><span>2</span><strong>Review</strong><small>Requirements and evidence</small></li>
        <li class="workflow-step"><span>3</span><strong>Plan</strong><small>Signals and next actions</small></li>
      </ol>
      <div class="panel">
        <div class="toolbar intake-stage">
          <button id="analyze-button" type="button">Analyze this role</button>
          <button id="example-button" class="secondary" type="button">Load example</button>
          <button id="clear-button" class="secondary" type="button">Clear</button>
          <span id="status" class="status" aria-live="polite">Ready for analysis</span>
        </div>
        <div class="input-grid intake-stage">
          <div>
            <label class="input-label" for="job-input">Job posting <span>target role</span></label>
            <textarea id="job-input" aria-label="Job posting" placeholder="Paste the full job posting, including must-have and preferred requirements."></textarea>
          </div>
          <div>
            <label class="input-label" for="candidate-input">Your experience <span>resume, profile, or projects</span></label>
            <textarea id="candidate-input" aria-label="Your experience" placeholder="Paste a resume or profile, or describe projects, courses, tools, tasks, and results."></textarea>
            <div class="file-import-row">
              <label class="file-input-label" for="candidate-file">Load a resume or profile</label>
              <input id="candidate-file" type="file" accept=".txt,.md,.json,.docx,.pdf,text/plain,text/markdown,application/json,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/pdf" />
              <span id="candidate-file-status" class="status" aria-live="polite">Supports TXT, Markdown, JSON, DOCX, and text PDFs. Review identifiers before loading.</span>
            </div>
            <div id="document-preview" class="document-preview" hidden>
              <p id="document-preview-notice" class="detail-copy"></p>
              <label for="document-preview-text">Review imported text before using it<textarea id="document-preview-text" rows="9" aria-label="Editable imported resume text"></textarea></label>
              <div class="toolbar"><button id="use-document-preview-button" class="secondary" type="button">Use reviewed text</button><button id="cancel-document-preview-button" class="secondary" type="button">Discard import</button></div>
            </div>
            <label class="input-label" for="candidate-language">Profile language <span>helps avoid silent gaps</span></label>
            <select id="candidate-language" aria-label="Profile language">
              <option value="auto">Detect automatically</option>
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="zh">Chinese</option>
              <option value="other">Another language</option>
            </select>
            <p id="language-status" class="status" aria-live="polite">The rule-based dictionary is English-first. Choose a language when the profile is not primarily English.</p>
          </div>
        </div>
        <p class="privacy-note intake-stage">__PRIVACY_NOTE__</p>
        <div class="occupation-context-panel intake-stage">
          <div class="section-head"><div><span class="eyebrow">Optional occupation context</span><h3>What workers say about this occupation.</h3></div><p>Career Fit analyzes a specific posting. If you confirm a standard occupation from AI Labor Atlas, this panel can show public worker comments about pay, interviews, management, and the work environment.</p></div>
          <div class="occupation-search-row">
            <label for="occupation-query">Occupation or job-family name
              <input id="occupation-query" type="search" placeholder="e.g. Data Scientist or People Analytics Analyst" />
            </label>
            <button id="occupation-search-button" class="secondary" type="button">Find occupations</button>
          </div>
          <p id="occupation-status" class="occupation-status" aria-live="polite">Select a standard occupation before viewing worker context.</p>
          <div id="occupation-candidates" class="occupation-candidates"></div>
          <div id="occupation-context-result" hidden>
            <p id="occupation-context-title" class="occupation-interpretation"></p>
            <div id="market-context" class="market-context" hidden>
              <div class="section-head"><div><span class="eyebrow">Market context</span><h4>Descriptive signals for this occupation</h4></div><p id="market-context-interpretation"></p></div>
              <div id="market-metrics" class="market-metrics"></div>
              <div id="market-tasks" class="market-tasks"></div>
              <div id="market-adjacent" class="market-adjacent"></div>
              <small id="market-provenance" class="detail-copy"></small>
            </div>
            <div class="occupation-review-filter-row">
              <label for="occupation-review-source-filter">Source
                <select id="occupation-review-source-filter"><option value="all">All sources</option></select>
              </label>
              <label for="occupation-review-topic-filter">Topic
                <select id="occupation-review-topic-filter"><option value="all">All topics</option></select>
              </label>
            </div>
            <div id="occupation-reviews" class="occupation-reviews"></div>
            <details class="occupation-disclosure"><summary>About these reviews</summary><p id="occupation-disclosure-text">Reviews are user-generated and may be incomplete, subjective, outdated, or biased. They are not verified facts or representative of all workers. Source links and dates are shown where available.</p></details>
          </div>
        </div>
        <div class="compare-panel intake-stage">
          <div class="section-head"><div><span class="eyebrow">Choose where to focus</span><h3>Compare target roles</h3></div><p>Paste two or three job descriptions separated by a line containing <code>---</code>. Career Fit reuses reviewed candidate evidence, but leaves roles unranked until their requirements and eligibility gates are confirmed.</p></div>
          <label class="input-label" for="roles-input">Target roles <span>optional role portfolio</span></label>
          <textarea id="roles-input" class="compare-input" aria-label="Target roles" placeholder="Role: People Analytics Analyst&#10;Must have Python and SQL...&#10;---&#10;Role: Data Analyst&#10;Must have Python and data visualization..."></textarea>
          <div class="toolbar"><button id="compare-button" class="secondary" type="button">Compare roles</button><span id="compare-status" class="status" aria-live="polite">Use this when you are deciding where to focus first.</span></div>
          <div id="comparison-panel" class="comparison-panel" hidden><div id="comparison-grid" class="comparison-grid"></div></div>
        </div>
        <div class="toolbar plan-stage">
          <button id="edit-inputs-button" class="secondary" type="button">Edit inputs</button>
          <button id="download-markdown-button" class="secondary" type="button" disabled>Download Markdown plan</button>
          <button id="download-pdf-button" class="secondary" type="button" disabled>Download PDF plan</button>
          <button id="deep-review-button" class="secondary" type="button" disabled>Optional semantic review</button>
          <span id="semantic-status" class="status" aria-live="polite">Optional review available when enabled.</span>
        </div>
        <div class="summary-grid plan-stage" aria-live="polite">
          <article class="summary-card"><span class="label">Evidence fit</span><strong id="fit-score" class="summary-value">—</strong><span class="summary-note">weighted requirement overlap</span></article>
          <article class="summary-card"><span class="label">Application readiness</span><strong id="readiness-score" class="summary-value">—</strong><span class="summary-note">preparation triage, not hiring odds</span></article>
          <article class="summary-card"><span class="label">Requirements identified</span><strong id="input-coverage-score" class="summary-value">—</strong><span class="summary-note">not a completeness or confidence score</span></article>
          <article class="summary-card"><span class="label">Eligibility requirements</span><strong id="blocked-count" class="summary-value">—</strong><span class="summary-note">requirements needing verification</span></article>
        </div>
        <div id="coverage-panel" class="coverage-panel plan-stage" hidden>
          <div class="section-head"><div><span class="eyebrow">Coverage, not confidence</span><h3>What the current text supports</h3></div><p>These components show what was mapped from the supplied inputs. They are not calibrated probabilities and do not measure hiring likelihood.</p></div>
          <div class="coverage-grid">
            <article class="coverage-card"><span>Requirements identified</span><strong id="requirement-coverage-score">—</strong><small>the system cannot infer the full set of employer requirements</small></article>
            <article class="coverage-card"><span>Reviewable evidence</span><strong id="evidence-coverage-score">—</strong><small>requirements with concrete evidence or an explicit transfer</small></article>
            <article class="coverage-card"><span>Eligibility status</span><strong id="eligibility-coverage-score">—</strong><small>no gate detected is not the same as verified</small></article>
          </div>
        </div>
        <div id="review-panel" class="review-panel review-stage" hidden>
          <div class="section-head"><div><span class="eyebrow">Step 2 · Review before relying</span><h3>Confirm the extraction</h3></div><p>Keep or remove each requirement, correct its importance, confirm eligibility gates, and label the kind of evidence you want to use. Scores remain hidden until this step is submitted.</p></div>
          <div id="review-requirements" class="review-requirements"></div>
          <div id="guided-intake" class="guided-intake" hidden>
            <div class="section-head"><div><span class="eyebrow">No resume? Start with one example</span><h3>Describe work you have actually done</h3></div></div>
            <p class="guided-intake-copy">Choose a role requirement, then describe one task and where it happened. A result is helpful but optional. This records your own example; it does not verify it or infer ability from personal circumstances.</p>
            <div class="guided-intake-grid">
              <label for="guided-intake-requirement">Requirement<select id="guided-intake-requirement" aria-label="Requirement for guided example"></select></label>
              <label for="guided-intake-task">What did you do?<textarea id="guided-intake-task" rows="2" placeholder="Scheduled appointments or maintained records"></textarea></label>
              <label for="guided-intake-context">Where or with whom?<textarea id="guided-intake-context" rows="2" placeholder="At a community group, family business, or volunteer role"></textarea></label>
              <label for="guided-intake-result">What changed? <span>(optional)</span><textarea id="guided-intake-result" rows="2" placeholder="Kept requests organized and reduced missed follow-ups"></textarea></label>
              <label for="guided-intake-type">Evidence type<select id="guided-intake-type"></select></label>
              <label for="guided-intake-duration">Months<input id="guided-intake-duration" type="number" min="0" step="1" placeholder="e.g. 6" /></label>
              <label for="guided-intake-recency">Years ago<input id="guided-intake-recency" type="number" min="0" step="0.5" placeholder="e.g. 1" /></label>
              <button id="guided-intake-button" class="secondary" type="button">Add example</button>
            </div>
            <p id="guided-intake-status" class="guided-intake-status" aria-live="polite">One concrete example is enough to begin.</p>
          </div>
          <div class="review-add-row"><label for="added-requirement-input">Add a missed requirement <span>known or user-supplied label</span><input id="added-requirement-input" type="text" placeholder="e.g. SQL or Kubernetes" /></label><label for="added-requirement-importance">Importance<select id="added-requirement-importance"><option value="must">Must have</option><option value="strongly_preferred">Strongly preferred</option><option value="preferred">Preferred</option><option value="inferred">Inferred</option></select></label><button id="add-requirement-button" class="secondary" type="button">Add requirement</button></div>
          <div id="review-added-list" class="review-added-list"></div>
          <div class="toolbar"><button id="back-to-inputs-button" class="secondary" type="button">Edit inputs</button><button id="apply-review-button" type="button">Recalculate after review</button><span id="review-status" class="status" aria-live="polite">Review the items above before relying on the result.</span></div>
        </div>
        <div id="fingerprint-panel" class="fingerprint-panel plan-stage" hidden>
          <div class="section-head"><div><span class="eyebrow">Role fingerprint</span><h3>See the dimensions behind the role.</h3></div><p>Categories organize the posting; named skills remain the evidence unit. This is a descriptive mismatch view, not an ability test.</p></div>
          <div class="fingerprint-layout">
            <div class="fingerprint-card"><div id="category-profile" class="category-profile"></div></div>
            <aside class="fingerprint-card"><span class="eyebrow">Largest dimensions to investigate</span><div id="mismatch-list" class="mismatch-list"></div></aside>
          </div>
          <div class="fingerprint-card"><div class="section-head"><div><span class="eyebrow">Requirements that appear together</span><h3>Turn a skill bundle into one proof artifact.</h3></div><p>These pairs come from this posting only. They do not estimate market value or wage complementarity.</p></div><div id="bundle-grid" class="bundle-grid"></div></div>
        </div>
        <div id="semantic-preview" class="semantic-panel plan-stage" hidden>
          <span class="eyebrow">Optional remote review - confirm sharing</span>
          <p id="semantic-endpoint" class="detail-copy"></p>
          <p class="detail-copy">The editable preview contains the fields sent to the configured endpoint after common direct identifiers are removed. It is not fully anonymized.</p>
          <label for="semantic-payload">Review or edit the transmitted payload<textarea id="semantic-payload" rows="12" aria-label="Editable optional semantic review payload"></textarea></label>
          <div class="toolbar"><button id="send-semantic-review-button" class="secondary" type="button">Send optional review</button><button id="cancel-semantic-review-button" class="secondary" type="button">Cancel</button></div>
        </div>
        <div id="semantic-panel" class="semantic-panel plan-stage" hidden>
          <span class="eyebrow">Deep semantic review</span>
          <p id="semantic-summary" class="detail-copy"></p>
          <div id="semantic-list" class="semantic-list"></div>
        </div>
      </div>
    </section>

    <section class="section plan-stage">
      <div class="section-head"><div><span class="eyebrow">Three questions</span><h2>Capability, proof, and readiness are different signals.</h2></div><p id="decision-label">Run an analysis to see what the current text can support.</p></div>
      <div class="signal-grid">
        <article class="signal-card"><div id="capability-ring" class="ring" style="--ring-color: var(--violet)"><strong id="capability-signal">—</strong></div><div><span class="eyebrow">Can I do it?</span><h3>Capability signal</h3><p>Includes direct and transferable overlap. Transfer is a lead for exploration, not proof of equivalence.</p></div></article>
        <article class="signal-card"><div id="proof-ring" class="ring" style="--ring-color: var(--cyan)"><strong id="proof-signal">—</strong></div><div><span class="eyebrow">Can I prove it?</span><h3>Proof signal</h3><p>Rewards concrete tasks, results, duration, and reviewable evidence instead of bare keywords.</p></div></article>
        <article class="signal-card"><div id="readiness-ring" class="ring" style="--ring-color: var(--amber)"><strong id="readiness-signal">—</strong></div><div><span class="eyebrow">Should I apply now?</span><h3>Application readiness</h3><p>Combines must-have evidence, proof strength, and unresolved hard requirements.</p></div></article>
      </div>
    </section>

    <section class="section plan-stage">
      <div class="section-head"><div><span class="eyebrow">Requirement and evidence matrix</span><h2>Inspect the reason behind every signal.</h2></div><p>Click a row to see the original job wording, the evidence behind the result, and the most useful next move.</p></div>
      <div class="result-grid">
        <div class="panel">
          <div class="matrix matrix-head" aria-hidden="true"><div>Requirement</div><div>Status</div><div>Importance</div><div>Score</div></div>
          <div id="matrix" class="matrix" aria-live="polite"></div>
        </div>
        <aside id="detail" class="detail-card">
          <span class="eyebrow">Selected requirement</span>
          <h3 class="detail-title">Waiting for analysis</h3>
          <p class="detail-copy">Run the analysis, then select a requirement to inspect its evidence trail.</p>
        </aside>
      </div>
    </section>

    <section class="section plan-stage">
      <div class="section-head"><div><span class="eyebrow">Fit profile</span><h2>See the shape of the opportunity.</h2></div><p>This chart shows relative evidence signals by requirement. A high bar is not a hiring promise; a low bar is an invitation to investigate the gap.</p></div>
      <div class="panel"><svg id="fit-chart" class="chart-svg" viewBox="0 0 900 340" role="img" aria-label="Requirement evidence profile"></svg></div>
    </section>

    <section class="section plan-stage">
      <div class="section-head"><div><span class="eyebrow">Gap to action</span><h2>Leave with a useful next move.</h2></div><p>Actions are ordered by requirement importance and evidence shortfall. Each card names the proof artifact you can create or the gate you can verify.</p></div>
      <div id="gap-list" class="gap-grid" aria-live="polite"></div>
    </section>

    <section class="section plan-stage">
      <div class="section-head"><div><span class="eyebrow">How to read the numbers</span><h2>Useful for preparation, limited for prediction.</h2></div></div>
      <div class="meaning-grid">
        <article class="meaning"><h3>Evidence fit is not hiring probability</h3><p>It is an importance-weighted summary of requirement overlap and supplied evidence. It does not estimate employer decisions.</p></article>
        <article class="meaning"><h3>A proof gap is not an ability gap</h3><p>A candidate may have the capability but lack a concrete task, result, work sample, or clear translation into employer language.</p></article>
        <article class="meaning"><h3>Transfer is deliberately cautious</h3><p>Adjacent evidence can suggest a bridge project, but the system never silently upgrades it to direct equivalence.</p></article>
        <article class="meaning"><h3>Eligibility requirements stay separate</h3><p>Licenses, work authorization, degrees, and experience floors need verification. Soft skill overlap cannot offset an unresolved requirement.</p></article>
      </div>
      <p class="source-note">__PRIVACY_FOOTER__ Career Fit is designed for preparation, not prediction.</p>
    </section>
    <footer class="footer-row"><span>Career Fit · evidence before confidence</span><span>Preparation support, not an automated hiring system.</span></footer>
  </main>
  <script>
    (function () {
      const DEFAULT_JOB = __DEFAULT_JOB__;
      const DEFAULT_CANDIDATE = __DEFAULT_CANDIDATE__;
      const jobInput = document.getElementById("job-input");
      const candidateInput = document.getElementById("candidate-input");
      const candidateLanguage = document.getElementById("candidate-language");
      const languageStatus = document.getElementById("language-status");
      const candidateFile = document.getElementById("candidate-file");
      const candidateFileStatus = document.getElementById("candidate-file-status");
      const documentPreview = document.getElementById("document-preview");
      const documentPreviewNotice = document.getElementById("document-preview-notice");
      const documentPreviewText = document.getElementById("document-preview-text");
      const useDocumentPreviewButton = document.getElementById("use-document-preview-button");
      const cancelDocumentPreviewButton = document.getElementById("cancel-document-preview-button");
      const analyzeButton = document.getElementById("analyze-button");
      const exampleButton = document.getElementById("example-button");
      const clearButton = document.getElementById("clear-button");
      const compareButton = document.getElementById("compare-button");
      const editInputsButton = document.getElementById("edit-inputs-button");
      const backToInputsButton = document.getElementById("back-to-inputs-button");
      const downloadMarkdownButton = document.getElementById("download-markdown-button");
      const downloadPdfButton = document.getElementById("download-pdf-button");
      const rolesInput = document.getElementById("roles-input");
      const occupationQuery = document.getElementById("occupation-query");
      const occupationSearchButton = document.getElementById("occupation-search-button");
      const occupationStatus = document.getElementById("occupation-status");
      const occupationCandidates = document.getElementById("occupation-candidates");
      const occupationContextResult = document.getElementById("occupation-context-result");
      const occupationContextTitle = document.getElementById("occupation-context-title");
      const marketContext = document.getElementById("market-context");
      const marketContextInterpretation = document.getElementById("market-context-interpretation");
      const marketMetrics = document.getElementById("market-metrics");
      const marketTasks = document.getElementById("market-tasks");
      const marketAdjacent = document.getElementById("market-adjacent");
      const marketProvenance = document.getElementById("market-provenance");
      const occupationReviews = document.getElementById("occupation-reviews");
      const occupationDisclosure = document.getElementById("occupation-disclosure-text");
      const occupationReviewSourceFilter = document.getElementById("occupation-review-source-filter");
      const occupationReviewTopicFilter = document.getElementById("occupation-review-topic-filter");
      const compareStatus = document.getElementById("compare-status");
      const comparisonPanel = document.getElementById("comparison-panel");
      const comparisonGrid = document.getElementById("comparison-grid");
      const fingerprintPanel = document.getElementById("fingerprint-panel");
      const categoryProfile = document.getElementById("category-profile");
      const mismatchList = document.getElementById("mismatch-list");
      const bundleGrid = document.getElementById("bundle-grid");
      const status = document.getElementById("status");
      const matrix = document.getElementById("matrix");
      const detail = document.getElementById("detail");
      const gapList = document.getElementById("gap-list");
      const fitChart = document.getElementById("fit-chart");
      const decisionLabel = document.getElementById("decision-label");
      const fitScore = document.getElementById("fit-score");
      const readinessScore = document.getElementById("readiness-score");
      const blockedCount = document.getElementById("blocked-count");
      const deepReviewButton = document.getElementById("deep-review-button");
      const semanticStatus = document.getElementById("semantic-status");
      const semanticPreview = document.getElementById("semantic-preview");
      const semanticEndpoint = document.getElementById("semantic-endpoint");
      const semanticPayload = document.getElementById("semantic-payload");
      const sendSemanticReviewButton = document.getElementById("send-semantic-review-button");
      const cancelSemanticReviewButton = document.getElementById("cancel-semantic-review-button");
      const semanticPanel = document.getElementById("semantic-panel");
      const semanticSummary = document.getElementById("semantic-summary");
      const semanticList = document.getElementById("semantic-list");
      const coveragePanel = document.getElementById("coverage-panel");
      const inputCoverageScore = document.getElementById("input-coverage-score");
      const requirementCoverageScore = document.getElementById("requirement-coverage-score");
      const evidenceCoverageScore = document.getElementById("evidence-coverage-score");
      const eligibilityCoverageScore = document.getElementById("eligibility-coverage-score");
      const reviewPanel = document.getElementById("review-panel");
      const reviewRequirements = document.getElementById("review-requirements");
      const reviewAddedList = document.getElementById("review-added-list");
      const guidedIntake = document.getElementById("guided-intake");
      const guidedIntakeRequirement = document.getElementById("guided-intake-requirement");
      const guidedIntakeTask = document.getElementById("guided-intake-task");
      const guidedIntakeContext = document.getElementById("guided-intake-context");
      const guidedIntakeResult = document.getElementById("guided-intake-result");
      const guidedIntakeType = document.getElementById("guided-intake-type");
      const guidedIntakeDuration = document.getElementById("guided-intake-duration");
      const guidedIntakeRecency = document.getElementById("guided-intake-recency");
      const guidedIntakeButton = document.getElementById("guided-intake-button");
      const guidedIntakeStatus = document.getElementById("guided-intake-status");
      const addedRequirementInput = document.getElementById("added-requirement-input");
      const addRequirementButton = document.getElementById("add-requirement-button");
      const applyReviewButton = document.getElementById("apply-review-button");
      const reviewStatus = document.getElementById("review-status");
      const addedRequirementImportance = document.getElementById("added-requirement-importance");
      const workflowSteps = Array.from(document.querySelectorAll(".workflow-step"));
      const app = document.getElementById("app");
      const llmEnabled = __LLM_ENABLED__;
      const reviewEndpoint = __REVIEW_ENDPOINT__;
      const statusLabels = {
        direct: "Directly related, user-supplied evidence",
        direct_weak: "Mentioned, proof is thin",
        transferable: "Transferable evidence",
        claimed: "Claimed capability, proof not supplied",
        transferable_claimed: "Transferable claim, proof not supplied",
        missing: "No evidence found",
        met: "Requirement appears met",
        not_met: "Explicitly not met",
        unknown: "Needs verification"
      };
      const readinessLabels = {
        apply_and_refine: "Apply and refine",
        apply_after_targeted_proof: "Targeted proof first",
        verify_before_applying: "Verify before applying",
        blocked_by_constraint: "Eligibility issue",
        build_evidence_before_prioritizing: "Build evidence first"
      };
      const importanceLabels = {
        must: "Must have",
        strongly_preferred: "Strongly preferred",
        preferred: "Preferred",
        inferred: "Inferred"
      };
      const evidenceTypeLabels = {
        work: "Work experience",
        research_project: "Research project",
        portfolio: "Portfolio sample",
        github_project: "GitHub project",
        course: "Course or training",
        certificate: "Certificate",
        self_reported: "Self-reported claim",
        unknown: "Unknown source"
      };
      let latest = null;
      let latestOccupationContext = null;
      let latestScoreVisible = false;
      let analyzedSignature = "";
      let analysisRequestId = 0;
      let compareRequestId = 0;
      let comparisonEvidence = [];
      let comparisonRoleReviews = {};
      let activeComparisonRoleId = "";
      function setWorkflowStage(stage) {
        app.dataset.workflowStage = stage;
        const index = stage === "intake" ? 0 : stage === "review" ? 1 : 2;
        workflowSteps.forEach(function (step, position) { step.classList.toggle("active", position === index); step.classList.toggle("current", position === index); });
      }
      function newReviewState() {
        return { removed_requirement_ids: [], added_requirements: [], importance_overrides: {}, constraint_status_overrides: {}, added_evidence: [], applied: false, base_signature: "" };
      }
      let reviewState = newReviewState();
      function inputSignature() { return jobInput.value + "\n---\n" + candidateInput.value + "\n---language---\n" + candidateLanguage.value; }
      function currentAnalysisIsFresh() { return Boolean(latest && analyzedSignature === inputSignature()); }
      function clearComparisonResult() { clearNode(comparisonGrid); comparisonPanel.hidden = true; }
      function clearRenderedAnalysis() {
        compareRequestId += 1;
        latest = null;
        analyzedSignature = "";
        latestScoreVisible = false;
        clearNode(matrix); clearNode(gapList); clearNode(fitChart); clearNode(categoryProfile); clearNode(mismatchList); clearNode(bundleGrid);
        clearNode(semanticList); clearNode(reviewRequirements); clearNode(reviewAddedList);
        clearComparisonResult();
        coveragePanel.hidden = true; reviewPanel.hidden = true; guidedIntake.hidden = true; fingerprintPanel.hidden = true; semanticPanel.hidden = true; semanticPreview.hidden = true;
        detail.innerHTML = ""; detail.append(make("span", "eyebrow", "Selected requirement"), make("h3", "detail-title", "Waiting for analysis"), make("p", "detail-copy", "Run the analysis, then select a requirement to inspect its evidence trail."));
        [fitScore, readinessScore, inputCoverageScore, blockedCount, requirementCoverageScore, evidenceCoverageScore, eligibilityCoverageScore].forEach(function (node) { node.textContent = "—"; });
        ["capability-signal", "proof-signal", "readiness-signal"].forEach(function (id) { document.getElementById(id).textContent = "—"; });
        ["capability-ring", "proof-ring", "readiness-ring"].forEach(function (id) { document.getElementById(id).style.setProperty("--ring-progress", "0%"); });
        downloadMarkdownButton.disabled = true; downloadPdfButton.disabled = true; deepReviewButton.disabled = true;
        semanticSummary.textContent = ""; reviewStatus.textContent = "Review the extracted requirements before relying on the result."; guidedIntakeStatus.textContent = "One concrete example is enough to begin.";
      }
      function invalidateCurrentResult(message) {
        analysisRequestId += 1;
        clearRenderedAnalysis();
        reviewState = newReviewState();
        comparisonEvidence = [];
        comparisonRoleReviews = {};
        activeComparisonRoleId = "";
        setWorkflowStage("intake");
        if (message) status.textContent = message;
      }
      function handleInputChange() {
        if (!latest && !analyzedSignature && !latestScoreVisible && reviewPanel.hidden && comparisonPanel.hidden && semanticPanel.hidden) return;
        invalidateCurrentResult("Inputs changed. Analyze the current text before relying on a result.");
      }

      function reviewSourceLabel(value) {
        return { user_submitted: "User submitted", reddit: "Reddit", indeed: "Indeed", other: "Other public source" }[value] || "Public source";
      }
      function reviewScopeLabel(value) {
        return { occupation: "Occupation context", employer_role: "Employer and role", job_posting: "Specific job posting" }[value] || "Scope not specified";
      }
      function reviewTopicLabel(value) {
        return { pay_benefits: "Pay and benefits", interview_management: "Interview and management", work_environment: "Work environment", workload: "Workload", growth: "Growth", tasks_tools: "Tasks and tools", other: "Other" }[value] || value;
      }
      function marketNumber(value, suffix) { return value == null || value === "" ? "Not available" : String(value) + (suffix || ""); }
      function marketMoney(value) { return value == null || value === "" ? "Not available" : "$" + Math.round(Number(value)).toLocaleString("en-US"); }
      function renderMarketContext(payload) {
        const context = payload.market_context || {};
        const metrics = context.metrics || {};
        marketContext.hidden = !Object.keys(metrics).length;
        clearNode(marketMetrics); clearNode(marketTasks); clearNode(marketAdjacent);
        if (marketContext.hidden) return;
        const mapping = context.mapping || {};
        const mappingFlags = mapping.data_quality_flags || [];
        const mappingNotes = [];
        if (mapping.status === "multiple_soc_crosswalk") mappingNotes.push("Reference metrics are weighted across " + (mapping.soc_2018_codes || []).length + " SOC mappings; they are not a direct SOC statistic.");
        if (mappingFlags.includes("uniform_crosswalk_fallback")) mappingNotes.push("The source supplied no allocation across those mappings, so a uniform fallback was used.");
        if (mappingFlags.includes("shared_soc_crosswalk")) mappingNotes.push("A SOC target is shared by multiple O*NET occupations; top-line SOC weighting deduplicates that target.");
        if (mappingFlags.includes("missing_crosswalk")) mappingNotes.push("No SOC mapping is available; SOC-linked market fields are not available for this occupation.");
        const mappingNote = mappingNotes.length ? " " + mappingNotes.join(" ") : "";
        marketContextInterpretation.textContent = (context.interpretation || "Descriptive market context only; it does not change the job-specific score.") + mappingNote;
        [["Median wage", marketMoney(metrics.median_annual_wage)], ["Employment", marketNumber(metrics.employment_2024)], ["Annual openings", marketNumber(metrics.annual_openings_2024_2034)], ["Projected change", marketNumber(metrics.employment_change_2024_2034_pct, "%")], ["AI exposure", marketNumber(metrics.ai_exposure)], ["SOC mapping", mapping.status === "multiple_soc_crosswalk" ? (mapping.soc_2018_codes || []).join(", ") : ((mapping.soc_2018_codes || [])[0] || "Not available")], ["Occupation", context.title || "Not available"]].forEach(function (item) {
          const card = make("article", "market-metric"); card.append(make("span", "", item[0]), make("strong", "", item[1])); marketMetrics.appendChild(card);
        });
        const tasks = context.representative_tasks || [];
        marketTasks.appendChild(make("strong", "", tasks.length ? "Representative tasks" : "No representative tasks available"));
        if (tasks.length) { const list = document.createElement("ul"); tasks.forEach(function (item) { list.appendChild(make("li", "", item.task_statement)); }); marketTasks.appendChild(list); }
        const adjacent = context.adjacent_occupations || [];
        if (adjacent.length) {
          marketAdjacent.appendChild(make("strong", "", "Descriptive adjacent occupations"));
          adjacent.slice(0, 4).forEach(function (item) {
            const card = make("article", "market-adjacent-card");
            card.append(make("strong", "", item.title || "Occupation"), make("small", "", "Similarity " + marketNumber(item.structured_similarity)), make("small", "", "Wage " + marketMoney((item.labor_market || {}).median_annual_wage)), make("small", "", item.training_hint || "Use shared tasks to choose a focused proof sample."));
            marketAdjacent.appendChild(card);
          });
        }
        const provenance = context.provenance || {};
        marketProvenance.textContent = "Data: O*NET " + (provenance.onet_version || "not specified") + " · Wage " + (provenance.wage_vintage || "not specified") + " · Projections " + (provenance.projection_vintage || "not specified") + (provenance.data_quality_flags ? " · Flags: " + provenance.data_quality_flags : "") + ".";
      }
      function renderOccupationReviews(payload) {
        latestOccupationContext = payload;
        renderMarketContext(payload);
        clearNode(occupationReviews);
        const context = payload.reviews || {};
        occupationDisclosure.textContent = context.disclosure || "Reviews are user-generated and may be incomplete, subjective, outdated, or biased. They are not verified facts or representative of all workers. Source links and dates are shown where available.";
        const reviews = context.reviews || [];
        const sourceValue = occupationReviewSourceFilter.value;
        const topicValue = occupationReviewTopicFilter.value;
        const sourceLabels = context.source_labels || {};
        const topicLabels = context.topic_labels || {};
        occupationReviewSourceFilter.innerHTML = "";
        const allSources = make("option", "", "All sources"); allSources.value = "all"; occupationReviewSourceFilter.appendChild(allSources);
        Object.keys(context.source_counts || {}).forEach(function (value) { const option = make("option", "", sourceLabels[value] || reviewSourceLabel(value)); option.value = value; occupationReviewSourceFilter.appendChild(option); });
        occupationReviewTopicFilter.innerHTML = "";
        const allTopics = make("option", "", "All topics"); allTopics.value = "all"; occupationReviewTopicFilter.appendChild(allTopics);
        Object.keys(context.topic_counts || {}).forEach(function (value) { const option = make("option", "", topicLabels[value] || reviewTopicLabel(value)); option.value = value; occupationReviewTopicFilter.appendChild(option); });
        occupationReviewSourceFilter.value = sourceValue || "all";
        occupationReviewTopicFilter.value = topicValue || "all";
        occupationReviewSourceFilter.disabled = !reviews.length;
        occupationReviewTopicFilter.disabled = !reviews.length;
        const filteredReviews = reviews.filter(function (review) {
          return (sourceValue === "all" || !sourceValue || review.source === sourceValue)
            && (topicValue === "all" || !topicValue || (review.topics || []).includes(topicValue));
        });
        const occupationTitle = payload.occupation && payload.occupation.title ? payload.occupation.title : "Confirmed occupation";
        const occupationCode = payload.occupation && payload.occupation.onet_soc_code ? " · O*NET-SOC " + payload.occupation.onet_soc_code : "";
        const totalReviewCount = Number(context.total_review_count || reviews.length);
        const totalText = totalReviewCount > reviews.length ? " of " + totalReviewCount : "";
        occupationContextTitle.textContent = occupationTitle + occupationCode + " · " + (reviews.length ? filteredReviews.length + totalText + " public comment" + (totalReviewCount === 1 ? "" : "s") : "No public comments loaded") + ". There is no overall occupation rating.";
        if (context.is_truncated) occupationContextTitle.textContent += " Display limited to the most recent " + reviews.length + ".";
        if (!reviews.length) { occupationReviews.appendChild(make("p", "occupation-context-empty", "No public review context is loaded for this occupation yet. When available, comments remain tied to their source, date, and scope.")); return; }
        if (!filteredReviews.length) { occupationReviews.appendChild(make("p", "occupation-context-empty", "No comments match these filters. Try showing all sources and topics.")); return; }
        filteredReviews.slice(0, 8).forEach(function (review) {
          const card = make("article", "occupation-review");
          const meta = make("div", "occupation-review-meta");
          const source = review.source_url ? document.createElement("a") : make("span", "", "");
          source.textContent = reviewSourceLabel(review.source);
          if (review.source_url) { source.href = review.source_url; source.target = "_blank"; source.rel = "noreferrer"; }
          const fields = [reviewScopeLabel(review.review_scope), review.review_date || "Date not provided"];
          if (review.rating != null) fields.push("Rating " + review.rating + "/5");
          if (review.author_display) fields.push("By " + review.author_display);
          meta.append(source, make("span", "", fields.join(" · ")));
          card.appendChild(meta);
          const contextLine = [review.job_title, review.employer, review.location].filter(Boolean).join(" · ");
          if (contextLine) card.appendChild(make("p", "occupation-review-meta", contextLine));
          const quote = make("blockquote", "", review.excerpt); card.appendChild(quote);
          const tags = make("div", "occupation-review-tags");
          (review.topics || []).forEach(function (topic) { tags.appendChild(make("span", "occupation-review-tag", topicLabels[topic] || reviewTopicLabel(topic))); });
          if (tags.childNodes.length) card.appendChild(tags);
          occupationReviews.appendChild(card);
        });
      }
      async function loadOccupationContext(code) {
        occupationStatus.textContent = "Loading public occupation context…";
        try {
          const response = await fetch("/api/occupation-context?source=" + encodeURIComponent(code));
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.detail || "occupation context unavailable");
          occupationContextResult.hidden = false;
          renderOccupationReviews(payload);
          occupationStatus.textContent = "Occupation confirmed for context only. It does not change the job-specific analysis.";
        } catch (error) { occupationStatus.textContent = "Occupation context is unavailable. The job-specific analysis remains available."; }
      }
      occupationReviewSourceFilter.addEventListener("change", function () { if (!occupationContextResult.hidden && latestOccupationContext) renderOccupationReviews(latestOccupationContext); });
      occupationReviewTopicFilter.addEventListener("change", function () { if (!occupationContextResult.hidden && latestOccupationContext) renderOccupationReviews(latestOccupationContext); });
      async function findOccupations() {
        const query = occupationQuery.value.trim();
        if (!query) { occupationStatus.textContent = "Enter an occupation or job-family name first."; return; }
        occupationStatus.textContent = "Finding standard occupations…";
        clearNode(occupationCandidates); occupationContextResult.hidden = true;
        try {
          const response = await fetch("/api/occupation-context?query=" + encodeURIComponent(query));
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.detail || "occupation search unavailable");
          const hasCandidates = (payload.candidates || []).length > 0;
          const isCandidateFamily = payload.mapping_status === "editorial_candidate_crosswalk";
          if (isCandidateFamily && !hasCandidates) {
            occupationCandidates.appendChild(make("p", "occupation-context-empty", "This occupation family was recognized, but the current Atlas data release has no candidate occupations to display. Run the full data build or try another title."));
            occupationStatus.textContent = "Occupation family recognized; no candidate occupations are available in this Atlas release.";
            return;
          }
          if (!hasCandidates) { occupationCandidates.appendChild(make("p", "occupation-context-empty", "No title-based suggestion was found. Try a broader occupation name.")); occupationStatus.textContent = "No standard occupation suggestion found."; return; }
          occupationStatus.textContent = payload.mapping_status === "editorial_candidate_crosswalk"
            ? "These are candidate occupation families. Review the notes and confirm one from the job tasks."
            : "Choose the closest standard occupation. Suggestions require your confirmation.";
          (payload.candidates || []).forEach(function (candidate) {
            const card = make("article", "occupation-candidate");
            const basis = candidate.mapping_status === "candidate_family"
              ? "Candidate occupation family · confirmation required"
              : "Title evidence only · confirmation required";
            const copy = make("div", "", "");
            copy.append(
              make("strong", "", candidate.title),
              make("span", "", (candidate.onet_soc_code || "Code unavailable") + " · " + basis)
            );
            if (candidate.mapping_note) copy.append(make("small", "occupation-candidate-note", candidate.mapping_note));
            const button = make("button", "secondary", "Use this occupation"); button.type = "button"; button.addEventListener("click", function () { loadOccupationContext(candidate.onet_soc_code); });
            card.append(copy, button); occupationCandidates.appendChild(card);
          });
        } catch (error) { occupationStatus.textContent = "Occupation context is unavailable in this session. The job-specific analysis remains available."; }
      }

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
      function percent(value) { return value == null ? "—" : Math.round(Number(value)) + "/100"; }
      function scoreText(value, visible) { return visible && value != null ? percent(value) : "Review first"; }
      function eligibilityText(summary, visible) {
        if (!visible) return "Review first";
        if (summary.eligibility_status === "no_gate_detected") return "No gate detected";
        if (summary.eligibility_status === "verified") return "Verified";
        const count = Number(summary.blocking_constraint_count || 0);
        return count ? count + " to verify" : "Unresolved";
      }
      function updateWorkflow(summary) {
        const needsReview = summary && ["review_required", "insufficient_information"].includes(summary.analysis_status);
        setWorkflowStage(summary && summary.score_visibility === "visible" ? "plan" : (needsReview ? "review" : "intake"));
      }
      function setRing(ringId, value, labelId) {
        if (value == null) { document.getElementById(ringId).style.setProperty("--ring-progress", "0%"); setText(document.getElementById(labelId), "—"); return; }
        const number = Math.max(0, Math.min(100, Number(value || 0)));
        document.getElementById(ringId).style.setProperty("--ring-progress", number + "%");
        setText(document.getElementById(labelId), Math.round(number));
      }
      function renderSemanticReview(review) {
        semanticPanel.hidden = false;
        semanticSummary.textContent = review.overall_note || "The semantic review returned no overall note.";
        clearNode(semanticList);
        (review.requirements || []).forEach(function (item) {
          const card = make("article", "semantic-item");
          const meta = make("div", "semantic-meta");
          meta.append(make("strong", "", item.requirement || "Requirement"), make("span", "", (item.decision || "uncertain") + " · support level: " + (item.support_level || "limited") + " (not a probability)"));
          card.appendChild(meta);
          card.appendChild(make("p", "", item.rationale || "No rationale supplied."));
          if (item.next_step) card.appendChild(make("p", "", "Next step: " + item.next_step));
          semanticList.appendChild(card);
        });
      }
      function redactForPreview(value) {
        if (typeof value === "string") return value.replace(/\bhttps?:\/\/[^\s<>]+/gi, "[redacted URL]").replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "[redacted email]").replace(/(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-])\d{3,4}[\s.-]\d{3,4}(?!\d)/g, "[redacted phone]").replace(/\b\d{3}-\d{2}-\d{4}\b/g, "[redacted government ID]");
        if (Array.isArray(value)) return value.map(redactForPreview);
        if (value && typeof value === "object") { const copy = {}; Object.keys(value).forEach(function (key) { copy[key] = redactForPreview(value[key]); }); return copy; }
        return value;
      }
      function prepareDeepReview() {
        if (!currentAnalysisIsFresh()) { semanticStatus.textContent = "Run an analysis for the current inputs before requesting a review."; return; }
        semanticPayload.value = JSON.stringify(redactForPreview({ job_text: jobInput.value, candidate_text: candidateInput.value, requirements: latest.requirements || [] }), null, 2);
        semanticEndpoint.textContent = "Configured review endpoint: " + reviewEndpoint + ". Sharing is optional and off until you click Send optional review.";
        semanticPreview.hidden = false;
        semanticStatus.textContent = "Review the editable sharing preview before sending.";
      }
      async function sendDeepReview() {
        if (!currentAnalysisIsFresh()) { semanticStatus.textContent = "Inputs changed. Create a new sharing preview before sending."; return; }
        let request;
        try { request = JSON.parse(semanticPayload.value); } catch (error) { semanticStatus.textContent = "The sharing preview must remain valid JSON."; return; }
        if (!request || typeof request.job_text !== "string" || typeof request.candidate_text !== "string" || !Array.isArray(request.requirements)) { semanticStatus.textContent = "The sharing preview needs job text, candidate text, and requirements."; return; }
        const requestSignature = inputSignature();
        const requestId = analysisRequestId;
        semanticStatus.textContent = "Reviewing the supplied evidence…";
        deepReviewButton.disabled = true;
        try {
          const response = await fetch("/api/deep-review", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request) });
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.detail || "review unavailable");
          if (requestId !== analysisRequestId || inputSignature() !== requestSignature) return;
          semanticPreview.hidden = true; renderSemanticReview(payload);
          semanticStatus.textContent = "Review complete. Treat uncertain items as leads for verification.";
        } catch (error) {
          if (requestId !== analysisRequestId || inputSignature() !== requestSignature) return;
          semanticStatus.textContent = "Review unavailable. The rule-based result is still available.";
        }
        finally { if (requestId === analysisRequestId && inputSignature() === requestSignature) deepReviewButton.disabled = !llmEnabled; }
      }
      function requirementTypeLabel(value) {
        return value === "skill" ? "Skill" : "Eligibility requirement";
      }
      function matchingMethodLabel(value) {
        const labels = {
          no_evidence: "No evidence linked",
          direct_skill_id: "Directly related, user-supplied evidence",
          reviewable_transfer_crosswalk: "Transferable evidence",
          candidate_constraint_rule: "Eligibility check",
        };
        return labels[value] || "Requirement and evidence comparison";
      }
      function evidenceLabels(values) {
        const ids = values || [];
        if (!ids.length) return "No linked evidence";
        return ids.map(function (value) {
          const match = /^evidence-(\\d+)$/i.exec(value);
          return match ? "Candidate evidence " + Number(match[1]) : "Candidate evidence";
        }).join(", ");
      }
      function renderDetail(item) {
        clearNode(detail);
        detail.appendChild(make("span", "eyebrow", "Selected requirement"));
        detail.appendChild(make("h3", "detail-title", item.canonical_skill || item.original_text));
        detail.appendChild(make("span", "badge " + (item.status || "unknown"), statusLabels[item.status] || item.status));
        const list = make("div", "detail-list");
        [["Original job text", item.original_text], ["Requirement", requirementTypeLabel(item.requirement_type)], ["Importance", importanceLabels[item.importance_level] || item.importance_level], ["Match score", scoreText(item.match_score * 100, latestScoreVisible)], ["Why this result", matchingMethodLabel(item.matching_method)], ["Linked evidence", evidenceLabels(item.evidence_ids)]].forEach(function (pair) {
          const row = make("div", "detail-line"); row.append(make("span", "detail-copy", pair[0]), make("strong", "", pair[1])); list.appendChild(row);
        });
        detail.appendChild(list);
        let copy = "No reliable evidence was found in the supplied profile. Investigate whether this is a real foundation gap or simply missing information.";
        if (item.status === "direct") copy = "The profile contains direct evidence. Improve the application by making the task, context, and result easier to verify.";
        if (item.status === "direct_weak") copy = "The skill is mentioned, but the proof is thin. Add a concrete task, context, duration, and measurable result.";
        if (item.status === "transferable" || item.status === "transferable_claimed") copy = "The profile contains adjacent evidence. Treat it as a bridge to investigate, not as proof that the requirements are identical.";
        if (item.status === "claimed") copy = "The profile makes a capability claim, but no reviewable proof was supplied. Add a task, context, result, or work sample before relying on this signal.";
        if (item.hard_constraint) copy = item.status === "met" ? "This eligibility requirement appears satisfied from the supplied profile." : "This is an eligibility requirement. Verify it directly before using the soft score to prioritize the application.";
        detail.appendChild(make("p", "detail-copy", copy));
        if (item.source_context) detail.appendChild(make("p", "detail-copy", "Job context: " + item.source_context));
      }
      function renderMatrix(items) {
        clearNode(matrix);
        if (!items.length) { matrix.appendChild(make("p", "detail-copy", "No results yet. Run the analysis first.")); return; }
        items.forEach(function (item, index) {
          const row = make("button", "matrix-row" + (index === 0 ? " selected" : ""));
          row.type = "button";
          const name = make("span", ""); name.append(make("span", "requirement-name", item.canonical_skill || item.original_text), make("span", "requirement-type", requirementTypeLabel(item.requirement_type)));
          const badge = make("span", "badge " + (item.status || "unknown"), statusLabels[item.status] || item.status);
          const importance = make("span", "detail-copy", importanceLabels[item.importance_level] || item.importance_level);
          const score = make("span", "score-number", latestScoreVisible ? (item.hard_constraint ? (item.status === "met" ? "Met" : "Verify") : percent(item.match_score * 100)) : "Review first");
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
        const left = 232; const barWidth = 590;
        fitChart.appendChild(svgNode("line", { class: "chart-axis", x1: left, y1: 18, x2: left, y2: 320 }));
        visible.forEach(function (item, index) {
          const y = 25 + index * 37;
          const value = item.hard_constraint ? (item.status === "met" ? 100 : 0) : Math.max(0, Math.min(100, Number(item.match_score || 0) * 100));
          fitChart.appendChild(svgNode("text", { class: "chart-label", x: 0, y: y + 13 }, String(item.canonical_skill || item.original_text).slice(0, 30)));
          fitChart.appendChild(svgNode("rect", { x: left, y: y + 3, width: barWidth, height: 17, rx: 6, fill: "#e8e8ed" }));
          fitChart.appendChild(svgNode("rect", { class: "chart-bar", x: left, y: y + 3, width: barWidth * value / 100, height: 17, rx: 6 }));
          fitChart.appendChild(svgNode("text", { class: "chart-value", x: left + barWidth + 12, y: y + 16 }, item.hard_constraint ? (item.status === "met" ? "met" : "verify") : Math.round(value) + "%"));
        });
        fitChart.appendChild(svgNode("text", { class: "chart-label", x: left, y: 338 }, "0"));
        fitChart.appendChild(svgNode("text", { class: "chart-label", x: left + barWidth, y: 338, "text-anchor": "end" }, "100"));
      }
      function renderGaps(gaps) {
        clearNode(gapList);
        if (!gaps.length) { gapList.appendChild(make("article", "gap-card low", "No priority gaps found.")); return; }
        gaps.slice(0, 6).forEach(function (gap) {
          const card = make("article", "gap-card " + (gap.priority || "medium"));
          const meta = make("div", "gap-meta"); meta.append(make("span", "", (gap.gap_type || "gap").replaceAll("_", " ")), make("span", "", (gap.priority || "medium") + " priority"));
          card.append(meta, make("h3", "", gap.canonical_skill));
          card.append(make("p", "gap-action", gap.action));
          card.append(make("p", "gap-artifact", "Expected proof: " + gap.expected_artifact));
          card.append(make("p", "detail-copy", "Timing: " + gap.time_horizon + " · Effort: " + gap.estimated_effort));
          gapList.appendChild(card);
        });
      }
      function renderFingerprint(fingerprint) {
        fingerprintPanel.hidden = !fingerprint;
        clearNode(categoryProfile); clearNode(mismatchList); clearNode(bundleGrid);
        if (!fingerprint) return;
        (fingerprint.categories || []).forEach(function (item) {
          const row = make("div", "category-row");
          const meta = make("div", "category-meta");
          meta.append(make("span", "category-name", item.category_name || item.category_code), make("span", "", Math.round(Number(item.evidence_coverage || 0) * 100) + "% evidence coverage"));
          const track = make("div", "category-track");
          const fill = make("div", "category-fill"); fill.style.width = Math.max(0, Math.min(100, Number(item.evidence_coverage || 0) * 100)) + "%";
          track.appendChild(fill);
          const foot = make("div", "category-foot");
          foot.append(make("span", "", String(item.required_count || 0) + " role requirement" + (item.required_count === 1 ? "" : "s")), make("span", "", String(item.direct_count || 0) + " direct · " + String(item.transferable_count || 0) + " transferable"));
          row.append(meta, track, foot); categoryProfile.appendChild(row);
        });
        const dimensions = fingerprint.mismatch_dimensions || [];
        if (!dimensions.length) mismatchList.appendChild(make("p", "detail-copy", "No category-level gap is visible in the supplied evidence."));
        dimensions.forEach(function (item) {
          const card = make("div", "mismatch-item");
          card.append(make("strong", "", item.category_name || item.category_code), make("span", "detail-copy", Math.round(Number(item.gap_score || 0) * 100) + "% gap signal · " + String(item.required_count || 0) + " requirement" + (item.required_count === 1 ? "" : "s")));
          mismatchList.appendChild(card);
        });
        const bundles = fingerprint.skill_bundles || [];
        if (!bundles.length) bundleGrid.appendChild(make("p", "detail-copy", "No multi-skill bundle was found in this role text."));
        bundles.slice(0, 6).forEach(function (bundle) {
          const card = make("article", "bundle-card" + (bundle.is_supported ? " supported" : ""));
          const meta = make("div", "bundle-meta"); meta.append(make("span", "", (bundle.gap_type || "role bundle").replaceAll("_", " ")), make("span", "", Math.round(Number(bundle.bundle_match_score || 0) * 100) + "% joint signal"));
          card.append(meta, make("h3", "", (bundle.skills || []).join(" + ")));
          card.append(make("p", "bundle-status", (bundle.statuses || []).map(function (value) { return statusLabels[value] || value; }).join(" · ")));
          card.append(make("p", "bundle-action", bundle.action || "Show the context and result that connect these skills."));
          bundleGrid.appendChild(card);
        });
      }
      function populateGuidedIntakeTypes() {
        if (guidedIntakeType.options.length) return;
        Object.keys(evidenceTypeLabels).forEach(function (value) {
          const option = make("option", "", evidenceTypeLabels[value]);
          option.value = value;
          guidedIntakeType.appendChild(option);
        });
        guidedIntakeType.value = "work";
      }
      function renderGuidedIntake(payload) {
        populateGuidedIntakeTypes();
        const queue = (payload.review_queue || []).filter(function (item) {
          return !item.hard_constraint && item.skill_id;
        });
        const hasActiveEvidence = (payload.evidence || []).some(function (item) {
          return !item.negated && item.skill_id;
        });
        const summary = payload.summary || {};
        const shouldShow = summary.analysis_status === "insufficient_information" || !hasActiveEvidence;
        guidedIntake.hidden = !shouldShow;
        if (!shouldShow) return;
        clearNode(guidedIntakeRequirement);
        if (!queue.length) {
          const option = make("option", "", "Add a soft requirement above, then recalculate");
          option.value = "";
          option.disabled = true;
          option.selected = true;
          guidedIntakeRequirement.appendChild(option);
          guidedIntakeButton.disabled = true;
          guidedIntakeStatus.textContent = "No reviewable skill requirement is available yet. Add a missed requirement above and recalculate first.";
          return;
        }
        queue.forEach(function (item) {
          const option = make("option", "", item.canonical_skill || item.original_text || "Role requirement");
          option.value = item.skill_id;
          guidedIntakeRequirement.appendChild(option);
        });
        const existing = reviewState.added_evidence.find(function (item) {
          return item.intake && queue.some(function (requirement) { return requirement.skill_id === item.skill_id; });
        });
        guidedIntakeRequirement.value = existing ? existing.skill_id : queue[0].skill_id;
        guidedIntakeButton.disabled = false;
        guidedIntakeStatus.textContent = "One concrete example is enough to begin. Add another requirement example if your experience is broader.";
      }
      function addGuidedIntake() {
        if (!latest) {
          guidedIntakeStatus.textContent = "Run an analysis before adding an example.";
          return;
        }
        const requirement = (latest.review_queue || []).find(function (item) {
          return item.skill_id === guidedIntakeRequirement.value && !item.hard_constraint;
        });
        const taskText = guidedIntakeTask.value.trim();
        const contextText = guidedIntakeContext.value.trim();
        const resultText = guidedIntakeResult.value.trim();
        if (!requirement) {
          guidedIntakeStatus.textContent = "Choose a soft role requirement first.";
          return;
        }
        if (!taskText || !contextText) {
          guidedIntakeStatus.textContent = "Add what you did and where or with whom it happened.";
          return;
        }
        const sourceText = taskText + " Context: " + contextText;
        reviewState.added_evidence = reviewState.added_evidence.filter(function (item) {
          return item.skill_id !== requirement.skill_id;
        });
        reviewState.added_evidence.push({
          intake: true,
          skill_id: requirement.skill_id,
          canonical_skill: requirement.canonical_skill,
          analysis_category_code: requirement.analysis_category_code,
          source_text: sourceText,
          result: resultText,
          evidence_type: guidedIntakeType.value,
          duration_months: guidedIntakeDuration.value,
          recency_years: guidedIntakeRecency.value
        });
        guidedIntakeTask.value = "";
        guidedIntakeContext.value = "";
        guidedIntakeResult.value = "";
        guidedIntakeDuration.value = "";
        guidedIntakeRecency.value = "";
        renderAddedReviewItems();
        guidedIntakeStatus.textContent = "Example recorded. Recalculate after reviewing the checklist to include it.";
        reviewStatus.textContent = "Guided example recorded. Recalculate when the review is complete.";
      }
      function renderAddedReviewItems() {
        clearNode(reviewAddedList);
        reviewState.added_requirements.forEach(function (item) {
          reviewAddedList.appendChild(make("span", "", "Added requirement: " + item.text + " (" + (importanceLabels[item.importance_level] || item.importance_level || "Must have") + ")"));
        });
        reviewState.added_evidence.forEach(function (item) {
          const label = evidenceTypeLabels[item.evidence_type] || item.evidence_type || "Evidence";
          const prefix = item.intake ? "Guided example" : label;
          reviewAddedList.appendChild(make("span", "", prefix + " for " + item.canonical_skill + ": " + item.source_text));
        });
      }
      function renderReview(payload) {
        const queue = payload.review_queue || [];
        reviewPanel.hidden = false;
        clearNode(reviewRequirements);
        queue.forEach(function (item) {
          const row = make("div", "review-item");
          const copy = make("div", "review-item-copy");
          copy.append(make("strong", "", item.canonical_skill || item.original_text), make("small", "", (item.original_text || "Extracted requirement") + " · " + (importanceLabels[item.importance_level] || item.importance_level || "Importance not set")));
          row.appendChild(copy);
          if (item.hard_constraint) {
            const select = document.createElement("select");
            select.setAttribute("aria-label", "Confirm " + (item.canonical_skill || "eligibility requirement"));
            [["unknown", "Needs verification"], ["met", "I confirm it is met"], ["not_met", "I confirm it is not met"]].forEach(function (optionValue) {
              const option = make("option", "", optionValue[1]); option.value = optionValue[0]; select.appendChild(option);
            });
            select.value = reviewState.constraint_status_overrides[item.requirement_id] || item.status || "unknown";
            select.addEventListener("change", function () { reviewState.constraint_status_overrides[item.requirement_id] = select.value; reviewStatus.textContent = "Eligibility confirmation recorded. Recalculate when the review is complete."; });
            row.appendChild(select);
          } else {
            const label = make("label", "review-check", "Keep this extracted requirement");
            const checkbox = document.createElement("input"); checkbox.type = "checkbox"; checkbox.checked = !reviewState.removed_requirement_ids.includes(item.requirement_id);
            checkbox.addEventListener("change", function () {
              if (checkbox.checked) reviewState.removed_requirement_ids = reviewState.removed_requirement_ids.filter(function (value) { return value !== item.requirement_id; });
              else if (!reviewState.removed_requirement_ids.includes(item.requirement_id)) reviewState.removed_requirement_ids.push(item.requirement_id);
              reviewStatus.textContent = "Requirement selection recorded. Recalculate when the review is complete.";
            });
            label.prepend(checkbox); row.appendChild(label);
            const importanceLabel = make("label", "review-evidence-field", "Importance");
            const importanceSelect = document.createElement("select");
            importanceSelect.setAttribute("aria-label", "Set importance for " + item.canonical_skill);
            Object.keys(importanceLabels).forEach(function (value) { const option = make("option", "", importanceLabels[value]); option.value = value; importanceSelect.appendChild(option); });
            importanceSelect.value = reviewState.importance_overrides[item.requirement_id] || item.importance_level || "preferred";
            importanceSelect.addEventListener("change", function () { reviewState.importance_overrides[item.requirement_id] = importanceSelect.value; reviewStatus.textContent = "Importance recorded. Recalculate when the review is complete."; });
            importanceLabel.appendChild(importanceSelect); row.appendChild(importanceLabel);
          }
          if (item.skill_id) {
          const evidenceRow = make("div", "review-evidence-grid");
          const typeField = make("label", "review-evidence-field", "Evidence type");
          const typeSelect = document.createElement("select");
          typeSelect.setAttribute("aria-label", "Evidence type for " + item.canonical_skill);
          Object.keys(evidenceTypeLabels).forEach(function (value) { const option = make("option", "", evidenceTypeLabels[value]); option.value = value; typeSelect.appendChild(option); });
          typeSelect.value = "work";
          typeField.appendChild(typeSelect);
          const sourceField = make("label", "review-evidence-field", "Source or context");
          const sourceInput = make("input", ""); sourceInput.type = "text"; sourceInput.placeholder = "Where did this happen?"; sourceInput.setAttribute("aria-label", "Source or context for " + item.canonical_skill); sourceField.appendChild(sourceInput);
          const resultField = make("label", "review-evidence-field", "Task or result");
          const resultInput = make("input", ""); resultInput.type = "text"; resultInput.placeholder = "What did you do or achieve?"; resultInput.setAttribute("aria-label", "Task or result for " + item.canonical_skill); resultField.appendChild(resultInput);
          const durationField = make("label", "review-evidence-field", "Months");
          const durationInput = make("input", ""); durationInput.type = "number"; durationInput.min = "0"; durationInput.step = "1"; durationInput.placeholder = "e.g. 12"; durationInput.setAttribute("aria-label", "Duration in months for " + item.canonical_skill); durationField.appendChild(durationInput);
          const recencyField = make("label", "review-evidence-field", "Years ago");
          const recencyInput = make("input", ""); recencyInput.type = "number"; recencyInput.min = "0"; recencyInput.step = "0.5"; recencyInput.placeholder = "e.g. 1"; recencyInput.setAttribute("aria-label", "Recency in years for " + item.canonical_skill); recencyField.appendChild(recencyInput);
          const evidenceButton = make("button", "secondary", "Add evidence"); evidenceButton.type = "button";
          evidenceButton.addEventListener("click", function () {
            const sourceText = sourceInput.value.trim();
            const resultText = resultInput.value.trim();
            if (!sourceText && !resultText) { reviewStatus.textContent = "Add a source, task, or result before recording evidence."; return; }
            reviewState.added_evidence = reviewState.added_evidence.filter(function (value) { return value.skill_id !== item.skill_id; });
            reviewState.added_evidence.push({ skill_id: item.skill_id, canonical_skill: item.canonical_skill, analysis_category_code: item.analysis_category_code, source_text: sourceText || resultText, result: resultText, evidence_type: typeSelect.value, duration_months: durationInput.value, recency_years: recencyInput.value });
            sourceInput.value = ""; resultInput.value = ""; durationInput.value = ""; recencyInput.value = "";
            renderAddedReviewItems(); reviewStatus.textContent = (evidenceTypeLabels[typeSelect.value] || "Evidence") + " recorded. Recalculate when the review is complete.";
          });
          evidenceRow.append(typeField, sourceField, resultField, durationField, recencyField, evidenceButton); row.appendChild(evidenceRow);
          }
          reviewRequirements.appendChild(row);
        });
        renderGuidedIntake(payload);
        renderAddedReviewItems();
        reviewStatus.textContent = payload.review && ["user_confirmed", "candidate_evidence_confirmed"].includes(payload.review.status) ? "User confirmations applied. You can review and recalculate again." : "The current result is provisional until you confirm the extracted items.";
      }
      function renderComparison(payload) {
        clearNode(comparisonGrid);
        (payload.roles || []).forEach(function (item) {
          const summary = item.summary || {};
          const card = make("article", "comparison-card");
          const rank = make("div", "comparison-rank");
          const roleReviewed = summary.review_status === "user_confirmed";
          rank.append(make("span", "", roleReviewed && item.priority_rank != null ? "Priority " + item.priority_rank : "Role review required"), make("span", "", readinessLabels[summary.readiness_status] || "Preparation route"));
          card.appendChild(rank);
          card.appendChild(make("h3", "", item.role_label || "Target role"));
          card.appendChild(make("p", "comparison-basis", (roleReviewed ? "" : "No preparation ranking is shown before this role checklist is confirmed. ") + (item.priority_basis || "Review this role before comparing it.")));
          const metrics = make("div", "comparison-metrics");
          [["Readiness", scoreText(summary.application_readiness_score, roleReviewed)], ["Evidence fit", scoreText(summary.evidence_fit_score, roleReviewed)], ["Requirements", roleReviewed ? String(summary.requirements_identified == null ? "—" : summary.requirements_identified) + " found" : "Review first"], ["Eligibility", eligibilityText(summary, roleReviewed)]].forEach(function (pair) {
            const metric = make("div", "comparison-metric");
            metric.append(make("span", "", pair[0]), make("strong", "", pair[1]));
            metrics.appendChild(metric);
          });
          card.appendChild(metrics);
          const action = item.top_action ? item.top_action.action : "No priority action was generated from the supplied text.";
          card.appendChild(make("p", "comparison-action", "Next move: " + action));
          const inspect = make("button", "secondary", "Inspect this role");
          inspect.type = "button";
          inspect.addEventListener("click", function () {
            jobInput.value = item.role_text || "";
            activeComparisonRoleId = item.role_id || "";
            reviewState = comparisonRoleReviews[activeComparisonRoleId]
              ? JSON.parse(JSON.stringify(comparisonRoleReviews[activeComparisonRoleId]))
              : newReviewState();
            analyze();
            status.textContent = "Loading " + (item.role_label || "the selected role") + " so you can confirm its checklist.";
            jobInput.scrollIntoView({ behavior: "smooth", block: "center" });
          });
          card.appendChild(inspect);
          comparisonGrid.appendChild(card);
        });
        comparisonPanel.hidden = !(payload.roles || []).length;
      }
      function render(payload) {
        latest = payload;
        analyzedSignature = inputSignature();
        deepReviewButton.disabled = !llmEnabled;
        const summary = payload.summary || {};
        const language = summary.candidate_language || {};
        languageStatus.textContent = language.requires_language_review
          ? (language.note || "Some profile content may need translation or structured evidence before relying on a complete role picture.")
          : "The current profile language is compatible with the English-first rule-based dictionary; confirm mixed-language terms during review.";
        latestScoreVisible = summary.score_visibility === "visible" && summary.review_status === "user_confirmed";
        downloadMarkdownButton.disabled = !latestScoreVisible;
        downloadPdfButton.disabled = !latestScoreVisible;
        setText(fitScore, scoreText(summary.evidence_fit_score, latestScoreVisible));
        setText(readinessScore, scoreText(summary.application_readiness_score, latestScoreVisible));
        setText(inputCoverageScore, summary.requirements_identified == null ? "—" : String(summary.requirements_identified) + " found");
        setText(blockedCount, eligibilityText(summary, latestScoreVisible));
        coveragePanel.hidden = false;
        setText(requirementCoverageScore, summary.requirements_identified == null ? "—" : String(summary.requirements_identified) + " found");
        setText(evidenceCoverageScore, scoreText(summary.evidence_coverage_score, latestScoreVisible));
        setText(eligibilityCoverageScore, eligibilityText(summary, latestScoreVisible));
        setText(decisionLabel, latestScoreVisible ? summary.decision_label : "Review the extracted requirements and evidence before relying on a preparation signal.");
        setRing("capability-ring", latestScoreVisible ? summary.capability_signal_score : null, "capability-signal");
        setRing("proof-ring", latestScoreVisible ? summary.proof_signal_score : null, "proof-signal");
        setRing("readiness-ring", latestScoreVisible ? summary.application_readiness_score : null, "readiness-signal");
        renderMatrix(payload.requirements || []);
        if (!latestScoreVisible) clearNode(fitChart); else renderChart(payload.requirements || []);
        const canShowNonScoreActions = summary.analysis_status === "insufficient_information";
        if (!latestScoreVisible && !canShowNonScoreActions) { clearNode(gapList); gapList.appendChild(make("article", "gap-card low", "Review the extracted checklist first. The next-action plan will appear after you confirm it.")); }
        else renderGaps(payload.next_actions || payload.gaps || []);
        renderFingerprint(latestScoreVisible ? payload.role_fingerprint : null);
        renderReview(payload);
        updateWorkflow(summary);
        status.textContent = (summary.analysis_status === "insufficient_information" ? "More input needed · " : summary.review_status === "provisional" ? "Review required · " : summary.review_status === "candidate_evidence_confirmed" ? "Candidate evidence reviewed · " : "Reviewed analysis · ") + (summary.requirement_count || 0) + " requirements mapped";
      }
      async function analyze() {
        if (!jobInput.value.trim() || !candidateInput.value.trim()) { status.textContent = "Both texts are required."; return; }
        const requestSignature = inputSignature();
        if (reviewState.base_signature && reviewState.base_signature !== requestSignature) reviewState = newReviewState();
        const requestReview = reviewState.applied ? Object.assign({}, reviewState) : null;
        const requestId = ++analysisRequestId;
        clearRenderedAnalysis();
        status.textContent = "Analyzing your inputs…";
        try {
          const request = { job_text: jobInput.value, candidate_text: candidateInput.value, candidate_language: candidateLanguage.value };
          if (activeComparisonRoleId && comparisonEvidence.length) request.evidence = comparisonEvidence;
          if (requestReview) request.review = Object.assign({}, requestReview, { scope: "role_requirements" });
          const response = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request) });
          if (!response.ok) throw new Error("request failed");
          const payload = await response.json();
          if (requestId !== analysisRequestId || inputSignature() !== requestSignature) return;
          render(payload);
        } catch (error) {
          if (requestId !== analysisRequestId || inputSignature() !== requestSignature) return;
          clearRenderedAnalysis();
          reviewState = newReviewState();
          status.textContent = "Analysis unavailable. Please try again.";
        }
      }
      async function applyReview() {
        if (!currentAnalysisIsFresh()) { invalidateCurrentResult("Inputs changed. Analyze the current text before reviewing the extraction."); reviewStatus.textContent = "Run an analysis for the current inputs before reviewing the extraction."; return; }
        reviewState.applied = true;
        reviewState.base_signature = inputSignature();
        reviewStatus.textContent = "Recalculating from the reviewed inputs...";
        await analyze();
        if (activeComparisonRoleId && latest && (latest.summary || {}).review_status === "user_confirmed") {
          comparisonRoleReviews[activeComparisonRoleId] = Object.assign(
            {},
            JSON.parse(JSON.stringify(reviewState)),
            { scope: "role_requirements" }
          );
          reviewStatus.textContent = "This role checklist is confirmed. Return to the role comparison and compare again to update the priority order.";
        }
      }
      function addRequirement() {
        const text = addedRequirementInput.value.trim();
        if (!text) { reviewStatus.textContent = "Enter a requirement before adding it."; return; }
        reviewState.added_requirements.push({ text: text, importance_level: addedRequirementImportance.value });
        addedRequirementInput.value = "";
        renderAddedReviewItems();
        reviewStatus.textContent = "The added requirement will be mapped when you recalculate.";
      }
      async function downloadPlan(format) {
        if (!currentAnalysisIsFresh()) { invalidateCurrentResult("Inputs changed. Analyze the current text before downloading the plan."); return; }
        if (!latestScoreVisible) { status.textContent = "Review the extracted requirements before downloading the plan."; return; }
        const button = format === "pdf" ? downloadPdfButton : downloadMarkdownButton;
        button.disabled = true;
        status.textContent = "Preparing your " + (format === "pdf" ? "PDF" : "Markdown") + " plan…";
        try {
          const request = { format: format, job_text: jobInput.value, candidate_text: candidateInput.value, candidate_language: candidateLanguage.value, review: Object.assign({}, reviewState, { scope: "role_requirements" }) };
          if (activeComparisonRoleId && comparisonEvidence.length) request.evidence = comparisonEvidence;
          const response = await fetch("/api/report", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request) });
          if (!response.ok) { const payload = await response.json(); throw new Error(payload.detail || "report unavailable"); }
          const blob = await response.blob();
          const filename = format === "pdf" ? "career-fit-plan.pdf" : "career-fit-plan.md";
          const link = document.createElement("a");
          link.href = URL.createObjectURL(blob);
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          link.remove();
          window.setTimeout(function () { URL.revokeObjectURL(link.href); }, 0);
          status.textContent = "Downloaded your evidence-first " + (format === "pdf" ? "PDF" : "Markdown") + " plan.";
        } catch (error) { status.textContent = "The plan could not be created. Confirm the reviewed analysis and try again."; }
        finally { button.disabled = !latestScoreVisible; }
      }
      async function compare() {
        const roles = rolesInput.value.split(/\r?\n\s*---+\s*\r?\n/).map(function (value) { return value.trim(); }).filter(Boolean);
        if (roles.length < 2) { compareStatus.textContent = "Add at least two roles, separated by a line containing --- ."; return; }
        if (roles.length > 3) { compareStatus.textContent = "Compare up to three roles at a time."; return; }
        if (!candidateInput.value.trim()) { compareStatus.textContent = "Add a candidate profile before comparing roles."; return; }
        if (!currentAnalysisIsFresh() || !reviewState.base_signature || reviewState.base_signature !== inputSignature()) { compareStatus.textContent = "Run the analysis and review the current candidate evidence before comparing roles."; return; }
        if (!latest || !["user_confirmed", "candidate_evidence_confirmed"].includes((latest.summary || {}).review_status)) { compareStatus.textContent = "Review the candidate evidence before comparing roles."; return; }
        if (!comparisonEvidence.length) comparisonEvidence = latest.evidence || [];
        const requestSignature = inputSignature();
        const requestRoles = rolesInput.value;
        const requestId = ++compareRequestId;
        clearComparisonResult();
        compareStatus.textContent = "Comparing the supplied roles…";
        compareButton.disabled = true;
        try {
          const response = await fetch("/api/compare", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ roles: roles, candidate_text: candidateInput.value, candidate_language: candidateLanguage.value, evidence: comparisonEvidence, review: { scope: "candidate_evidence", applied: true, base_signature: inputSignature() }, role_reviews: comparisonRoleReviews }) });
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.detail || "comparison unavailable");
          if (requestId !== compareRequestId || inputSignature() !== requestSignature || rolesInput.value !== requestRoles) return;
          renderComparison(payload);
          compareStatus.textContent = payload.comparison_status === "ranked_after_role_review" ? "All role checklists are confirmed. Priorities reflect reviewed readiness and evidence fit, not hiring probability." : "Role cards are ready. Confirm each role's requirements before assigning a preparation priority.";
        } catch (error) {
          if (requestId !== compareRequestId || inputSignature() !== requestSignature || rolesInput.value !== requestRoles) return;
          clearComparisonResult();
          compareStatus.textContent = "Comparison unavailable. Check the role separators and try again.";
        }
        finally { compareButton.disabled = false; }
      }
      function reset() {
        analysisRequestId += 1;
        compareRequestId += 1;
        latest = null;
        analyzedSignature = "";
        latestScoreVisible = false;
        reviewState = newReviewState();
        comparisonEvidence = [];
        comparisonRoleReviews = {};
        activeComparisonRoleId = "";
        jobInput.value = ""; candidateInput.value = ""; candidateLanguage.value = "auto"; rolesInput.value = ""; clearNode(matrix); clearNode(gapList); clearNode(fitChart); clearNode(comparisonGrid); clearNode(categoryProfile); clearNode(mismatchList); clearNode(bundleGrid);
        candidateFile.value = ""; candidateFileStatus.textContent = "No file selected. Contact details should be removed first.";
        documentPreview.hidden = true; documentPreviewText.value = "";
        detail.innerHTML = ""; detail.append(make("span", "eyebrow", "Selected requirement"), make("h3", "detail-title", "Waiting for analysis"), make("p", "detail-copy", "Run the analysis, then select a requirement to inspect its evidence trail."));
        semanticPanel.hidden = true; comparisonPanel.hidden = true; fingerprintPanel.hidden = true; coveragePanel.hidden = true; reviewPanel.hidden = true; guidedIntake.hidden = true; clearNode(semanticList); clearNode(reviewRequirements); clearNode(reviewAddedList); clearNode(guidedIntakeRequirement); guidedIntakeTask.value = ""; guidedIntakeContext.value = ""; guidedIntakeResult.value = ""; guidedIntakeDuration.value = ""; guidedIntakeRecency.value = ""; guidedIntakeStatus.textContent = "One concrete example is enough to begin."; semanticSummary.textContent = "";
        clearNode(occupationCandidates); occupationContextResult.hidden = true; marketContext.hidden = true; clearNode(marketMetrics); clearNode(marketTasks); clearNode(marketAdjacent); occupationStatus.textContent = "Select a standard occupation before viewing worker context.";
        latestOccupationContext = null;
        [fitScore, readinessScore, inputCoverageScore, blockedCount, requirementCoverageScore, evidenceCoverageScore, eligibilityCoverageScore].forEach(function (node) { node.textContent = "—"; });
        languageStatus.textContent = "The rule-based dictionary is English-first. Choose a language when the profile is not primarily English.";
        downloadMarkdownButton.disabled = true;
        downloadPdfButton.disabled = true;
        deepReviewButton.disabled = true;
        ["capability-ring", "proof-ring", "readiness-ring"].forEach(function (id) { document.getElementById(id).style.setProperty("--ring-progress", "0%"); });
        ["capability-signal", "proof-signal", "readiness-signal"].forEach(function (id) { document.getElementById(id).textContent = "—"; });
        decisionLabel.textContent = "Run an analysis to see what the current text can support."; status.textContent = "Cleared."; compareStatus.textContent = "Use this when you are deciding where to focus first."; semanticStatus.textContent = llmEnabled ? "Optional review available." : "Optional review available when enabled.";
      }
      candidateFile.addEventListener("change", async function () {
        const file = candidateFile.files && candidateFile.files[0];
        if (!file) return;
        if (file.size > 1000000) { candidateFileStatus.textContent = "That file is larger than 1 MB. Paste a shorter, redacted version instead."; candidateFile.value = ""; return; }
        try {
          candidateFileStatus.textContent = "Preparing " + file.name + " for this app's editable redacted preview…";
          const encoded = await new Promise(function (resolve, reject) { const reader = new FileReader(); reader.onerror = reject; reader.onload = function () { resolve(String(reader.result || "").split(",").pop()); }; reader.readAsDataURL(file); });
          const response = await fetch("/api/document-preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ filename: file.name, content_type: file.type, file_base64: encoded }) });
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.detail || "document unavailable");
          documentPreviewText.value = payload.redacted_preview || "";
          documentPreviewNotice.textContent = payload.notice || "Review the imported text before using it.";
          documentPreview.hidden = false;
          candidateFileStatus.textContent = file.name + " is ready for review. It has not been added to your profile.";
        } catch (error) { candidateFileStatus.textContent = "The document could not be imported safely. Paste a short, redacted text version instead."; candidateFile.value = ""; }
      });
      useDocumentPreviewButton.addEventListener("click", function () { const text = documentPreviewText.value.trim(); if (!text) { candidateFileStatus.textContent = "Review text is empty. Paste your experience instead."; return; } invalidateCurrentResult("Reviewed document text loaded. Analyze when ready."); candidateInput.value = text; documentPreview.hidden = true; candidateFileStatus.textContent = "Reviewed text is now in your experience field."; });
      cancelDocumentPreviewButton.addEventListener("click", function () { documentPreview.hidden = true; documentPreviewText.value = ""; candidateFile.value = ""; candidateFileStatus.textContent = "Import discarded. Your existing experience text was not changed."; });
      exampleButton.addEventListener("click", function () { reviewState = newReviewState(); jobInput.value = DEFAULT_JOB; candidateInput.value = DEFAULT_CANDIDATE; analyze(); });
      [jobInput, candidateInput, candidateLanguage].forEach(function (input) { input.addEventListener("input", handleInputChange); });
      rolesInput.addEventListener("input", function () { comparisonRoleReviews = {}; activeComparisonRoleId = ""; if (!comparisonPanel.hidden) { compareRequestId += 1; clearComparisonResult(); compareStatus.textContent = "Target roles changed. Compare again to refresh the ranking."; } });
      analyzeButton.addEventListener("click", analyze);
      compareButton.addEventListener("click", compare);
      occupationSearchButton.addEventListener("click", findOccupations);
      occupationQuery.addEventListener("keydown", function (event) { if (event.key === "Enter") findOccupations(); });
      downloadMarkdownButton.addEventListener("click", function () { downloadPlan("markdown"); });
      downloadPdfButton.addEventListener("click", function () { downloadPlan("pdf"); });
      deepReviewButton.addEventListener("click", prepareDeepReview);
      sendSemanticReviewButton.addEventListener("click", sendDeepReview);
      cancelSemanticReviewButton.addEventListener("click", function () { semanticPreview.hidden = true; semanticStatus.textContent = "Optional review was not sent."; });
      editInputsButton.addEventListener("click", function () { setWorkflowStage("intake"); jobInput.focus(); });
      backToInputsButton.addEventListener("click", function () { setWorkflowStage("intake"); jobInput.focus(); });
      clearButton.addEventListener("click", reset);
      addRequirementButton.addEventListener("click", addRequirement);
      guidedIntakeButton.addEventListener("click", addGuidedIntake);
      applyReviewButton.addEventListener("click", applyReview);
      deepReviewButton.disabled = !llmEnabled;
      if (llmEnabled) semanticStatus.textContent = "Optional review available.";
      setWorkflowStage("intake");
    }());
  </script>
</body>
</html>
"""


def _json_literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def render_page() -> str:
    configured_endpoint = urlparse(LLM_REVIEW_CLIENT.config.base_url).netloc
    review_endpoint = configured_endpoint or "not configured"
    privacy_note = (
        "Privacy and sharing: rule-based analysis stays in this app. Importing a document sends the selected file to this app only to make an editable redacted preview; use a local deployment for personal documents. Deep semantic review is optional; it sends only the editable sharing preview you approve to the configured endpoint. Common direct identifiers are removed first, but the preview is not fully anonymous."
        if LLM_REVIEW_CLIENT.config.enabled
        else "Privacy reminder: rule-based analysis stays in this app. If you choose a document, the complete selected file is sent to this app to create an editable redacted preview before you decide whether to use that text; use a local deployment for personal documents. Remove names, email addresses, phone numbers, identification numbers, health information, and other sensitive details before analyzing."
    )
    privacy_footer = (
        "Privacy note: Rule-based analysis runs in this app, but optional semantic review sends the editable sharing preview to the configured endpoint only when you click Send. Remove remaining sensitive details first; this app does not provide hosted personal-data storage."
        if LLM_REVIEW_CLIENT.config.enabled
        else "Privacy note: Inputs are processed by this app and are not permanently stored by it. If you choose a document, the complete selected file is sent to this app to create an editable redacted preview before you decide whether to use that text; use a local deployment for personal documents. Remove sensitive details before analysis."
    )
    return (
        HTML.replace("__DEFAULT_JOB__", _json_literal(DEFAULT_JOB))
        .replace("__DEFAULT_CANDIDATE__", _json_literal(DEFAULT_CANDIDATE))
        .replace("__LLM_ENABLED__", json.dumps(LLM_REVIEW_CLIENT.config.enabled))
        .replace("__REVIEW_ENDPOINT__", _json_literal(review_endpoint))
        .replace("__PRIVACY_NOTE__", html.escape(privacy_note))
        .replace("__PRIVACY_FOOTER__", html.escape(privacy_footer))
    )


def _fetch_atlas_context(params: dict[str, str]) -> tuple[dict[str, object], int]:
    if not ATLAS_URL:
        return (
            {
                "error": "not_configured",
                "detail": "Set CAREER_FIT_ATLAS_URL to connect AI Labor Atlas.",
            },
            503,
        )
    atlas = urlparse(ATLAS_URL)
    if atlas.scheme not in {"http", "https"} or not atlas.netloc:
        return (
            {
                "error": "invalid_configuration",
                "detail": "CAREER_FIT_ATLAS_URL must be an http(s) URL.",
            },
            503,
        )
    url = f"{ATLAS_URL}/api/occupation-context?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with build_opener(ProxyHandler({})).open(request, timeout=8) as response:
            payload = json.loads(response.read(240_000).decode("utf-8"))
            return payload, response.status
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read(240_000).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {"error": "atlas_error", "detail": str(exc)}
        return payload, exc.code
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"error": "atlas_unavailable", "detail": str(exc)}, 502


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
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

    def _send_bytes(
        self, body: bytes, content_type: str, filename: str, status: int = 200
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        request_limits = {
            "/api/deep-review": 120_000,
            "/api/compare": 160_000,
            "/api/analyze": 160_000,
            "/api/document-preview": 1_500_000,
            "/api/report": 320_000,
        }
        if parsed.path in request_limits:
            try:
                request_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_json(
                    {"error": "invalid_request", "detail": "invalid Content-Length"},
                    status=400,
                )
                return
            if request_length < 0 or request_length > request_limits[parsed.path]:
                self._send_json(
                    {
                        "error": "request_too_large",
                        "detail": f"request body must be at most {request_limits[parsed.path]} bytes",
                    },
                    status=413,
                )
                return
        if parsed.path == "/api/deep-review":
            try:
                length = min(int(self.headers.get("Content-Length", "0")), 120_000)
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                requirements = payload.get("requirements", [])
                if not isinstance(requirements, list):
                    raise TypeError("requirements must be a list")
                job_text = payload.get("job_text", "")
                candidate_text = payload.get("candidate_text", "")
                if not isinstance(job_text, str):
                    raise TypeError("job_text must be a string")
                if not isinstance(candidate_text, str):
                    raise TypeError("candidate_text must be a string")
                result = LLM_REVIEW_CLIENT.review_fit(
                    job_text[:40_000],
                    candidate_text[:40_000],
                    requirements[:30],
                )
            except LLMNotConfiguredError as exc:
                self._send_json(
                    {"error": "not_configured", "detail": str(exc)}, status=503
                )
                return
            except LLMReviewError as exc:
                self._send_json(
                    {"error": "review_failed", "detail": str(exc)}, status=502
                )
                return
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                self._send_json(
                    {"error": "invalid_request", "detail": str(exc)}, status=400
                )
                return
            self._send_json(result)
            return
        if parsed.path == "/api/document-preview":
            try:
                length = min(int(self.headers.get("Content-Length", "0")), 1_500_000)
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(payload, dict):
                    raise TypeError("request body must be a JSON object")
                result = extract_import_preview(
                    payload.get("file_base64", ""),
                    payload.get("filename", ""),
                    payload.get("content_type", ""),
                )
            except (
                DocumentExtractionError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                self._send_json(
                    {"error": "invalid_document", "detail": str(exc)}, status=400
                )
                return
            self._send_json(result)
            return
        if parsed.path == "/api/report":
            try:
                length = min(int(self.headers.get("Content-Length", "0")), 320_000)
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(payload, dict):
                    raise TypeError("request body must be a JSON object")
                job_text = payload.get("job_text", "")
                candidate_text = payload.get("candidate_text", "")
                if not isinstance(job_text, str) or not isinstance(candidate_text, str):
                    raise TypeError("job_text and candidate_text must be strings")
                analysis = analyze_fit(
                    job_text[:40_000],
                    candidate_text[:40_000],
                    payload.get("evidence"),
                    payload.get("review"),
                    payload.get("candidate_language", "auto"),
                )
                summary = analysis.get("summary", {})
                if (
                    not isinstance(summary, dict)
                    or summary.get("review_status") != "user_confirmed"
                    or summary.get("score_visibility") != "visible"
                ):
                    raise ValueError(
                        "review the extracted requirements before exporting a plan"
                    )
                report_format = payload.get("format")
                if report_format == "markdown":
                    self._send_bytes(
                        build_markdown_plan(analysis).encode("utf-8"),
                        "text/markdown; charset=utf-8",
                        "career-fit-plan.md",
                    )
                elif report_format == "pdf":
                    self._send_bytes(
                        build_pdf_plan(analysis),
                        "application/pdf",
                        "career-fit-plan.pdf",
                    )
                else:
                    raise ValueError("format must be markdown or pdf")
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                self._send_json(
                    {"error": "invalid_report", "detail": str(exc)}, status=400
                )
            return
        if parsed.path == "/api/compare":
            try:
                length = min(int(self.headers.get("Content-Length", "0")), 160_000)
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(payload, dict):
                    raise TypeError("request body must be a JSON object")
                roles = payload.get("roles", [])
                if not isinstance(roles, list):
                    raise TypeError("roles must be a list")
                role_texts = []
                for role in roles:
                    if not isinstance(role, str):
                        raise TypeError("roles must contain job-description strings")
                    role_texts.append(role[:40_000])
                candidate_text = payload.get("candidate_text", "")
                if not isinstance(candidate_text, str):
                    raise TypeError("candidate_text must be a string")
                result = compare_roles(
                    role_texts,
                    candidate_text[:40_000],
                    payload.get("evidence"),
                    payload.get("review"),
                    payload.get("candidate_language", "auto"),
                    payload.get("role_reviews"),
                )
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                self._send_json(
                    {"error": "invalid_request", "detail": str(exc)}, status=400
                )
                return
            self._send_json(result)
            return
        if parsed.path != "/api/analyze":
            self._send_json({"error": "not_found"}, status=404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise TypeError("request body must be a JSON object")
            job_text = payload.get("job_text", "")
            candidate_text = payload.get("candidate_text", "")
            if not isinstance(job_text, str):
                raise TypeError("job_text must be a string")
            if not isinstance(candidate_text, str):
                raise TypeError("candidate_text must be a string")
            result = analyze_fit(
                job_text,
                candidate_text,
                payload.get("evidence"),
                payload.get("review"),
                payload.get("candidate_language", "auto"),
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._send_json(
                {"error": "invalid_request", "detail": str(exc)}, status=400
            )
            return
        self._send_json(result)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if parsed.path == "/" or parsed.path == "/index.html":
            self._send_page()
            return
        if parsed.path in {"/api/analyze", "/api/document-preview", "/api/report"}:
            self._send_json({"error": "use_post"}, status=405)
            return
        if parsed.path == "/api/occupation-context":
            params = parse_qs(parsed.query)
            source = params.get("source", [""])[0]
            query = params.get("query", [""])[0]
            if bool(source) == bool(query):
                self._send_json(
                    {
                        "error": "invalid_request",
                        "detail": "provide exactly one of source or query",
                    },
                    status=400,
                )
                return
            payload, status = _fetch_atlas_context(
                {"source": source} if source else {"query": query}
            )
            self._send_json(payload, status=status)
            return
        self._send_json({"error": "not_found"}, status=404)

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8766) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Career Fit running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
