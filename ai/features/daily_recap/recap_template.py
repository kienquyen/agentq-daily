from jinja2 import Template
import datetime

RECAP_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>AgentQ · Bản tin buổi sáng</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

:root{
  /* Base */
  --bg:        #F4F5F8;
  --surface:   #FFFFFF;
  --surface-2: #F9FAFB;
  --border:    #E8EAF0;
  --border-2:  #D4D8E4;

  /* Ink */
  --t1: #0E1117;
  --t2: #3B4259;
  --t3: #7B849C;
  --t4: #B4BAC8;

  /* Brand — electric violet */
  --v:    #6C3EF4;
  --v-lt: #EDE8FE;
  --v-md: #8B5CF6;
  --v-glow: rgba(108,62,244,.12);

  /* Semantic */
  --g:    #059669;
  --g-lt: #D1FAE5;
  --g-md: #10B981;
  --r:    #DC2626;
  --r-lt: #FEE2E2;
  --r-md: #EF4444;
  --a:    #D97706;
  --a-lt: #FEF3C7;
  --a-md: #F59E0B;

  --font: 'Outfit', sans-serif;
  --mono: 'JetBrains Mono', monospace;
  --rad:  14px;
  --rad-sm: 8px;
}

html{background:var(--bg);color:var(--t1);font-family:var(--font);-webkit-font-smoothing:antialiased;font-size:14px}
body{display:flex;justify-content:center;padding:0;background:var(--bg)}
.page{width:100%;max-width:460px;padding-bottom:40px}

/* ── KEYFRAMES ── */
@keyframes in-up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes shimmer{0%{background-position:200% center}100%{background-position:-200% center}}

.s{animation:in-up .4s cubic-bezier(.22,.68,0,1.2) both}
.s:nth-child(1){animation-delay:.00s}.s:nth-child(2){animation-delay:.06s}
.s:nth-child(3){animation-delay:.11s}.s:nth-child(4){animation-delay:.16s}
.s:nth-child(5){animation-delay:.21s}.s:nth-child(6){animation-delay:.26s}
.s:nth-child(7){animation-delay:.31s}

/* ── MASTHEAD ── */
.mast{
  background:var(--t1);
  padding:18px 20px 16px;
  position:relative;
  overflow:hidden;
}
.mast::after{
  content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse 60% 80% at 90% 50%, rgba(108,62,244,.25) 0%, transparent 70%);
  pointer-events:none;
}
.mast-inner{display:flex;justify-content:space-between;align-items:center;position:relative;z-index:1}
.brand-row{display:flex;align-items:center;gap:10px}
.brand-mark{
  width:28px;height:28px;border-radius:8px;
  background:linear-gradient(135deg,#6C3EF4,#A78BFA);
  display:flex;align-items:center;justify-content:center;
  font-size:12px;font-weight:800;color:#fff;letter-spacing:-.5px;
  font-family:var(--font);flex-shrink:0;
}
.brand-text{}
.brand-name{font-size:13px;font-weight:700;color:#fff;letter-spacing:.02em}
.brand-tag{font-family:var(--mono);font-size:9px;color:rgba(255,255,255,.45);letter-spacing:.14em;text-transform:uppercase;margin-top:1px}
.live-chip{
  display:flex;align-items:center;gap:5px;
  background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);
  border-radius:20px;padding:3px 9px;margin-top:5px;
}
.live-dot{width:5px;height:5px;border-radius:50%;background:#4ADE80;animation:pulse 1.6s infinite}
.live-lbl{font-family:var(--mono);font-size:8px;color:#4ADE80;letter-spacing:.12em;text-transform:uppercase;font-weight:600}
.mast-right{text-align:right}
.mast-date{font-family:var(--mono);font-size:9px;color:rgba(255,255,255,.4);letter-spacing:.08em}
.mast-time{font-family:var(--mono);font-size:20px;font-weight:600;color:#fff;letter-spacing:-.02em;line-height:1;margin-top:4px}
.mast-tz{font-family:var(--mono);font-size:8px;color:rgba(255,255,255,.35);letter-spacing:.1em;margin-top:2px}

/* ── CARD ── */
.card{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--rad);
  padding:16px;
  margin:8px;
  position:relative;
  overflow:hidden;
}
.card.violet-accent{border-color:rgba(108,62,244,.2);box-shadow:0 0 0 1px rgba(108,62,244,.06) inset, 0 4px 20px rgba(108,62,244,.07)}
.card.green-accent{border-color:rgba(5,150,105,.2);box-shadow:0 4px 20px rgba(5,150,105,.06)}
.card.warning-accent{border-color:rgba(217,119,6,.25);box-shadow:0 0 0 1px rgba(217,119,6,.05) inset,0 4px 20px rgba(217,119,6,.07)}

/* top accent line */
.card.violet-accent::before,.card.warning-accent::before{content:'';position:absolute;top:0;left:16px;right:16px;height:2px;background:linear-gradient(90deg,#6C3EF4,#A78BFA,transparent);border-radius:0 0 2px 2px}
.card.warning-accent::before{background:linear-gradient(90deg,#D97706,#F59E0B,transparent)}

/* ── SECTION LABEL ── */
.sec-lbl{
  display:flex;align-items:center;gap:7px;
  font-family:var(--mono);font-size:8.5px;font-weight:600;
  letter-spacing:.2em;text-transform:uppercase;color:var(--t4);
  margin-bottom:12px;
}
.sec-lbl::after{content:'';flex:1;height:1px;background:var(--border)}
.sec-lbl .badge{
  background:var(--g-lt);color:var(--g);font-size:8px;padding:2px 8px;border-radius:4px;
  letter-spacing:.08em;text-transform:uppercase;font-weight:600;border:1px solid rgba(5,150,105,.15);
  margin-right:auto;
}

/* ── REGIME BLOCK ── */
.regime-wrap{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px}
.regime-chip{
  display:inline-flex;align-items:center;gap:5px;
  font-family:var(--mono);font-size:8px;font-weight:600;
  letter-spacing:.14em;text-transform:uppercase;
  background:var(--v-lt);color:var(--v);
  border:1px solid rgba(108,62,244,.2);
  border-radius:4px;padding:2px 8px;margin-bottom:8px;
}
.regime-chip.warning{background:var(--a-lt);color:var(--a);border-color:rgba(217,119,6,.25)}
.regime-name{
  font-size:28px;font-weight:800;color:var(--t1);
  letter-spacing:-.03em;line-height:1;
}
.regime-name.score-bear{
  background:linear-gradient(135deg,#DC2626,#F87171);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.regime-name.score-ranging,.regime-name.ranging{
  background:linear-gradient(135deg,#D97706,#F59E0B);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.regime-name.score-recovery{
  background:linear-gradient(135deg,#059669,#34D399);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.regime-name.score-bull,.regime-name.bull{
  background:linear-gradient(135deg,#6C3EF4,#A78BFA);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.score-chip-bear{background:#FEE2E2;color:#DC2626;border-color:rgba(220,38,38,.2)}
.score-chip-ranging{background:#FEF3C7;color:#D97706;border-color:rgba(217,119,6,.25)}
.score-chip-recovery{background:#D1FAE5;color:#059669;border-color:rgba(5,150,105,.2)}
.score-chip-bull{background:#EDE8FE;color:#6C3EF4;border-color:rgba(108,62,244,.2)}
.regime-hint{font-size:11px;color:var(--t3);margin-top:5px;font-weight:400}

/* Overall score display */
.overall-block{text-align:right;flex-shrink:0}
.overall-num{
  font-family:var(--mono);font-size:36px;font-weight:700;
  line-height:1;letter-spacing:-.04em;
}
.overall-num.score-bear{
  background:linear-gradient(135deg,#DC2626,#F87171);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.overall-num.score-ranging{
  background:linear-gradient(135deg,#D97706,#F59E0B);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.overall-num.score-recovery{
  background:linear-gradient(135deg,#059669,#34D399);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.overall-num.score-bull{
  background:linear-gradient(135deg,#6C3EF4,#A78BFA);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.overall-lbl{font-family:var(--mono);font-size:7.5px;color:var(--t4);text-transform:uppercase;letter-spacing:.14em;margin-top:4px}
.overall-bar-wrap{display:flex;align-items:center;gap:5px;margin-top:7px;justify-content:flex-end}
.overall-bar-track{width:56px;height:4px;background:var(--border);border-radius:3px;overflow:hidden}
.overall-bar-fill{height:100%;border-radius:3px}
.overall-bar-fill.score-bar-bear{background:linear-gradient(90deg,#DC2626,#F87171)}
.overall-bar-fill.score-bar-ranging{background:linear-gradient(90deg,#D97706,#F59E0B)}
.overall-bar-fill.score-bar-recovery{background:linear-gradient(90deg,#059669,#34D399)}
.overall-bar-fill.score-bar-bull{background:linear-gradient(90deg,#6C3EF4,#A78BFA)}

/* Score row */
.score-row{display:grid;grid-template-columns:repeat(5,1fr);gap:5px;margin-bottom:12px}
.sc-cell{
  background:var(--surface-2);border:1px solid var(--border);
  border-radius:var(--rad-sm);padding:7px 4px 6px;text-align:center;
}
.sc-val{font-family:var(--mono);font-size:12.5px;font-weight:600;color:var(--t1)}
.sc-lbl{font-size:7.5px;color:var(--t4);margin-top:3px;text-transform:uppercase;letter-spacing:.05em;font-family:var(--mono)}

/* Score legend */
.legend{
  display:grid;grid-template-columns:repeat(4,1fr);gap:5px;
}
.leg-item{display:flex;flex-direction:column;align-items:center;gap:3px}
.leg-swatch{
  display:flex;align-items:center;gap:4px;
  padding:4px 6px;border-radius:5px;border:1px solid transparent;width:100%;justify-content:center;
}
.leg-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.leg-range{font-family:var(--mono);font-size:8px;font-weight:600;letter-spacing:0;white-space:nowrap}
.leg-label{font-size:8px;color:var(--t4);font-weight:400;text-align:center;line-height:1.3}

/* Market hero — compact */
.mkt-hero{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:8px}
.mkt-hero-left{flex:1}
.mkt-big{font-family:var(--mono);font-size:20px;font-weight:700;color:var(--t1);letter-spacing:-.02em;line-height:1.15;display:flex;align-items:baseline;gap:8px}
.mkt-delta{font-family:var(--mono);font-size:13px;font-weight:600}
.mkt-note{font-size:9.5px;color:var(--t3);margin-top:3px}
.mkt-pills{display:flex;flex-direction:column;gap:4px;align-items:flex-end;flex-shrink:0}
.mkt-pill{
  display:flex;align-items:center;gap:6px;
  padding:3px 8px;border-radius:5px;
  background:var(--surface-2);border:1px solid var(--border);
  white-space:nowrap;
}
.mkt-pill-lbl{font-family:var(--mono);font-size:8px;color:var(--t4);letter-spacing:.04em}
.mkt-pill-val{font-family:var(--mono);font-size:10px;font-weight:600}

/* Market grid — reference style */
.mkt-row{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:6px}
.mkt-row-2{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:0}
.mkt-box{
  background:var(--surface-2);border:1px solid var(--border);
  border-radius:9px;padding:8px 10px;
}
.mkt-box-lbl{
  font-family:var(--mono);font-size:7.5px;font-weight:500;
  letter-spacing:.12em;text-transform:uppercase;color:var(--t4);
  margin-bottom:5px;
}
.mkt-box-val{
  font-family:var(--mono);font-size:15px;font-weight:700;
  color:var(--t1);letter-spacing:-.01em;line-height:1;
}
.mkt-box-sub{font-size:9.5px;color:var(--t3);margin-top:3px;font-weight:400}
.mkt-box-sub.dn{color:var(--r)}
.mkt-box-sub.up{color:var(--g)}
.up{color:var(--g)}.up b{color:var(--g)}
.dn{color:var(--r)}.dn b{color:var(--r)}
.mkt-box.main{grid-column:span 2;display:flex;align-items:center;gap:16px}
.mkt-box.ma50{display:flex;flex-direction:column;justify-content:center}

/* FX compact inline */
.fx-inline{
  display:flex;align-items:center;gap:7px;
  padding:6px 9px;
  background:var(--surface-2);border:1px solid var(--border);border-radius:6px;
  margin-bottom:8px;
}
.fx-inline-icon{font-size:12px;line-height:1}
.fx-inline-lbl{font-family:var(--mono);font-size:8.5px;color:var(--t4);letter-spacing:.08em;text-transform:uppercase}
.fx-inline-val{font-family:var(--mono);font-size:13px;font-weight:700;color:var(--t1);letter-spacing:-.01em;margin-left:auto}
.fx-inline-delta{font-family:var(--mono);font-size:9.5px;font-weight:500;color:var(--t3)}
.fx-inline-src{font-size:9px;color:var(--t4)}

/* Action strip */
.action-strip{
  display:flex;align-items:flex-start;gap:8px;
  padding:9px 10px;
  background:var(--v-lt);border:1px solid rgba(108,62,244,.15);
  border-radius:7px;
}
.action-strip.warning{background:var(--a-lt);border-color:rgba(217,119,6,.15)}
.as-arrow{font-family:var(--mono);font-size:13px;font-weight:700;color:var(--v);flex-shrink:0;line-height:1.4}
.action-strip.warning .as-arrow{color:var(--a)}
.as-text{font-size:11px;color:var(--v);font-weight:500;line-height:1.5}
.action-strip.warning .as-text{color:var(--a)}

/* ── FLOW ── */
.flow-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.flow-side-hdr{
  display:flex;align-items:center;gap:6px;
  padding:6px 0;border-bottom:2px solid var(--border);margin-bottom:2px;
}
.fh-indicator{width:24px;height:3px;border-radius:2px;flex-shrink:0}
.fh-indicator.in{background:linear-gradient(90deg,var(--g),var(--g-md))}
.fh-indicator.out{background:linear-gradient(90deg,var(--r),var(--r-md))}
.fh-lbl{font-family:var(--mono);font-size:8px;font-weight:600;letter-spacing:.14em;text-transform:uppercase}
.fh-lbl.in{color:var(--g)}.fh-lbl.out{color:var(--r)}

.fi{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--border)}
.fi:last-child{border-bottom:none}
.fi-sector{font-size:10.5px;color:var(--t1);font-weight:500}
.fi-tickers{font-family:var(--mono);font-size:8px;color:var(--t4);margin-top:1px}
.fi-val{font-family:var(--mono);font-size:10.5px;font-weight:600;white-space:nowrap}
.fi-val.up{color:var(--g)}.fi-val.dn{color:var(--r)}

/* ── WATCHLIST ── */
.wl-row{display:grid;grid-template-columns:52px 1fr auto;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid var(--border)}
.wl-row:last-child{border-bottom:none}
.wl-sym{font-family:var(--mono);font-size:15px;font-weight:700;color:var(--t1);letter-spacing:.02em}
.wl-sig{font-size:10.5px;color:var(--t3);line-height:1.4;font-weight:400}
.score-widget{display:flex;align-items:center;gap:8px;justify-content:flex-end}
.score-dash{width:28px;height:3px;border-radius:2px;flex-shrink:0}
.bar-track{flex:1;height:3px;background:var(--border);border-radius:2px;overflow:hidden;max-width:32px}
.bar-fill{height:100%;border-radius:2px}
.score-num{font-family:var(--mono);font-size:15px;font-weight:700;min-width:26px;text-align:right;letter-spacing:-.01em}

/* Weekly filter chip */
.weekly-filter{
  display:inline-flex;align-items:center;gap:6px;
  font-family:var(--mono);font-size:9px;font-weight:500;color:var(--t3);
  background:var(--surface-2);border:1px solid var(--border);
  border-radius:6px;padding:5px 10px;margin-bottom:10px;letter-spacing:.03em;
}
.wf-icon{color:var(--v);font-size:12px;font-weight:700;line-height:1}

/* ── PORTFOLIO ── */
.port-row{display:grid;grid-template-columns:46px 1fr auto;gap:8px;align-items:center;padding:7px 0;border-bottom:1px solid var(--border)}
.port-row:last-child{border-bottom:none}
.port-sym{font-family:var(--mono);font-size:13.5px;font-weight:700;color:var(--t1)}
.port-meta{font-size:10px;color:var(--t3);line-height:1.5}
.port-meta b{font-weight:600}
.tag{
  font-family:var(--mono);font-size:8.5px;font-weight:600;
  letter-spacing:.06em;text-transform:uppercase;
  padding:4px 10px;border-radius:6px;white-space:nowrap;
}
.tag-hold{background:var(--surface-2);color:var(--t3);border:1px solid var(--border)}
.tag-cut{background:var(--r-lt);color:var(--r);border:1px solid rgba(220,38,38,.15)}
.tag-add{background:var(--g-lt);color:var(--g);border:1px solid rgba(5,150,105,.15)}
.tag-tp{background:var(--v-lt);color:var(--v);border:1px solid rgba(108,62,244,.15)}

/* ── NEWS ── */
.news-row{display:flex;gap:11px;align-items:flex-start;padding:8px 0;border-bottom:1px solid var(--border)}
.news-row:last-child{border-bottom:none}
.news-n{
  font-family:var(--mono);font-size:9px;font-weight:600;color:var(--t4);
  min-width:18px;flex-shrink:0;padding-top:2px;letter-spacing:.02em;
}
.news-body{}
.news-hl{font-size:12px;color:var(--t1);line-height:1.5;font-weight:400}
.news-foot{display:flex;align-items:center;gap:7px;margin-top:5px}
.news-src{
  font-family:var(--mono);font-size:8px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
  padding:2px 7px;border-radius:4px;
  background:var(--surface-2);color:var(--t3);border:1px solid var(--border);
}
.news-cat{font-size:9.5px;font-weight:500}
.news-cat.macro{color:var(--v)}.news-cat.sector{color:var(--g)}.news-cat.risk{color:var(--r)}

/* ── FOOTER ── */
.foot{
  display:flex;justify-content:space-between;align-items:center;
  margin:4px 8px 0;padding:12px 16px;
  background:var(--surface);border:1px solid var(--border);
  border-radius:var(--rad);
}
.foot-l{font-family:var(--mono);font-size:9px;color:var(--t4);letter-spacing:.08em}
.foot-l strong{color:var(--v);font-weight:600}
.foot-r{font-family:var(--mono);font-size:8px;color:var(--t4);letter-spacing:.04em;text-align:right}
</style>
</head>
<body>
<div class="page">

  <!-- ══ MASTHEAD ══ -->
  <div class="mast s">
    <div class="mast-inner">
      <div>
        <div class="brand-row">
          <div class="brand-mark">AQ</div>
          <div class="brand-text">
            <div class="brand-name">AgentQ</div>
            <div class="brand-tag">Bản tin buổi sáng</div>
          </div>
        </div>
        <div class="live-chip">
          <div class="live-dot"></div>
          <div class="live-lbl">Live</div>
        </div>
      </div>
      <div class="mast-right">
        <div class="mast-date">{{ mast_date }}</div>
        <div class="mast-time">{{ mast_time }}</div>
        <div class="mast-tz">ICT · UTC+7</div>
      </div>
    </div>
  </div>

  <!-- ══ 1. XU HƯỚNG THỊ TRƯỜNG ══ -->
  <div class="card s {% if ai_data.regime == 'ranging' %}warning-accent{% else %}violet-accent{% endif %}">
    <div class="sec-lbl">Xu hướng thị trường</div>
    <div class="regime-wrap">
      <div>
        <div class="regime-chip score-chip-{% if ai_data.regime_score < 0.35 %}bear{% elif ai_data.regime_score < 0.50 %}ranging{% elif ai_data.regime_score < 0.70 %}recovery{% else %}bull{% endif %}">Xu hướng hiện tại</div>
        <div class="regime-name score-text-{% if ai_data.regime_score < 0.35 %}bear{% elif ai_data.regime_score < 0.50 %}ranging{% elif ai_data.regime_score < 0.70 %}recovery{% else %}bull{% endif %}">{{ ai_data.regime_vn }}</div>
        <div class="regime-hint">{{ ai_data.regime_recommendation }}</div>
      </div>
      <div class="overall-block">
        <div class="overall-num score-{% if ai_data.regime_score < 0.35 %}bear{% elif ai_data.regime_score < 0.50 %}ranging{% elif ai_data.regime_score < 0.70 %}recovery{% else %}bull{% endif %}">{{ ai_data.regime_score | round(2) }}</div>
        <div class="overall-lbl">Overall Score</div>
        <div class="overall-bar-wrap">
          <div class="overall-bar-track"><div class="overall-bar-fill score-bar-{% if ai_data.regime_score < 0.35 %}bear{% elif ai_data.regime_score < 0.50 %}ranging{% elif ai_data.regime_score < 0.70 %}recovery{% else %}bull{% endif %}" style="width:{{ (ai_data.regime_score * 100) | int }}%"></div></div>
        </div>
      </div>
    </div>
    <div class="legend">
      <div class="leg-item">
        <div class="leg-swatch" style="background:#FEE2E2;border-color:rgba(220,38,38,.2)">
          <div class="leg-dot" style="background:#DC2626"></div>
          <div class="leg-range" style="color:#DC2626">0–0.35</div>
        </div>
        <div class="leg-label">Bear / Rủi ro</div>
      </div>
      <div class="leg-item">
        <div class="leg-swatch" style="background:#FEF3C7;border-color:rgba(217,119,6,.3)">
          <div class="leg-dot" style="background:#D97706"></div>
          <div class="leg-range" style="color:#B45309">0.35–0.50</div>
        </div>
        <div class="leg-label">Tích lũy / Sideway</div>
      </div>
      <div class="leg-item">
        <div class="leg-swatch" style="background:#D1FAE5;border-color:rgba(5,150,105,.2)">
          <div class="leg-dot" style="background:#059669"></div>
          <div class="leg-range" style="color:#059669">0.50–0.70</div>
        </div>
        <div class="leg-label">Hồi phục / Tăng</div>
      </div>
      <div class="leg-item">
        <div class="leg-swatch" style="background:#EDE8FE;border-color:rgba(108,62,244,.2)">
          <div class="leg-dot" style="background:#6C3EF4"></div>
          <div class="leg-range" style="color:#6C3EF4">0.70–1.0</div>
        </div>
        <div class="leg-label">Bull Trending</div>
      </div>
    </div>
  </div>

  <!-- ══ 2. TỔNG QUAN THỊ TRƯỜNG ══ -->
  <div class="card s">
    <div class="sec-lbl">Tổng quan thị trường
      <span style="font-size:8px;color:var(--t4);letter-spacing:.06em;text-transform:none;font-weight:400;margin-left:auto;margin-right:0">{{ snapshot.date }}</span>
    </div>

    <!-- Hàng 1: VN-Index (2 cols) · Lệch MA50 (1 col) -->
    <div class="mkt-row" style="margin-bottom:6px">
      <div class="mkt-box main">
        <div>
          <div class="mkt-box-lbl">VN-Index</div>
          <div class="mkt-box-val" style="font-size:20px">{{ snapshot.vni_price }}</div>
        </div>
        <div>
          <div class="mkt-box-sub {% if snapshot.vni_chg >= 0 %}up{% else %}dn{% endif %}" style="font-size:13px;font-weight:700">{% if snapshot.vni_chg >= 0 %}+{% endif %}{{ snapshot.vni_chg_pct }}%</div>
          <div class="mkt-box-sub" style="color:var(--t4);margin-top:3px">{% if snapshot.vs_ma50_pct_val >= 0 %}Trên MA50{% else %}Dưới MA50{% endif %}</div>
        </div>
      </div>
      <div class="mkt-box ma50">
        <div class="mkt-box-lbl">Lệch MA50</div>
        <div class="mkt-box-val {% if snapshot.vs_ma50_pct_val >= 0 %}up{% else %}dn{% endif %}">{% if snapshot.vs_ma50_pct_val >= 0 %}+{% endif %}{{ snapshot.vs_ma50_pct }}%</div>
        <div class="mkt-box-sub" style="color:var(--t3)">Vùng yếu KT</div>
      </div>
    </div>

    <!-- Hàng 2: Độ rộng · Khối ngoại · Phân phối -->
    <div class="mkt-row-2" style="margin-bottom:6px">
      <div class="mkt-box">
        <div class="mkt-box-lbl">Độ rộng VN100</div>
        <div class="mkt-box-val {% if snapshot.ad_de_ratio_val >= 1 %}up{% else %}dn{% endif %}">{{ snapshot.advances }}/{{ snapshot.declines }}</div>
        <div class="mkt-box-sub" style="color:var(--t4)">Tăng / Giảm</div>
      </div>
      <div class="mkt-box">
        <div class="mkt-box-lbl">Khối ngoại</div>
        <div class="mkt-box-val {% if snapshot.foreign_flow_bil >= 0 %}up{% else %}dn{% endif %}">{% if snapshot.foreign_flow_bil >= 0 %}+{% endif %}{{ snapshot.foreign_flow_bil }}B</div>
        <div class="mkt-box-sub" style="color:var(--t4)">{% if snapshot.foreign_flow_bil >= 0 %}Mua ròng{% else %}Bán ròng{% endif %}</div>
      </div>
      <div class="mkt-box" style="{% if snapshot.dist_days >= 5 %}border-color:rgba(217,119,6,.25);background:#FFFBEB{% endif %}">
        <div class="mkt-box-lbl" {% if snapshot.dist_days >= 5 %}style="color:var(--a)"{% endif %}>Phân phối</div>
        <div class="mkt-box-val" {% if snapshot.dist_days >= 5 %}style="color:var(--a)"{% endif %}>{{ snapshot.dist_days }} phiên</div>
        <div class="mkt-box-sub" {% if snapshot.dist_days >= 5 %}style="color:var(--a);font-weight:500"{% endif %}>
          {% if snapshot.dist_days >= 8 %}🟢 Sạch{% elif snapshot.dist_days >= 6 %}🔴 Nguy hiểm{% elif snapshot.dist_days >= 5 %}⚠ Rủi ro tăng{% elif snapshot.dist_days >= 3 %}🟡 Thận trọng{% else %}🟢 Sạch{% endif %}
        </div>
      </div>
    </div>

    <!-- FX — dòng riêng -->
    <div class="fx-inline">
      <span class="fx-inline-icon">🇺🇸</span>
      <span class="fx-inline-lbl">USD/VND</span>
      <span class="fx-inline-val">{{ snapshot.usd_vnd }}</span>
      <span class="fx-inline-src">Tỉ giá LNH</span>
    </div>

    <!-- Action -->
    {% if ai_data.interpretation %}
    <div class="action-strip {% if ai_data.regime == 'ranging' %}warning{% endif %}">
      <div class="as-arrow">→</div>
      <div class="as-text">{{ ai_data.interpretation }}</div>
    </div>
    {% endif %}
  </div>

  <!-- ══ 3. LUÂN CHUYỂN DÒNG TIỀN ══ -->
  <div class="card s">
    <div class="sec-lbl">Luân chuyển dòng tiền</div>
    <div class="flow-grid">
      <div>
        <div class="flow-side-hdr">
          <div class="fh-indicator in"></div>
          <div class="fh-lbl in">Dòng vào</div>
        </div>
        {% if flow.inflow %}
          {% for item in flow.inflow[:5] %}
          <div class="fi"><div><div class="fi-sector">{{ item.sector }}</div><div class="fi-tickers">{{ item.tickers | join(' · ') }}</div></div><div class="fi-val up">+{{ item.value }}B</div></div>
          {% endfor %}
        {% else %}
          <div class="fi"><div class="fi-sector" style="color:var(--t4)">Không có dữ liệu</div></div>
        {% endif %}
      </div>
      <div>
        <div class="flow-side-hdr">
          <div class="fh-indicator out"></div>
          <div class="fh-lbl out">Dòng ra</div>
        </div>
        {% if flow.outflow %}
          {% for item in flow.outflow[:5] %}
          <div class="fi"><div><div class="fi-sector">{{ item.sector }}</div><div class="fi-tickers">{{ item.tickers | join(' · ') }}</div></div><div class="fi-val dn">{{ item.value }}B</div></div>
          {% endfor %}
        {% else %}
          <div class="fi"><div class="fi-sector" style="color:var(--t4)">Không có dữ liệu</div></div>
        {% endif %}
      </div>
    </div>
  </div>

  <!-- ══ 4. DANH SÁCH THEO DÕI NGÀY ══ -->
  <div class="card green-accent s">
    <div class="sec-lbl">Danh sách theo dõi
      <span style="background:var(--g-lt);color:var(--g);font-size:8px;padding:2px 8px;border-radius:4px;letter-spacing:.08em;text-transform:uppercase;font-weight:600;border:1px solid rgba(5,150,105,.15);margin-right:auto">{{ watchlist | length }} mã</span>
    </div>
    {% if watchlist %}
      {% for ticker, sig in watchlist.items() %}
      <div class="wl-row">
        <div class="wl-sym">{{ ticker }}</div>
        <div class="wl-sig">{{ sig.label }}</div>
        <div class="score-widget">
          {% set rsi = (sig.rsi14 if sig.rsi14 is not none else 50) | int %}
          {% set score = (sig.score if sig.score is not none else 70) | int %}
          {% set bar_color = '#059669' if rsi >= 70 else ('#10B981' if rsi >= 60 else ('#D97706' if rsi >= 50 else '#DC2626')) %}
          <div class="score-dash" style="background:{{ bar_color }}"></div>
          <div class="score-num" style="color:{{ bar_color }}">{{ score }}</div>
        </div>
      </div>
      {% endfor %}
    {% else %}
      <div class="wl-row" style="justify-content:center;color:var(--t4);font-size:11px;padding:12px 0">
        Không có dữ liệu kỹ thuật
      </div>
    {% endif %}
  </div>

  <!-- ══ 5. DANH MỤC THEO DÕI TUẦN ══ -->
  <div class="card s">
    <div class="sec-lbl">Danh mục theo dõi tuần</div>
    <div class="weekly-filter">
      <span class="wf-icon">↑</span> Top 5 inflow tuần · EMA9 &gt; EMA26
    </div>
    {% if weekly_watchlist %}
      {% for item in weekly_watchlist %}
      <div class="wl-row">
        <div class="wl-sym">{{ item.ticker }}</div>
        <div class="wl-sig">{{ item.sector }}</div>
        <div class="score-widget">
          {% set score = (item.score if item.score is not none else 50) | int %}
          {% set bar_color = '#059669' if score >= 70 else ('#10B981' if score >= 60 else ('#D97706' if score >= 50 else '#DC2626')) %}
          <div class="score-dash" style="background:{{ bar_color }}"></div>
          <div class="score-num" style="color:{{ bar_color }}">{{ score }}</div>
        </div>
      </div>
      {% endfor %}
    {% else %}
      <div class="wl-row" style="justify-content:center;color:var(--t4);font-size:11px;padding:12px 0">
        Chưa có dữ liệu dòng tiền tuần này
      </div>
    {% endif %}
  </div>

  <!-- ══ 6. HÀNH ĐỘNG DANH MỤC ══ -->
  {% if portfolio_actions %}
  <div class="card s">
    <div class="sec-lbl">Hành động danh mục</div>
    {% for p in portfolio_actions %}
    <div class="port-row">
      <div class="port-sym">{{ p.symbol }}</div>
      <div class="port-meta">
        {% if p.pnl_pct is defined %}Lãi/lỗ <b {% if p.pnl_pct < 0 %}class="dn"{% elif p.pnl_pct > 0 %}class="up"{% endif %}>{% if p.pnl_pct >= 0 %}+{% endif %}{{ '{:.1f}'.format(p.pnl_pct) }}%</b>{% endif %}
        {% if p.tag == 'Cắt lỗ' %} · Vượt ngưỡng cắt lỗ{% endif %}
      </div>
      {% set tag_class = 'tag-cut' if p.tag in ['Cắt lỗ', 'Giảm tỉ trọng'] else 'tag-add' if p.tag in ['Giữ/Thêm', 'Thêm'] else 'tag-tp' if p.tag == 'Chốt lời' else 'tag-hold' %}
      <div class="tag {{ tag_class }}">{{ p.tag }}</div>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- ══ 7. TIN TỨC ĐÁNG CHÚ Ý ══ -->
  {% if news %}
  <div class="card s">
    <div class="sec-lbl">Tin tức đáng chú ý</div>
    {% for item in news[:5] %}
    <div class="news-row">
      <div class="news-n">{{ "%02d" % (loop.index) }}</div>
      <div class="news-body">
        <div class="news-hl">{{ item.headline }}</div>
        <div class="news-foot">
          <span class="news-src">{{ item.source | default('Vietstock') }}</span>
          <span class="news-cat {% if item.tag in ['Neutral', 'Vĩ mô'] %}macro{% elif item.tag in ['Tích cực', 'Bullish'] %}sector{% elif item.tag in ['Rủi ro', 'Bearish'] %}risk{% endif %}">{{ item.tag | default('Neutral') }}</span>
        </div>
      </div>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- ══ FOOTER ══ -->
  <div class="foot s">
    <div class="foot-l">Tạo bởi <strong>AgentQ</strong></div>
    <div class="foot-r">Chỉ mang tính tham khảo<br>Không phải tư vấn đầu tư</div>
  </div>

</div>
</body>
</html>
"""


def render_recap_html(data: dict) -> str:
    """
    Performs data binding to the HTML template.
    """
    template = Template(RECAP_HTML_TEMPLATE)

    # Ensure required fields with defaults
    now = datetime.datetime.now()
    day_names = [
        "THỨ HAI",
        "THỨ BA",
        "THỨ TƯ",
        "THỨ NĂM",
        "THỨ SÁU",
        "THỨ BẢY",
        "CHỦ NHẬT",
    ]

    if "mast_date" not in data:
        data["mast_date"] = (
            f"{day_names[now.weekday()]} · {now.strftime('%d %b %Y').upper()}"
        )
    if "mast_time" not in data:
        data["mast_time"] = now.strftime("%H:%M")

    # Regime VN mapping
    regime_map = {
        "bull_trending": "BULL TRENDING",
        "recovery": "ĐANG HỒI PHỤC",
        "ranging": "TÍCH LŨY",
        "bear_risk": "GIẢM RỦI RO",
        "unknown": "QUAN SÁT",
    }

    rec_map = {
        "bear_risk": "Khuyến nghị phân bổ 0–20%",
        "ranging": "Khuyến nghị phân bổ 30–50%",
        "recovery": "Khuyến nghị phân bổ 50–80%",
        "bull_trending": "Khuyến nghị phân bổ 80–100%",
        "unknown": "Chưa có dữ liệu",
    }

    if "ai_data" not in data:
        data["ai_data"] = {}

    regime = data["ai_data"].get("regime", "unknown")
    data["ai_data"]["regime_vn"] = regime_map.get(regime, "QUAN SÁT")
    data["ai_data"]["regime_recommendation"] = rec_map.get(regime, "")

    # Ensure regime_breakdown exists
    if "regime_breakdown" not in data["ai_data"]:
        data["ai_data"]["regime_breakdown"] = {
            "trend": 0.5,
            "vol": 0.5,
            "breadth": 0.5,
            "foreign": 0.5,
            "valuation": 0.5,
        }

    if "regime_score" not in data["ai_data"]:
        data["ai_data"]["regime_score"] = 0.5

    return template.render(**data)
