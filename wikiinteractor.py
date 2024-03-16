import requests as r

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