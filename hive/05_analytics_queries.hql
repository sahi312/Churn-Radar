-- 05: Analytics queries (CTEs, window functions, rollups, percentiles)
USE telecom_churn;

-- Q1. Overall KPIs
SELECT COUNT(*) total_customers,
       SUM(CASE WHEN churn='Yes' THEN 1 ELSE 0 END) churned,
       ROUND(100*SUM(CASE WHEN churn='Yes' THEN 1 ELSE 0 END)/COUNT(*),2) churn_rate_pct,
       ROUND(SUM(CASE WHEN churn='Yes' THEN monthly_charges ELSE 0 END),0) monthly_revenue_lost,
       ROUND(AVG(monthly_charges),0) arpu
FROM customers;

-- Q2. Churn by contract / internet / payment
SELECT contract, COUNT(*) customers,
       ROUND(100*SUM(CASE WHEN churn='Yes' THEN 1 ELSE 0 END)/COUNT(*),2) churn_rate
FROM customers GROUP BY contract ORDER BY churn_rate DESC;

-- Q3. Rank segments by revenue lost (window function)
SELECT contract, internet_service, revenue_lost,
       RANK() OVER (ORDER BY revenue_lost DESC) AS rnk
FROM (SELECT contract, internet_service,
             SUM(CASE WHEN churn='Yes' THEN monthly_charges ELSE 0 END) revenue_lost
      FROM customers GROUP BY contract, internet_service) s;

-- Q4. Rollup / cube for BI drill-down
SELECT contract, internet_service, COUNT(*) customers,
       ROUND(100*SUM(CASE WHEN churn='Yes' THEN 1 ELSE 0 END)/COUNT(*),2) churn_rate
FROM customers GROUP BY contract, internet_service WITH ROLLUP;

-- Q5. Customer value deciles with NTILE
SELECT decile, COUNT(*) customers,
       ROUND(100*SUM(CASE WHEN churn='Yes' THEN 1 ELSE 0 END)/COUNT(*),2) churn_rate
FROM (SELECT churn, NTILE(10) OVER (ORDER BY monthly_charges) decile FROM customers) x
GROUP BY decile ORDER BY decile;

-- Q6. Tenure cohort analysis
SELECT tenure_band, COUNT(*) customers,
       ROUND(100*SUM(CASE WHEN churn='Yes' THEN 1 ELSE 0 END)/COUNT(*),2) churn_rate
FROM v_customer_360 GROUP BY tenure_band ORDER BY tenure_band;

-- Q7. Support tickets vs churn
SELECT LEAST(ticket_count,5) tickets, COUNT(*) customers,
       ROUND(100*SUM(CASE WHEN churn='Yes' THEN 1 ELSE 0 END)/COUNT(*),2) churn_rate
FROM v_customer_360 GROUP BY LEAST(ticket_count,5) ORDER BY tickets;

-- Q8. Monthly ticket trend with month-over-month growth (LAG)
SELECT created_month, tickets,
       tickets - LAG(tickets) OVER (ORDER BY created_month) AS mom_change
FROM (SELECT created_month, COUNT(*) tickets FROM support_tickets GROUP BY created_month) m;

-- Q9. Median / P90 resolution hours by category (Hive percentile)
SELECT category, COUNT(*) tickets, ROUND(AVG(resolution_hours),1) avg_hrs,
       percentile_approx(resolution_hours, 0.5) median_hrs,
       percentile_approx(resolution_hours, 0.9) p90_hrs
FROM support_tickets GROUP BY category;

-- Q10. Top 20 at-risk active customers (retention campaign list)
SELECT * FROM v_churn_risk ORDER BY risk_score DESC, monthly_charges DESC LIMIT 20;

-- Q11. Early-warning: top 3 risky customers per state (ROW_NUMBER)
SELECT * FROM (
  SELECT state, customer_id, risk_score,
         ROW_NUMBER() OVER (PARTITION BY state ORDER BY risk_score DESC) rn
  FROM v_churn_risk) r WHERE rn <= 3;
