-- 03: Load CSVs into staging, then into partitioned ORC tables
-- Run `hdfs dfs -put` first (see scripts/run_hive_pipeline.sh) OR use LOCAL load below.
USE telecom_churn;
SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;

LOAD DATA LOCAL INPATH '/data/customers.csv'       OVERWRITE INTO TABLE stg_customers;
LOAD DATA LOCAL INPATH '/data/usage_stats.csv'     OVERWRITE INTO TABLE stg_usage_stats;
LOAD DATA LOCAL INPATH '/data/support_tickets.csv' OVERWRITE INTO TABLE stg_support_tickets;

-- Dynamic partition insert (partition column must be LAST in SELECT)
INSERT OVERWRITE TABLE customers PARTITION (contract)
SELECT customer_id, gender, senior_citizen, partner, dependents, tenure_months, phone_service,
       multiple_lines, internet_service, online_security, tech_support, streaming_tv,
       paperless_billing, payment_method, monthly_charges, total_charges, state, churn, contract
FROM stg_customers
WHERE customer_id IS NOT NULL AND customer_id <> '';

INSERT OVERWRITE TABLE usage_stats SELECT * FROM stg_usage_stats;

INSERT OVERWRITE TABLE support_tickets PARTITION (created_month)
SELECT ticket_id, customer_id, category, resolution_hours, created_date, substr(created_date, 1, 7)
FROM stg_support_tickets;

-- Statistics for the cost-based optimizer
ANALYZE TABLE customers PARTITION (contract) COMPUTE STATISTICS;
ANALYZE TABLE customers COMPUTE STATISTICS FOR COLUMNS;
ANALYZE TABLE usage_stats COMPUTE STATISTICS;
ANALYZE TABLE support_tickets PARTITION (created_month) COMPUTE STATISTICS;

-- Data quality checks
SELECT 'customers' t, COUNT(*) n FROM customers
UNION ALL SELECT 'usage_stats', COUNT(*) FROM usage_stats
UNION ALL SELECT 'support_tickets', COUNT(*) FROM support_tickets;
