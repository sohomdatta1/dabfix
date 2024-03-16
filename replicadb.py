import pymysql as sql
from cnf import config

def get_conn(dbname):
    dbconn = sql.connections.Connection(user=config['username'], password=config['password'], host=config['host'], database=f'{dbname}')
    return dbconn
