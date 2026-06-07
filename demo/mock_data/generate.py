"""Generate mock Colmena data with valid Chilean RUTs."""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
OUT = Path(__file__).parent

def rut_dv(num: int) -> str:
    s, m = 0, 2
    for d in reversed(str(num)):
        s += int(d) * m
        m = 2 if m == 7 else m + 1
    r = 11 - (s % 11)
    return "0" if r == 11 else "K" if r == 10 else str(r)

def gen_rut() -> str:
    n = random.randint(5_000_000, 25_000_000)
    return f"{n}-{rut_dv(n)}"

FIRST = ["Juan", "Maria", "Pedro", "Ana", "Luis", "Carmen", "Jorge", "Patricia",
        "Carlos", "Sofia", "Diego", "Valentina", "Andres", "Francisca", "Felipe"]
LAST = ["Gonzalez", "Munoz", "Rojas", "Diaz", "Perez", "Soto", "Contreras",
        "Silva", "Martinez", "Sepulveda", "Morales", "Rodriguez", "Lopez", "Fuentes"]
COMUNAS = ["Las Condes", "Providencia", "Nunoa", "Vitacura", "Santiago Centro",
           "La Florida", "Maipu", "Penalolen", "La Reina", "Macul"]

# -------- dim_party --------
N_PARTIES = 1500
parties = []
for i in range(1, N_PARTIES + 1):
    fn = random.choice(FIRST)
    ln1 = random.choice(LAST)
    ln2 = random.choice(LAST)
    parties.append({
        "party_id":   f"PTY-{i:06d}",
        "rut":        gen_rut(),
        "full_name":  f"{fn} {ln1} {ln2}",
        "email":      f"{fn.lower()}.{ln1.lower()}{i}@mail.cl",
        "phone":      f"+569{random.randint(50000000, 99999999)}",
        "comuna":     random.choice(COMUNAS),
        "birth_date": (date(1960,1,1) + timedelta(days=random.randint(0, 20000))).isoformat(),
    })

with open(OUT/"dim_party.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=parties[0].keys())
    w.writeheader(); w.writerows(parties)

# -------- dim_product --------
PRODUCTS = [
    ("PRD-001", "ISAPRE-BASICO",    "Plan Salud Basico",      "Salud",   45000),
    ("PRD-002", "ISAPRE-PREMIUM",   "Plan Salud Premium",     "Salud",   120000),
    ("PRD-003", "ISAPRE-FAMILIAR",  "Plan Salud Familiar",    "Salud",   85000),
    ("PRD-004", "VIDA-INDIVIDUAL",  "Seguro Vida Individual", "Vida",    25000),
    ("PRD-005", "VIDA-GRUPAL",      "Seguro Vida Grupal",     "Vida",    18000),
    ("PRD-006", "DENTAL-PLUS",      "Plan Dental Plus",       "Dental",  15000),
]
with open(OUT/"dim_product.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["product_id","product_code","product_name","category","base_premium_clp"])
    w.writerows(PRODUCTS)

# -------- dim_policy --------
N_POLICIES = 2200
policies = []
for i in range(1, N_POLICIES + 1):
    party = random.choice(parties)
    prod  = random.choice(PRODUCTS)
    start = date(2022,1,1) + timedelta(days=random.randint(0, 1200))
    policies.append({
        "policy_id":       f"POL-{1000000000+i}",
        "party_id":        party["party_id"],
        "product_id":      prod[0],
        "start_date":      start.isoformat(),
        "end_date":        (start + timedelta(days=365)).isoformat(),
        "monthly_premium_clp": prod[4] + random.randint(-5000, 15000),
        "status":          random.choices(["ACTIVE","CANCELLED","EXPIRED"], [0.78,0.10,0.12])[0],
    })

with open(OUT/"dim_policy.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=policies[0].keys())
    w.writeheader(); w.writerows(policies)

# -------- fact_policy_monthly --------
fact_pm = []
for p in policies:
    if p["status"] == "ACTIVE":
        months = 6
    else:
        months = random.randint(1, 12)
    sd = date.fromisoformat(p["start_date"])
    for m in range(months):
        fact_pm.append({
            "policy_id":      p["policy_id"],
            "month_date":     date(sd.year + (sd.month + m - 1)//12,
                                   ((sd.month + m - 1) % 12) + 1, 1).isoformat(),
            "premium_paid_clp": p["monthly_premium_clp"] if random.random() > 0.05 else 0,
            "is_paid":        random.random() > 0.05,
        })

with open(OUT/"fact_policy_monthly.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fact_pm[0].keys())
    w.writeheader(); w.writerows(fact_pm)

# -------- fact_claim --------
CLAIM_TYPES = ["CONSULTA_MEDICA","HOSPITALIZACION","EXAMEN","MEDICAMENTO","DENTAL","URGENCIA"]
claims = []
n_claims = N_POLICIES // 3
for i in range(1, n_claims + 1):
    p = random.choice(policies)
    cd = date.fromisoformat(p["start_date"]) + timedelta(days=random.randint(10, 350))
    claims.append({
        "claim_id":     f"CLM-{cd.year}-{i:06d}",
        "policy_id":    p["policy_id"],
        "party_id":     p["party_id"],
        "claim_date":   cd.isoformat(),
        "claim_type":   random.choice(CLAIM_TYPES),
        "claim_amount_clp": random.randint(15000, 4500000),
        "status":       random.choices(["APPROVED","REJECTED","PENDING"], [0.75,0.10,0.15])[0],
    })

with open(OUT/"fact_claim.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=claims[0].keys())
    w.writeheader(); w.writerows(claims)

print(f"dim_party:           {len(parties)}")
print(f"dim_product:         {len(PRODUCTS)}")
print(f"dim_policy:          {len(policies)}")
print(f"fact_policy_monthly: {len(fact_pm)}")
print(f"fact_claim:          {len(claims)}")
print(f"sample RUT: {parties[0]['rut']}")
print(f"sample policy: {policies[0]['policy_id']}")
print(f"sample claim:  {claims[0]['claim_id']}")
