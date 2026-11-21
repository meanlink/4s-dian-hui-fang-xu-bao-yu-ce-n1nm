import os
import time
from contextlib import contextmanager
import pymysql


def connect():
    last = None
    for _ in range(30):
        try:
            return pymysql.connect(
                host=os.getenv("DB_HOST", "127.0.0.1"),
                user=os.getenv("DB_USER", "dealer"),
                password=os.getenv("DB_PASSWORD", "dealer_local_pw"),
                database=os.getenv("DB_NAME", "dealer_renewal"),
                port=int(os.getenv("DB_PORT_INTERNAL", "3306")),
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
            )
        except pymysql.MySQLError as exc:
            last = exc
            time.sleep(1)
    raise last


@contextmanager
def db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def one(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchone()


def all_rows(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchall()
