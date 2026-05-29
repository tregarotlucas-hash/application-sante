"""
Scraper PAP - nombre d'annonces et prix moyen au m²
Dépendances : pip install playwright && playwright install chromium
"""

import asyncio
import re
from playwright.async_api import async_playwright

URL = "https://www.pap.fr/annonce/locations-appartement-paris-75-g439-2-pieces-jusqu-a-2000-euros"


async def scrape_pap():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )

        print(f"Chargement de la page...")
        await page.goto(URL, wait_until="networkidle", timeout=30000)

        # Scroll pour charger les annonces lazy-loaded
        for _ in range(5):
            await page.keyboard.press("End")
            await asyncio.sleep(1)

        content = await page.content()
        await browser.close()

    # Extraction du nombre total d'annonces
    total_match = re.search(r"([\d\s]+)\s*annonce", content, re.IGNORECASE)
    total = total_match.group(0).strip() if total_match else "Non trouvé"

    # Extraction des prix et surfaces depuis le HTML brut
    # PAP affiche les prix sous forme "X XXX €/mois" et surfaces "XX m²"
    prix_list = [int(p.replace(" ", "").replace(" ", ""))
                 for p in re.findall(r"([\d  ]{3,6})\s*€/mois", content)]

    surfaces_list = [int(s) for s in re.findall(r"(\d{2,3})\s*m²", content)]

    print(f"\n{'='*40}")
    print(f"Nombre d'annonces trouvées   : {total}")
    print(f"Prix extraits                : {len(prix_list)}")
    print(f"Surfaces extraites           : {len(surfaces_list)}")

    if prix_list and surfaces_list:
        # Associe prix et surfaces (on prend le minimum des deux listes)
        pairs = list(zip(prix_list, surfaces_list))
        prix_m2_list = [p / s for p, s in pairs if s > 0]

        if prix_m2_list:
            print(f"\nPrix moyen au m²/mois        : {sum(prix_m2_list)/len(prix_m2_list):.1f} €/m²")
            print(f"Prix min au m²/mois          : {min(prix_m2_list):.1f} €/m²")
            print(f"Prix max au m²/mois          : {max(prix_m2_list):.1f} €/m²")
            print(f"\nDétail des annonces :")
            for i, (prix, surface) in enumerate(pairs[:len(prix_m2_list)], 1):
                print(f"  {i:2}. {surface} m² - {prix} €/mois - {prix/surface:.1f} €/m²")
    else:
        print("\nAucune donnée prix/surface extraite (structure HTML peut-être différente).")
        print("Conseil : relance avec headless=False pour inspecter la page manuellement.")


if __name__ == "__main__":
    asyncio.run(scrape_pap())
