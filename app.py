"""Flask REST API starting point"""

from datetime import datetime
from flask import Flask, jsonify, render_template
from flask_cors import CORS, cross_origin
import pytz

app: Flask = Flask(__name__)
cors: CORS = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"

ROUTE_PREFIX: str = "/api/v2"

@app.get(ROUTE_PREFIX + "/")
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
    cur: datetime = datetime.now(tz=pytz.timezone("Asia/Singapore"))

    if seed_type == "hourly":
        seed = int(datetime(cur.year, cur.month, cur.day, cur.hour, 0).timestamp())
    elif seed_type == "daily":
        seed = int(datetime(cur.year, cur.month, cur.day, 0, 0).timestamp())
    elif seed_type == "weekly":
        seed = int(datetime(cur.year, cur.month, int(cur.day / 7) * 7, 0, 0).timestamp())
    elif seed_type == "monthly":
        seed = int(datetime(cur.year, cur.month, 1, 0, 0).timestamp())
    elif seed_type == "yearly":
        seed = int(datetime(cur.year, 1, 1, 0, 0).timestamp())

    res: dict = {
        "status": 200,
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
    cur: datetime = datetime.now(tz=pytz.timezone("Asia/Singapore"))

    res: dict = {
        "status": 200,
        "datetime": cur.isoformat(),
        "timestamp": int(cur.timestamp()),
    }

    return jsonify(res)
