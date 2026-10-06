"""Database layer. HIVE_MODE=hive -> HiveServer2 via PyHive, HIVE_MODE=demo -> DuckDB over the CSV files."""
import os, re, time, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODE = os.getenv("HIVE_MODE", "demo").lower()
HIVE_HOST = os.getenv("HIVE_HOST", "localhost")
HIVE_PORT = int(os.getenv("HIVE_PORT", "10000"))
HIVE_DB = os.getenv("HIVE_DB", "telecom_churn")
HIVE_USER = os.getenv("HIVE_USER", "hive")

_lock = threading.Lock()
_duck = None
_cache = {}
TTL = int(os.getenv("CACHE_TTL", "60"))


def _split_sql(path):
    text = "\n".join(l for l in Path(path).read_text().splitlines() if not l.strip().startswith("--"))
    return [s.strip() for s in text.split(";") if s.strip()]


def _duck_conn():
    global _duck
    if _duck is None:
        import duckdb
        c = duckdb.connect(":memory:")
        d = ROOT / "data"
        yn = ["partner","dependents","phone_service","multiple_lines","online_security","tech_support",
              "streaming_tv","paperless_billing","churn"]
        types = "{" + ",".join(f"'{k}':'VARCHAR'" for k in yn) + "}"   # keep Yes/No as text (like Hive)
        for t in ("customers", "usage_stats", "support_tickets"):
            extra = f", types={types}" if t == "customers" else ""
            c.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('{(d / (t + '.csv')).as_posix()}', header=true{extra})")
        c.execute("ALTER TABLE support_tickets ADD COLUMN created_month VARCHAR")
        c.execute("UPDATE support_tickets SET created_month = substr(CAST(created_date AS VARCHAR),1,7)")
        # re-use the SAME view definitions that are deployed to Hive
        for stmt in _split_sql(ROOT / "hive" / "04_views_and_features.hql"):
            if stmt.upper().startswith("CREATE VIEW"):
                c.execute(stmt)
        _duck = c
    return _duck


def _hive_conn():
    from pyhive import hive
    return hive.Connection(host=HIVE_HOST, port=HIVE_PORT, username=HIVE_USER,
                           database=HIVE_DB, auth="NONE")


def query(sql, params=None):
    """Run SQL and return list[dict]. Results cached for TTL seconds."""
    key = sql
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    if MODE == "hive":
        conn = _hive_conn()
        try:
            cur = conn.cursor()
            cur.execute(sql)
            cols = [d[0].split(".")[-1] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        finally:
            conn.close()
    else:
        with _lock:
            cur = _duck_conn().execute(sql)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    rows = [{k: (float(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, (int, float, bool)) else v)
             for k, v in r.items()} for r in rows]
    _cache[key] = (time.time(), rows)
    return rows


def health():
    try:
        query("SELECT 1 AS ok")
        return {"status": "ok", "mode": MODE}
    except Exception as e:
        return {"status": "error", "mode": MODE, "detail": str(e)}
