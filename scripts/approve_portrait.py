#!/usr/bin/env python3
"""Attach a rights-cleared remote portrait URL to a character. No image downloading.
Use only after a human confirms image rights. Source, license and credit required.
"""
import argparse,sqlite3
from urllib.parse import urlparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--character-id',required=True)
p.add_argument('--image-url',required=True)
p.add_argument('--source-url',required=True)
p.add_argument('--license',required=True)
p.add_argument('--credit',required=True)
p.add_argument('--database',type=Path,default=ROOT/'data/ukiyora_characters.sqlite')
a=p.parse_args()
for label,val in [('image-url',a.image_url),('source-url',a.source_url)]:
    parsed=urlparse(val)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
        raise SystemExit(f'{label} must be a public HTTPS URL')
if not a.license.strip() or not a.credit.strip():
    raise SystemExit('Document image license and attribution before approval')
with sqlite3.connect(a.database) as db:
    res=db.execute('''UPDATE characters SET portrait_url=?,portrait_source_url=?,portrait_license=?,portrait_credit=?,
       portrait_status='approved',updated_at=CURRENT_TIMESTAMP WHERE id=?''',
       (a.image_url,a.source_url,a.license,a.credit,a.character_id))
    if res.rowcount!=1: raise SystemExit('Unknown character ID; no changes made.')
print('Approved rights-reviewed image URL for',a.character_id)
