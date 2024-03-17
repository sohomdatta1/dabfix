from flask import Flask, session, redirect, request, url_for, render_template
from requests_oauthlib import OAuth1
from replicadb import get_conn
from wikiinteractor import get_parsed_wikitext, get_raw_text, getdabs_w, editwikitext, generaterandomdisambigs
from dotenv import load_dotenv
import json
import mwoauth
import os
import uuid
import mwoauth.flask

load_dotenv()

app = Flask(__name__, template_folder='templates')

app.secret_key = os.environ.get( 'SECRETKEY' ) if os.environ.get( 'SECRETKEY' ) else uuid.uuid4().hex

@app.route('/')
def index():
    return render_template('index.html', username=session.get( 'username' ))

@app.route('/edit')
def edit():
    if session.get('username') and session.get('proj') == request.args.get('proj'):
        return render_template('edit.html', page=request.args.get('pagename'), proj=request.args.get('proj'), username=session.get( 'username' ) )
    return redirect(f'/tologin?referrer={request.full_path}')

@app.route('/tologin')
def tologin():
    if request.args.get('referrer'):
        session['referrer'] = request.args.get('referrer')
    if session.get('username'):
        return redirect('/')
    return render_template('tologin.html')

@app.route('/generatedab')
def generatedab():
    proj = request.args.get( 'proj' )
    if not session.get( 'username' ):
        session['proj'] = proj
        return redirect( f'/tologin?referrer={request.full_path}' )
    if not (proj == session['proj']):
        session['proj'] = proj
        return redirect( f'/tologin?referrer={request.full_path}' )
    page = generaterandomdisambigs(proj)
    return redirect(f'/edit?proj={proj}&pagename={page}&referer=generatedab' )


@app.route("/api/getdabs/<proj>/<path:pagename>")
def getdabs(proj: str, pagename: str):
    session['proj'] = proj
    return getdabs_w(proj, pagename)
    

@app.route("/api/getraw/<proj>/<path:pagename>")
def getrawtext(proj: str, pagename: str):
    return get_raw_text(pagename, proj)

@app.route("/api/edit/<proj>/<path:pagename>", methods=['POST'])
def make_edit(proj: str, pagename: str):
    if not session.get( 'access_token'):
        return redirect('/tologin')
    access_token = mwoauth.AccessToken(
        **session.get('access_token'))
    consumer_token = mwoauth.ConsumerToken(
        os.environ.get('CONSUMER_KEY'), os.environ.get('CONSUMER_SECRET'))
    auth1 = OAuth1(consumer_token.key,
                    client_secret=consumer_token.secret,
                    resource_owner_key=access_token.key,
                    resource_owner_secret=access_token.secret)
    edits = json.loads(request.form.get('edits'))
    summary = request.form.get('summary')
    return editwikitext(proj, pagename, auth1, edits, summary)


@app.route("/api/getparsed/<proj>/<path:pagename>")
def getparsedtext(proj: str, pagename: str):
    return get_parsed_wikitext(pagename, proj)


@app.route('/login')
def login():
    """Initiate an OAuth login.
    
    Call the MediaWiki server to get request secrets and then redirect the
    user to the MediaWiki server to sign the request.
    """
    if request.args.get( 'referrer' ):
        session['referrer'] = request.args.get( 'referrer' )
    consumer_token = mwoauth.ConsumerToken(
        os.environ.get('CONSUMER_KEY'), os.environ.get('CONSUMER_SECRET'))
    try:
        redirect_loc, request_token = mwoauth.initiate(
            f'https://{session["proj"]}.wikipedia.org/w/index.php', consumer_token)
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
            f'https://{session["proj"]}.wikipedia.org/w/index.php',
            consumer_token,
            mwoauth.RequestToken(**session['request_token']),
            request.query_string)

        identity = mwoauth.identify(
            f'https://{session["proj"]}.wikipedia.org/w/index.php', consumer_token, access_token)    
    except Exception as _:
        app.logger.exception('OAuth authentication failed')
    
    else:
        session['access_token'] = dict(zip(
            access_token._fields, access_token))
        session['username'] = identity['username']
    
    referrer = session.get('referrer')
    session['referrer'] = None

    return redirect(referrer or '/')

@app.route('/logout')
def logout():
    """Log the user out by clearing their session."""
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)