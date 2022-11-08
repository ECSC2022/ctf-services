import os
import uuid
import base64
import sqlite3
import datetime
from hashlib import sha256
from functools import wraps
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from flask import Flask, g, render_template, request, redirect, url_for, jsonify, session
from flask_session import Session


DATABASE = 'report.db'
SECRET_KEY = b'/\x93\x03$R]\x94\xd3\x83t\x9b\xe5=g\xec\xde'
POW_LENGTH = 3 # bytes
PUBKEY_PATH = './public_key.pem'

# queries
QUERY_SELECT_LINKID   = 'SELECT id FROM links WHERE uuid = ?'
QUERY_SELECT_TOVISIT  = 'SELECT id, url, uuid FROM links WHERE visited = 0 ORDER BY id ASC'
QUERY_SELECT_MESSAGES = 'SELECT id, message, ts FROM messages WHERE link_id = ?'
QUERY_INSERT_LINK     = 'INSERT INTO links(url, uuid) VALUES(?, ?)'
QUERY_INSERT_MESSAGE  = 'INSERT INTO messages(link_id, message, ts) VALUES(?, ?, ?)'
QUERY_UPDATE_VISITED  = 'UPDATE links SET visited = 1 WHERE uuid = ?'


app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = '/tmp/flask-sessions'
app.config['SESSION_FILE_THRESHOLD'] = 100
app.config['PERMANENT_SESSION_LIFETIME'] = 60*10 # 10 minutes
Session(app)

# load the public key
with open(PUBKEY_PATH, 'rb') as key_file:
    public_key = serialization.load_pem_public_key(
        key_file.read()
    )


# decorators

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # first check that the session is authenticated
        if session.get('admin') == True:
            return f(*args, **kwargs)
        
        # otherwise, validate the signature
        try:
            rec_signature = base64.b64decode(request.form.get('signature'))
            ses_challenge = base64.b64decode(session.get('challenge'))
            if rec_signature and ses_challenge:
                # raise InvalidSignature if signature does not match
                public_key.verify(
                    rec_signature,
                    ses_challenge,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                # now you can proceed
                session['admin'] = True
                return f(*args, **kwargs)
        except Exception as e:
            # not gonna let you in
            pass

        return 'Forbidden', 400
        
    return decorated_function


# helper functions

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE,
                               detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_select(query, args=(), one=False):
    """
    Executes a SELECT query and returns the resultset.
    """
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def query_insert(query, args=()):
    """
    Executes an INSERT query and returns the last inserted ID (or None if it fails).
    """
    try:
        con = get_db()
        cur = con.cursor()
        cur.execute(query, args)
        con.commit()
        last_row_id = cur.lastrowid
        cur.close()
        return last_row_id
    except sqlite3.Error as e:
        app.logger.error(f'Unable to execute {query}: {e}')
        return None

def query_update(query, args=()):
    """
    Executes an UPDATE query and returs the number of updated rows (or None if it fails).
    """
    try:
        con = get_db()
        cur = con.cursor()
        cur.execute(query, args)
        con.commit()
        row_count = cur.rowcount
        cur.close()
        return row_count
    except sqlite3.Error as e:
        app.logger.error(f'Unable to execute {query}: {e}')
        return None

def get_ts():
    """
    Get current timestamp.
    """
    return datetime.datetime.now()

def generate_uuid():
    """
    Generate a random UUID starting from a random sequence of 16 bytes.
    """
    return str(uuid.UUID(bytes=os.urandom(16)))

def valid_link(link):
    """
    Check that the link is well-formed.
    """
    if link.startswith('http://'):
        return True
    return False

def generate_pow():
    """
    Generate a PoW (salt and suffix), set the values in the session and return them as bytes.
    """
    pow_salt = os.urandom(8)
    pow_suffix = os.urandom(POW_LENGTH)
    session['pow_salt'] = pow_salt
    session['pow_suffix'] = pow_suffix
    return pow_salt, pow_suffix

def valid_pow(b64blob):
    """
    Check that the PoW is correct and clear the session to avoid replay attacks.
    """
    
    try:
        pow_salt = session.get('pow_salt')
        pow_suffix = session.get('pow_suffix')
        if len(pow_suffix) == POW_LENGTH:
            # take the last POW_LENGTH bytes
            suffix_hash = sha256(pow_salt + base64.b64decode(b64blob)).digest()[-POW_LENGTH:]
            return suffix_hash == pow_suffix
    except Exception as e:
        app.logger.error(f'Error while checking PoW: {e}')
        return False
    finally:
        session.clear()
    return False


# routes

@app.route('/', methods=['GET', 'POST'])
def report():
    """
    Report a link that will be processed by the administrator. Each link has a UUID associated 
    that is reported back the the user after submission.
    """
    error = None
    if request.method == 'POST':
        link = request.form.get('link')
        b64_pow = request.form.get('pow')
        # check the validity of the provided PoW and that the link is well-formed
        if valid_link(link):
            if valid_pow(b64_pow):
                # store the link in the DB
                link_uuid = generate_uuid()
                res = query_insert(QUERY_INSERT_LINK, (link, link_uuid))
                if res == None:
                    error = 'Unable to add the provided link'
                else:                    
                    return render_template('report.html',
                                           link_uuid=url_for('messages', link_uuid=link_uuid))
            else:
                error = 'PoW failed'
        else:
            error = 'Invalid URL format'
    pow_salt, pow_suffix = generate_pow()
    return render_template(
        'report.html',
        pow_salt=base64.b64encode(pow_salt).decode(),
        pow_suffix=base64.b64encode(pow_suffix).decode(),
        error=error
    )


@app.route('/report/<link_uuid>', methods=['GET', 'POST'])
def messages(link_uuid):
    """
    Show and set messages associated to a given link UUID.
    """
    row_link_id = query_select(QUERY_SELECT_LINKID, (link_uuid, ), one=True)
    if row_link_id == None:
        error = 'Invalid link UUID'
        return render_template('messages.html', error=error)
    link_id = row_link_id['id']
    if request.method == 'GET':
        messages = query_select(QUERY_SELECT_MESSAGES, (link_id, ))
        return render_template('messages.html', link_uuid=link_uuid, messages=messages)
    else:
        message = request.form.get('message')
        if message:
            res = query_insert(QUERY_INSERT_MESSAGE, (link_id, message, datetime.datetime.now()))
            if res == None:
                error = 'Unable to insert the provided message'
            else:
                # show all messages, including the new one
                return redirect(url_for('messages', link_uuid=link_uuid))
        else:
            error = 'Empty message'
        return render_template('messages.html', error=error)


@app.route('/admin/challenge')
def admin_challenge():
    """
    Returns a challenge via JSON and stores it in the session.
    """
    challenge = base64.b64encode(os.urandom(64)).decode()
    session['challenge'] = challenge
    return jsonify({'challenge': challenge})


@app.route('/admin/list', methods=['POST'])
@admin_required
def admin_list():
    """
    Returns a JSON list of unvisited links (oldest ones are listed first).
    """
    rows = query_select(QUERY_SELECT_TOVISIT)
    return jsonify([{'id': r['id'], 'url': r['url'], 'uuid': r['uuid']} for r in rows])


@app.route('/admin/<link_uuid>', methods=['POST'])
@admin_required
def admin_visit(link_uuid):
    """
    Mark the given link UUID as visited.
    """
    res = query_update(QUERY_UPDATE_VISITED, (link_uuid, ))
    if res:
        return 'OK'
    return f'Unable to UPDATE UUID {link_uuid}', 500


if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', threaded=True)