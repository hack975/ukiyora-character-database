#!/usr/bin/env python3
"""Opt-in import of local fadhilakbar anime-characters-dataset CSV.
The advertised CC BY 4.0 license applies to the dataset; verify upstream rights and
retain attribution before deployment. This file does not download or scrape data.

Dataset: https://huggingface.co/datasets/fadhilakbar/anime-characters-dataset
Expected columns: character_name, japanese_name, anime_name, character_source,
anime_source, role, and optional others.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,sqlite3,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_database import rebuild_fts

def stable_id(prefix,*values):
    value='|'.join(unicodedata.normalize('NFKC',str(v)).casefold().strip() for v in values)
    return prefix+'_'+hashlib.sha1(value.encode('utf8')).hexdigest()[:16]

def importer(path:Path,dbpath:Path,limit:int|None=None):
    if not dbpath.exists(): raise SystemExit('Build the starter database first: python scripts/build_database.py')
    conn=sqlite3.connect(dbpath)
    required={'character_name','anime_name'}
    processed=0; skipped=0
    with path.open(newline='',encoding='utf-8-sig') as stream:
        reader=csv.DictReader(stream)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('The CSV does not contain character_name and anime_name columns.')
        with conn:
            conn.execute('''INSERT OR REPLACE INTO source_attributions(id,name,url,license,license_url,remarks)
              VALUES(?,?,?,?,?,?)''',('hf_fadhilakbar','fadhilakbar/anime-characters-dataset',
              'https://huggingface.co/datasets/fadhilakbar/anime-characters-dataset',
              'CC BY 4.0','https://creativecommons.org/licenses/by/4.0/',
              'Character/anime appearance metadata; imported by Ukiyora with filtering and deduplication. Upstream intellectual-property restrictions must also be checked.'))
            for item in reader:
                anime=(item.get('anime_name') or '').strip(); name=(item.get('character_name') or '').strip()
                if not anime or not name or len(name)>500 or len(anime)>500:
                    skipped+=1;continue
                cs=(item.get('character_source') or '').strip()
                sourceKey=cs if cs.startswith('https://') else (anime+'|'+name)
                sid=stable_id('ser',anime)
                cid=stable_id('chr_ext',sourceKey)
                conn.execute('INSERT OR IGNORE INTO series(id,name,source_kind,source_url) VALUES(?,?,?,?)',
                  (sid,anime,'hf_fadhilakbar',(item.get('anime_source') or '').strip() or None))
                conn.execute('''INSERT OR IGNORE INTO characters
                 (id,name,japanese_name,source_kind,source_ref,profile_status,portrait_status)
                 VALUES(?,?,?,?,?,'unverified','missing')''',
                  (cid,name,(item.get('japanese_name') or '').strip() or None,'hf_fadhilakbar',cs or None))
                conn.execute('INSERT OR IGNORE INTO appearances(character_id,series_id,role,source_ref) VALUES(?,?,?,?)',
                    (cid,sid,(item.get('role') or '').strip() or None,cs or None))
                if cs.startswith('https://'):
                    prov='anilist' if 'anilist.co/' in cs else ('myanimelist' if 'myanimelist.net/' in cs else 'source')
                    conn.execute('''INSERT OR IGNORE INTO external_identifiers(character_id,provider,external_ref,source_url)
                     VALUES(?,?,?,?)''',(cid,prov,cs,cs))
                processed+=1
                if limit and processed>=limit:break
            rebuild_fts(conn)
    conn.close()
    print(json.dumps({'processed':processed,'skipped':skipped,'database':str(dbpath),'note':'All imported characters unverified. No images or forms inferred.'},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('csv_file',type=Path)
    p.add_argument('--database',type=Path,default=ROOT/'data/ukiyora_characters.sqlite')
    p.add_argument('--limit',type=int,default=None)
    a=p.parse_args()
    importer(a.csv_file,a.database,a.limit)
