"""Authorized read-only inspection snapshots. Never import or print source bodies.

Owner confirmed seven-language community permission 2026-10-25. Source access
remains subject to robots/HTTP restrictions. Snapshots belong in private artifacts.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from scripts.automatic_sources import new_session, discover, get_page, error_metadata
from scripts.watch_official_updates import fetch_archive, URL
from scripts.update_candidate_gate import sha256
from bs4 import BeautifulSoup
import re


def inspect_layout(raw):
    soup=BeautifulSoup(raw,'html.parser')
    for node in soup.select('script,style,noscript'): node.decompose()
    def selector(node):
        parts=[]
        while getattr(node,'name',None) and node.name!='[document]':
            part=node.name
            if node.get('id') and re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_-]*',node['id']):
                parts.insert(0,'#'+node['id']);break
            siblings=[s for s in node.parent.children if getattr(s,'name',None)==node.name] if node.parent else [node]
            if len(siblings)>1: part+=':nth-of-type('+str(siblings.index(node)+1)+')'
            parts.insert(0,part);node=node.parent
        return ' > '.join(parts)
    quotes=[]
    markers=('дорогие дети','drahé deti','dear children','дорогі діти','dārgie bērni','draga djeco','дарагія дзеці')
    for node in soup.select('p,blockquote'):
        text=node.get_text('\n',strip=True)
        if len(text)>150 and any(m in text.casefold()[:80] for m in markers):
            quotes.append(dict(selector=selector(node),parent_selector=selector(node.parent),
                chars=len(text),sha256=sha256(text.encode()),opening=text[:24],closing=text[-48:]))
    headings=[dict(tag=n.name,selector=selector(n),text=n.get_text(' ',strip=True)[:160]) for n in soup.select('h1,h2,h3') if len(n.get_text(' ',strip=True))<180]
    return dict(html_language=soup.html.get('lang') if soup.html else None,headings=headings[:60],quote_candidates=quotes[:12])


def probe(output, policies):
    output.mkdir(parents=True,exist_ok=True)
    report=dict(checked_at=datetime.now(timezone.utc).isoformat(), mode='authorized_read_only', official={}, sources={})
    try:
        html=fetch_archive().encode('utf-8')
        (output/'official.html').write_bytes(html)
        report['official']=dict(status='fetched',url=URL,sha256=sha256(html),snapshot='official.html',layout=inspect_layout(html))
    except Exception as error:
        report['official']=dict(status='blocked',url=URL,**error_metadata(error))
    session=new_session()
    for lang,policy in policies['languages'].items():
        if not policy.get('origin'):
            report['sources'][lang]=dict(status='no_current_source');continue
        entry=dict(status='checking',articles=[]);report['sources'][lang]=entry
        try:
            posts=discover(session,policy)
            # Include the newest candidate even before today's message appears;
            # a previous real page is necessary to validate parser structure.
            posts=sorted(posts,key=lambda p:p['published'],reverse=True)[:3]
            entry.update(status='discovered',count=len(posts))
            for post in posts:
                article=dict(url=post['url'],published_at=post['published'],source_id=post.get('guid') or post['url'])
                entry['articles'].append(article)
                try:
                    raw=get_page(session,post['url'],policy['origin'])
                    name=lang+'-'+sha256(raw)[:16]+'.html'
                    (output/name).write_bytes(raw)
                    article.update(status='fetched',snapshot=name,raw_sha256=sha256(raw),bytes=len(raw),layout=inspect_layout(raw))
                except Exception as error:
                    article.update(status='blocked',**error_metadata(error))
        except Exception as error:
            entry.update(status='blocked',**error_metadata(error))
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2)) # Structure, dates and short boundary excerpts only; never full bodies.
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('work/fulltext-probe'))
    a=p.parse_args();probe(a.output,json.loads(Path('research/automatic-source-policies.json').read_text()))
