#!/usr/bin/env bash
# Runs all Hive scripts in order against the dockerised HiveServer2.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 data/generate_data.py
docker compose up -d
echo "Waiting for HiveServer2 (can take ~60s)..."
until docker exec hiveserver2 beeline -u jdbc:hive2://localhost:10000 -e "SHOW DATABASES" >/dev/null 2>&1; do sleep 5; done
for f in hive/01_create_database.hql hive/02_create_tables.hql hive/03_load_data.hql hive/04_views_and_features.hql; do
  echo ">>> $f"
  docker exec hiveserver2 beeline -u jdbc:hive2://localhost:10000 -f /hive_scripts/$(basename $f)
done
echo "Pipeline done. Run analytics: docker exec hiveserver2 beeline -u jdbc:hive2://localhost:10000 -f /hive_scripts/05_analytics_queries.hql"
