"""Ordinary Python budget comparison for #890; reads quantities.json only.

Writes costs.csv, estimate.json and a standalone estimate.html beside this file.
USD comparisons use listed US products as proxies for the metric study; ranges
without exact product matches are explicit allowances. No purchasing, external
writes or changes to the Blender asset. This is not a contractor quotation.
"""
from pathlib import Path
import json, csv, math, html

def main(args):
    """Price an inventory with an explicit dated scenario, never live-price claims."""
    ROOT=args.output.resolve()
    q=json.loads(args.quantities.read_text(encoding='utf-8'));g=q['groups']
    if 'framing_profile' not in q or 'wall_stock_equivalents' not in q:raise ValueError('Takeoff lacks an explicit framing profile; regenerate quantities from a profile-selected native study')
    rates=json.loads(args.rates.read_text(encoding='utf-8'));SOURCES=rates['sources']
    if rates['currency']!='USD':raise ValueError('This example budget uses USD units/conversions; adapt the calculator for another currency')
    ROOT.mkdir(parents=True,exist_ok=False)
    rows = []

    def add(group, item, quantity, unit):
        rate = rates['items'][item]
        waste = rate['waste_percent'] / 100
        low = rate['unit_low_usd']
        high = rate['unit_high_usd']
        basis = rate['basis']
        if low < 0 or high < low or waste < 0:
            raise ValueError('Invalid rate range: ' + item)
        order = math.ceil(quantity * (1 + waste)) if unit in ('sheet', 'each') else quantity * (1 + waste)
        rows.append(dict(group=group, item=item, net_quantity=quantity, unit=unit, waste_percent=waste * 100, budget_quantity=order, unit_low_usd=low, unit_high_usd=high, low_usd=order * low, high_usd=order * high, basis=basis))
    ext = q['wall_stock_equivalents']['exterior']
    inside = q['wall_stock_equivalents']['interior']
    add('Timber and engineered wood', 'Exterior stud / plate / blocking stock', ext['volume_m3'] / (0.0381 * 0.1397 * 3.048), '10ft-board volume equivalent')
    add('Timber and engineered wood', 'Interior stud / plate / blocking stock', inside['volume_m3'] / (0.0381 * 0.0889 * 3.048), '10ft-board volume equivalent')
    roof = sum((v['volume_m3'] for k, v in g.items() if k.startswith('Roof framing:')))
    heavy = sum((g[k]['volume_m3'] for k in ['Roof framing: main ridge', 'Roof framing: cross ridge', 'Roof framing: valley beam', 'Roof framing: dining rear beam', 'Roof framing: dining ledger']))
    add('Timber and engineered wood', 'Roof rafters / ties / gable framing', roof - heavy, 'm3')
    add('Timber and engineered wood', 'Roof ridges / valleys / large beams', heavy, 'm3')
    add('Timber and engineered wood', 'Both-floor I-joists', g['Floors: engineered I-joist upper flanges']['length_m'] / 0.3048, 'linear ft')
    add('Timber and engineered wood', 'LVL bearers / transfer beams / opening headers', g['Beams: LVL bearers / transfers / headers']['volume_m3'], 'm3')
    add('Timber and engineered wood', 'Rim / stair-opening trimmers', g['Floors: rim / trimmer timber']['volume_m3'], 'm3')
    add('Timber and engineered wood', 'Treated sill stock', g['Timber: treated foundation sill']['volume_m3'], 'm3')
    add('Timber and engineered wood', 'Roof and rainscreen battens', sum((g[k]['volume_m3'] for k in ['Battens: roof', 'Battens: rainscreen'])), 'm3')
    add('Timber and engineered wood', 'Stair timber / treads / guard timber', 1, 'allowance')
    for item, key in [('22mm subfloor', 'Panels: 22mm subfloor'), ('12mm wall sheathing', 'Panels: 12mm wall sheathing'), ('18mm roof sheathing', 'Panels: 18mm roof sheathing')]:
        add('Structural panels', item, g[key]['area_m2'] / 2.97289728, 'sheet')
    add('Foundations and incidentals', 'Foundation concrete', q['foundation_union_m3'] / 0.764554857984, 'yd3')
    add('Foundations and incidentals', 'Formwork / reinforcing / foundation waterproofing', 1, 'allowance')
    add('Foundations and incidentals', 'Structural fixings / connectors / adhesives', 1, 'allowance')
    add('Envelope and finishes', 'Standing-seam field panels', g['Roof finish: metal field panels']['area_m2'] / 0.09290304, 'ft2')
    add('Envelope and finishes', 'Roof flashings / gutters / accessories', 1, 'allowance')
    add('Envelope and finishes', 'Wall and roof weather barriers', 1, 'allowance')
    add('Envelope and finishes', 'Exterior cladding', g['Cladding: exterior skin']['area_m2'] / 0.09290304, 'ft2')
    add('Envelope and finishes', 'Modeled wall-cavity insulation', g['Insulation: wall cavities']['volume_m3'], 'm3')
    add('Envelope and finishes', '15mm wall and ceiling lining', (g['Lining: walls']['area_m2'] + g['Lining: ceilings']['area_m2']) / 2.97289728, 'sheet')
    add('Envelope and finishes', 'Lining tape / compound / consumables', 1, 'allowance')
    add('Envelope and finishes', 'Wood floor finish', g['Floor finish: oak']['area_m2'] / 0.09290304, 'ft2')
    add('Envelope and finishes', 'Tile floor finish', g['Floor finish: tile']['area_m2'] / 0.09290304, 'ft2')
    add('Envelope and finishes', 'Windows', q['feature_counts']['windows'], 'each')
    add('Envelope and finishes', 'Interior doors', q['feature_counts']['interior_doors'], 'each')
    add('Envelope and finishes', 'Entry door', q['feature_counts']['entry_doors'], 'each')
    add('Envelope and finishes', 'Paint / trim / miscellaneous finish materials', 1, 'allowance')
    totals = {}
    for r in rows:
        t = totals.setdefault(r['group'], {'low_usd': 0, 'high_usd': 0})
        for k in t:
            t[k] += r[k]
    core = {k: sum((v[k] for group, v in totals.items() if group != 'Envelope and finishes')) for k in ('low_usd', 'high_usd')}
    allcost = {k: sum((v[k] for v in totals.values())) for k in ('low_usd', 'high_usd')}
    result = dict(currency=rates['currency'], price_references_checked=rates['checked'], source_blend_sha256=q['blend_sha256'], framing_profile=q['framing_profile'], totals_by_group=totals, structural_core=core, broader_fabric=allcost, items=rows, sources=SOURCES, exclusions=['labor', 'tax', 'delivery/pumping/equipment/sitework', 'land/permits/design/engineering', 'MEP/services', 'cabinets/sanitary fixtures/appliances/furniture', 'unmodeled attic/floor insulation and any redesign material changes'])
    (ROOT / 'estimate.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    with (ROOT / 'costs.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    money = lambda n: f'${n:,.0f}'
    e = html.escape
    style = 'body{font:16px system-ui;max-width:1180px;margin:36px auto;padding:0 24px;color:#203332;background:#f6f4ed}table{border-collapse:collapse;width:100%;margin:24px 0}td,th{padding:10px;border-bottom:1px solid #cdd1c7;text-align:left;vertical-align:top}th{background:#e1e8df}small{font-size:13px}a{color:#136756}.total{font-size:24px}.note{background:#e8e5d8;padding:18px}'
    page = [f'<!doctype html><html><meta charset="utf-8"><title>Family-wing material takeoff</title><style>{style}</style><body>', '<h1>Family-wing material takeoff — #890</h1>', '<p>Quantities extracted read-only from theoriginal construction-scene components. Presentation copies are excluded. Source .blend SHA256: <small>' + q['blend_sha256'] + '</small>.</p>', '<p class="total">Structural core: ' + money(core['low_usd']) + '–' + money(core['high_usd']) + '<br>Broader fabric + basic finishes: ' + money(allcost['low_usd']) + '–' + money(allcost['high_usd']) + '</p>', '<p class="note">Dated price-snapshot comparison; see source dates below. Not a local supplier quote or total house-build cost. Framing stock and spacing come from the selected native profile, shown below. US lumber comparisons use actual material volume; nominal labels are not actual section dimensions. No structural substitution is specified. Most ranges beyond lumber/panels/concrete/metal are explicit budgeting allowances.</p>', '<h2>Measured quantity summary</h2><table><tr><th>Material</th><th>Net modeled quantity</th></tr>']
    summary = [('Exterior '+ext['label']+' stock equivalent', f"{ext['length_m']:,.1f} linear m / {ext['volume_m3']:.3f} m³"), ('Interior '+inside['label']+' stock equivalent', f"{inside['length_m']:,.1f} linear m / {inside['volume_m3']:.3f} m³"), ('Roof framing', f'{roof:.3f} m³;rafters plus ties/gable members/ridges/valleys'), ('Engineered floor joists', f"{g['Floors: engineered I-joist upper flanges']['length_m']:,.1f} linear m across modeled span segments"), ('Total timber-tagged material', f"{q['total_timber_m3']:.3f} m³; includes I-joist flanges, excludes OSB webs and finish-material tags"), ('Foundation concrete union', f"{q['foundation_union_m3']:.3f} m³"), ('Subfloor / wall OSB / roof OSB', f"{g['Panels: 22mm subfloor']['area_m2']:.1f} / {g['Panels: 12mm wall sheathing']['area_m2']:.1f} / {g['Panels: 18mm roof sheathing']['area_m2']:.1f} m²"), ('Wall / ceiling lining', f"{g['Lining: walls']['area_m2']:.1f} / {g['Lining: ceilings']['area_m2']:.1f} m²")]
    fp=q['framing_profile']
    summary.insert(0,('Framing system / stud / joist / rafter spacing',fp['system']+': '+' / '.join(fp['spacing_labels'][r] for r in ('stud','joist','rafter'))))
    if fp['system']=='us':
        summary[1]=('Exterior '+ext['label']+' stock equivalent',f"{ext['length_ft']:,.1f} linear ft / {ext['volume_m3']:.3f} m³")
        summary[2]=('Interior '+inside['label']+' stock equivalent',f"{inside['length_ft']:,.1f} linear ft / {inside['volume_m3']:.3f} m³")
    page += ['<tr><td>' + e(a) + '</td><td>' + e(b) + '</td></tr>' for a, b in summary]
    page += ['</table><p>Stock equivalents are based on installed volume: they are not purchased board counts. Geometric fragments around corners and beam cuts are not separate stock boards. Roof long members, grades, joints and load paths remain conceptual and could change considerably after real engineering.</p><h2>Cost assumptions and arithmetic</h2><table><tr><th>Item</th><th>Budget quantity<br><small>includes waste</small></th><th>Unit USD</th><th>Subtotal</th><th>Basis</th></tr>']
    for r in rows:
        page.append('<tr><td>' + e(r['item']) + '</td><td>' + f"{r['budget_quantity']:,.1f} " + e(r['unit']) + f"<br><small>{r['waste_percent']:g}% allowance</small>" + '</td><td>' + money(r['unit_low_usd']) + '–' + money(r['unit_high_usd']) + '</td><td>' + money(r['low_usd']) + '–' + money(r['high_usd']) + '</td><td><small>' + e(r['basis']) + '</small></td></tr>')
    page += ['</table><h2>Scope and limits</h2><p>Excluded: ' + e(', '.join(result['exclusions'])) + '. No supplier order or model change was made. Timber volumes sum modeled pieces; roof joints are not shop-cut boolean joints. Concrete overlaps between pads/strip footings are removed by an independent3D rectangle-union takeoff. Roof panel areas use actual sloped faces. Floor I-joists are charged once as purchased assemblies, not as separately purchased flange/web meshes.</p><h2>Price references</h2><ul>']
    page += [f'<li><a href="{e(url)}">{e(name)}</a> — {e(note)}</li>' for name, url, note in SOURCES]
    page += ['</ul><p>Files: components.csv (all original source parts), quantities.json, costs.csv, estimate.json. Scripts: takeoff.py (Blender5, no save) and price_takeoff.py (ordinary Python, local reports only).</p></body></html>']
    (ROOT / 'estimate.html').write_text('\n'.join(page), encoding='utf-8')
    print(json.dumps({'groups': totals, 'structural_core': core, 'broader_fabric': allcost}, indent=2))
