"""Builds the Arsenal page - weapons.md as a web page, with the game's own
pictures of every round, weapon and vehicle, sortable and searchable.

The numbers are dataset.py's and mean what weapons.md says they mean; the
names, the pictures and the descriptions come from the launcher's catalog
(launcher/catalog.txt and launcher/catalog/*.png, gen_catalog.py). The
pictures go into the page as data URIs, the vehicles shrunk to 112 px, so
the page is one file.

Usage:
    python gen_weapons_web.py <out.html>               the page body, for the Artifact wrapper
    python gen_weapons_web.py <out.html> --standalone  a whole document, for GitHub Pages
"""
import base64
import io
import json
import os
import sys

from PIL import Image

import dataset

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, 'launcher', 'catalog.txt')
PICTURES = os.path.join(HERE, 'launcher', 'catalog')

EFFECT = {0: 'none', 1: 'fire', 2: 'bullet', 3: 'HE', 4: 'HEAT', 5: 'heavy HE'}
GUIDANCE = {0: 'ballistic', 1: 'straight', 2: 'guided'}


def catalog():
    out = {}
    with open(CATALOG, encoding='utf-8') as f:
        head = f.readline().lstrip('#').strip().split('\t')
        for line in f:
            cols = line.rstrip('\n').split('\t')
            row = dict(zip(head, cols))
            out[row['identifier']] = row
    return out


def picture(name, limit):
    path = os.path.join(PICTURES, name)
    if not name or not os.path.exists(path):
        return None
    im = Image.open(path).convert('RGBA')
    if max(im.size) > limit:
        im.thumbnail((limit, limit), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def val(r, i):
    if i >= r['fields']:
        return None
    c, f = r['ints'][i], r['floats'][i]
    if c and abs(c) > 0x30000000:
        return round(f, 3)
    return c


def build():
    cat = catalog()
    records = dataset.load(with_m34=True)
    by_number = {r['number']: r for r in records}

    def common(r, limit):
        c = cat.get(r['id'], {})
        return {'id': r['id'], 'number': r['number'], 'name': c.get('name') or r['name'], 'german': r['name'],
                'group': c.get('group', ''), 'carrier': c.get('carrier', ''),
                'description': (c.get('description') or '').replace('\\n', '\n'),
                'value': val(r, 0), 'picture': picture(c.get('image') or r['id'] + '.png', limit)}

    ammo, weapons, vehicles = [], [], []
    for r in records:
        if r['type'] == 1:
            d = common(r, 120)
            d.update({'weight': val(r, 1), 'soldiers': [val(r, 2), val(r, 3)], 'vehicle': [val(r, 4), val(r, 5)],
                      'armour': [val(r, 6), val(r, 7)], 'threshold': val(r, 8), 'radius': val(r, 9),
                      'effect': EFFECT.get(r['ints'][10], str(r['ints'][10])),
                      'flight': GUIDANCE.get(r['ints'][14], str(r['ints'][14])),
                      'speed': val(r, 15), 'stack': val(r, 13)})
            ammo.append(d)
        elif r['type'] == 2:
            d = common(r, 120)
            count = r['ints'][17] if r['fields'] > 17 else 0
            ids = [by_number[r['ints'][18 + k]]['id'] for k in range(count)
                   if 18 + k < r['fields'] and r['ints'][18 + k] in by_number]
            after = 18 + count
            d.update({'weight': val(r, 1), 'range': val(r, 2), 'minRange': val(r, 3), 'rpm': val(r, 4),
                      'aim': val(r, 6), 'ammo': ids, 'speed': val(r, after), 'salvo': val(r, after + 1),
                      'f13': val(r, 13), 'f14': val(r, 14), 'f15': val(r, 15), 'f16': val(r, 16)})
            weapons.append(d)
        elif r['type'] == 3:
            d = common(r, 112)
            d.update({'hp': val(r, 5), 'armour': val(r, 2), 'speed': val(r, 4), 'seats': val(r, 6),
                      'f3': val(r, 3), 'f9': val(r, 9)})
            vehicles.append(d)
    return {'ammo': ammo, 'weapons': weapons, 'vehicles': vehicles}


PAGE = r'''<title>Soldiers of Anarchy Arsenal</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Saira+Condensed:wght@500;700&family=IBM+Plex+Sans:ital,wght@0,400;0,500;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {
  --ground: #ece5cf; --panel: #f6f1e1; --inset: #262a22; --inset-2: #30352b;
  --ink: #23271c; --ink-soft: #5c6150; --ink-on-inset: #e2d9b8; --soft-on-inset: #a49e82;
  --line: #cdc4a4; --line-inset: #43483b;
  --accent: #b5731c; --accent-ink: #7a4b0c; --accent-on-inset: #e6a63e;
  --bar: #6b7a3a; --bar-armour: #8a6b2c; --bar-hp: #8f3a2a;
  --font-display: "Saira Condensed", "Arial Narrow", sans-serif;
  --font-body: "IBM Plex Sans", "Segoe UI", sans-serif;
  --font-mono: "IBM Plex Mono", Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground: #171a14; --panel: #1f231c; --inset: #0f110d; --inset-2: #181b15;
    --ink: #ded6b6; --ink-soft: #9e9880; --ink-on-inset: #e2d9b8; --soft-on-inset: #8f8a70;
    --line: #363b2f; --line-inset: #2c3027;
    --accent: #e0a13a; --accent-ink: #e6b055; --accent-on-inset: #e6a63e;
    --bar: #8a9c4e; --bar-armour: #b98f3c; --bar-hp: #c4553f;
  }
}
:root[data-theme="dark"] {
  --ground: #171a14; --panel: #1f231c; --inset: #0f110d; --inset-2: #181b15;
  --ink: #ded6b6; --ink-soft: #9e9880; --ink-on-inset: #e2d9b8; --soft-on-inset: #8f8a70;
  --line: #363b2f; --line-inset: #2c3027;
  --accent: #e0a13a; --accent-ink: #e6b055; --accent-on-inset: #e6a63e;
  --bar: #8a9c4e; --bar-armour: #b98f3c; --bar-hp: #c4553f;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--ground); color: var(--ink); font-family: var(--font-body); font-size: 15px; line-height: 1.5; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 32px 24px 64px; }
header { display: grid; grid-template-columns: 1fr auto; gap: 24px; align-items: end; border-bottom: 2px solid var(--ink); padding-bottom: 16px; }
.eyebrow { font-family: var(--font-display); font-weight: 500; text-transform: uppercase; letter-spacing: .14em; font-size: 13px; color: var(--ink-soft); }
h1 { font-family: var(--font-display); font-weight: 700; font-size: 52px; line-height: .95; margin: 4px 0 0; text-transform: uppercase; letter-spacing: .01em; text-wrap: balance; }
.lede { max-width: 62ch; margin: 18px 0 0; font-size: 16px; }
.lede b { font-weight: 500; }
.counts { font-family: var(--font-mono); font-size: 13px; color: var(--ink-soft); text-align: right; white-space: nowrap; }
.counts span { display: block; }
.counts em { font-style: normal; color: var(--ink); font-weight: 500; }

.rules { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 28px; margin: 28px 0 0; align-items: start; }
.rules h2 { font-family: var(--font-display); text-transform: uppercase; letter-spacing: .08em; font-size: 20px; margin: 0 0 8px; font-weight: 700; }
.rules p { margin: 0 0 10px; max-width: 60ch; }
.rules ol { margin: 0; padding-left: 20px; }
.rules li { margin: 0 0 8px; }
.diagram { background: var(--inset); color: var(--ink-on-inset); border-radius: 4px; padding: 16px; }
.diagram svg { width: 100%; height: auto; display: block; }
.diagram figcaption { font-size: 13px; color: var(--soft-on-inset); margin-top: 8px; }
.difficulty { display: flex; gap: 12px; flex-wrap: wrap; font-family: var(--font-mono); font-size: 13px; margin-top: 8px; }
.difficulty span { border: 1px solid var(--line); padding: 2px 8px; }

nav.tabs { display: flex; gap: 0; margin: 36px 0 0; border-bottom: 1px solid var(--line); align-items: end; flex-wrap: wrap; }
nav.tabs button { font-family: var(--font-display); font-weight: 700; text-transform: uppercase; letter-spacing: .08em; font-size: 17px; background: none; border: 0; border-bottom: 3px solid transparent; color: var(--ink-soft); padding: 8px 14px; cursor: pointer; margin-bottom: -1px; }
nav.tabs button[aria-selected="true"] { color: var(--ink); border-bottom-color: var(--accent); }
nav.tabs button:focus-visible, .sort:focus-visible, input:focus-visible, .row:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
nav.tabs .search { margin-left: auto; padding: 0 0 8px; }
nav.tabs input { font: inherit; font-family: var(--font-mono); font-size: 13px; padding: 6px 10px; border: 1px solid var(--line); background: var(--panel); color: var(--ink); width: 220px; }

section[hidden] { display: none; }
.note { font-size: 13px; color: var(--ink-soft); margin: 14px 0 10px; max-width: 80ch; }
.scroll { overflow-x: auto; background: var(--panel); border: 1px solid var(--line); }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th { font-family: var(--font-display); font-weight: 500; text-transform: uppercase; letter-spacing: .08em; font-size: 12.5px; color: var(--ink-soft); text-align: left; padding: 10px 10px 8px; border-bottom: 1px solid var(--line); white-space: nowrap; position: sticky; top: 0; background: var(--panel); }
th.num, td.num { text-align: right; }
th .sort { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; text-transform: inherit; letter-spacing: inherit; }
th[aria-sort="ascending"] .sort::after { content: " ▲"; color: var(--accent); }
th[aria-sort="descending"] .sort::after { content: " ▼"; color: var(--accent); }
td { padding: 7px 10px; border-bottom: 1px solid var(--line); vertical-align: middle; font-family: var(--font-mono); font-size: 13.5px; }
td.item { font-family: var(--font-body); min-width: 250px; }
.who { display: flex; align-items: center; gap: 12px; }
.pic { width: 64px; height: 36px; flex: none; display: grid; place-items: center; background: var(--inset); border-radius: 3px; }
.pic img { max-width: 60px; max-height: 32px; image-rendering: auto; }
.pic.big { width: 72px; height: 56px; }
.pic.big img { max-width: 68px; max-height: 52px; }
.who .name { font-weight: 500; }
.who .id { font-family: var(--font-mono); font-size: 11.5px; color: var(--ink-soft); }
.range { white-space: nowrap; }
.range small { color: var(--ink-soft); font-size: 11px; }
.bar { display: inline-block; height: 8px; background: var(--bar); vertical-align: middle; margin-right: 6px; border-radius: 1px; }
.bar.armour { background: var(--bar-armour); }
.bar.hp { background: var(--bar-hp); }
.tag { font-family: var(--font-display); text-transform: uppercase; letter-spacing: .06em; font-size: 12px; padding: 1px 6px; border: 1px solid var(--line); color: var(--ink-soft); white-space: nowrap; }
.ammo-list { font-family: var(--font-body); font-size: 13px; }
.ammo-list a { color: var(--accent-ink); text-decoration: none; border-bottom: 1px dotted var(--accent); }
.row { cursor: pointer; }
.row:hover td { background: color-mix(in srgb, var(--accent) 8%, transparent); }
tr.detail td { background: var(--inset); color: var(--ink-on-inset); font-family: var(--font-body); padding: 14px 18px 16px 86px; white-space: pre-line; line-height: 1.5; }
tr.detail td .german { color: var(--soft-on-inset); font-size: 13px; }
.empty td { text-align: center; color: var(--ink-soft); font-family: var(--font-body); padding: 24px; }
footer { margin-top: 40px; font-size: 13px; color: var(--ink-soft); max-width: 80ch; }
@media (max-width: 760px) {
  h1 { font-size: 38px; }
  header, .rules { grid-template-columns: 1fr; }
  .counts { text-align: left; }
  .counts span { display: inline; margin-right: 12px; }
}
@media (prefers-reduced-motion: no-preference) { .row td { transition: background .15s; } }
</style>
<div class="wrap">
<header>
  <div>
    <div class="eyebrow">Soldiers of Anarchy · Data.set, read off the code and checked with the gun</div>
    <h1>Arsenal</h1>
    <p class="lede">Every round of ammunition with its three damage ranges and the armour it has to get under, every weapon with its range and rate of fire, every vehicle with its hit points and armour — the numbers the game plays by, with the game's own pictures. <b>Click a row for the game's description.</b></p>
  </div>
  <div class="counts" id="counts"></div>
</header>

<div class="rules">
  <div>
    <h2>How a hit is resolved</h2>
    <p>Every unit carries two pools: <b>hit points</b> and <b>armour</b>. A soldier's armour is his vest — the heavy vest counts 80, the light one 40, none 0; a vehicle's is its armour figure. One hit with a round:</p>
    <ol>
      <li>the <b>armour</b> pool loses a random value from the round's <i>vs armour</i> range;</li>
      <li>the <b>hit points</b> lose something only when the armour left is below the round's <i>penetrates below</i> figure — then a value from <i>vs soldiers</i> for a soldier, from <i>vs vehicle hp</i> for anything else.</li>
    </ol>
    <p>So an AK‑74 round (armour 3–4, penetrates below 4) has to strip a BTR‑80's 1500 armour before its 2–3 points of hit‑point damage ever count, while an RPG‑7 grenade (armour 1400–1800, penetrates below 500) takes a T‑55's 2500 armour in two hits and then does 150–200 to its 100 hit points. A monk with no vest takes 9–11 from every AK‑74 round — ten rounds, watched live.</p>
    <p>An <b>explosion</b> reaches everything within the blast radius and scales the top of each range by 1 − distance ⁄ radius; a rocket that hits something directly does its direct damage first. <b>Fire</b> (the Plamya incendiary, the Molotov) burns instead: a tenth of the values per tick to whoever stands in it.</p>
    <p>The difficulty scales only what the human player's units take; the enemy takes full damage on every setting.</p>
    <div class="difficulty"><span>Easy ×0.5</span><span>Normal ×0.75</span><span>Hard ×1.0</span><span>Very hard ×1.25</span></div>
  </div>
  <figure class="diagram" aria-label="A round against a BTR-80: the armour pool takes the armour damage on every hit; the hit points only once the armour is below the round's threshold.">
    <svg viewBox="0 0 520 250" xmlns="http://www.w3.org/2000/svg" font-family="IBM Plex Sans, sans-serif" font-size="13">
      <text x="14" y="24" fill="#e6a63e" font-family="Saira Condensed, sans-serif" font-size="15" letter-spacing="1.5" style="text-transform:uppercase">RPG-7 GRENADE × T-55, HIT BY HIT</text>
      <text x="14" y="58" fill="#a49e82">armour 2500</text>
      <rect x="120" y="46" width="380" height="16" fill="#181b15" stroke="#43483b"/>
      <rect x="120" y="46" width="380" height="16" fill="#b98f3c"/>
      <text x="14" y="96" fill="#a49e82">hit 1: −1400…1800</text>
      <rect x="120" y="84" width="380" height="16" fill="#181b15" stroke="#43483b"/>
      <rect x="120" y="84" width="137" height="16" fill="#b98f3c"/>
      <line x1="196" y1="80" x2="196" y2="104" stroke="#e6a63e" stroke-dasharray="3 2"/>
      <text x="200" y="118" fill="#e6a63e" font-size="11">penetrates below 500 → still above it, hit points untouched</text>
      <text x="14" y="150" fill="#a49e82">hit 2: −1400…1800</text>
      <rect x="120" y="138" width="380" height="16" fill="#181b15" stroke="#43483b"/>
      <text x="126" y="151" fill="#a49e82" font-size="11">armour 0</text>
      <text x="14" y="196" fill="#a49e82">hit points 100</text>
      <rect x="120" y="184" width="380" height="16" fill="#181b15" stroke="#43483b"/>
      <rect x="120" y="184" width="380" height="16" fill="#c4553f"/>
      <text x="14" y="230" fill="#a49e82">hit 3: −150…200</text>
      <rect x="120" y="218" width="380" height="16" fill="#181b15" stroke="#43483b"/>
      <text x="126" y="231" fill="#c4553f" font-size="11">destroyed</text>
    </svg>
    <figcaption>Read off TakeDamage (0x57CDB0 → 0x57CE70) and the explosion (0x56D9A0); the AK‑74 numbers were checked by shooting a monk, a Hummer and a BTR‑80 while the round's fields were changed in memory.</figcaption>
  </figure>
</div>

<nav class="tabs" role="tablist">
  <button role="tab" aria-selected="true" data-tab="ammo">Ammunition</button>
  <button role="tab" aria-selected="false" data-tab="weapons">Weapons</button>
  <button role="tab" aria-selected="false" data-tab="vehicles">Vehicles</button>
  <div class="search"><input id="q" type="search" placeholder="filter by name or id" aria-label="Filter"></div>
</nav>

<section id="tab-ammo">
  <p class="note">Ranges are min–max per hit. <i>Effect</i> is what the impact does (bullet, HE burst, shaped charge, heavy burst, fire, or nothing for smoke and flares); <i>flight</i> is ballistic, straight or guided; <i>speed</i> is the projectile's in world units per second. Sort by any column.</p>
  <div class="scroll"><table id="t-ammo"></table></div>
</section>
<section id="tab-weapons" hidden>
  <p class="note">Range and minimum range in world units (one unit is one map cell); <i>aim</i> is the time a shot takes to line up, in seconds. A weapon's damage is its ammunition's — follow the link. <i>Salvo</i> is the rounds one shot sends (a rocket pod's tubes).</p>
  <div class="scroll"><table id="t-weapons"></table></div>
</section>
<section id="tab-vehicles" hidden>
  <p class="note">Hit points and armour are what the vehicle carries in a mission, checked live for the Hummer, the BTR‑80, the BMP‑1 and the T‑55. Speed and seats are the record's; the vehicle's weapons are on the Weapons tab, filtered by its name.</p>
  <div class="scroll"><table id="t-vehicles"></table></div>
</section>

<footer>Generated from <code>Data.set</code> by <code>gen_weapons_web.py</code>; the same numbers and their provenance are in <code>weapons.md</code>. Two fields of the weapons (f13–f16) and two of the vehicles (f3, f9) are not understood and are left out here.</footer>
</div>
<script>
const DATA = __DATA__;
const byId = {};
for (const k of ['ammo','weapons','vehicles']) for (const d of DATA[k]) byId[d.id] = d;

const COLS = {
  ammo: [
    {key:'name', label:'Round', item:true},
    {key:'soldiers', label:'vs soldiers', num:true, range:true, sortBy:d=>d.soldiers[1]},
    {key:'vehicle', label:'vs vehicle hp', num:true, range:true, sortBy:d=>d.vehicle[1]},
    {key:'armour', label:'vs armour', num:true, range:true, sortBy:d=>d.armour[1]},
    {key:'threshold', label:'penetrates below', num:true},
    {key:'radius', label:'blast radius', num:true, bar:{max:20, cls:''}},
    {key:'effect', label:'effect', tag:true},
    {key:'flight', label:'flight', tag:true},
    {key:'speed', label:'speed', num:true},
    {key:'stack', label:'stack', num:true},
    {key:'weight', label:'weight', num:true},
    {key:'value', label:'value', num:true},
  ],
  weapons: [
    {key:'name', label:'Weapon', item:true},
    {key:'carrier', label:'carrier', text:true},
    {key:'range', label:'range', num:true, bar:{max:400, cls:''}},
    {key:'minRange', label:'min range', num:true},
    {key:'rpm', label:'rounds/min', num:true},
    {key:'aim', label:'aim s', num:true},
    {key:'ammo', label:'ammunition', ammo:true},
    {key:'speed', label:'speed', num:true},
    {key:'salvo', label:'salvo', num:true},
    {key:'weight', label:'weight', num:true},
    {key:'value', label:'value', num:true},
  ],
  vehicles: [
    {key:'name', label:'Vehicle', item:true, big:true},
    {key:'hp', label:'hit points', num:true, bar:{max:170, cls:'hp'}},
    {key:'armour', label:'armour', num:true, bar:{max:3300, cls:'armour'}},
    {key:'speed', label:'speed', num:true},
    {key:'seats', label:'seats', num:true},
    {key:'value', label:'value', num:true},
  ],
};
const state = {tab:'ammo', q:'', sort:{ammo:null, weapons:null, vehicles:null}};

function esc(s){ return String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function fmt(v){ return v == null ? '—' : (Number.isInteger(v) ? String(v) : String(v)); }
function cell(col, d) {
  const v = d[col.key];
  if (col.item) return `<td class="item"><div class="who"><span class="pic${col.big?' big':''}">${d.picture?`<img src="${d.picture}" alt="">`:''}</span><span><div class="name">${esc(d.name)}</div><div class="id">${esc(d.id)} · #${d.number}</div></span></div></td>`;
  if (col.range) return `<td class="num range">${fmt(v[0])}<small>–</small>${fmt(v[1])}</td>`;
  if (col.tag) return `<td><span class="tag">${esc(v)}</span></td>`;
  if (col.ammo) return `<td class="ammo-list">${v.length ? v.map(id => `<a href="#" data-ammo="${esc(id)}">${esc(byId[id]?byId[id].name:id)}</a>`).join(', ') : '—'}</td>`;
  if (col.text) return `<td class="item" style="min-width:0;font-family:var(--font-body)">${esc(v)||'—'}</td>`;
  if (col.bar) { const w = v ? Math.max(3, Math.round(Math.min(1, v/col.bar.max)*80)) : 0; return `<td class="num"><span class="bar ${col.bar.cls}" style="width:${w}px"></span>${fmt(v)}</td>`; }
  return `<td class="num">${fmt(v)}</td>`;
}
function render(tab) {
  const cols = COLS[tab], t = document.getElementById('t-' + tab), s = state.sort[tab];
  let rows = DATA[tab].filter(d => !state.q || (d.name + ' ' + d.id + ' ' + (d.carrier||'') + ' ' + d.german).toLowerCase().includes(state.q));
  if (s) {
    const col = cols.find(c => c.key === s.key);
    const key = col.sortBy || (d => d[col.key]);
    rows = rows.slice().sort((a, b) => {
      const x = key(a), y = key(b);
      if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1;
      return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y))) * (s.dir === 'asc' ? 1 : -1);
    });
  }
  t.innerHTML = '<thead><tr>' + cols.map(c => `<th class="${c.num?'num':''}" aria-sort="${s&&s.key===c.key?(s.dir==='asc'?'ascending':'descending'):'none'}"><button class="sort" data-key="${c.key}">${c.label}</button></th>`).join('') + '</tr></thead><tbody>'
    + (rows.length ? rows.map(d => `<tr class="row" tabindex="0" data-id="${esc(d.id)}">${cols.map(c => cell(c, d)).join('')}</tr>`).join('') : `<tr class="empty"><td colspan="${cols.length}">Nothing matches "${esc(state.q)}".</td></tr>`)
    + '</tbody>';
  document.getElementById('counts').innerHTML = `<span><em>${DATA.ammo.length}</em> rounds</span><span><em>${DATA.weapons.length}</em> weapons</span><span><em>${DATA.vehicles.length}</em> vehicles</span>`;
}
function toggleDetail(tr) {
  const next = tr.nextElementSibling;
  if (next && next.classList.contains('detail')) { next.remove(); return; }
  const d = byId[tr.dataset.id];
  const text = d.description ? esc(d.description) : 'The game has no description for this one.';
  const row = document.createElement('tr'); row.className = 'detail';
  row.innerHTML = `<td colspan="${tr.children.length}">${text}\n<span class="german">In the data: ${esc(d.german)}</span></td>`;
  tr.after(row);
}
document.querySelector('nav.tabs').addEventListener('click', e => {
  const b = e.target.closest('button[data-tab]'); if (!b) return;
  state.tab = b.dataset.tab;
  document.querySelectorAll('nav.tabs button[data-tab]').forEach(x => x.setAttribute('aria-selected', x === b));
  document.querySelectorAll('section[id^="tab-"]').forEach(s => s.hidden = s.id !== 'tab-' + state.tab);
  render(state.tab);
});
document.getElementById('q').addEventListener('input', e => { state.q = e.target.value.trim().toLowerCase(); render(state.tab); });
document.addEventListener('click', e => {
  const sort = e.target.closest('.sort');
  if (sort) { const s = state.sort[state.tab]; state.sort[state.tab] = s && s.key === sort.dataset.key ? (s.dir === 'desc' ? {key:s.key, dir:'asc'} : null) : {key: sort.dataset.key, dir:'desc'}; render(state.tab); return; }
  const a = e.target.closest('a[data-ammo]');
  if (a) { e.preventDefault(); state.q = a.dataset.ammo.toLowerCase(); document.getElementById('q').value = a.dataset.ammo; document.querySelector('button[data-tab="ammo"]').click(); return; }
  const tr = e.target.closest('tr.row');
  if (tr) toggleDetail(tr);
});
document.addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.classList.contains('row')) toggleDetail(e.target); });
for (const k of ['ammo','weapons','vehicles']) render(k);

</script>
'''


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    data = build()
    html = PAGE.replace('__DATA__', json.dumps(data, ensure_ascii=False))
    if '--standalone' in sys.argv:
        head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
                '<meta name="description" content="Every round, weapon and vehicle of Soldiers of Anarchy '
                'with its damage, blast radius, armour and range.">\n')
        html = head + html.replace('</style>', '</style>\n</head>\n<body>', 1) + '\n</body>\n</html>\n'
    with open(sys.argv[1], 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)
    print('wrote %s (%d kB)' % (sys.argv[1], len(html.encode('utf-8')) // 1024))


if __name__ == '__main__':
    main()
