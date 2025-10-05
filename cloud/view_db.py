#!/usr/bin/env python3
# view_db.py
import sqlite3
import pandas as pd
import time

DB = "telemetry.db"

def show_latest(n=20):
    conn = sqlite3.connect(DB)
    try:
        df = pd.read_sql_query(f"SELECT * FROM telemetry ORDER BY ts DESC LIMIT {n}", conn)
        # print with timestamp column converted for readability if present
        if 'ts' in df.columns:
            df['ts'] = pd.to_datetime(df['ts'], unit='s')
        print(df)
    finally:
        conn.close()

if __name__ == "__main__":
    # single-shot print
    show_latest(20)
    # uncomment below to refresh every 5s:
    # while True:
    #     show_latest(10)
    #     print("-" * 60)
    #     time.sleep(5)
