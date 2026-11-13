#!/usr/bin/env python3
"""Import only human-cleared HTTPS portraits with source, credit and license.
CSV: character_id,image_url,source_url,license,credit,approved_by
Do not infer image permissions from publicly accessible URLs.
"""
from __future__ import annotations
import argparse,csv,ipaddress,sqlite3
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]

def public_https(value:str)->bool:
    try:
        p=urlsplit(value.strip())
        if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):return False
        host=p.hostname.rstrip('.').lower()
        if host in ('localhost','localhost.localdomain') or host.endswith(('.local','.internal')):return False
        try:
            ip=ipaddress.ip_address(host)
            return ip.is_global
        except ValueError:
            return '.' in host and all(host.split('.'))
    except ValueError:return False

def run(csv_path:Path,db_path:Path,dry_run:bool=False):
    with csv_path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        required={'character_id','image_url','source_url','license','credit','approved_by'}
        if not required.issubset(reader.fieldnames or []):raise ValueError('Manifest is missing required columns')
        rows=[{k:(r.get(k) or '').strip() for k in required} for r in reader]
    if len({r['character_id'] for r in rows})!=len(rows):raise ValueError('Duplicate character IDs in manifest')
    for i,r in enumerate(rows,2):
        if not r['character_id'] or not all(r[k] for k in ('license','credit','approved_by')):
            raise ValueError(f'Row {i}: license, credit, reviewer and character ID required')
        if not public_https(r['image_url']) or not public_https(r['source_url']):
            raise ValueError(f'Row {i}: image/source must be public HTTPS URLs')
    with sqlite3.connect(db_path) as db:
        db.execute('PRAGMA foreign_keys=ON')
        ids={r[0] for r in db.execute('SELECT id FROM characters')}
        unknown=[r['character_id'] for r in rows if r['character_id'] not in ids]
        if unknown:raise ValueError(f'Unknown character IDs: {unknown[:10]}')
        if not dry_run:
            for r in rows:
                db.execute("""UPDATE characters SET portrait_url=?,portrait_source_url=?,portrait_license=?,portrait_credit=?,
                   portrait_status='approved',updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                   (r['image_url'],r['source_url'],r['license'],r['credit']+' (approved by '+r['approved_by']+')',r['character_id']))
            db.commit()
    print(f'Validated {len(rows)} rights-reviewed image records. Applied: {not dry_run}.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('csv_file',type=Path)
    p.add_argument('--database',type=Path,default=ROOT/'data/ukiyora_characters.sqlite')
    p.add_argument('--dry-run',action='store_true')
    a=p.parse_args();run(a.csv_file,a.database,a.dry_run)
