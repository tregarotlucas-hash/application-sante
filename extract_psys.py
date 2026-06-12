"""
Extraction des psychologues Mon Soutien Psy – API FHIR Annuaire Santé
Stratégie : requête sur PractitionerRole (role=40) + _include pour ramener Practitioner
"""

import requests
import csv
import time

API_KEY   = "277a43fd-869d-47e0-ba43-fd869d07e020"
BASE_URL  = "https://gateway.api.esante.gouv.fr/fhir/v2"
OUTPUT    = "psys_mon_soutien_psy.csv"
PAGE_SIZE = 200

HEADERS = {
    "ESANTE-API-KEY": API_KEY,
    "Accept": "application/fhir+json"
}

CSV_COLUMNS = ["rpps", "nom", "prenom", "genre", "adresse", "code_postal", "ville", "telephone", "email"]


def get_all_pages(url, params):
    practitioners = {}
    roles = []
    next_url = url
    next_params = params
    page = 0

    while next_url:
        page += 1
        print(f"  → page {page} ({len(roles)} rôles, {len(practitioners)} praticiens)...", end="\r")
        resp = requests.get(next_url, headers=HEADERS, params=next_params, timeout=30)

        if resp.status_code != 200:
            print(f"\nErreur HTTP {resp.status_code}: {resp.text[:500]}")
            break

        bundle = resp.json()

        for entry in bundle.get("entry", []):
            res = entry.get("resource", {})
            rtype = res.get("resourceType", "")
            if rtype == "Practitioner":
                pid = res.get("id", "")
                if pid:
                    practitioners[pid] = res
            elif rtype == "PractitionerRole":
                roles.append(res)

        next_url = None
        next_params = None
        for link in bundle.get("link", []):
            if link.get("relation") == "next":
                next_url = link["url"]
                break

        time.sleep(0.3)

    print(f"\n  Total : {len(roles)} rôles, {len(practitioners)} praticiens")
    return practitioners, roles


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
        for addr in role.get("location", []):
            pass
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

    print("\n[1/3] Récupération des PractitionerRole (psychologues)...")
    url = f"{BASE_URL}/PractitionerRole"
    params = {
        "role": "40",
        "_include": "PractitionerRole:practitioner",
        "_count": PAGE_SIZE,
    }
    practitioners, roles = get_all_pages(url, params)

    print("\n[2/3] Construction des lignes...")
    rows = build_rows(practitioners, roles)

    seen, unique_rows = set(), []
    for r in rows:
        key = r["rpps"] or (r["nom"] + r["prenom"] + r["code_postal"])
        if key and key not in seen:
            seen.add(key)
            unique_rows.append(r)

    print(f"  Lignes uniques : {len(unique_rows)}")

    print(f"\n[3/3] Écriture dans {OUTPUT}...")
    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(unique_rows)

    print(f"\n✅  Terminé ! {len(unique_rows)} psychologues → {OUTPUT}")


if __name__ == "__main__":
    main()
