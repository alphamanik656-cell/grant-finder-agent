"""
Kauffman Foundation Knowledge Graph Builder
Generates a fully self-contained HTML file — no internet, no server, no libraries.
Open the output HTML file directly in any browser.

Run:  python build_graph.py
Out:  output/knowledge-graph/kauffman-foundation-graph.html
"""

import json
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output" / "knowledge-graph"


# ── Graph data ────────────────────────────────────────────────────────────────

def build_graph() -> dict:
    nodes, edges = [], []

    def n(nid, label, group, tooltip):
        nodes.append({"id": nid, "label": label, "group": group, "title": tooltip})

    def e(src, dst, label=""):
        edges.append({"from": src, "to": dst, "label": label})

    # Center
    n("kauffman", "Kauffman\nFoundation", "foundation",
      "The Ewing Marion Kauffman Foundation is one of the largest private foundations "
      "in the US. It gives grants to nonprofits working on entrepreneurship and "
      "education — mostly in the Kansas City area.")

    # Focus areas
    n("fa_entre",    "Entrepreneurship",        "focus_area",
      "Kauffman funds programs that help people start businesses — especially people "
      "who normally don't get access to money or mentorship, like women, minorities, "
      "and low-income founders.")
    n("fa_workforce","Job Training\n& Careers", "focus_area",
      "Kauffman funds programs that teach job skills and help people land good careers — "
      "apprenticeships, trade certifications, and manufacturing training programs.")
    n("fa_college",  "College Access\n& Completion", "focus_area",
      "Kauffman funds programs that help students get into college and actually finish — "
      "especially first-generation and low-income students.")

    e("kauffman", "fa_entre",    "funds")
    e("kauffman", "fa_workforce","funds")
    e("kauffman", "fa_college",  "funds")

    # Grant pathways
    n("pw_research",   "Research Grants\n$150K+ per year",  "pathway",
      "Gives $150,000 or more per year to organizations doing research on "
      "entrepreneurship or education.\n\nOpen: June 1 – June 30, 2026\nWho can apply: Any qualifying nonprofit")
    n("pw_capacity",   "Capacity Grants\n$100K – $250K",    "pathway",
      "Helps nonprofits grow — more staff, better technology, expanded programs — "
      "so they can serve more people.\n\nOpen: July 13 – August 13, 2026\nWho can apply: Any qualifying nonprofit")
    n("pw_collective", "Collective Impact\nUp to $20 million", "pathway",
      "For large partnerships between multiple organizations working on a big "
      "community goal together.\n\nPlanning grants: up to $500,000\n"
      "Implementation: $5M – $20M (multi-year)\nIMPORTANT: Invitation only")
    n("pw_project",    "Project Grants\n$250K+ per year",   "pathway",
      "Supports specific programs or initiatives a nonprofit is already running.\n\n"
      "Open: November 2026 – January 2027\nWho can apply: Any qualifying nonprofit")

    e("kauffman", "pw_research",   "offers")
    e("kauffman", "pw_capacity",   "offers")
    e("kauffman", "pw_collective", "offers")
    e("kauffman", "pw_project",    "offers")

    # Requirements
    n("req_nonprofit", "Must Be a\nRegistered Nonprofit", "requirement",
      "Your organization must be a 501(c)(3) nonprofit — registered with the IRS "
      "as a tax-exempt charitable organization.")
    n("req_kc",        "Must Serve\nKansas City",         "requirement",
      "Kauffman primarily funds programs that benefit people in the Kansas City "
      "metro area (both Kansas and Missouri sides).")

    e("pw_research",   "req_nonprofit", "requires")
    e("pw_capacity",   "req_nonprofit", "requires")
    e("pw_collective", "req_nonprofit", "requires")
    e("pw_project",    "req_nonprofit", "requires")
    e("pw_research",   "req_kc",        "requires")
    e("pw_capacity",   "req_kc",        "requires")
    e("pw_collective", "req_kc",        "requires")
    e("pw_project",    "req_kc",        "requires")

    # Foundation goals
    n("goal_mobility",  "Economic\nMobility",          "goal",
      "Kauffman's big-picture goal is economic mobility — helping people move "
      "from poverty or low income to financial stability and independence.")
    n("goal_equity",    "Equal Opportunity\nfor Everyone", "goal",
      "Kauffman specifically tries to reach people left out of the economy — "
      "Black and Latino entrepreneurs, women, first-generation students.")
    n("goal_ecosystem", "Stronger\nEntrepreneurship\nEcosystem", "goal",
      "Kauffman wants to build a city where anyone can start a business — by "
      "improving access to money, mentors, training, and networks.")

    e("kauffman", "goal_mobility",  "works toward")
    e("kauffman", "goal_equity",    "works toward")
    e("kauffman", "goal_ecosystem", "works toward")

    # Example grantees
    n("ex_rising_tide", "Rising Tide Capital",         "grantee",
      "Received a grant to expand financial coaching and access to small business "
      "loans for entrepreneurs on Kansas City's East Side.")
    n("ex_pipeline",    "Pipeline, Inc.",               "grantee",
      "Received a grant to help KC founders get financially ready for loans — "
      "through education, mentorship, and technology.")
    n("ex_mo_works",    "Missouri Works\nInitiative",   "grantee",
      "Received a grant to run a pre-apprenticeship program connecting people "
      "from underrepresented communities to advanced manufacturing careers.")
    n("ex_futures",     "Futures First",                "grantee",
      "Received a grant to connect Kansas Citians to careers in early childhood "
      "education — training, certifications, and a path to advancement.")
    n("ex_jr_achieve",  "Junior Achievement\nof Greater KC", "grantee",
      "Received a grant to expand an evidence-based program that helps students "
      "build skills and confidence to get into and finish college.")
    n("ex_umkc",        "UMKC Math Academy",            "grantee",
      "Received a grant to offer free dual-credit math classes to high school "
      "students, helping close math gaps and prepare more students for STEM.")

    e("ex_rising_tide", "fa_entre",    "funded for")
    e("ex_pipeline",    "fa_entre",    "funded for")
    e("ex_mo_works",    "fa_workforce","funded for")
    e("ex_futures",     "fa_workforce","funded for")
    e("ex_jr_achieve",  "fa_college",  "funded for")
    e("ex_umkc",        "fa_college",  "funded for")
    e("ex_rising_tide", "kauffman",    "funded by")
    e("ex_pipeline",    "kauffman",    "funded by")
    e("ex_mo_works",    "kauffman",    "funded by")
    e("ex_futures",     "kauffman",    "funded by")
    e("ex_jr_achieve",  "kauffman",    "funded by")
    e("ex_umkc",        "kauffman",    "funded by")

    return {"nodes": nodes, "edges": edges}


# ── HTML (pure SVG + vanilla JS — zero external dependencies) ─────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Kauffman Foundation — Knowledge Graph</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #eef0f8;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
header {
  background: #1e2233;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
header h1 { color: #fff; font-size: 16px; font-weight: 700; }
header span { color: #777; font-size: 11px; }
#main { display: flex; flex: 1; overflow: hidden; }
#svg-wrap { flex: 1; overflow: hidden; background: #fff; cursor: default; }
svg { width: 100%; height: 100%; display: block; }
#sidebar {
  width: 320px; flex-shrink: 0;
  background: #fff;
  border-left: 1px solid #dde1f0;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.panel { padding: 16px 18px; border-bottom: 1px solid #edf0f8; }
.panel-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1.2px; color: #b0b8cc; margin-bottom: 10px;
}
#detail-title {
  font-size: 16px; font-weight: 700; color: #1e2233; margin-bottom: 6px; line-height: 1.3;
}
#detail-badge {
  display: none; font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.8px; padding: 2px 9px; border-radius: 20px; margin-bottom: 10px;
}
#detail-body { font-size: 13px; line-height: 1.75; color: #555; white-space: pre-line; }
.muted { color: #b0b8cc; font-style: italic; }
.controls { padding: 10px 18px; border-bottom: 1px solid #edf0f8; display: flex; gap: 8px; }
.btn {
  background: #f0f3fb; border: 1px solid #d8dcee; color: #555;
  padding: 6px 14px; border-radius: 8px; cursor: pointer; font-size: 12px;
}
.btn:hover { background: #e4e8f6; }
#legend-wrap { padding: 16px 18px; overflow-y: auto; flex: 1; }
.leg-item { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px; }
.leg-dot { width: 13px; height: 13px; border-radius: 50%; flex-shrink: 0; margin-top: 2px; }
.leg-text .leg-name { font-size: 12px; font-weight: 600; color: #333; }
.leg-text .leg-desc { font-size: 11px; color: #aaa; margin-top: 1px; }
footer { background: #1e2233; padding: 6px 20px; font-size: 10px; color: #555; flex-shrink: 0; }
</style>
</head>
<body>
<header>
  <h1>Kauffman Foundation — Knowledge Graph</h1>
  <span>NODE_COUNT nodes &nbsp;&middot;&nbsp; EDGE_COUNT connections &nbsp;&middot;&nbsp; GEN_DATE</span>
</header>
<div id="main">
  <div id="svg-wrap">
    <svg id="svg">
      <defs>
        <marker id="arr" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
          <path d="M0,0 L7,2.5 L0,5 Z" fill="#b8c0d8"/>
        </marker>
      </defs>
      <g id="zg">
        <g id="EL"></g>
        <g id="NL"></g>
      </g>
    </svg>
  </div>
  <div id="sidebar">
    <div class="controls">
      <button class="btn" onclick="rearrange()">Re-arrange</button>
      <button class="btn" onclick="fitView()">Fit View</button>
    </div>
    <div class="panel">
      <div class="panel-label">Click any node to learn more</div>
      <div id="detail-title" class="muted">Select a node</div>
      <div id="detail-badge"></div>
      <div id="detail-body" class="muted">Click any circle or shape in the graph to see a plain-English explanation here.</div>
    </div>
    <div id="legend-wrap">
      <div class="panel-label">What each color means</div>
      <div id="LEG"></div>
    </div>
  </div>
</div>
<footer>YEA Today Grant Finder &nbsp;&middot;&nbsp; Sources: Kauffman Foundation Timeline 2026 &amp; Grantee Organizations</footer>

<script>
// ── Data ──────────────────────────────────────────────────────────────────────
const DATA = GRAPH_DATA_PLACEHOLDER;

// ── Visual config ─────────────────────────────────────────────────────────────
const CFG = {
  foundation:  { color:'#E74C3C', label:'Foundation',              desc:'The grant-giving organization' },
  focus_area:  { color:'#2980B9', label:'Focus Area',              desc:'Main topics Kauffman funds' },
  pathway:     { color:'#27AE60', label:'Grant Pathway',           desc:'Ways to apply for a grant' },
  requirement: { color:'#E67E22', label:'Eligibility Requirement', desc:'Rules you must meet to apply' },
  goal:        { color:'#8E44AD', label:'Foundation Goal',         desc:'What Kauffman is working toward' },
  grantee:     { color:'#16A085', label:'Funded Organization',     desc:'A nonprofit that received a grant' },
};

// Pre-seeded positions give the simulation a smart head start
const SEED = {
  kauffman:      [540, 370],
  fa_entre:      [210, 185],
  fa_workforce:  [210, 375],
  fa_college:    [210, 565],
  pw_research:   [870, 130],
  pw_capacity:   [910, 280],
  pw_collective: [910, 440],
  pw_project:    [870, 595],
  goal_mobility: [455, 100],
  goal_equity:   [620,  75],
  goal_ecosystem:[790, 100],
  req_nonprofit: [385, 680],
  req_kc:        [580, 700],
  ex_rising_tide:[ 30, 105],
  ex_pipeline:   [ 30, 240],
  ex_mo_works:   [ 30, 370],
  ex_futures:    [ 30, 500],
  ex_jr_achieve: [ 30, 625],
  ex_umkc:       [200, 700],
};

function nodeR(n) {
  if (n.group === 'foundation') return 52;
  if (n.group === 'focus_area') return 44;
  if (n.group === 'pathway')    return 40;
  if (n.group === 'goal')       return 38;
  if (n.group === 'requirement')return 38;
  return 28;
}

// ── Force simulation ──────────────────────────────────────────────────────────
let SN, SE;   // sim nodes / edges

function initSim() {
  SN = DATA.nodes.map(nd => {
    const p = SEED[nd.id] || [540 + (Math.random()-0.5)*300, 370 + (Math.random()-0.5)*300];
    return { ...nd, x:p[0], y:p[1], vx:0, vy:0 };
  });
  SE = DATA.edges;
}

function tick() {
  const REP = 6000, SPK = 0.022, SPL = 230, GR = 0.007, DAMP = 0.80;
  const CX = 540, CY = 370;

  for (let i = 0; i < SN.length; i++) {
    for (let j = i+1; j < SN.length; j++) {
      const a = SN[i], b = SN[j];
      const dx = b.x-a.x, dy = b.y-a.y;
      const d2 = dx*dx + dy*dy || 0.01;
      const d  = Math.sqrt(d2);
      const f  = REP / d2;
      a.vx -= dx/d*f; a.vy -= dy/d*f;
      b.vx += dx/d*f; b.vy += dy/d*f;
    }
  }

  for (const ed of SE) {
    const a = SN.find(x => x.id === ed.from);
    const b = SN.find(x => x.id === ed.to);
    if (!a || !b) continue;
    const dx = b.x-a.x, dy = b.y-a.y;
    const d  = Math.sqrt(dx*dx+dy*dy) || 0.01;
    const f  = SPK * (d - SPL);
    a.vx += dx/d*f; a.vy += dy/d*f;
    b.vx -= dx/d*f; b.vy -= dy/d*f;
  }

  for (const nd of SN) {
    nd.vx += (CX - nd.x) * GR;
    nd.vy += (CY - nd.y) * GR;
    nd.vx *= DAMP; nd.vy *= DAMP;
    nd.x  += nd.vx; nd.y  += nd.vy;
  }
}

function runSim(n) { for (let i=0;i<n;i++) tick(); }

// ── SVG helpers ───────────────────────────────────────────────────────────────
const NS = 'http://www.w3.org/2000/svg';
const svgEl = document.getElementById('svg');
const EL = document.getElementById('EL');
const NL = document.getElementById('NL');

function el(tag, attrs) {
  const e = document.createElementNS(NS, tag);
  for (const [k,v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

function edgePt(nd, tx, ty) {
  const dx = tx-nd.x, dy = ty-nd.y;
  const d  = Math.sqrt(dx*dx+dy*dy) || 1;
  const r  = nodeR(nd) + (nd.group==='pathway' ? 30 : 5);
  return { x: nd.x + dx/d*r, y: nd.y + dy/d*r };
}

function addText(parent, x, y, text, size, bold, color) {
  const t = el('text', { x, y, 'text-anchor':'middle', 'dominant-baseline':'middle',
    fill: color||'#fff', 'font-size':size, 'font-weight': bold?'700':'500',
    'font-family':'Segoe UI,system-ui,sans-serif', 'pointer-events':'none' });
  t.textContent = text;
  parent.appendChild(t);
}

// ── Render ────────────────────────────────────────────────────────────────────
function render() {
  EL.innerHTML = '';
  NL.innerHTML = '';

  // Draw edges first (behind nodes)
  for (const ed of SE) {
    const a = SN.find(x => x.id === ed.from);
    const b = SN.find(x => x.id === ed.to);
    if (!a || !b) continue;
    const p1 = edgePt(a, b.x, b.y);
    const p2 = edgePt(b, a.x, a.y);

    EL.appendChild(el('line', {
      x1:p1.x, y1:p1.y, x2:p2.x, y2:p2.y,
      stroke:'#c0c8dc', 'stroke-width':1.4,
      'marker-end':'url(#arr)',
    }));

    if (ed.label) {
      const t = el('text', {
        x:(p1.x+p2.x)/2, y:(p1.y+p2.y)/2,
        'text-anchor':'middle', 'dominant-baseline':'middle',
        fill:'#c0c8dc', 'font-size':9,
        'font-family':'Segoe UI,system-ui,sans-serif',
        'pointer-events':'none',
      });
      t.textContent = ed.label;
      EL.appendChild(t);
    }
  }

  // Draw nodes
  for (const nd of SN) {
    const c  = (CFG[nd.group] || {color:'#aaa'}).color;
    const r  = nodeR(nd);
    const g  = el('g', {});
    g.style.cursor = 'pointer';
    g.addEventListener('click', () => showDetail(nd));
    g.addEventListener('mouseenter', () => { g.style.opacity = '0.82'; });
    g.addEventListener('mouseleave', () => { g.style.opacity = '1'; });

    const shadow = 'drop-shadow(0 3px 8px rgba(0,0,0,0.18))';

    if (nd.group === 'foundation') {
      g.appendChild(el('ellipse', { cx:nd.x, cy:nd.y, rx:r, ry:Math.round(r*0.55),
        fill:c, filter:shadow }));
    } else if (nd.group === 'pathway') {
      g.appendChild(el('rect', {
        x:nd.x-80, y:nd.y-28, width:160, height:56,
        rx:11, ry:11, fill:c, filter:shadow,
      }));
    } else if (nd.group === 'requirement') {
      const pts = `${nd.x},${nd.y-r} ${nd.x+r},${nd.y} ${nd.x},${nd.y+r} ${nd.x-r},${nd.y}`;
      g.appendChild(el('polygon', { points:pts, fill:c, filter:shadow }));
    } else {
      g.appendChild(el('circle', { cx:nd.x, cy:nd.y, r, fill:c, filter:shadow }));
    }

    // Multi-line label
    const lines  = nd.label.split('\n');
    const lineH  = nd.group === 'pathway' ? 13 : 14;
    const startY = nd.y - (lines.length-1) * lineH / 2;
    const fsize  = nd.group === 'foundation' ? 13 : (nd.group === 'pathway' ? 10 : 11);
    const bold   = nd.group === 'foundation' || nd.group === 'pathway';
    lines.forEach((ln, i) => addText(g, nd.x, startY + i*lineH, ln, fsize, bold));

    NL.appendChild(g);
  }
}

// ── Pan & zoom ────────────────────────────────────────────────────────────────
let vb = {x:0, y:0, w:1000, h:750};
let drag = null;

function applyVB() {
  svgEl.setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
}

svgEl.addEventListener('wheel', ev => {
  ev.preventDefault();
  const f   = ev.deltaY > 0 ? 1.12 : 0.89;
  const rc  = svgEl.getBoundingClientRect();
  const mx  = (ev.clientX - rc.left)  / rc.width;
  const my  = (ev.clientY - rc.top)   / rc.height;
  const px  = vb.x + mx*vb.w, py = vb.y + my*vb.h;
  vb.w *= f; vb.h *= f;
  vb.x = px - mx*vb.w; vb.y = py - my*vb.h;
  applyVB();
}, {passive:false});

svgEl.addEventListener('mousedown', ev => {
  if (ev.target.closest && ev.target.closest('g[data-node]')) return;
  drag = { cx:ev.clientX, cy:ev.clientY, vx:vb.x, vy:vb.y };
  svgEl.style.cursor = 'grabbing';
});
window.addEventListener('mousemove', ev => {
  if (!drag) return;
  const rc = svgEl.getBoundingClientRect();
  vb.x = drag.vx - (ev.clientX-drag.cx)/rc.width  * vb.w;
  vb.y = drag.vy - (ev.clientY-drag.cy)/rc.height * vb.h;
  applyVB();
});
window.addEventListener('mouseup', () => { drag=null; svgEl.style.cursor=''; });

function fitView() {
  if (!SN.length) return;
  const pad=80;
  const xs = SN.map(n=>n.x), ys = SN.map(n=>n.y);
  vb.x = Math.min(...xs) - pad;
  vb.y = Math.min(...ys) - pad;
  vb.w = Math.max(...xs) - vb.x + pad;
  vb.h = Math.max(...ys) - vb.y + pad;
  applyVB();
}

// ── Detail panel ──────────────────────────────────────────────────────────────
function showDetail(nd) {
  const cfg = CFG[nd.group] || {};
  const titleEl = document.getElementById('detail-title');
  const badge   = document.getElementById('detail-badge');
  const body    = document.getElementById('detail-body');

  titleEl.textContent = nd.label.replace(/\n/g,' ');
  titleEl.style.color = cfg.color || '#1e2233';
  titleEl.className   = '';

  badge.textContent        = cfg.label || nd.group;
  badge.style.display      = 'inline-block';
  badge.style.background   = (cfg.color||'#aaa') + '20';
  badge.style.color        = cfg.color || '#555';
  badge.style.border       = `1px solid ${cfg.color||'#aaa'}55`;

  body.textContent = nd.title || '';
  body.className   = '';
}

// ── Legend ────────────────────────────────────────────────────────────────────
function buildLegend() {
  const wrap = document.getElementById('LEG');
  Object.entries(CFG).forEach(([grp, cfg]) => {
    const count = DATA.nodes.filter(n=>n.group===grp).length;
    if (!count) return;
    const div = document.createElement('div');
    div.className = 'leg-item';
    div.innerHTML =
      `<span class="leg-dot" style="background:${cfg.color}"></span>
       <span class="leg-text">
         <div class="leg-name">${cfg.label} <span style="color:#bbb;font-weight:400">(${count})</span></div>
         <div class="leg-desc">${cfg.desc}</div>
       </span>`;
    wrap.appendChild(div);
  });
}

// ── Re-arrange button ─────────────────────────────────────────────────────────
function rearrange() {
  initSim();
  runSim(500);
  render();
  fitView();
}

// ── Boot ──────────────────────────────────────────────────────────────────────
buildLegend();
initSim();
runSim(500);
render();
fitView();
</script>
</body>
</html>
"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Building knowledge graph...")
    graph = build_graph()
    print(f"  {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")

    html = (
        HTML_TEMPLATE
        .replace("GRAPH_DATA_PLACEHOLDER", json.dumps(graph, ensure_ascii=False))
        .replace("NODE_COUNT", str(len(graph["nodes"])))
        .replace("EDGE_COUNT", str(len(graph["edges"])))
        .replace("GEN_DATE", datetime.now().strftime("%B %d, %Y"))
    )

    out = OUTPUT_DIR / "kauffman-foundation-graph.html"
    out.write_text(html, encoding="utf-8")
    print(f"\nSaved: {out}")
    print("Open that file directly in Chrome or Edge — no server needed.")


if __name__ == "__main__":
    main()
