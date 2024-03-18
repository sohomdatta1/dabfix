import requests as r
from replicadb import get_conn
import re
import random

def get_raw_text(pagename, proj):
    resp = r.post(f'https://{proj}.wikipedia.org/w/api.php', data={
                "action": "query",
                "format": "json",
                "prop": "revisions",
                "titles": pagename,
                "formatversion": "2",
                "rvprop": "content",
                "rvslots": "*"
            }, timeout=50, headers={'X-Api-User-Agent': 'toolforge-dabfix/1.0'})
    data = resp.json()
    if 'missing' in data['query']['pages'][0]:
        return {
            "success": False
        }
    return {
        "text": data["query"]['pages'][0]["revisions"][0]["slots"]["main"],
        "success": True
    }

def get_parsed_wikitext(pagename, proj):
    resp = r.post(f'https://{proj}.wikipedia.org/w/api.php', data={
        "action": "parse",
        "format": "json",
        "page": pagename,
        "prop": "text",
        "formatversion": "2"
    }, timeout=50, headers={'X-Api-User-Agent': 'toolforge-dabfix/1.0'})
    data = resp.json()
    if 'parse' not in data:
        return {
            "success": False
        }
    return {
        "text": data["parse"]["text"],
        "success": True
    }

def getdabs_w(proj: str, pagename: str):
    with get_conn(f'{proj}wiki') as conn:
        with conn.cursor() as cursor:
            pagename=pagename.replace(' ', '_')
            cursor.execute("select page_id from page where page_title = %s and page_namespace = 0", (pagename))
            res = cursor.fetchall()
            pageid = res[0][0]
            print(pageid)
            cursor.execute("""SELECT page_title, pp_propname
                            FROM page LEFT 
                           JOIN page_props ON pp_page = page_id
                           AND pp_propname = 'disambiguation'
                           WHERE page_namespace = 0 
                           AND page_title IN 
                           (select pl_title 
                           from pagelinks l 
                           where l.pl_namespace = 0 
                           and l.pl_from = %s) 
                           AND pp_propname = 'disambiguation'""", (str(pageid)))
            rows = cursor.fetchall()
            resp = []
            for i in rows:
                resp.append(i[0].decode('utf-8'))
            return resp
        
def makesenseofedits(proj, pagename, edits):
    text = get_raw_text(pagename, proj)['text']['content']
    dabs = getdabs_w(proj, pagename)
    print(dabs)
    for i in range(len(dabs)):
        if i < len(edits) and edits[i]:
            text = re.sub( f"\\[\\[{dabs[i].replace('_', '[ _]')}", f'[[{edits[i]}', text )
    print(text)
    return text

def editwikitext(proj: str, pagename: str, auth, edits, summary: str):
    text = makesenseofedits(proj, pagename, edits)

    R = r.get(url=f'https://{proj}.wikipedia.org/w/api.php', params={
        "action": "query",
        "meta": "tokens",
        "format": "json"
    }, auth=auth, timeout=50)
    DATA = R.json()
    CSRF_TOKEN = DATA['query']['tokens']['csrftoken']

    resp = r.post(f'https://{proj}.wikipedia.org/w/api.php', data={
        "action": "edit",
        "title": pagename,
        "text": text,
        "token": CSRF_TOKEN,
        "summary": summary + ' (dabfix)',
        "format": "json",
    },
    auth=auth,
    timeout=50)
    return resp.json()

def generaterandomdisambigs(proj):
    resp  = r.post(f'https://{proj}.wikipedia.org/w/api.php', data={
        "action": "query",
        "format": "json",
        "list": "querypage",
        "formatversion": "2",
        "qppage": "DisambiguationPageLinks",
        "qplimit": "500"
    }, timeout=50, headers={'X-Api-User-Agent': 'toolforge-dabfix/1.0'})
    data = resp.json()
    return random.choice(data['query']['querypage']["results"])["title"]
