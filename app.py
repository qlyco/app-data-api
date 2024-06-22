"""Flask REST API starting point"""

from datetime import datetime, timedelta
from threading import Thread
from time import sleep
import sqlite3
import os
import hashlib
import requests
from flask import Flask, jsonify, render_template, request, send_file
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

    cur.execute(
        "CREATE TABLE IF NOT EXISTS app_scores(id INTEGER PRIMARY KEY, app, user, score, date, signature);"
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

@app.get("/auth")
@cross_origin()
def get_auth() -> str:
    """Get unique user signature for the API"""
    creds: tuple = ()
    
    if request.authorization:
        creds = (request.authorization.get("username", None), request.authorization.get("password", None))

    res: dict = {
        "status": "Valid authorization header required."
    }

    if creds and not None in creds:
        signature: str = hashlib.sha256(str.encode(f"{creds[0]}:{creds[1]}")).hexdigest()
        
        res = {"user": creds[0], "signature": signature}

        return jsonify(res), 200

    return jsonify(res), 401

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

@app.get(ROUTE_PREFIX + "/scores/<appid>")
@app.get(ROUTE_PREFIX + "/scores/<appid>/<type>")
@cross_origin()
def get_leaderboard(appid: str = "", type: str = "lifetime"):
    """Return the current leaderboard"""
    limit: int = request.args.get("limit", 10)
    order: str = request.args.get("order", "desc")

    res: dict = {
        "scores": []
    }

    if appid:
        con: sqlite3.Connection = sqlite3.connect(f"{CACHE_PATH}/cache.db")
        cur: sqlite3.Cursor = con.cursor()

        ordering: str = "ASC" if order == "asc" else "DESC"
        modifier: str = "MIN" if order == "asc" else "MAX"

        sql: str = f"SELECT user, {modifier}(score), date, signature FROM app_scores WHERE app = ? GROUP BY signature ORDER BY score {ordering}, date ASC LIMIT ?;"

        match (type):
            case "lifetime":
                sql = f"SELECT user, {modifier}(score), date, signature FROM app_scores WHERE app = ? GROUP BY signature ORDER BY score {ordering}, date ASC LIMIT ?;"
            case "daily":
                sql = f"SELECT user, {modifier}(score), date, signature FROM app_scores WHERE app = ? AND DATE(date) = DATE('now') GROUP BY signature ORDER BY score {ordering}, date ASC LIMIT ?;"
            case "weekly":
                sql = f"SELECT user, {modifier}(score), date, signature FROM app_scores WHERE app = ? AND strftime('%W', DATE(date)) = strftime('%W', 'now') AND strftime('%Y', DATE(date)) = strftime('%Y', 'now') GROUP BY signature ORDER BY score {ordering}, date ASC LIMIT ?;"
            case "monthly":
                sql = f"SELECT user, {modifier}(score), date, signature FROM app_scores WHERE app = ? AND strftime('%m', DATE(date)) = strftime('%m', 'now') AND strftime('%Y', DATE(date)) = strftime('%Y', 'now') GROUP BY signature ORDER BY score {ordering}, date ASC LIMIT ?;"
            case "yearly":
                sql = f"SELECT user, {modifier}(score), date, signature FROM app_scores WHERE app = ? AND strftime('%Y', DATE(date)) = strftime('%Y', 'now') GROUP BY signature ORDER BY score {ordering}, date ASC LIMIT ?;"


        data: sqlite3.Cursor = cur.execute(
            sql, (appid, limit)
        )

        for row in data.fetchall():
            res["scores"].append(row)

    return jsonify(res)

@app.post(ROUTE_PREFIX + "/scores/<appid>")
@cross_origin()
def set_scores(appid: str = ""):
    """Add new scores to the leaderboard"""
    cur_time: datetime = datetime.now(tz=pytz.timezone("Asia/Singapore"))

    creds: tuple = ()
    
    if request.authorization:
        creds = (request.authorization.get("username", None), request.authorization.get("password", None))

    res: dict = {
        "status": "Invalid request."
    }

    submission: dict = request.json

    if appid and submission.get("score", None) and (creds and not None in creds):
        con: sqlite3.Connection = sqlite3.connect(f"{CACHE_PATH}/cache.db")
        cur: sqlite3.Cursor = con.cursor()
    
        signature: str = hashlib.sha256(str.encode(f"{creds[0]}:{creds[1]}")).hexdigest()

        cur.execute(
            "INSERT INTO \
                app_scores (app, user, score, date, signature) \
                VALUES (?, ?, ?, ?, ?)",
                (appid, creds[0], submission["score"], cur_time.isoformat(), signature)
        )

        con.commit()

        res["status"] = "OK"

    return jsonify(res), 401

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

@app.get("/backup")
@cross_origin()
def get_backup():
    passkey: str = hashlib.sha256(str.encode(request.headers.get("passkey", ""))).hexdigest()

    if passkey == os.environ["DATABASE_PASSKEY"]:
        return send_file(f"{CACHE_PATH}/cache.db")
    
    res: dict = {
        "status": "Backup requires a valid passkey."
    }

    return jsonify(res), 401
