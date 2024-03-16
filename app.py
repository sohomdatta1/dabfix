from flask import Flask, session, redirect, request, url_for, render_template
from replicadb import get_conn
from wikiinteractor import get_parsed_wikitext, get_raw_text
from dotenv import load_dotenv
import mwoauth
import os
import uuid

load_dotenv()

app = Flask(__name__, template_folder='templates')

app.secret_key = os.environ.get( 'SECRETKEY' ) if os.environ.get( 'SECRETKEY' ) else uuid.uuid4().hex

@app.route('/')
def index():
    if session.get('username'):
        print( session.get( 'username' ) )
        return render_template('index.html', username=session.get( 'username' ))
    return redirect('/tologin')

@app.route('/edit')
def edit():
    if session.get('username'):
        return render_template('edit.html', page=request.args.get('page'), proj=request.args.get('proj'), username=session.get( 'username' ) )
    return redirect('/tologin')

@app.route('/tologin')
def tologin():
    if session.get('username'):
        return redirect('/')
    return render_template('tologin.html')


@app.route("/api/getdabs/<proj>/<path:pagename>")
def getdabs(proj: str, pagename: str):
    with get_conn(f'{proj}wiki_p') as conn:
        with conn.cursor() as cursor:
            cursor.execute("select page_id from page where page_title = %s and page_namespace = 0;", pagename)
            res = cursor.fetchone()
            pageid = res[0]
            cursor.excute("""SELECT page_title, pp_propname
                            FROM page
                            LEFT JOIN page_props ON pp_page = page_id AND pp_propname = 'disambiguation'
                            WHERE page_namespace = 0
                            AND page_title IN (select pl_title
                            from pagelinks l
                            where l.pl_namespace = 0
                            and l.pl_from = %s)
                            AND pp_propname = 'disambiguation'""", pageid)
            rows = cursor.fetchall()
            resp = []
            for i in rows:
                resp.append(i[0])
            return resp

@app.route("/api/getraw/<proj>/<path:pagename>")
def getrawtext(proj: str, pagename: str):
    return get_raw_text(pagename, proj)

@app.route("/api/getparsed/<proj>/<path:pagename>")
def getparsedtext(proj: str, pagename: str):
    return get_parsed_wikitext(pagename, proj)


@app.route('/login')
def login():
    """Initiate an OAuth login.
    
    Call the MediaWiki server to get request secrets and then redirect the
    user to the MediaWiki server to sign the request.
    """
    consumer_token = mwoauth.ConsumerToken(
        os.environ.get('CONSUMER_KEY'), os.environ.get('CONSUMER_SECRET'))
    try:
        redirect_loc, request_token = mwoauth.initiate(
            'https://meta.wikimedia.org/w/index.php', consumer_token)
    except Exception:
        app.logger.exception('mwoauth.initiate failed')
        return redirect(url_for('index'))
    else:
        session['request_token'] = dict(zip(
            request_token._fields, request_token))
        return redirect(redirect_loc)


@app.route('/dabfix-oauth-callback')
def oauth_callback():
    if 'request_token' not in session:
        return redirect(url_for('index'))

    consumer_token = mwoauth.ConsumerToken(
        os.environ.get('CONSUMER_KEY'), os.environ.get('CONSUMER_SECRET'))

    try:
        access_token = mwoauth.complete(
            'https://meta.wikimedia.org/w/index.php',
            consumer_token,
            mwoauth.RequestToken(**session['request_token']),
            request.query_string)

        identity = mwoauth.identify(
            'https://meta.wikimedia.org/w/index.php', consumer_token, access_token)    
    except Exception as _:
        app.logger.exception('OAuth authentication failed')
    
    else:
        session['access_token'] = dict(zip(
            access_token._fields, access_token))
        session['username'] = identity['username']

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    """Log the user out by clearing their session."""
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)