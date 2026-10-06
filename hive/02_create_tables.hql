-- 02: Staging (raw CSV) + optimized ORC tables
USE telecom_churn;

-- ---------- STAGING TABLES (raw CSV, header skipped) ----------
DROP TABLE IF EXISTS stg_customers;
CREATE EXTERNAL TABLE stg_customers (
  customer_id STRING, gender STRING, senior_citizen INT, partner STRING, dependents STRING,
  tenure_months INT, phone_service STRING, multiple_lines STRING, internet_service STRING,
  online_security STRING, tech_support STRING, streaming_tv STRING, contract STRING,
  paperless_billing STRING, payment_method STRING, monthly_charges DOUBLE, total_charges DOUBLE,
  state STRING, churn STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n'
STORED AS TEXTFILE
LOCATION '/user/hive/staging/customers'
TBLPROPERTIES ('skip.header.line.count'='1');

DROP TABLE IF EXISTS stg_usage_stats;
CREATE EXTERNAL TABLE stg_usage_stats (
  customer_id STRING, avg_minutes DOUBLE, avg_data_gb DOUBLE, avg_sms INT, dropped_calls INT)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n'
STORED AS TEXTFILE
LOCATION '/user/hive/staging/usage_stats'
TBLPROPERTIES ('skip.header.line.count'='1');

DROP TABLE IF EXISTS stg_support_tickets;
CREATE EXTERNAL TABLE stg_support_tickets (
  ticket_id STRING, customer_id STRING, category STRING, resolution_hours DOUBLE, created_date STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n'
STORED AS TEXTFILE
LOCATION '/user/hive/staging/support_tickets'
TBLPROPERTIES ('skip.header.line.count'='1');

-- ---------- ORC TABLES (columnar, compressed) ----------
-- customers: PARTITIONED BY contract (most common filter / group-by dimension)
DROP TABLE IF EXISTS customers;
CREATE TABLE customers (
  customer_id STRING, gender STRING, senior_citizen INT, partner STRING, dependents STRING,
  tenure_months INT, phone_service STRING, multiple_lines STRING, internet_service STRING,
  online_security STRING, tech_support STRING, streaming_tv STRING,
  paperless_billing STRING, payment_method STRING, monthly_charges DOUBLE, total_charges DOUBLE,
  state STRING, churn STRING)
PARTITIONED BY (contract STRING)
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

DROP TABLE IF EXISTS usage_stats;
CREATE TABLE usage_stats (
  customer_id STRING, avg_minutes DOUBLE, avg_data_gb DOUBLE, avg_sms INT, dropped_calls INT)
STORED AS ORC TBLPROPERTIES ('orc.compress'='SNAPPY');

-- tickets: PARTITIONED BY month of creation
DROP TABLE IF EXISTS support_tickets;
CREATE TABLE support_tickets (
  ticket_id STRING, customer_id STRING, category STRING, resolution_hours DOUBLE, created_date STRING)
PARTITIONED BY (created_month STRING)
STORED AS ORC TBLPROPERTIES ('orc.compress'='SNAPPY');
