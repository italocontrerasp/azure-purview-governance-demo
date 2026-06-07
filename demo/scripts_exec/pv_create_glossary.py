"""Create the Colmena business glossary in Purview.

Terms:
  - Poliza       (POL-* en sistemas, contrato de cobertura)
  - Siniestro    (CLM-*, evento que dispara cobertura)
  - Beneficiario (party_id, persona natural cubierta)
  - Prima        (monthly_premium_clp, pago periodico)
"""
import requests, json
from pathlib import Path

SECRETS = Path(__file__).resolve().parent.parent / ".secrets"
EP   = "https://pv-italodemo-16de97.purview.azure.com"
TOK  = (SECRETS / "pv_token.txt").read_text().strip()
H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}

# create glossary "Colmena"
glos_body = {"name": "Colmena",
             "shortDescription": "Glosario de negocio para el dominio Colmena",
             "language": "es"}
r = requests.post(f"{EP}/catalog/api/atlas/v2/glossary", json=glos_body, headers=H)
print("glossary:", r.status_code, r.text[:200])
glossary_guid = r.json().get("guid")

TERMS = [
    ("Poliza",        "Contrato de cobertura entre la aseguradora y el beneficiario. Identificada por un policy_id con formato POL-NNNNNNNNNN."),
    ("Siniestro",     "Evento cubierto por una poliza que dispara una solicitud de pago. Identificado por claim_id con formato CLM-YYYY-NNNNNN."),
    ("Beneficiario",  "Persona natural titular o cubierta por una poliza. Identificado por party_id y RUT chileno."),
    ("Prima",         "Pago periodico (mensual) que el beneficiario abona a la aseguradora a cambio de cobertura."),
    ("RUT",           "Rol Unico Tributario: identificador nacional chileno con formato NNNNNNNN-D donde D es el digito verificador."),
]

for name, desc in TERMS:
    body = {
        "name": name,
        "longDescription": desc,
        "anchor": {"glossaryGuid": glossary_guid},
        "status": "Approved",
    }
    r = requests.post(f"{EP}/catalog/api/atlas/v2/glossary/term", json=body, headers=H)
    print(f"term {name:15s} -> {r.status_code} guid={r.json().get('guid','?')}")
