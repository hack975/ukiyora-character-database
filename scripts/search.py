#!/usr/bin/env python3
import argparse,sqlite3,re
from pathlib import Path
DB=Path(__file__).resolve().parents[1]/'data/ukiyora_characters.sqlite'
p=argparse.ArgumentParser();p.add_argument('query');p.add_argument('--limit',type=int,default=15);args=p.parse_args()
tokens=re.findall(r'\w+',args.query,flags=re.UNICODE)[:8]
if not tokens: raise SystemExit('Enter a character name or series title')
fts=' AND '.join('"'+t+'"*' for t in tokens)
with sqlite3.connect(DB) as db:
    rows=db.execute('''WITH hits AS (SELECT character_id, bm25(character_search_fts) AS score
 FROM character_search_fts WHERE character_search_fts MATCH ? ORDER BY score LIMIT ?)
 SELECT c.id,c.name,s.name,(SELECT COUNT(*) FROM character_forms f WHERE f.character_id=c.id) AS forms
 FROM hits JOIN characters c ON c.id=hits.character_id JOIN appearances a ON a.character_id=c.id
 JOIN series s ON s.id=a.series_id ORDER BY hits.score,c.name''',(fts,max(1,min(args.limit,50)))).fetchall()
    for r in rows: print(f'{r[1]} | {r[2]} | {r[3]} form candidates | {r[0]}')
    if not rows: print('No local results. Catalogue expansion or verification may be needed.')
