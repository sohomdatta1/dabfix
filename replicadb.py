import pymysql as sql
from cnf import config
import os

def get_conn(dbname):
    if os.environ.get( 'TOOLFORGE' ):
        host = f'{dbname}.db.svc.wikimedia.cloud'
    else:
        host = config['host']
    dbconn = sql.connections.Connection(user=config['username'], password=config['password'], host=host, database=f'{dbname}_p')
    return dbconn
