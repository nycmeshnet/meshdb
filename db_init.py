import psycopg
import sys
import variables




def db_init(base)
try:
    with psycopg.connect(
    host=variables.db_host,
    user=variables.db_user,
    password=variables.db_password) as conn:
        cur = conn.cursor()
        cur.execute("select relname from pg_class where relkind='r' and relname !~ '^(pg_|sql_)';")
        if variables.db_host not in cur.fetchall():

        
except:
    print("Error")