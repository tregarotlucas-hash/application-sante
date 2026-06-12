"""
Extraction des psychologues – API FHIR Annuaire Santé
Stratégie en 2 étapes :
  1. Récupérer tous les Practitioner avec qualification-code=40
  2. Récupérer leurs PractitionerRole par lots (paramètre 'practitioner')
"""

import requests
import csv
import time

API_KEY   = "277a43fd-869d-47e0-ba43-fd869d07e020"
BASE_URL  = "https://gateway.api.esante.gouv.fr/fhir/v2"
OUTPUT    = "psys_mon_soutien_psy.csv"
PAGE_SIZE = 200
BATCH_SIZE = 50  # nb d'IDs par requête PractitionerRole

HEADERS = {
    "ESANTE-API-KEY": API_KEY,
    "Accept": "application/fhir+json"
}

CSV_COLUMNS = ["rpps", "nom", "prenom", "genre", "adresse", "code_postal", "ville", "telephone", "email"]


def fetch_bundle(url, params=None):
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"\nErreur HTTP {resp.status_code}: {resp.text[:300]}")
        return None
    import json
    return json.loads(resp.content, strict=False)


def get_practitioners():
    """Étape 1 : tous les Practitioner psychologues (qualification-code=40)."""
    practitioners = {}
    next_url = f"{BASE_URL}/Practitioner"
    next_params = {"qualification-code": "40", "_count": PAGE_SIZE}
    page = 0

    while next_url:
        page += 1
        print(f"  → page {page} ({len(practitioners)} praticiens)...", end="\r")
        bundle = fetch_bundle(next_url, next_params)
        if not bundle:
            break

        for entry in bundle.get("entry", []):
            res = entry.get("resource", {})
            if res.get("resourceType") == "Practitioner":
                pid = res.get("id", "")
                if pid:
                    practitioners[pid] = res

        next_url, next_params = None, None
        for link in bundle.get("link", []):
            if link.get("relation") == "next":
                next_url = link["url"]
                break
        time.sleep(0.2)

    print(f"\n  Total praticiens : {len(practitioners)}")
    return practitioners


def get_roles_for_batch(ids):
    """Requête PractitionerRole pour un lot d'IDs."""
    roles = []
    next_url = f"{BASE_URL}/PractitionerRole"
    next_params = {
        "practitioner": ",".join(ids),
        "_count": PAGE_SIZE,
    }

    while next_url:
        bundle = fetch_bundle(next_url, next_params)
        if not bundle:
            break
        for entry in bundle.get("entry", []):
            res = entry.get("resource", {})
            if res.get("resourceType") == "PractitionerRole":
                roles.append(res)
        next_url, next_params = None, None
        for link in bundle.get("link", []):
            if link.get("relation") == "next":
                next_url = link["url"]
                break
        time.sleep(0.2)
    return roles


def get_all_roles(practitioners):
    """Étape 2 : PractitionerRole pour tous les praticiens, par lots."""
    ids = list(practitioners.keys())
    roles = []
    total_batches = (len(ids) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(ids), BATCH_SIZE):
        batch = ids[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"  → lot {batch_num}/{total_batches} ({len(roles)} rôles)...", end="\r")
        roles.extend(get_roles_for_batch(batch))

    print(f"\n  Total rôles : {len(roles)}")
    return roles


def build_rows(practitioners, roles):
    rows = []
    for role in roles:
        ref = role.get("practitioner", {}).get("reference", "")
        pid = ref.replace("Practitioner/", "")
        prac = practitioners.get(pid, {})

        rpps = ""
        for ident in prac.get("identifier", []):
            if "rpps" in ident.get("system", "").lower():
                rpps = ident.get("value", "")
                break

        nom, prenom = "", ""
        for name in prac.get("name", []):
            nom    = name.get("family", "").upper()
            prenom = " ".join(name.get("given", [])).title()
            break

        genre = {"male": "H", "female": "F"}.get(prac.get("gender", ""), "")

        adresse, code_postal, ville = "", "", ""
        for addr in role.get("address", []):
            adresse     = " ".join(addr.get("line", []))
            code_postal = addr.get("postalCode", "")
            ville       = addr.get("city", "")
            break

        telephone, email = "", ""
        for tc in role.get("telecom", []):
            s, v = tc.get("system", ""), tc.get("value", "")
            if s == "phone" and not telephone:
                telephone = v
            elif s == "email" and not email:
                email = v

        rows.append({
            "rpps": rpps, "nom": nom, "prenom": prenom, "genre": genre,
            "adresse": adresse, "code_postal": code_postal, "ville": ville,
            "telephone": telephone, "email": email
        })
    return rows


def main():
    print("=" * 55)
    print("  Extraction Psychologues – API FHIR Annuaire Santé")
    print("=" * 55)

    print("\n[1/4] Récupération des praticiens (qualification-code=40)...")
    practitioners = get_practitioners()

    print("\n[2/4] Récupération des rôles / lieux d'exercice...")
    roles = get_all_roles(practitioners)

    print("\n[3/4] Construction des lignes...")
    rows = build_rows(practitioners, roles)

    seen, unique_rows = set(), []
    for r in rows:
        key = r["rpps"] or (r["nom"] + r["prenom"] + r["code_postal"])
        if key and key not in seen:
            seen.add(key)
            unique_rows.append(r)
    print(f"  Lignes uniques : {len(unique_rows)}")

    print(f"\n[4/4] Écriture dans {OUTPUT}...")
    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(unique_rows)

    print(f"\n✅  Terminé ! {len(unique_rows)} psychologues → {OUTPUT}")


if __name__ == "__main__":
    main()
