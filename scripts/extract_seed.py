#!/usr/bin/env python3
"""Extract the original Ukiyora research PDF table into structured, unverified seed data.
Source: Ukiyora_Anime_Characters_and_Forms.pdf (user-supplied reference).
"""
from __future__ import annotations
import argparse, re, json, hashlib, unicodedata
from pathlib import Path
import fitz

SERIES_RE = re.compile(r'(.+?)\s*[•·]\s*(\d+) characters\s*[•·]\s*(\d+) with form notes')
PENDING = 'Standard/unspecified; form research pending'

def stable_id(prefix, *parts):
    v='|'.join(unicodedata.normalize('NFKC',p).strip().casefold() for p in parts)
    return f'{prefix}_{hashlib.sha1(v.encode()).hexdigest()[:16]}'

def parse(pdf):
    doc=fitz.open(pdf); series=None; rows=[]; pending=None; series_counts={}
    def flush():
        nonlocal pending
        if pending:
            pending['forms_raw']=' '.join(pending['form_parts']).strip()
            del pending['form_parts']; rows.append(pending); pending=None
    for page in doc:
        for block in sorted((b for b in page.get_text('dict')['blocks'] if 'lines' in b),key=lambda b:b['bbox'][1]):
            ln=[]
            for line in block['lines']:
                text=''.join(s['text'] for s in line['spans']).strip()
                if text: ln.append((round(line['bbox'][0]),text))
            full=' '.join(t for _,t in ln)
            m=SERIES_RE.search(full)
            if m:
                flush(); series=m.group(1).strip(); series_counts[series]=int(m.group(2)); continue
            if not series or not ln: continue
            a=[t for x,t in ln if 55 <= x < 130]
            b=[t for x,t in ln if x>=200]
            if a and b and a[0] != 'CHARACTER':
                flush(); pending={'series':series,'name':' '.join(a),'form_parts':b}
            elif b and pending and not a and 42 < block['bbox'][1]<795:
                pending['form_parts'].extend(b)
            elif a and not b and a[0] != 'CHARACTER' and 42 < block['bbox'][1]<795:
                # Long character names can occupy their own block; the form text follows at x=226.
                flush(); pending={'series':series,'name':' '.join(a),'form_parts':[]}
    flush()
    return rows,series_counts

def to_catalogue(rows):
    character_list=[]; form_list=[]; seen=set(); series_data={}
    for row in rows:
        s=row['series']; n=row['name']; raw=row['forms_raw']
        sid=stable_id('ser',s); cid=stable_id('chr',s,n)
        series_data[sid]={'id':sid,'name':s,'provenance':'ukiyora_research_index_2026_11_13'}
        if cid in seen:
            continue
        seen.add(cid)
        cf=[]
        if raw and raw!=PENDING:
            for order, form in enumerate(raw.split(' / ')):
                name=form.strip()
                if not name: continue
                formid=stable_id('frm',s,n,name)
                kind='state'
                if name.casefold() in ('base','human','normal','standard','default','arrancar base','base form'):
                    kind='baseline'
                elif any(k in name.casefold() for k in ['(ability','ability,','technique','special move']):
                    kind='ability_note'
                elif '(manga)' in name.casefold() or '(anime)' in name.casefold():
                    kind='continuity_note'
                form_list.append({'id':formid,'character_id':cid,'label':name,'kind':kind,
                   'continuity':'unspecified','verification_status':'research_candidate',
                   'source_ref':'Ukiyora_Anime_Characters_and_Forms.pdf', 'order':order})
                cf.append(formid)
        character_list.append({'id':cid,'name':n,'series_id':sid,'series_name':s,
          'japanese_name':None,'aliases':[], 'profile_status':'unverified',
          'image_url':None,'image_source_url':None,'image_license':None,
          'image_credit':None,'image_review_status':'missing',
          'source':'Ukiyora_Anime_Characters_and_Forms.pdf', 'forms_status':'candidates_unverified' if cf else 'research_pending',
          'form_ids':cf})
    return list(sorted(series_data.values(),key=lambda x:x['name'])),character_list,form_list

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('pdf');ap.add_argument('--out',default='data');args=ap.parse_args()
    rows,counts=parse(args.pdf); series,chars,forms=to_catalogue(rows)
    print('rows',len(rows),'series',len(series),'characters',len(chars),'forms',len(forms),'expected',sum(counts.values()))
    for s,n in counts.items():
        actual=sum(r['series']==s for r in rows)
        if actual!=n: print('MISMATCH',s,'expected',n,'got',actual)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    for name,data in [('series',series),('characters',chars),('forms',forms)]:
        (out/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'stats.json').write_text(json.dumps({'series':len(series),'characters':len(chars),'form_candidates':len(forms),'source':'Ukiyora research catalogue, not canon-verified'},indent=2)+'\n')
