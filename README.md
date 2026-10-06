# Churn Radar – Telecom Customer Churn Analytics (Apache Hive)

End-to-end project: **data generation → Hive data warehouse → REST API → web dashboard**.

```
CSV data ──► Hive staging (TEXTFILE) ──► ORC tables (partitioned) ──► Views / feature tables
                                                                         │
                         Flask REST API (PyHive) ◄───────────────────────┘
                                   │
                         Browser dashboard (Chart.js)
```

## Project structure
| Path | What it does |
|---|---|
| `data/generate_data.py` | Creates 5,000 customers, usage stats and ~6,000 support tickets (CSV) |
| `hive/01_create_database.hql` | Database |
| `hive/02_create_tables.hql` | External staging tables + **ORC**, **partitioned** (`contract`, `created_month`) tables |
| `hive/03_load_data.hql` | `LOAD DATA`, **dynamic-partition inserts**, `ANALYZE` stats, row-count checks |
| `hive/04_views_and_features.hql` | `v_customer_360`, `v_ticket_summary`, `v_churn_risk` (risk score 0-100), CTAS `churn_summary_by_segment` |
| `hive/05_analytics_queries.hql` | 11 queries: KPIs, `RANK`, `NTILE`, `LAG`, `ROW_NUMBER`, `WITH ROLLUP`, `percentile_approx`, cohorts |
| `backend/app.py`, `db.py` | Flask API. `HIVE_MODE=hive` uses HiveServer2, `HIVE_MODE=demo` uses DuckDB on the CSVs |
| `frontend/index.html` | Dashboard: overview, segments, support & usage, at-risk list, customer explorer, risk calculator |
| `docker-compose.yml`, `scripts/` | One-command Hive setup |

## Quick start A – demo mode (no Hive needed, 1 minute)
```bash
pip install flask flask-cors duckdb
python data/generate_data.py
cd backend && python app.py          # HIVE_MODE defaults to demo
# open http://localhost:5000
```
Demo mode builds the **same views** from `hive/04_views_and_features.hql`, so the API SQL is identical.

## Quick start B – real Hive
```bash
./scripts/run_hive_pipeline.sh                 # generates data, starts Hive in Docker, runs 01–04
pip install -r backend/requirements.txt
cd backend
HIVE_MODE=hive HIVE_HOST=localhost HIVE_PORT=10000 python app.py
# open http://localhost:5000
```
Run the analytics queries in Hive:
```bash
docker exec hiveserver2 beeline -u jdbc:hive2://localhost:10000 -f /hive_scripts/05_analytics_queries.hql
```
(Windows: run the commands in the script one by one in PowerShell or use WSL.)

## API
| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Connection status + mode |
| `GET /api/filters` | Values for filter dropdowns |
| `GET /api/summary` | KPIs |
| `GET /api/churn-by/<dimension>` | contract, internet_service, payment_method, state, gender, tenure_band, charge_band, … |
| `GET /api/tenure-curve`, `/api/tickets-vs-churn`, `/api/usage-compare`, `/api/segments/heatmap` | Analysis charts |
| `GET /api/ticket-trend`, `/api/ticket-categories` | Support analytics |
| `GET /api/at-risk?limit=25`, `/api/risk-distribution` | Retention campaign list |
| `GET /api/customers?q=&churn=&page=&size=` | Search + pagination |
| `GET /api/customers/<id>` | Customer 360 |
| `POST /api/predict` | What-if risk score + recommended actions |

All dashboard endpoints accept `?contract=&internet_service=&state=` filters.

## Security notes
Dimensions are whitelisted; filter values are validated with a strict regex; customer IDs are pattern-checked. No raw user text is placed in SQL.

## Ideas to extend
Train a Spark MLlib / scikit-learn model on `v_customer_360` and replace the rule-based score; schedule the pipeline with Airflow; add Superset/Tableau on top of `churn_summary_by_segment`.

## Troubleshooting
- *PyHive install errors on Windows/Python 3.12*: use demo mode, or `pip install "pyhive[hive_pure_sasl]" thrift thrift-sasl pure-sasl`.
- *Hive container slow to start*: wait for `beeline -e "SHOW DATABASES"` to succeed.
- *`LOAD DATA LOCAL` fails*: confirm `./data` is mounted at `/data` inside the container.
