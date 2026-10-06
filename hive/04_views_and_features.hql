-- 04: Feature tables / views used by the API
USE telecom_churn;

-- Ticket aggregates per customer
DROP VIEW IF EXISTS v_ticket_summary;
CREATE VIEW v_ticket_summary AS
SELECT customer_id, COUNT(*) AS ticket_count, ROUND(AVG(resolution_hours),1) AS avg_resolution_hours
FROM support_tickets GROUP BY customer_id;

-- Customer 360: every attribute in one place
DROP VIEW IF EXISTS v_customer_360;
CREATE VIEW v_customer_360 AS
SELECT c.*, u.avg_minutes, u.avg_data_gb, u.avg_sms, u.dropped_calls,
       COALESCE(t.ticket_count,0) AS ticket_count,
       COALESCE(t.avg_resolution_hours,0) AS avg_resolution_hours,
       CASE WHEN c.tenure_months <= 12 THEN '0-12'
            WHEN c.tenure_months <= 24 THEN '13-24'
            WHEN c.tenure_months <= 48 THEN '25-48'
            ELSE '49-72' END AS tenure_band,
       CASE WHEN c.monthly_charges < 600 THEN 'Low (<600)'
            WHEN c.monthly_charges < 1100 THEN 'Medium (600-1100)'
            ELSE 'High (>1100)' END AS charge_band
FROM customers c
LEFT JOIN usage_stats u ON c.customer_id = u.customer_id
LEFT JOIN v_ticket_summary t ON c.customer_id = t.customer_id;

-- Rule-based churn risk score (0-100) for ACTIVE customers
DROP VIEW IF EXISTS v_churn_risk;
CREATE VIEW v_churn_risk AS
SELECT customer_id, contract, internet_service, payment_method, tenure_months, monthly_charges,
       ticket_count, dropped_calls, state,
       ( CASE WHEN contract='Month-to-month' THEN 30 WHEN contract='One year' THEN 10 ELSE 0 END
       + CASE WHEN tenure_months <= 12 THEN 20 WHEN tenure_months <= 24 THEN 10 ELSE 0 END
       + CASE WHEN internet_service='Fiber optic' THEN 10 ELSE 0 END
       + CASE WHEN payment_method='Electronic check' THEN 10 ELSE 0 END
       + CASE WHEN online_security='No' AND internet_service<>'No' THEN 5 ELSE 0 END
       + CASE WHEN tech_support='No' AND internet_service<>'No' THEN 5 ELSE 0 END
       + CASE WHEN ticket_count >= 3 THEN 15 WHEN ticket_count = 2 THEN 8 ELSE 0 END
       + CASE WHEN dropped_calls >= 5 THEN 5 ELSE 0 END ) AS risk_score
FROM v_customer_360
WHERE churn = 'No';

-- Materialised summary (CTAS) – fast dashboard reads
DROP TABLE IF EXISTS churn_summary_by_segment;
CREATE TABLE churn_summary_by_segment STORED AS ORC AS
SELECT contract, internet_service, payment_method, tenure_band,
       COUNT(*) AS customers,
       SUM(CASE WHEN churn='Yes' THEN 1 ELSE 0 END) AS churned,
       ROUND(100*SUM(CASE WHEN churn='Yes' THEN 1 ELSE 0 END)/COUNT(*),2) AS churn_rate,
       ROUND(SUM(CASE WHEN churn='Yes' THEN monthly_charges ELSE 0 END),2) AS revenue_lost
FROM v_customer_360
GROUP BY contract, internet_service, payment_method, tenure_band;
