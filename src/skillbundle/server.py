from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import ProxyHandler, Request, build_opener

from .career import analyze_fit, compare_roles
from .llm_review import LLMNotConfiguredError, LLMReviewClient, LLMReviewError


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
    @media (max-width: 700px) { .shell { width: min(100% - 36px, 1180px); } .hero { padding-top: 54px; } .input-grid, .meaning-grid, .gap-grid, .comparison-grid { grid-template-columns: 1fr; } .panel { padding: 21px; } .summary-grid { grid-template-columns: 1fr 1fr; gap: 22px; } .summary-card:nth-child(3) { padding-left: 0; border-left: 0; } .summary-card:nth-child(3), .summary-card:nth-child(4) { margin-top: 0; } .matrix-row, .matrix-head { grid-template-columns: minmax(125px, 1fr) 106px 78px; } .matrix-row > :nth-child(3), .matrix-head > :nth-child(3) { display: none; } .signal-card { grid-template-columns: 64px minmax(0, 1fr); } .ring { width: 58px; } .toolbar { align-items: flex-start; } }
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div class="brand"><span class="brand-mark" aria-hidden="true"></span><span class="brand-name">Career Fit</span></div>
      <span class="micro">Private by default · explainable preparation</span>
    </header>

    <section class="hero">
      <div class="hero-copy">
        <div class="hero-badge">EVIDENCE-FIRST JOB SEARCH</div>
        <h1>Turn uncertainty into an application plan.</h1>
        <p>Career Fit helps you answer three practical questions: can I do this, can I prove it, and should I apply now? It translates a job description into an evidence map without pretending to predict a hiring decision.</p>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div><span class="eyebrow">Start with one target role</span><h2>Make the hidden decision visible.</h2></div>
        <p>Paste a role and a candidate profile. Every result is tied back to a requirement, an evidence signal, or a verification step.</p>
      </div>
      <div class="panel">
        <div class="toolbar">
          <button id="analyze-button" type="button">Analyze this role</button>
          <button id="example-button" class="secondary" type="button">Load example</button>
          <button id="clear-button" class="secondary" type="button">Clear</button>
          <button id="download-button" class="secondary" type="button" disabled>Download plan</button>
          <span id="status" class="status" aria-live="polite">Ready for analysis</span>
          <button id="deep-review-button" class="secondary" type="button" disabled>Deep semantic review</button>
          <span id="semantic-status" class="status" aria-live="polite">Optional review available when enabled.</span>
        </div>
        <div class="input-grid">
          <div>
            <label class="input-label" for="job-input">Job description <span>target role</span></label>
            <textarea id="job-input" aria-label="Job description"></textarea>
          </div>
          <div>
            <label class="input-label" for="candidate-input">Candidate profile <span>your evidence</span></label>
            <textarea id="candidate-input" aria-label="Candidate profile"></textarea>
          </div>
        </div>
        <p class="privacy-note">Privacy reminder: paste only what you want analyzed. Do not include contact details, identification numbers, or sensitive personal data.</p>
        <div class="occupation-context-panel">
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
        <div class="compare-panel">
          <div class="section-head"><div><span class="eyebrow">Choose where to focus</span><h3>Compare target roles</h3></div><p>Paste two or three job descriptions separated by a line containing <code>---</code>. Career Fit reuses the same candidate evidence and ranks preparation priority, not hiring odds.</p></div>
          <label class="input-label" for="roles-input">Target roles <span>optional role portfolio</span></label>
          <textarea id="roles-input" class="compare-input" aria-label="Target roles" placeholder="Role: People Analytics Analyst&#10;Must have Python and SQL...&#10;---&#10;Role: Data Analyst&#10;Must have Python and data visualization..."></textarea>
          <div class="toolbar"><button id="compare-button" class="secondary" type="button">Compare roles</button><span id="compare-status" class="status" aria-live="polite">Use this when you are deciding where to focus first.</span></div>
          <div id="comparison-panel" class="comparison-panel" hidden><div id="comparison-grid" class="comparison-grid"></div></div>
        </div>
        <div class="summary-grid" aria-live="polite">
          <article class="summary-card"><span class="label">Evidence fit</span><strong id="fit-score" class="summary-value">—</strong><span class="summary-note">weighted requirement overlap</span></article>
          <article class="summary-card"><span class="label">Application readiness</span><strong id="readiness-score" class="summary-value">—</strong><span class="summary-note">preparation triage, not hiring odds</span></article>
          <article class="summary-card"><span class="label">Information confidence</span><strong id="confidence-score" class="summary-value">—</strong><span class="summary-note">clarity and evidence completeness</span></article>
          <article class="summary-card"><span class="label">Eligibility requirements</span><strong id="blocked-count" class="summary-value">—</strong><span class="summary-note">requirements needing verification</span></article>
        </div>
        <div id="fingerprint-panel" class="fingerprint-panel" hidden>
          <div class="section-head"><div><span class="eyebrow">Role fingerprint</span><h3>See the dimensions behind the role.</h3></div><p>Categories organize the posting; named skills remain the evidence unit. This is a descriptive mismatch view, not an ability test.</p></div>
          <div class="fingerprint-layout">
            <div class="fingerprint-card"><div id="category-profile" class="category-profile"></div></div>
            <aside class="fingerprint-card"><span class="eyebrow">Largest dimensions to investigate</span><div id="mismatch-list" class="mismatch-list"></div></aside>
          </div>
          <div class="fingerprint-card"><div class="section-head"><div><span class="eyebrow">Requirements that appear together</span><h3>Turn a skill bundle into one proof artifact.</h3></div><p>These pairs come from this posting only. They do not estimate market value or wage complementarity.</p></div><div id="bundle-grid" class="bundle-grid"></div></div>
        </div>
        <div id="semantic-panel" class="semantic-panel" hidden>
          <span class="eyebrow">Deep semantic review</span>
          <p id="semantic-summary" class="detail-copy"></p>
          <div id="semantic-list" class="semantic-list"></div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-head"><div><span class="eyebrow">Three questions</span><h2>Capability, proof, and readiness are different signals.</h2></div><p id="decision-label">Run an analysis to see what the current text can support.</p></div>
      <div class="signal-grid">
        <article class="signal-card"><div id="capability-ring" class="ring" style="--ring-color: var(--violet)"><strong id="capability-signal">—</strong></div><div><span class="eyebrow">Can I do it?</span><h3>Capability signal</h3><p>Includes direct and transferable overlap. Transfer is a lead for exploration, not proof of equivalence.</p></div></article>
        <article class="signal-card"><div id="proof-ring" class="ring" style="--ring-color: var(--cyan)"><strong id="proof-signal">—</strong></div><div><span class="eyebrow">Can I prove it?</span><h3>Proof signal</h3><p>Rewards concrete tasks, results, duration, and reviewable evidence instead of bare keywords.</p></div></article>
        <article class="signal-card"><div id="readiness-ring" class="ring" style="--ring-color: var(--amber)"><strong id="readiness-signal">—</strong></div><div><span class="eyebrow">Should I apply now?</span><h3>Application readiness</h3><p>Combines must-have evidence, proof strength, and unresolved hard requirements.</p></div></article>
      </div>
    </section>

    <section class="section">
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

    <section class="section">
      <div class="section-head"><div><span class="eyebrow">Fit profile</span><h2>See the shape of the opportunity.</h2></div><p>This chart shows relative evidence signals by requirement. A high bar is not a hiring promise; a low bar is an invitation to investigate the gap.</p></div>
      <div class="panel"><svg id="fit-chart" class="chart-svg" viewBox="0 0 900 340" role="img" aria-label="Requirement evidence profile"></svg></div>
    </section>

    <section class="section">
      <div class="section-head"><div><span class="eyebrow">Gap to action</span><h2>Leave with a useful next move.</h2></div><p>Actions are ordered by requirement importance and evidence shortfall. Each card names the proof artifact you can create or the gate you can verify.</p></div>
      <div id="gap-list" class="gap-grid" aria-live="polite"></div>
    </section>

    <section class="section">
      <div class="section-head"><div><span class="eyebrow">How to read the numbers</span><h2>Useful for preparation, limited for prediction.</h2></div></div>
      <div class="meaning-grid">
        <article class="meaning"><h3>Evidence fit is not hiring probability</h3><p>It is an importance-weighted summary of requirement overlap and supplied evidence. It does not estimate employer decisions.</p></article>
        <article class="meaning"><h3>A proof gap is not an ability gap</h3><p>A candidate may have the capability but lack a concrete task, result, work sample, or clear translation into employer language.</p></article>
        <article class="meaning"><h3>Transfer is deliberately cautious</h3><p>Adjacent evidence can suggest a bridge project, but the system never silently upgrades it to direct equivalence.</p></article>
        <article class="meaning"><h3>Eligibility requirements stay separate</h3><p>Licenses, work authorization, degrees, and experience floors need verification. Soft skill overlap cannot offset an unresolved requirement.</p></article>
      </div>
      <p class="source-note">Privacy note: Your inputs are analyzed locally and are not permanently stored by this app. Career Fit is designed for preparation, not prediction.</p>
    </section>
    <footer class="footer-row"><span>Career Fit · evidence before confidence</span><span>Preparation support, not an automated hiring system.</span></footer>
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
      const compareButton = document.getElementById("compare-button");
      const downloadButton = document.getElementById("download-button");
      const rolesInput = document.getElementById("roles-input");
      const occupationQuery = document.getElementById("occupation-query");
      const occupationSearchButton = document.getElementById("occupation-search-button");
      const occupationStatus = document.getElementById("occupation-status");
      const occupationCandidates = document.getElementById("occupation-candidates");
      const occupationContextResult = document.getElementById("occupation-context-result");
      const occupationContextTitle = document.getElementById("occupation-context-title");
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
      const confidenceScore = document.getElementById("confidence-score");
      const blockedCount = document.getElementById("blocked-count");
      const deepReviewButton = document.getElementById("deep-review-button");
      const semanticStatus = document.getElementById("semantic-status");
      const semanticPanel = document.getElementById("semantic-panel");
      const semanticSummary = document.getElementById("semantic-summary");
      const semanticList = document.getElementById("semantic-list");
      const llmEnabled = __LLM_ENABLED__;
      const statusLabels = {
        direct: "Direct evidence",
        direct_weak: "Mentioned, proof is thin",
        transferable: "Transferable evidence",
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
      let latest = null;
      let latestOccupationContext = null;

      function reviewSourceLabel(value) {
        return { user_submitted: "User submitted", reddit: "Reddit", indeed: "Indeed", other: "Other public source" }[value] || "Public source";
      }
      function reviewScopeLabel(value) {
        return { occupation: "Occupation context", employer_role: "Employer and role", job_posting: "Specific job posting" }[value] || "Scope not specified";
      }
      function reviewTopicLabel(value) {
        return { pay_benefits: "Pay and benefits", interview_management: "Interview and management", work_environment: "Work environment", workload: "Workload", growth: "Growth", tasks_tools: "Tasks and tools", other: "Other" }[value] || value;
      }
      function renderOccupationReviews(payload) {
        latestOccupationContext = payload;
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
      function percent(value) { return Math.round(Number(value || 0)) + "/100"; }
      function setRing(ringId, value, labelId) {
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
          meta.append(make("strong", "", item.requirement || "Requirement"), make("span", "", (item.decision || "uncertain") + " · " + Math.round(Number(item.confidence || 0) * 100) + "% confidence"));
          card.appendChild(meta);
          card.appendChild(make("p", "", item.rationale || "No rationale supplied."));
          if (item.next_step) card.appendChild(make("p", "", "Next step: " + item.next_step));
          semanticList.appendChild(card);
        });
      }
      async function deepReview() {
        if (!latest) { semanticStatus.textContent = "Run an analysis before requesting a review."; return; }
        semanticStatus.textContent = "Reviewing the supplied evidence…";
        deepReviewButton.disabled = true;
        try {
          const response = await fetch("/api/deep-review", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ job_text: jobInput.value, candidate_text: candidateInput.value, requirements: latest.requirements || [] }) });
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.detail || "review unavailable");
          renderSemanticReview(payload);
          semanticStatus.textContent = "Review complete. Treat uncertain items as leads for verification.";
        } catch (error) { semanticStatus.textContent = "Review unavailable. The rule-based result is still available."; }
        finally { deepReviewButton.disabled = !llmEnabled; }
      }
      function requirementTypeLabel(value) {
        return value === "skill" ? "Skill" : "Eligibility requirement";
      }
      function matchingMethodLabel(value) {
        const labels = {
          direct_skill_id: "Direct evidence",
          reviewable_transfer_crosswalk: "Transferable evidence",
          same_category_baseline: "Related skill category",
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
        [["Original job text", item.original_text], ["Requirement", requirementTypeLabel(item.requirement_type)], ["Importance", importanceLabels[item.importance_level] || item.importance_level], ["Match score", percent(item.match_score * 100)], ["Why this result", matchingMethodLabel(item.matching_method)], ["Linked evidence", evidenceLabels(item.evidence_ids)]].forEach(function (pair) {
          const row = make("div", "detail-line"); row.append(make("span", "detail-copy", pair[0]), make("strong", "", pair[1])); list.appendChild(row);
        });
        detail.appendChild(list);
        let copy = "No reliable evidence was found in the supplied profile. Investigate whether this is a real foundation gap or simply missing information.";
        if (item.status === "direct") copy = "The profile contains direct evidence. Improve the application by making the task, context, and result easier to verify.";
        if (item.status === "direct_weak") copy = "The skill is mentioned, but the proof is thin. Add a concrete task, context, duration, and measurable result.";
        if (item.status === "transferable") copy = "The profile contains adjacent evidence. Treat it as a bridge to investigate, not as proof that the requirements are identical.";
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
      function renderComparison(payload) {
        clearNode(comparisonGrid);
        (payload.roles || []).forEach(function (item) {
          const summary = item.summary || {};
          const card = make("article", "comparison-card");
          const rank = make("div", "comparison-rank");
          rank.append(make("span", "", "Priority " + item.priority_rank), make("span", "", readinessLabels[summary.readiness_status] || "Preparation route"));
          card.appendChild(rank);
          card.appendChild(make("h3", "", item.role_label || "Target role"));
          card.appendChild(make("p", "comparison-basis", item.priority_basis || "Preparation priority based on the supplied evidence."));
          const metrics = make("div", "comparison-metrics");
          [["Readiness", percent(summary.application_readiness_score)], ["Evidence fit", percent(summary.evidence_fit_score)], ["Confidence", percent(summary.assessment_confidence)], ["Eligibility", summary.blocking_constraint_count ? String(summary.blocking_constraint_count) + " to verify" : "Clear"]].forEach(function (pair) {
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
            render(item.analysis);
            status.textContent = "Loaded " + (item.role_label || "the selected role") + " into the detailed view.";
            jobInput.scrollIntoView({ behavior: "smooth", block: "center" });
          });
          card.appendChild(inspect);
          comparisonGrid.appendChild(card);
        });
        comparisonPanel.hidden = !(payload.roles || []).length;
      }
      function render(payload) {
        latest = payload;
        downloadButton.disabled = false;
        deepReviewButton.disabled = !llmEnabled;
        const summary = payload.summary || {};
        setText(fitScore, percent(summary.evidence_fit_score));
        setText(readinessScore, percent(summary.application_readiness_score));
        setText(confidenceScore, percent(summary.assessment_confidence));
        setText(blockedCount, summary.blocking_constraint_count);
        setText(decisionLabel, summary.decision_label);
        setRing("capability-ring", summary.capability_signal_score, "capability-signal");
        setRing("proof-ring", summary.proof_signal_score, "proof-signal");
        setRing("readiness-ring", summary.application_readiness_score, "readiness-signal");
        renderMatrix(payload.requirements || []);
        renderChart(payload.requirements || []);
        renderGaps(payload.next_actions || payload.gaps || []);
        renderFingerprint(payload.role_fingerprint);
        status.textContent = "Analysis ready · " + (summary.requirement_count || 0) + " requirements mapped";
      }
      async function analyze() {
        if (!jobInput.value.trim() || !candidateInput.value.trim()) { status.textContent = "Both texts are required."; return; }
        status.textContent = "Analyzing your inputs…";
        try {
          const response = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ job_text: jobInput.value, candidate_text: candidateInput.value }) });
          if (!response.ok) throw new Error("request failed");
          render(await response.json());
        } catch (error) { status.textContent = "Analysis unavailable. Please try again."; }
      }
      function downloadPlan() {
        if (!latest) { status.textContent = "Run an analysis before downloading the plan."; return; }
        const blob = new Blob([JSON.stringify(latest, null, 2)], { type: "application/json" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "career-fit-analysis.json";
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(function () { URL.revokeObjectURL(link.href); }, 0);
        status.textContent = "Downloaded the evidence-first analysis plan.";
      }
      async function compare() {
        const roles = rolesInput.value.split(/\r?\n\s*---+\s*\r?\n/).map(function (value) { return value.trim(); }).filter(Boolean);
        if (roles.length < 2) { compareStatus.textContent = "Add at least two roles, separated by a line containing --- ."; return; }
        if (roles.length > 3) { compareStatus.textContent = "Compare up to three roles at a time."; return; }
        if (!candidateInput.value.trim()) { compareStatus.textContent = "Add a candidate profile before comparing roles."; return; }
        compareStatus.textContent = "Comparing the supplied roles…";
        compareButton.disabled = true;
        try {
          const response = await fetch("/api/compare", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ roles: roles, candidate_text: candidateInput.value }) });
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.detail || "comparison unavailable");
          renderComparison(payload);
          compareStatus.textContent = "Comparison ready. Rankings describe preparation priority, not hiring odds.";
        } catch (error) { compareStatus.textContent = "Comparison unavailable. Check the role separators and try again."; }
        finally { compareButton.disabled = false; }
      }
      function reset() {
        latest = null;
        jobInput.value = ""; candidateInput.value = ""; rolesInput.value = ""; clearNode(matrix); clearNode(gapList); clearNode(fitChart); clearNode(comparisonGrid); clearNode(categoryProfile); clearNode(mismatchList); clearNode(bundleGrid);
        detail.innerHTML = ""; detail.append(make("span", "eyebrow", "Selected requirement"), make("h3", "detail-title", "Waiting for analysis"), make("p", "detail-copy", "Run the analysis, then select a requirement to inspect its evidence trail."));
        semanticPanel.hidden = true; comparisonPanel.hidden = true; fingerprintPanel.hidden = true; clearNode(semanticList); semanticSummary.textContent = "";
        clearNode(occupationCandidates); occupationContextResult.hidden = true; occupationStatus.textContent = "Select a standard occupation before viewing worker context.";
        latestOccupationContext = null;
        [fitScore, readinessScore, confidenceScore, blockedCount].forEach(function (node) { node.textContent = "—"; });
        downloadButton.disabled = true;
        deepReviewButton.disabled = true;
        ["capability-ring", "proof-ring", "readiness-ring"].forEach(function (id) { document.getElementById(id).style.setProperty("--ring-progress", "0%"); });
        ["capability-signal", "proof-signal", "readiness-signal"].forEach(function (id) { document.getElementById(id).textContent = "—"; });
        decisionLabel.textContent = "Run an analysis to see what the current text can support."; status.textContent = "Cleared."; compareStatus.textContent = "Use this when you are deciding where to focus first."; semanticStatus.textContent = llmEnabled ? "Optional review available." : "Optional review available when enabled.";
      }
      exampleButton.addEventListener("click", function () { jobInput.value = DEFAULT_JOB; candidateInput.value = DEFAULT_CANDIDATE; analyze(); });
      analyzeButton.addEventListener("click", analyze);
      compareButton.addEventListener("click", compare);
      occupationSearchButton.addEventListener("click", findOccupations);
      occupationQuery.addEventListener("keydown", function (event) { if (event.key === "Enter") findOccupations(); });
      downloadButton.addEventListener("click", downloadPlan);
      deepReviewButton.addEventListener("click", deepReview);
      clearButton.addEventListener("click", reset);
      deepReviewButton.disabled = !llmEnabled;
      if (llmEnabled) semanticStatus.textContent = "Optional review available.";
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
    return (
        HTML.replace("__DEFAULT_JOB__", _json_literal(DEFAULT_JOB))
        .replace("__DEFAULT_CANDIDATE__", _json_literal(DEFAULT_CANDIDATE))
        .replace("__LLM_ENABLED__", json.dumps(LLM_REVIEW_CLIENT.config.enabled))
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
        with build_opener(ProxyHandler({})).open(request, timeout=3) as response:
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
        if parsed.path == "/api/deep-review":
            try:
                length = min(int(self.headers.get("Content-Length", "0")), 120_000)
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                requirements = payload.get("requirements", [])
                if not isinstance(requirements, list):
                    raise TypeError("requirements must be a list")
                result = LLM_REVIEW_CLIENT.review_fit(
                    str(payload.get("job_text", ""))[:40_000],
                    str(payload.get("candidate_text", ""))[:40_000],
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
                result = compare_roles(
                    role_texts,
                    str(payload.get("candidate_text", ""))[:40_000],
                    payload.get("evidence"),
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
            result = analyze_fit(
                str(payload.get("job_text", "")),
                str(payload.get("candidate_text", "")),
                payload.get("evidence"),
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
        if parsed.path == "/api/analyze":
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
