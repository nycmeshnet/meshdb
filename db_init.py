

# returns true if DB is present, false if DB is not
def initDB(base):
    import psycopg
    import sys
    import variables
    try:
        with psycopg.connect(
        host=variables.db_host,
        user=variables.db_user,
        password=variables.db_password) as conn:
            cur = conn.cursor()
            cur.execute("select relname from pg_class where relkind='r' and relname !~ '^(pg_|sql_)';")
            if variables.db_host in cur.fetchall():
                return True
            else:
                return False
            
    except:
        return "Error"
    

def main():
    import models.building
    import models.install
    import models.member
    import models.request
    import models.baseModel
    from sqlalchemy import create_engine

    engine = create_engine("postgresql://", echo=True)
    models.baseModel.Base.metadata.create_all(engine)