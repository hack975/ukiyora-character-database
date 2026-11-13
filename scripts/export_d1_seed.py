#!/usr/bin/env python3
"""Export current SQLite records as safe Cloudflare D1 SQL seed statements.
Usage: python scripts/export_d1_seed.py --input data/ukiyora_characters.sqlite --output db/seed.sql
"""
import sqlite3,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TABLES=['series','characters','appearances','external_identifiers','character_forms','feats_ledger','source_attributions']
def literal(x):
    if x is None: return 'NULL'
    if isinstance(x,(float,int)):return str(x)
    return "'"+str(x).replace("'","''")+"'"
def export(dbpath,output):
    db=sqlite3.connect(dbpath)
    with open(output,'w',encoding='utf-8') as f:
        f.write('-- Generated Ukiyora D1 seed; run after db/schema.sql\n')
        for table in TABLES:
            names=[r[1] for r in db.execute(f'PRAGMA table_info({table})')]
            # Keep sqlite-generated timestamps unless present in dump.
            cols=','.join('"'+n+'"' for n in names)
            cur=db.execute(f'SELECT {cols} FROM {table}')
            for row in cur:
                f.write(f'INSERT OR IGNORE INTO {table}({cols}) VALUES ('+','.join(map(literal,row))+');\n')
        f.write('DELETE FROM character_search_fts;\n')
        f.write('''INSERT INTO character_search_fts(character_id,name,series_title,aliases)
SELECT c.id,c.name,COALESCE(group_concat(s.name,' '),''),COALESCE((SELECT group_concat(value,' ') FROM json_each(c.aliases_json)),'')
FROM characters c LEFT JOIN appearances a ON a.character_id=c.id
LEFT JOIN series s ON s.id=a.series_id GROUP BY c.id;\n''')
    db.close()
    print(output,output.stat().st_size,'bytes')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=ROOT/'data/ukiyora_characters.sqlite');p.add_argument('--output',type=Path,default=ROOT/'db/seed.sql');a=p.parse_args();export(a.input,a.output)
