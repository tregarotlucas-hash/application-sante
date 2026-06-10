#!/usr/bin/env python3
"""
eBay Handbag Price Estimator
Uses eBay Browse API (OAuth 2.0 client credentials) to search sold/active listings.

Setup:
  1. Create a free eBay developer account at https://developer.ebay.com
  2. Create an app and get your App ID (Client ID) and Client Secret
  3. Set env vars:  EBAY_CLIENT_ID  and  EBAY_CLIENT_SECRET
     or pass them as CLI args:  python3 ebay_handbag_pricer.py --client-id ... --client-secret ...

eBay Browse API docs: https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search
"""

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Optional

import requests


# ──────────────────────────────────────────────
# eBay OAuth token endpoint (production)
# ──────────────────────────────────────────────
EBAY_AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_BROWSE_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

# Handbag category ID on eBay (Women > Bags, Handbags & Cases)
HANDBAG_CATEGORY_ID = "169291"

# Condition filter mapping (eBay conditionIds)
CONDITION_MAP = {
    "neuf":         ["NEW"],
    "comme neuf":   ["NEW"],
    "très bon":     ["LIKE_NEW", "EXCELLENT"],
    "bon":          ["VERY_GOOD", "GOOD"],
    "acceptable":   ["ACCEPTABLE", "FOR_PARTS_OR_NOT_WORKING"],
    "occasion":     ["LIKE_NEW", "EXCELLENT", "VERY_GOOD", "GOOD", "ACCEPTABLE"],
}


@dataclass
class Listing:
    title: str
    price: float
    currency: str
    condition: str
    url: str
    image: str
    sold: bool


def get_oauth_token(client_id: str, client_secret: str) -> str:
    resp = requests.post(
        EBAY_AUTH_URL,
        data={"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"},
        auth=(client_id, client_secret),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def search_listings(
    token: str,
    model: str,
    condition: str,
    material: str,
    year: str,
    limit: int = 20,
) -> list[Listing]:
    parts = [model]
    if material:
        parts.append(material)
    if year:
        parts.append(year)
    query = " ".join(parts)

    norm = condition.lower().strip()
    conditions = CONDITION_MAP.get(norm, [])

    params: dict = {
        "q": query,
        "category_ids": HANDBAG_CATEGORY_ID,
        "limit": limit,
        "sort": "newlyListed",
        "fieldgroups": "MATCHING_ITEMS",
    }
    if conditions:
        params["filter"] = "conditionIds:{" + "|".join(conditions) + "}"

    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_FR",
        "X-EBAY-C-ENDUSERCTX": "contextualLocation=country=FR",
        "Content-Type": "application/json",
    }

    print(f"\n🔍 Recherche : {query}  |  État : {condition}")
    print(f"📡 eBay Browse API — {limit} résultats demandés\n")

    resp = requests.get(EBAY_BROWSE_URL, params=params, headers=headers, timeout=15)

    if resp.status_code == 400:
        print("⚠️  Réponse eBay :", resp.text[:400])
    resp.raise_for_status()

    data = resp.json()
    items = data.get("itemSummaries", [])

    listings = []
    for item in items:
        price_info = item.get("price", {})
        price_val = float(price_info.get("value", 0))
        currency = price_info.get("currency", "EUR")
        url = item.get("itemWebUrl", "")
        image = item.get("image", {}).get("imageUrl", "")
        cond = item.get("condition", "—")
        title = item.get("title", "—")

        listings.append(
            Listing(
                title=title,
                price=price_val,
                currency=currency,
                condition=cond,
                url=url,
                image=image,
                sold=False,
            )
        )

    return listings


def compute_stats(prices: list[float]) -> dict:
    if not prices:
        return {}
    s = sorted(prices)
    n = len(s)
    mean = sum(s) / n
    median = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    p10 = s[max(0, int(n * 0.10))]
    p90 = s[min(n - 1, int(n * 0.90))]
    return {
        "Nombre de résultats": n,
        "Prix minimum": round(s[0], 2),
        "Prix maximum": round(s[-1], 2),
        "Moyenne": round(mean, 2),
        "Médiane": round(median, 2),
        "Fourchette basse (P10)": round(p10, 2),
        "Fourchette haute (P90)": round(p90, 2),
    }


def display_results(listings: list[Listing], model: str, condition: str):
    if not listings:
        print("❌ Aucun résultat. Essayez avec des termes plus généraux.")
        return

    print(f"{'='*70}")
    print(f"  Résultats pour : {model}  |  État : {condition}")
    print(f"{'='*70}\n")

    for i, lst in enumerate(listings, 1):
        print(f"[{i:02d}] {lst.title[:65]}")
        print(f"     💶 {lst.price:.2f} {lst.currency}  |  État : {lst.condition}")
        print(f"     🔗 {lst.url}")
        print()

    prices = [lst.price for lst in listings if lst.price > 0]
    stats = compute_stats(prices)

    print(f"{'─'*70}")
    print("  STATISTIQUES DE PRIX")
    print(f"{'─'*70}")
    for k, v in stats.items():
        print(f"  {k:<35} {v} €")

    p10 = stats.get("Fourchette basse (P10)", 0)
    p90 = stats.get("Fourchette haute (P90)", 0)
    med = stats.get("Médiane", 0)
    print(f"{'─'*70}")
    print(f"\n  📊 Fourchette recommandée : {p10:.2f} € — {p90:.2f} €  (médiane : {med:.2f} €)\n")


def main():
    parser = argparse.ArgumentParser(description="eBay Handbag Price Estimator")
    parser.add_argument("--client-id", default=os.getenv("EBAY_CLIENT_ID"), help="eBay App Client ID")
    parser.add_argument("--client-secret", default=os.getenv("EBAY_CLIENT_SECRET"), help="eBay App Client Secret")
    parser.add_argument("--model", help="Modèle du sac (ex: 'Louis Vuitton Speedy 30')")
    parser.add_argument("--condition", default="occasion", help="État du sac")
    parser.add_argument("--material", default="", help="Matière (ex: cuir)")
    parser.add_argument("--year", default="", help="Année (ex: 2019)")
    parser.add_argument("--limit", type=int, default=20, help="Nombre de résultats max")
    args = parser.parse_args()

    print("\n===  eBay Handbag Price Estimator  ===\n")

    # Interactive mode if no model provided
    if not args.model:
        args.model = input("Modèle du sac (ex: Chanel Classic Flap, Louis Vuitton Speedy 30) : ").strip()
        args.condition = input("État (neuf / comme neuf / très bon / bon / acceptable / occasion) : ").strip() or "occasion"
        args.material = input("Matière (ex: cuir, toile) [optionnel] : ").strip()
        args.year = input("Année approximative (ex: 2019) [optionnel] : ").strip()

    if not args.client_id or not args.client_secret:
        print("❌ Clés API eBay manquantes.")
        print()
        print("  Pour utiliser ce script :")
        print("  1. Créez un compte développeur GRATUIT sur https://developer.ebay.com")
        print("  2. Créez une app et récupérez le Client ID et Client Secret")
        print("  3. Exportez les variables :")
        print("       export EBAY_CLIENT_ID='votre-client-id'")
        print("       export EBAY_CLIENT_SECRET='votre-client-secret'")
        print("  4. Relancez le script")
        sys.exit(1)

    print("🔑 Authentification eBay API...")
    try:
        token = get_oauth_token(args.client_id, args.client_secret)
        print("✅ Token obtenu\n")
    except Exception as e:
        print(f"❌ Erreur d'authentification : {e}")
        sys.exit(1)

    listings = search_listings(
        token=token,
        model=args.model,
        condition=args.condition,
        material=args.material,
        year=args.year,
        limit=args.limit,
    )

    display_results(listings, model=args.model, condition=args.condition)


if __name__ == "__main__":
    main()
