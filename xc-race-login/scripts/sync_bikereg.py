"""Refresh public BikeReg registrations; never change officer-owned records."""
import copy
import datetime
import json
import pathlib
import re
import shutil
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATEGORIES = ['Pro Men','Cat 1 Men','Collegiate Cat 1/2 Men','Pro Women','Cat 1 Women','Collegiate Cat 1/2 Women','Cat 2 Women','Collegiate Cat 2/3 Women','Junior Women 15-16','Junior Women 17-18','Cat 3 Women','Master’s Women 40-49','Master’s Women 50-59','Master’s Women 60+','Junior Boys 13-14','Junior Boys 9-12','Junior Girls 13-14','Junior Girls 9-12','Cat 2 Men','Junior Men 15-16','Junior Men 17-18','Collegiate Cat 2 Men','Master’s Men 40-49','Master’s Men 50-59','Master’s Men 60+','Collegiate Cat 3 Men','Cat 3 Men','Women’s Open Short Track','Men’s Open Short Track']
IDS = set(range(962360, 962389))
SEED = re.compile(r'(<script id="seed" type="application/json">)(.*?)(</script>)', re.S)

def key(s):
    return ' '.join(s.strip().lower().split())

def team_match(team):
    t = key(team).replace('.', '')
    if re.search(r'arizona state|northern arizona|\basu\b|\bnau\b', t):
        return 'other'
    if t in {'university of arizona','univeristy of arizona','university of arizona cycling','ua cycling','u of a','uofa','u of a cycling','uarizona','uarizona cycling'}:
        return 'match'
    return 'review' if re.search(r'arizona|\bua\b|wildcat|univ.*ariz', t) else 'other'

def extract(response):
    categories = response.get('data', {}).get('AR_EventCategories')
    if response.get('errors') or not isinstance(categories, list) or len(categories) != len(IDS):
        raise ValueError('BikeReg returned errors or an incomplete category list; previous deployment is unchanged.')
    entries, review, seen, seen_entries = [], [], set(), set()
    for c in categories:
        cid = int(c['raceRecId'])
        if cid not in IDS or cid in seen or not isinstance(c.get('eventEntries'), list):
            raise ValueError('Unexpected BikeReg category format.')
        seen.add(cid)
        for e in c['eventEntries']:
            first, last = e.get('firstName'), e.get('lastName')
            if not isinstance(first, str) or not isinstance(last, str) or not first.strip() or not last.strip():
                raise ValueError('Unexpected rider format; refusing a partial update.')
            entry = dict(name=' '.join((first+' '+last).split()), team=str(e.get('teamName') or ''), category=CATEGORIES[cid-962360], date=str(e.get('entryDate') or ''))
            if len(entry['name']) > 100 or any(len(entry[f]) > 300 for f in ('team','category','date')):
                raise ValueError('Unexpected field length.')
            identity = (key(entry['name']), cid, key(entry['team']))
            if identity in seen_entries:
                continue
            seen_entries.add(identity)
            match = team_match(entry['team'])
            if match == 'match':
                entries.append(entry)
            elif match == 'review':
                review.append(entry)
    if not entries:
        raise ValueError('No team registrations returned; refusing to erase the previous snapshot.')
    return dict(eventId='76688', entries=entries, review=review, syncedAt=datetime.datetime.now(datetime.timezone.utc).isoformat())

def merge(seed, snapshot):
    result = copy.deepcopy(seed)
    result.update(entries=snapshot['entries'], review=snapshot['review'], syncedAt=snapshot['syncedAt'], source='BikeReg auto-update · '+snapshot['syncedAt'])
    known = {m['id'] for m in result['members']}
    for entry in snapshot['entries']:
        mid = key(entry['name'])
        if mid not in known:
            result['members'].append(dict(id=mid, name=entry['name'], volunteer='none', note=''))
            known.add(mid)
    result['members'].sort(key=lambda m: key(m['name']))
    return result

def build(html, snapshot):
    match = SEED.search(html)
    if not match:
        raise ValueError('Cannot find embedded dashboard data.')
    seed = json.loads(match[2])
    merged = merge(seed, snapshot)
    encoded = json.dumps(merged, ensure_ascii=False).replace('<', '\\u003c')
    return html[:match.start(2)] + encoded + html[match.end(2):]

def main():
    payload = {'operationName':'AR_GetWhosRegisteredEntries','variables':{'appType':'BIKEREG','categoryIds':sorted(IDS)},'extensions':{'persistedQuery':{'version':1,'sha256Hash':'4f2a7496c1456746dcb31cc651e74f7250f3a7ccb9af2e8b063d6d70e9832a8e'}}}
    request = urllib.request.Request('https://www.bikereg.com/api/supergraph/gql', data=json.dumps(payload).encode(), headers={'Content-Type':'application/json','User-Agent':'SonoranShredDashboard/1.0'})
    with urllib.request.urlopen(request, timeout=45) as response:
        snapshot = extract(json.load(response))
    html = build((ROOT/'index.html').read_text(), snapshot)
    output = ROOT/'public'
    output.mkdir(exist_ok=True)
    (output/'index.html').write_text(html)
    (output/'registrations.json').write_text(json.dumps(snapshot, ensure_ascii=False))
    (output/'.nojekyll').write_text('')
    for name in ('app.js', 'config.js'):
        shutil.copy2(ROOT/name, output/name)
    shutil.copytree(ROOT/'vendor', output/'vendor', dirs_exist_ok=True)
    print(f"Updated {len(snapshot['entries'])} team entries; {len(snapshot['review'])} entries need review.")

if __name__ == '__main__':
    main()
