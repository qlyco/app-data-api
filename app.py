"""Flask REST API starting point"""

from datetime import datetime, timedelta
from threading import Thread
from time import sleep
import sqlite3
import os
import requests
from flask import Flask, jsonify, render_template
from flask_cors import CORS, cross_origin
import pytz

app: Flask = Flask(__name__)
cors: CORS = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"

CACHE_PATH: str = os.environ["CACHE_PATH"]

if not os.path.exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)

def update_cache():
    """Update the local cache of the database."""

    print("Starting cache updater.")

    DATABASE_URL: str = os.environ["SUPABASE_URL"]
    ANON_KEY: str = os.environ["SUPABASE_ANON_KEY"]

    con: sqlite3.Connection = sqlite3.connect(f"{CACHE_PATH}/cache.db")
    cur: sqlite3.Cursor = con.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS app_details(name UNIQUE, version, changelog, updated_on, release_date);"
    )

    cur.execute(
        "CREATE TABLE IF NOT EXISTS app_traffic(id UNIQUE, app, year, month, count);"
    )

    while True:
        print("Getting data")
        data: requests.Response = requests.get(
            f"{DATABASE_URL}/app_details?apikey={ANON_KEY}",
            timeout=(5, 5),
        )
        
        if data.status_code == 200:
            args: list = []

            for row in data.json():
                args.append(tuple(row.values()))
            
            cur.executemany(
                "INSERT INTO \
                    app_details (name, version, changelog, updated_on, release_date) \
                    VALUES (?, ?, ?, ?, ?) \
                    ON CONFLICT (name) \
                    DO UPDATE SET \
                        version = excluded.version, \
                        changelog = excluded.changelog, \
                        updated_on = excluded.updated_on, \
                        release_date = excluded.release_date \
                    WHERE excluded.updated_on > app_details.updated_on;",
                args
            )

            con.commit()
        
        print("Cache updated.")
        sleep(60 * 60)

Thread(target=update_cache, daemon=True).start()

ROUTE_PREFIX: str = "/api/v2"

@app.get("/")
@cross_origin()
def home() -> str:
    """Home route for the REST API"""
    return render_template("index.html")

@app.get(ROUTE_PREFIX + "/seed")
@app.get(ROUTE_PREFIX + "/seed/<seed_type>")
@cross_origin()
def get_seed(seed_type="daily"):
    """Return a static seed for a standardized RNG."""
    seed: int = -1
    cur_time: datetime = datetime.now(tz=pytz.timezone("Asia/Singapore"))

    if seed_type == "hourly":
        seed = int(datetime(cur_time.year, cur_time.month, cur_time.day, cur_time.hour, 0).timestamp())
    elif seed_type == "daily":
        seed = int(datetime(cur_time.year, cur_time.month, cur_time.day, 0, 0).timestamp())
    elif seed_type == "weekly":
        seed = int(
            datetime(
                cur_time.year,
                cur_time.month,
                (cur_time - timedelta(days=cur_time.isoweekday() % 7)).day,
                0,
                0
            ).timestamp()
        )
    elif seed_type == "monthly":
        seed = int(datetime(cur_time.year, cur_time.month, 1, 0, 0).timestamp())
    elif seed_type == "yearly":
        seed = int(datetime(cur_time.year, 1, 1, 0, 0).timestamp())

    res: dict = {
        "seed": seed
    }

    if seed == -1:
        res["error"] = "Invalid value for seed-type (hourly, daily, weekly, monthly, yearly)."
    else:
        res["timestamp"] = datetime.fromtimestamp(seed).isoformat()

    return jsonify(res)

@app.get(ROUTE_PREFIX + "/time")
@cross_origin()
def get_server_time():
    """Return the server time"""
    cur_time: datetime = datetime.now(tz=pytz.timezone("Asia/Singapore"))

    res: dict = {
        "datetime": cur_time.isoformat(),
        "timestamp": int(cur_time.timestamp()),
    }

    return jsonify(res)

@app.get(ROUTE_PREFIX + "/tracker/<appid>/<year>/<month>")
@cross_origin()
def get_visitor_stats(appid: str ="", year: str ="", month: str =""):
    """Return the total visitors of a specific month"""

    res: dict = {
        "count": 0
    }

    if appid and year and month:
        con: sqlite3.Connection = sqlite3.connect(f"{CACHE_PATH}/cache.db")
        cur: sqlite3.Cursor = con.cursor()

        data: sqlite3.Cursor = cur.execute(
            "SELECT * FROM app_traffic WHERE app = ? AND year = ? AND month = ?;",
                (appid, year, month)
        )

        count: int = -1

        for row in data.fetchall():
            res["count"] = row[4]

    return jsonify(res)

@app.post(ROUTE_PREFIX + "/tracker/<appid>")
@cross_origin()
def set_visitor_stats(appid: str = ""):
    """Add new visitor for the given app ID"""
    cur_time: datetime = datetime.now(tz=pytz.timezone("Asia/Singapore"))

    year: str = str(cur_time.year)
    month: str = f"{cur_time.month:0>2}"
    id: str = f"{appid}.{year}.{month}"

    con: sqlite3.Connection = sqlite3.connect(f"{CACHE_PATH}/cache.db")
    cur: sqlite3.Cursor = con.cursor()

    res: dict = {
        "status": "Invalid parameter."
    }

    if appid:
        data: sqlite3.Cursor = cur.execute(
            "SELECT * FROM app_details WHERE name = ?;",
            (appid, )
        )

        exist: bool = False

        for row in data.fetchall():
            exist = True

        if exist:
            cur.execute(
                "INSERT OR IGNORE INTO \
                    app_traffic (id, app, year, month, count) \
                    VALUES (?, ?, ?, ?, 1) \
                    ON CONFLICT (id) \
                    DO UPDATE SET \
                        count = count + 1",
                    (id, appid, year, month)
            )

            con.commit()

            res["status"] = "OK"

    return jsonify(res)

@app.get(ROUTE_PREFIX + "/apps")
@app.get(ROUTE_PREFIX + "/apps/<app_name>")
@cross_origin()
def get_app_data(app_name=None):
    """Return the app data from the database"""

    con: sqlite3.Connection = sqlite3.connect(f"{CACHE_PATH}/cache.db")
    cur: sqlite3.Cursor = con.cursor()

    data: sqlite3.Cursor = None

    if app_name is not None:
        data = cur.execute(
            "SELECT * FROM app_details WHERE name = ?;",
            (app_name, )
        )
    else:
        data = cur.execute(
            "SELECT * FROM app_details;"
        )

    query_res: list = []

    for row in data.fetchall():
        query_res.append(
            {
                "name": row[0],
                "version": row[1],
                "changelog": row[2],
                "updated_on": row[3],
                "release_date": row[4]
            }
        )

    res: dict = {
        "data": query_res,
    }

    return jsonify(res)
