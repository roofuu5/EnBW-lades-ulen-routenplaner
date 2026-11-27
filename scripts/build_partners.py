"""Holt das Ladesäulenregister der Bundesnetzagentur (CC BY 4.0) und schreibt partners.json:
alle öffentlichen Schnellladeorte ab 50 kW, die nicht von EnBW oder EnBW-Töchtern betrieben werden.
Aufruf: python3 scripts/build_partners.py [lokale_datei.json]"""
import json, re, sys, math, urllib.request, datetime

URL = 'https://ladesaeulenregister.bnetza.de/els/service/public/v1/chargepoints'
MIN_KW = 50
SKIP_OP = re.compile(r'enbw|smatrics|naturenergie|tesla', re.I)  # EnBW-Konzern steckt schon in der App, Tesla läuft nicht über EnBW

def load():
    if len(sys.argv) > 1:
        return json.load(open(sys.argv[1], encoding='utf-8'))
    req = urllib.request.Request(URL, headers={'Accept': 'application/json', 'User-Agent': 'enbw-ladestopp (github.com/roofuu5)'})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)

def num(v):
    try: return float(str(v).replace(',', '.'))
    except Exception: return None

def evse_kw(e):
    """Leistung eines Ladepunkts, falls im Datensatz vorhanden."""
    if not isinstance(e, dict): return None
    for k in ('max_electric_power', 'max_power', 'power', 'nominal_power', 'maxElectricPower'):
        if k in e and num(e[k]): return num(e[k])
    best = None
    for c in e.get('connectors') or e.get('plugs') or []:
        if isinstance(c, dict):
            for k in ('max_electric_power_connector', 'max_electric_power', 'max_power', 'power'):
                if num(c.get(k)): best = max(best or 0, num(c.get(k)))
    return best

def base_points(path='index.html'):
    txt = open(path, encoding='utf-8').read(); i = txt.find('const STATIONS=')
    if i < 0: return []
    arr, _ = json.JSONDecoder().raw_decode(txt, i + len('const STATIONS='))
    return [(s[1], s[2]) for s in arr]

def main():
    d = load()
    rows = d.get('chargingStations') if isinstance(d, dict) else d
    if not rows: sys.exit('Keine Daten im Register gefunden: ' + str(list(d)[:10] if isinstance(d, dict) else type(d)))
    print('Register:', len(rows), 'Ladeeinrichtungen. Beispiel-Schlüssel:', sorted(rows[0].keys()))
    print('Beispiel-EVSE:', json.dumps((rows[0].get('evses') or [None])[0], ensure_ascii=False)[:400])
    base = base_points()
    grid = {}
    for la, lo in base: grid.setdefault((round(la, 3), round(lo, 3)), []).append((la, lo))
    def near_base(la, lo):
        for dy in (-0.001, 0, 0.001):
            for dx in (-0.001, 0, 0.001):
                for b in grid.get((round(la + dy, 3), round(lo + dx, 3)), []):
                    if abs(b[0] - la) < 0.0006 and abs(b[1] - lo) < 0.0009: return True
        return False
    sites, cells, skipped = [], {}, {'kw': 0, 'op': 0, 'status': 0, 'access': 0, 'coord': 0, 'enbw_ort': 0}
    for r in rows:
        op = ((r.get('operator') or {}).get('displayName') or (r.get('operator') or {}).get('companyName') or '').strip()
        kw = num(r.get('max_electric_power_station')) or 0
        co = r.get('coordinates') or {}
        la, lo = num(co.get('latitude')), num(co.get('longitude'))
        st = r.get('status') or {}
        oper = st.get('operational') if isinstance(st, dict) else st
        acc = str(r.get('access_restriction') or '')
        if kw < MIN_KW: skipped['kw'] += 1; continue
        if SKIP_OP.search(op): skipped['op'] += 1; continue
        if oper is False or re.search(r'au(ss|ß)er betrieb|false|stillgelegt', str(oper), re.I): skipped['status'] += 1; continue
        if re.search(r'privat|nur für kunden|mitarbeiter', acc, re.I): skipped['access'] += 1; continue
        if not la or not lo or not (47 < la < 55.2 and 5.5 < lo < 15.2): skipped['coord'] += 1; continue
        if near_base(la, lo): skipped['enbw_ort'] += 1; continue
        evses = r.get('evses') or []
        pts = {}
        for e in evses:
            k = round(evse_kw(e) or kw)
            pts[k] = pts.get(k, 0) + 1
        if not pts: pts[round(kw)] = 1
        key = (op, round(la, 3), round(lo, 3))
        hit = None
        for s in cells.get(key, []):
            if abs(s['la'] - la) < 0.0006 and abs(s['lo'] - lo) < 0.0009: hit = s; break
        if hit:
            hit['kw'] = max(hit['kw'], kw)
            for k, n in pts.items(): hit['pts'][k] = hit['pts'].get(k, 0) + n
            continue
        addr = ', '.join(x for x in [' '.join(x for x in [r.get('street'), r.get('house_no')] if x), ' '.join(x for x in [r.get('postal_code'), r.get('city')] if x)] if x)
        s = {'id': r.get('id'), 'la': la, 'lo': lo, 'kw': kw, 'addr': addr + ', DE', 'loc': (r.get('location_description') or '').strip(), 'op': op, 'pts': pts}
        cells.setdefault(key, []).append(s); sites.append(s)
    out = [[-int(s['id'] or i + 1), round(s['la'], 5), round(s['lo'], 5), round(s['kw']), s['addr'],
            (s['loc'] or '')[:80], s['op'], 2, sorted([[k, n] for k, n in s['pts'].items()], reverse=True)] for i, s in enumerate(sites)]
    meta = {'generatedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
            'source': 'Bundesnetzagentur, Ladesäulenregister, CC BY 4.0', 'count': len(out)}
    with open('partners.json', 'w', encoding='utf-8') as f:
        json.dump({'meta': meta, 'stations': out}, f, ensure_ascii=False, separators=(',', ':'))
    print('Ausgeschlossen:', skipped)
    print('Geschrieben: partners.json mit', len(out), 'Ladeorten von', len({s['op'] for s in sites}), 'Betreibern')
    if len(out) < 1000: sys.exit('Verdächtig wenige Ladeorte, breche ab')

main()
