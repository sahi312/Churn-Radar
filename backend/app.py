"""Telecom Churn Analytics – Flask REST API + static frontend."""
import re
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import db

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app = Flask(__name__, static_folder=str(FRONTEND), static_url_path="")
CORS(app)

# ---- safe-by-construction input handling (no raw user text reaches SQL) ----
DIMENSIONS = {"contract", "internet_service", "payment_method", "gender", "state", "tenure_band",
              "charge_band", "senior_citizen", "paperless_billing", "tech_support", "online_security",
              "streaming_tv", "partner", "dependents"}
FILTERABLE = {"contract", "internet_service", "state"}
SAFE = re.compile(r"^[A-Za-z0-9 \-]{1,40}$")
CHURNED = "SUM(CASE WHEN churn='Yes' THEN 1 ELSE 0 END)"


def where(extra=None):
    parts = []
    for col in FILTERABLE:
        v = request.args.get(col)
        if v and v != "all":
            if not SAFE.match(v):
                raise ValueError(f"invalid {col}")
            parts.append(f"{col} = '{v}'")
    if extra:
        parts += extra
    return ("WHERE " + " AND ".join(parts)) if parts else ""


def num(x, default=0):
    return default if x is None else x


@app.errorhandler(Exception)
def on_error(e):
    code = 400 if isinstance(e, ValueError) else 500
    return jsonify(error=str(e)), code


@app.get("/api/health")
def health():
    return jsonify(db.health())


@app.get("/api/filters")
def filters():
    return jsonify({c: [r["v"] for r in db.query(f"SELECT DISTINCT {c} AS v FROM v_customer_360 ORDER BY v")]
                    for c in sorted(FILTERABLE)})


@app.get("/api/summary")
def summary():
    r = db.query(f"""
        SELECT COUNT(*) AS total_customers, {CHURNED} AS churned,
               ROUND(100.0*{CHURNED}/COUNT(*),2) AS churn_rate,
               ROUND(SUM(CASE WHEN churn='Yes' THEN monthly_charges ELSE 0 END),0) AS monthly_revenue_lost,
               ROUND(AVG(monthly_charges),0) AS arpu,
               ROUND(AVG(CASE WHEN churn='Yes' THEN tenure_months END),1) AS avg_tenure_churned,
               ROUND(AVG(CASE WHEN churn='No'  THEN tenure_months END),1) AS avg_tenure_retained
        FROM v_customer_360 {where()}""")[0]
    return jsonify({k: num(v) for k, v in r.items()})


@app.get("/api/churn-by/<dim>")
def churn_by(dim):
    if dim not in DIMENSIONS:
        return jsonify(error=f"unknown dimension; choose from {sorted(DIMENSIONS)}"), 400
    rows = db.query(f"""
        SELECT CAST({dim} AS STRING) AS segment, COUNT(*) AS customers, {CHURNED} AS churned,
               ROUND(100.0*{CHURNED}/COUNT(*),2) AS churn_rate,
               ROUND(SUM(CASE WHEN churn='Yes' THEN monthly_charges ELSE 0 END),0) AS revenue_lost
        FROM v_customer_360 {where()} GROUP BY {dim} ORDER BY churn_rate DESC""")
    return jsonify(rows)


@app.get("/api/tenure-curve")
def tenure_curve():
    return jsonify(db.query(f"""
        SELECT tenure_band AS segment, COUNT(*) AS customers,
               ROUND(100.0*{CHURNED}/COUNT(*),2) AS churn_rate
        FROM v_customer_360 {where()} GROUP BY tenure_band ORDER BY MIN(tenure_months)"""))


@app.get("/api/tickets-vs-churn")
def tickets_vs_churn():
    return jsonify(db.query(f"""
        SELECT LEAST(ticket_count,5) AS tickets, COUNT(*) AS customers,
               ROUND(100.0*{CHURNED}/COUNT(*),2) AS churn_rate
        FROM v_customer_360 {where()} GROUP BY LEAST(ticket_count,5) ORDER BY tickets"""))


@app.get("/api/ticket-trend")
def ticket_trend():
    return jsonify(db.query("""
        SELECT created_month AS month, COUNT(*) AS tickets, ROUND(AVG(resolution_hours),1) AS avg_hours
        FROM support_tickets GROUP BY created_month ORDER BY created_month"""))


@app.get("/api/ticket-categories")
def ticket_categories():
    return jsonify(db.query("""
        SELECT category, COUNT(*) AS tickets, ROUND(AVG(resolution_hours),1) AS avg_hours
        FROM support_tickets GROUP BY category ORDER BY tickets DESC"""))


@app.get("/api/usage-compare")
def usage_compare():
    return jsonify(db.query(f"""
        SELECT churn, ROUND(AVG(avg_minutes),0) AS minutes, ROUND(AVG(avg_data_gb),1) AS data_gb,
               ROUND(AVG(dropped_calls),2) AS dropped_calls, ROUND(AVG(monthly_charges),0) AS charges,
               ROUND(AVG(ticket_count),2) AS tickets
        FROM v_customer_360 {where()} GROUP BY churn ORDER BY churn"""))


@app.get("/api/segments/heatmap")
def heatmap():
    return jsonify(db.query(f"""
        SELECT contract, internet_service, COUNT(*) AS customers,
               ROUND(100.0*{CHURNED}/COUNT(*),2) AS churn_rate
        FROM v_customer_360 {where()} GROUP BY contract, internet_service"""))


@app.get("/api/at-risk")
def at_risk():
    limit = min(int(request.args.get("limit", 25)), 200)
    return jsonify(db.query(f"""
        SELECT customer_id, state, contract, internet_service, payment_method, tenure_months,
               monthly_charges, ticket_count, risk_score
        FROM v_churn_risk {where()} ORDER BY risk_score DESC, monthly_charges DESC LIMIT {limit}"""))


@app.get("/api/risk-distribution")
def risk_distribution():
    return jsonify(db.query(f"""
        SELECT CASE WHEN risk_score>=55 THEN 'High' WHEN risk_score>=35 THEN 'Medium' ELSE 'Low' END AS level,
               COUNT(*) AS customers, ROUND(SUM(monthly_charges),0) AS revenue_at_risk
        FROM v_churn_risk {where()} GROUP BY CASE WHEN risk_score>=55 THEN 'High' WHEN risk_score>=35 THEN 'Medium' ELSE 'Low' END"""))


@app.get("/api/customers")
def customers():
    page = max(int(request.args.get("page", 1)), 1)
    size = min(int(request.args.get("size", 15)), 100)
    extra = []
    q = request.args.get("q", "").strip()
    if q:
        if not SAFE.match(q):
            raise ValueError("invalid search text")
        extra.append(f"customer_id LIKE '%{q.upper()}%'")
    ch = request.args.get("churn")
    if ch in ("Yes", "No"):
        extra.append(f"churn = '{ch}'")
    w = where(extra)
    total = db.query(f"SELECT COUNT(*) AS n FROM v_customer_360 {w}")[0]["n"]
    rows = db.query(f"""
        SELECT customer_id, gender, state, contract, internet_service, payment_method, tenure_months,
               monthly_charges, ticket_count, churn
        FROM v_customer_360 {w} ORDER BY customer_id LIMIT {size} OFFSET {(page-1)*size}""")
    return jsonify({"total": total, "page": page, "size": size, "rows": rows})


@app.get("/api/customers/<cid>")
def customer(cid):
    if not re.match(r"^C\d{5}$", cid):
        raise ValueError("customer id looks like C00001")
    rows = db.query(f"SELECT * FROM v_customer_360 WHERE customer_id = '{cid}'")
    if not rows:
        return jsonify(error="not found"), 404
    return jsonify(rows[0])


# ---- what-if risk calculator (same rules as Hive view v_churn_risk) ----
def score(d):
    s, f = 0, []
    def add(pts, why):
        nonlocal s
        if pts:
            s += pts; f.append({"points": pts, "reason": why})
    add({"Month-to-month": 30, "One year": 10}.get(d.get("contract"), 0), f"{d.get('contract')} contract")
    t = int(d.get("tenure_months", 0))
    add(20 if t <= 12 else 10 if t <= 24 else 0, f"short tenure ({t} months)")
    net = d.get("internet_service")
    add(10 if net == "Fiber optic" else 0, "fiber optic (higher churn segment)")
    add(10 if d.get("payment_method") == "Electronic check" else 0, "pays by electronic check")
    add(5 if net != "No" and d.get("online_security") == "No" else 0, "no online security add-on")
    add(5 if net != "No" and d.get("tech_support") == "No" else 0, "no tech support add-on")
    tk = int(d.get("ticket_count", 0))
    add(15 if tk >= 3 else 8 if tk == 2 else 0, f"{tk} support tickets")
    add(5 if int(d.get("dropped_calls", 0)) >= 5 else 0, "frequent dropped calls")
    return s, f


@app.post("/api/predict")
def predict():
    d = request.get_json(force=True) or {}
    s, factors = score(d)
    level = "High" if s >= 60 else "Medium" if s >= 35 else "Low"
    tips = {"High": ["Assign a retention agent within 48h", "Offer 12-month contract with discount",
                     "Proactively fix network/ticket issues"],
            "Medium": ["Send loyalty offer", "Promote security / tech-support add-ons"],
            "Low": ["Keep in regular engagement journey"]}[level]
    return jsonify({"risk_score": s, "level": level, "factors": factors, "recommendations": tips})


@app.get("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
