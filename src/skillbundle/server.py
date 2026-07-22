from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

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
    .privacy-note { margin: 14px 0 0; color: var(--muted); font-size: .78rem; }
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
    @media (max-width: 900px) { .result-grid { display: block !important; } .result-grid > * { width: 100%; margin-bottom: 18px; } .gap-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
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
    @media (max-width: 700px) { .shell { width: min(100% - 36px, 1180px); } .hero { padding-top: 54px; } .input-grid, .meaning-grid, .gap-grid { grid-template-columns: 1fr; } .panel { padding: 21px; } .summary-grid { grid-template-columns: 1fr 1fr; gap: 22px; } .summary-card:nth-child(3) { padding-left: 0; border-left: 0; } .summary-card:nth-child(3), .summary-card:nth-child(4) { margin-top: 0; } .matrix-row, .matrix-head { grid-template-columns: minmax(125px, 1fr) 106px 78px; } .matrix-row > :nth-child(3), .matrix-head > :nth-child(3) { display: none; } .signal-card { grid-template-columns: 64px minmax(0, 1fr); } .ring { width: 58px; } .toolbar { align-items: flex-start; } }
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div class="brand"><span class="brand-mark" aria-hidden="true"></span><span class="brand-name">Career Fit</span></div>
      <span class="micro">Local-first · explainable preparation · v0.2.0</span>
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
          <span id="status" class="status" aria-live="polite">Local analyzer ready</span>
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
        <div class="summary-grid" aria-live="polite">
          <article class="summary-card"><span class="label">Evidence fit</span><strong id="fit-score" class="summary-value">—</strong><span class="summary-note">weighted requirement overlap</span></article>
          <article class="summary-card"><span class="label">Application readiness</span><strong id="readiness-score" class="summary-value">—</strong><span class="summary-note">preparation triage, not hiring odds</span></article>
          <article class="summary-card"><span class="label">Information confidence</span><strong id="confidence-score" class="summary-value">—</strong><span class="summary-note">clarity and evidence completeness</span></article>
          <article class="summary-card"><span class="label">Hard gates</span><strong id="blocked-count" class="summary-value">—</strong><span class="summary-note">requirements needing verification</span></article>
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
      <div class="section-head"><div><span class="eyebrow">Requirement–evidence matrix</span><h2>Inspect the reason behind every signal.</h2></div><p>Click a row to see the original job wording, the matching method, linked evidence, and the most useful next move.</p></div>
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
      <div class="section-head"><div><span class="eyebrow">Gap → action</span><h2>Leave with a useful next move.</h2></div><p>Actions are ordered by requirement importance and evidence shortfall. Each card names the proof artifact you can create or the gate you can verify.</p></div>
      <div id="gap-list" class="gap-grid" aria-live="polite"></div>
    </section>

    <section class="section">
      <div class="section-head"><div><span class="eyebrow">How to read the numbers</span><h2>Useful for preparation, limited for prediction.</h2></div></div>
      <div class="meaning-grid">
        <article class="meaning"><h3>Evidence fit is not hiring probability</h3><p>It is an importance-weighted summary of requirement overlap and supplied evidence. It does not estimate employer decisions.</p></article>
        <article class="meaning"><h3>A proof gap is not an ability gap</h3><p>A candidate may have the capability but lack a concrete task, result, work sample, or clear translation into employer language.</p></article>
        <article class="meaning"><h3>Transfer is deliberately cautious</h3><p>Adjacent evidence can suggest a bridge project, but the system never silently upgrades it to direct equivalence.</p></article>
        <article class="meaning"><h3>Hard gates stay separate</h3><p>Licenses, work authorization, degrees, and experience floors need verification. Soft skill overlap cannot offset an unresolved gate.</p></article>
      </div>
      <p class="source-note">Career Fit v0.2 uses a versioned English seed dictionary, explicit transfer rules, conservative negation handling, and transparent preparation heuristics. The local demo does not permanently store inputs.</p>
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
      const statusLabels = {
        direct: "Direct evidence",
        direct_weak: "Mentioned, proof is thin",
        transferable: "Transferable evidence",
        missing: "No evidence found",
        met: "Requirement appears met",
        not_met: "Explicitly not met",
        unknown: "Needs verification"
      };
      const importanceLabels = {
        must: "Must have",
        strongly_preferred: "Strongly preferred",
        preferred: "Preferred",
        inferred: "Inferred"
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
      function setRing(ringId, value, labelId) {
        const number = Math.max(0, Math.min(100, Number(value || 0)));
        document.getElementById(ringId).style.setProperty("--ring-progress", number + "%");
        setText(document.getElementById(labelId), Math.round(number));
      }
      function renderDetail(item) {
        clearNode(detail);
        detail.appendChild(make("span", "eyebrow", "Selected requirement"));
        detail.appendChild(make("h3", "detail-title", item.canonical_skill || item.original_text));
        detail.appendChild(make("span", "badge " + (item.status || "unknown"), statusLabels[item.status] || item.status));
        const list = make("div", "detail-list");
        [["Original job text", item.original_text], ["Requirement type", item.requirement_type], ["Importance", importanceLabels[item.importance_level] || item.importance_level], ["Match score", percent(item.match_score * 100)], ["Matching method", item.matching_method || "constraint rule"], ["Linked evidence", (item.evidence_ids || []).length ? item.evidence_ids.join(", ") : "No linked evidence"]].forEach(function (pair) {
          const row = make("div", "detail-line"); row.append(make("span", "detail-copy", pair[0]), make("strong", "", pair[1])); list.appendChild(row);
        });
        detail.appendChild(list);
        let copy = "No reliable evidence was found in the supplied profile. Investigate whether this is a real foundation gap or simply missing information.";
        if (item.status === "direct") copy = "The profile contains direct evidence. Improve the application by making the task, context, and result easier to verify.";
        if (item.status === "direct_weak") copy = "The skill is mentioned, but the proof is thin. Add a concrete task, context, duration, and measurable result.";
        if (item.status === "transferable") copy = "The profile contains adjacent evidence. Treat it as a bridge to investigate, not as proof that the requirements are identical.";
        if (item.hard_constraint) copy = item.status === "met" ? "This gate appears satisfied from the supplied profile." : "This is an admission gate. Verify it directly before using the soft score to prioritize the application.";
        detail.appendChild(make("p", "detail-copy", copy));
        if (item.source_context) detail.appendChild(make("p", "detail-copy", "Job context: " + item.source_context));
      }
      function renderMatrix(items) {
        clearNode(matrix);
        if (!items.length) { matrix.appendChild(make("p", "detail-copy", "No results yet. Run the analysis first.")); return; }
        items.forEach(function (item, index) {
          const row = make("button", "matrix-row" + (index === 0 ? " selected" : ""));
          row.type = "button";
          const name = make("span", ""); name.append(make("span", "requirement-name", item.canonical_skill || item.original_text), make("span", "requirement-type", item.requirement_type === "skill" ? "Skill" : "Admission gate"));
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
      function render(payload) {
        latest = payload;
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
        status.textContent = "Updated · " + (summary.requirement_count || 0) + " requirements analyzed";
      }
      async function analyze() {
        if (!jobInput.value.trim() || !candidateInput.value.trim()) { status.textContent = "Both texts are required."; return; }
        status.textContent = "Analyzing locally…";
        try {
          const response = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ job_text: jobInput.value, candidate_text: candidateInput.value }) });
          if (!response.ok) throw new Error("request failed");
          render(await response.json());
        } catch (error) { status.textContent = "Local analyzer unavailable."; }
      }
      function reset() {
        jobInput.value = ""; candidateInput.value = ""; clearNode(matrix); clearNode(gapList); clearNode(fitChart);
        detail.innerHTML = ""; detail.append(make("span", "eyebrow", "Selected requirement"), make("h3", "detail-title", "Waiting for analysis"), make("p", "detail-copy", "Run the analysis, then select a requirement to inspect its evidence trail."));
        [fitScore, readinessScore, confidenceScore, blockedCount].forEach(function (node) { node.textContent = "—"; });
        ["capability-ring", "proof-ring", "readiness-ring"].forEach(function (id) { document.getElementById(id).style.setProperty("--ring-progress", "0%"); });
        ["capability-signal", "proof-signal", "readiness-signal"].forEach(function (id) { document.getElementById(id).textContent = "—"; });
        decisionLabel.textContent = "Run an analysis to see what the current text can support."; status.textContent = "Cleared.";
      }
      exampleButton.addEventListener("click", function () { jobInput.value = DEFAULT_JOB; candidateInput.value = DEFAULT_CANDIDATE; analyze(); });
      analyzeButton.addEventListener("click", analyze);
      clearButton.addEventListener("click", reset);
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
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": "invalid_request", "detail": str(exc)}, status=400)
            return
        self._send_json(result)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self._send_page()
            return
        if parsed.path == "/api/analyze":
            self._send_json({"error": "use_post"}, status=405)
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
