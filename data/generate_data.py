"""Generates synthetic telecom data: customers, usage_stats, support_tickets (CSV, with header)."""
import csv, random
from datetime import date, timedelta
random.seed(42)
N = 5000
STATES = ["Tamil Nadu","Karnataka","Kerala","Andhra Pradesh","Telangana","Maharashtra","Delhi","Gujarat","West Bengal","Rajasthan"]
PAY = ["Electronic check","Mailed check","Bank transfer","Credit card","UPI"]
yn = lambda p: "Yes" if random.random() < p else "No"

customers, usage, tickets = [], [], []
tid = 1
for i in range(1, N + 1):
    cid = f"C{i:05d}"
    senior = 1 if random.random() < 0.16 else 0
    contract = random.choices(["Month-to-month","One year","Two year"], [0.55, 0.25, 0.20])[0]
    tenure = random.randint(1, 72) if contract != "Month-to-month" else int(min(71, random.expovariate(1/20)) + 1)
    internet = random.choices(["Fiber optic","DSL","No"], [0.44, 0.34, 0.22])[0]
    phone = yn(0.9)
    multi = yn(0.4) if phone == "Yes" else "No"
    sec = yn(0.3) if internet != "No" else "No"
    tech = yn(0.3) if internet != "No" else "No"
    stv = yn(0.45) if internet != "No" else "No"
    paperless = yn(0.6)
    pay = random.choice(PAY)
    monthly = 150 + (350 if phone == "Yes" else 0) + {"Fiber optic":650,"DSL":400,"No":0}[internet]
    monthly += 80*(multi=="Yes") + 60*(sec=="Yes") + 60*(tech=="Yes") + 120*(stv=="Yes") + random.randint(-40, 60)
    total = round(monthly * tenure * random.uniform(0.95, 1.05), 2)

    n_tix = max(0, int(random.gauss(1.0 + (1.2 if internet == "Fiber optic" else 0), 1.3)))
    z = -2.2
    z += 1.3*(contract == "Month-to-month") - 0.9*(contract == "Two year")
    z += 0.8*(internet == "Fiber optic") - 0.04*tenure + 0.4*(pay == "Electronic check")
    z += 0.3*senior - 0.5*(sec == "Yes") - 0.5*(tech == "Yes") + 0.003*(monthly - 800) + 0.35*n_tix
    churn = "Yes" if random.random() < 1/(1+2.718**(-z)) else "No"

    customers.append([cid, random.choice(["Male","Female"]), senior, yn(0.5), yn(0.3), tenure, phone, multi,
                      internet, sec, tech, stv, contract, paperless, pay, round(monthly,2), total,
                      random.choice(STATES), churn])
    usage.append([cid, round(max(30, random.gauss(420 if phone=="Yes" else 60, 150)),1),
                  round(0 if internet=="No" else max(1, random.gauss(55 if internet=="Fiber optic" else 28, 20)),1),
                  max(0, int(random.gauss(90, 50))), max(0, int(random.gauss(2.5 + 2*(churn=="Yes"), 2)))])
    for _ in range(n_tix):
        tickets.append([f"T{tid:06d}", cid, random.choices(["Network","Billing","Plan change","Device","Service quality"],[.3,.25,.15,.1,.2])[0],
                        round(random.expovariate(1/(30 if churn=="Yes" else 14)) + 1, 1),
                        (date(2026,1,1)+timedelta(days=random.randint(0,270))).isoformat()])
        tid += 1

def w(name, header, rows):
    with open(f"data/{name}.csv","w",newline="") as f:
        cw = csv.writer(f); cw.writerow(header); cw.writerows(rows)
w("customers", ["customer_id","gender","senior_citizen","partner","dependents","tenure_months","phone_service","multiple_lines","internet_service","online_security","tech_support","streaming_tv","contract","paperless_billing","payment_method","monthly_charges","total_charges","state","churn"], customers)
w("usage_stats", ["customer_id","avg_minutes","avg_data_gb","avg_sms","dropped_calls"], usage)
w("support_tickets", ["ticket_id","customer_id","category","resolution_hours","created_date"], tickets)
print(f"customers={len(customers)} usage={len(usage)} tickets={len(tickets)}")
