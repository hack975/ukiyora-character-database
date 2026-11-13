#!/usr/bin/env python3
"""Build searchable SQLite DB from licensed/owned Ukiyora seed JSON.
Requires Python 3.10+; no third-party packages needed.
"""
from __future__ import annotations
import argparse,json,sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def build(destination:Path,base:Path=ROOT,force:bool=False):
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        if not force:
            raise FileExistsError(
                f"Refusing to replace {destination}; it might contain imported characters, "
                "reviewed feats or approved portraits. Use --output for a new file or --force "
                "only after backing up the existing database."
            )
        destination.unlink()
    db=sqlite3.connect(destination)
    db.executescript((base/'db/schema.sql').read_text(encoding='utf8'))
    ss=json.loads((base/'data/series.json').read_text(encoding='utf8'))
    cc=json.loads((base/'data/characters.json').read_text(encoding='utf8'))
    ff=json.loads((base/'data/forms.json').read_text(encoding='utf8'))
    with db:
        db.executemany('INSERT INTO series(id,name,source_kind) VALUES(?,?,?)',[(s['id'],s['name'],'ukiyora_seed') for s in ss])
        db.executemany('''INSERT INTO characters
            (id,name,japanese_name,aliases_json,profile_status,portrait_url,portrait_source_url,portrait_license,portrait_credit,portrait_status,source_kind,source_ref)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',[(c['id'],c['name'],c.get('japanese_name'),json.dumps(c['aliases'],ensure_ascii=False),c['profile_status'],c['image_url'],c['image_source_url'],c['image_license'],c['image_credit'],c['image_review_status'],'ukiyora_seed',c['source']) for c in cc])
        db.executemany('INSERT INTO appearances(character_id,series_id,source_ref) VALUES(?,?,?)',[(c['id'],c['series_id'],c['source']) for c in cc])
        db.executemany('''INSERT INTO character_forms(id,character_id,label,kind,continuity,verification_status,source_ref,sort_order)
            VALUES(?,?,?,?,?,?,?,?)''',[(f['id'],f['character_id'],f['label'],f['kind'],f['continuity'],f['verification_status'],f['source_ref'],f['order']) for f in ff])
        db.execute('''INSERT INTO source_attributions(id,name,url,license,remarks) VALUES (?,?,?,?,?)''',('ukiyora_forms_pdf','Ukiyora Character and Forms Research Index',None,'User-supplied research','Named forms are unverified editorial candidates.'))
        rebuild_fts(db)
    db.execute('PRAGMA optimize'); db.close()
    print(f'Built {destination} | {len(ss):,} series | {len(cc):,} characters | {len(ff):,} provisional forms')

def rebuild_fts(db):
    db.execute('DELETE FROM character_search_fts')
    db.execute('''INSERT INTO character_search_fts(character_id,name,series_title,aliases)
      SELECT c.id,c.name,COALESCE(group_concat(s.name, ' '),''),
             COALESCE((SELECT group_concat(value,' ') FROM json_each(c.aliases_json)),'')
      FROM characters c
      LEFT JOIN appearances a ON a.character_id=c.id
      LEFT JOIN series s ON s.id=a.series_id
      GROUP BY c.id''')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'data/ukiyora_characters.sqlite');p.add_argument('--force',action='store_true',help='Explicitly overwrite existing DB after backup');a=p.parse_args();build(a.output,force=a.force)
