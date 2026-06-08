import os

import pymysql
from dotenv import load_dotenv

load_dotenv()

ERP_ORG_ID = int(os.getenv('ERP_ORG_ID', 1))


def erp_query(sql: str, params=None) -> list:
    conn = pymysql.connect(
        host=os.getenv('ERP_DB_HOST'),
        port=int(os.getenv('ERP_DB_PORT', 3306)),
        database=os.getenv('ERP_DB_NAME'),
        user=os.getenv('ERP_DB_USER'),
        password=os.getenv('ERP_DB_PASSWORD'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()
