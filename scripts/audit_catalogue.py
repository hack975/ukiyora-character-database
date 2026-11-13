#!/usr/bin/env python3
"""Report catalogue coverage and integrity without modifying any records."""
from __future__ import annotations
import argparse,json,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def inspect(db_path:Path):
    with sqlite3.connect(db_path) as db:
        db.row_factory=sqlite3.Row
        count=lambda q: db.execute(q).fetchone()[0]
        duplicate_names=[dict(x) for x in db.execute("""SELECT lower(trim(name)) AS name_key,COUNT(*) AS records,
            GROUP_CONCAT(id, ',') AS ids FROM characters GROUP BY lower(trim(name))
            HAVING COUNT(*)>1 ORDER BY records DESC,name_key LIMIT 30""")]
        duplicated_forms=[dict(x) for x in db.execute("""SELECT character_id, lower(trim(label)) AS form_key,
            continuity,COUNT(*) AS count FROM character_forms
            GROUP BY character_id,lower(trim(label)),continuity HAVING COUNT(*)>1 LIMIT 30""")]
        broken_fts=count("""SELECT COUNT(*) FROM characters c WHERE NOT EXISTS
            (SELECT 1 FROM character_search_fts f WHERE f.character_id=c.id)""")
        orphan_forms=count("""SELECT COUNT(*) FROM character_forms f LEFT JOIN characters c ON c.id=f.character_id
            WHERE c.id IS NULL""")
        bad_approved_images=count("""SELECT COUNT(*) FROM characters WHERE portrait_status='approved' AND
            (portrait_url NOT LIKE 'https://%' OR COALESCE(TRIM(portrait_credit),'')='' OR
             COALESCE(TRIM(portrait_license),'')='' OR COALESCE(TRIM(portrait_source_url),'')='')""")
        return {
            'series':count('SELECT COUNT(*) FROM series'),
            'characters':count('SELECT COUNT(*) FROM characters'),
            'appearances':count('SELECT COUNT(*) FROM appearances'),
            'candidate_forms':count("SELECT COUNT(*) FROM character_forms WHERE verification_status='research_candidate'"),
            'verified_forms':count("SELECT COUNT(*) FROM character_forms WHERE verification_status='verified'"),
            'verified_feats':count("SELECT COUNT(*) FROM feats_ledger WHERE verification_status='verified'"),
            'approved_portraits':count("SELECT COUNT(*) FROM characters WHERE portrait_status='approved'"),
            'unverified_characters':count("SELECT COUNT(*) FROM characters WHERE profile_status='unverified'"),
            'broken_search_entries':broken_fts,
            'orphan_forms':orphan_forms,
            'invalid_approved_portraits':bad_approved_images,
            'duplicate_name_examples_not_automatically_merged':duplicate_names,
            'duplicate_form_candidates':duplicated_forms,
            'warning':'This is an identity discovery catalogue. Candidate forms and unverified characters cannot produce battle verdicts.'
        }

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--database',type=Path,default=ROOT/'data/ukiyora_characters.sqlite')
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    result=inspect(a.database)
    output=json.dumps(result,indent=2,ensure_ascii=False)
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(output+'\n',encoding='utf-8')
    print(output)
    if any(result[k] for k in ('broken_search_entries','orphan_forms','invalid_approved_portraits')):
        raise SystemExit('Catalogue integrity issue detected')
