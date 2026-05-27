"""
Application de suivi de santé quotidien
Enregistre chaque jour : sommeil, humeur, énergie, stress, sport (note de 1 à 5)
"""

import csv
import os
from datetime import datetime

# ---------- CONFIG ----------
FICHIER_CSV = "donnees_sante.csv"

PARAMETRES = {
    "sommeil":  "😴 Qualité du sommeil",
    "humeur":   "😊 Humeur générale",
    "energie":  "⚡ Niveau d'énergie",
    "stress":   "😤 Niveau de stress",
    "sport":    "🏃 Activité physique",
}

DESCRIPTIONS = {
    1: "Très mauvais",
    2: "Mauvais",
    3: "Moyen",
    4: "Bon",
    5: "Excellent",
}


# ---------- UTILITAIRES ----------

def ligne_separatrice():
    print("─" * 45)


def demander_note(label):
    """Demande une note entre 1 et 5 pour un paramètre."""
    while True:
        print(f"\n{label}")
        print("  1 = Très mauvais  |  2 = Mauvais  |  3 = Moyen")
        print("  4 = Bon           |  5 = Excellent")
        saisie = input("  → Votre note : ").strip()
        if saisie in ("1", "2", "3", "4", "5"):
            return int(saisie)
        print("  ⚠️  Entrez un chiffre entre 1 et 5.")


def csv_existe():
    return os.path.isfile(FICHIER_CSV)


def entree_du_jour_existe():
    """Vérifie si une entrée a déjà été faite aujourd'hui."""
    if not csv_existe():
        return False
    aujourd_hui = datetime.today().strftime("%Y-%m-%d")
    with open(FICHIER_CSV, newline="", encoding="utf-8") as f:
        lecteur = csv.DictReader(f)
        for ligne in lecteur:
            if ligne.get("date") == aujourd_hui:
                return True
    return False


def initialiser_csv():
    """Crée le fichier CSV avec les en-têtes si nécessaire."""
    if not csv_existe():
        with open(FICHIER_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["date"] + list(PARAMETRES.keys()))


def enregistrer(notes):
    """Ajoute une ligne dans le CSV."""
    with open(FICHIER_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.today().strftime("%Y-%m-%d")] + notes)


def lire_donnees():
    """Retourne toutes les données sous forme de liste de dicts."""
    if not csv_existe():
        return []
    with open(FICHIER_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------- FONCTIONNALITÉS ----------

def saisie_du_jour():
    """Saisie quotidienne des notes."""
    if entree_du_jour_existe():
        print("\n✅ Tu as déjà saisi tes données aujourd'hui !")
        return

    print("\n📋 SAISIE DU JOUR —", datetime.today().strftime("%A %d %B %Y"))
    ligne_separatrice()

    notes = []
    for cle, label in PARAMETRES.items():
        note = demander_note(label)
        notes.append(note)

    initialiser_csv()
    enregistrer(notes)
    ligne_separatrice()
    print("✅ Données enregistrées ! Bonne journée 💪")


def afficher_historique():
    """Affiche toutes les entrées passées dans le terminal."""
    donnees = lire_donnees()
    if not donnees:
        print("\n📭 Aucune donnée pour l'instant.")
        return

    print("\n📅 HISTORIQUE COMPLET")
    ligne_separatrice()

    # En-tête
    entetes = ["Date"] + [p[:7].capitalize() for p in PARAMETRES.keys()]
    print("  " + "  ".join(f"{e:<10}" for e in entetes))
    ligne_separatrice()

    for ligne in donnees:
        valeurs = [ligne["date"]] + [ligne.get(p, "?") for p in PARAMETRES]
        print("  " + "  ".join(f"{v:<10}" for v in valeurs))

    ligne_separatrice()
    print(f"  Total : {len(donnees)} jour(s) enregistré(s)")


def afficher_stats():
    """Calcule et affiche les moyennes par paramètre."""
    donnees = lire_donnees()
    if not donnees:
        print("\n📭 Aucune donnée pour l'instant.")
        return

    print(f"\n📊 STATISTIQUES ({len(donnees)} jour(s))")
    ligne_separatrice()

    for cle, label in PARAMETRES.items():
        valeurs = []
        for ligne in donnees:
            try:
                valeurs.append(int(ligne[cle]))
            except (ValueError, KeyError):
                pass

        if valeurs:
            moyenne = sum(valeurs) / len(valeurs)
            mini = min(valeurs)
            maxi = max(valeurs)

            # Barre de progression visuelle
            nb_blocs = round(moyenne)
            barre = "█" * nb_blocs + "░" * (5 - nb_blocs)

            print(f"  {label}")
            print(f"    [{barre}]  Moyenne : {moyenne:.1f}/5  "
                  f"(min {mini} / max {maxi})")
        print()
    ligne_separatrice()


def afficher_graphiques():
    """Génère et sauvegarde des graphiques via matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")          # pas d'écran nécessaire
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from datetime import datetime as dt
    except ImportError:
        print("\n⚠️  matplotlib n'est pas installé.")
        print("   Lance : pip install matplotlib")
        return

    donnees = lire_donnees()
    if len(donnees) < 2:
        print("\n📭 Il faut au moins 2 entrées pour tracer un graphique.")
        return

    # Conversion des données
    dates = [dt.strptime(d["date"], "%Y-%m-%d") for d in donnees]
    couleurs = ["#6c8ebf", "#82b366", "#d6b656", "#ae4132", "#9c72b5"]

    fig, axes = plt.subplots(
        len(PARAMETRES), 1,
        figsize=(10, 3 * len(PARAMETRES)),
        sharex=True
    )
    fig.suptitle("📈 Suivi Santé Quotidien", fontsize=14, fontweight="bold")

    for idx, (cle, label) in enumerate(PARAMETRES.items()):
        valeurs = []
        for d in donnees:
            try:
                valeurs.append(int(d[cle]))
            except (ValueError, KeyError):
                valeurs.append(None)

        ax = axes[idx]
        valeurs_filtrees = [(d, v) for d, v in zip(dates, valeurs) if v is not None]
        if valeurs_filtrees:
            x, y = zip(*valeurs_filtrees)
            ax.plot(x, y, marker="o", color=couleurs[idx], linewidth=2, markersize=5)
            ax.fill_between(x, y, alpha=0.15, color=couleurs[idx])

        ax.set_ylabel(label.split(" ", 1)[-1], fontsize=9)
        ax.set_ylim(0.5, 5.5)
        ax.set_yticks(range(1, 6))
        ax.yaxis.grid(True, linestyle="--", alpha=0.5)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    fig.autofmt_xdate()
    plt.tight_layout()

    nom_fichier = "graphique_sante.png"
    plt.savefig(nom_fichier, dpi=120, bbox_inches="tight")
    plt.close()

    print(f"\n✅ Graphique sauvegardé : {nom_fichier}")


# ---------- MENU PRINCIPAL ----------

def afficher_menu():
    print("\n╔══════════════════════════════════════════╗")
    print("║       🏥  SUIVI SANTÉ QUOTIDIEN          ║")
    print("╠══════════════════════════════════════════╣")
    print("║  1 → Saisie du jour                      ║")
    print("║  2 → Voir l'historique                   ║")
    print("║  3 → Statistiques                        ║")
    print("║  4 → Générer les graphiques (PNG)         ║")
    print("║  0 → Quitter                             ║")
    print("╚══════════════════════════════════════════╝")


def main():
    while True:
        afficher_menu()
        choix = input("  Votre choix : ").strip()

        if choix == "1":
            saisie_du_jour()
        elif choix == "2":
            afficher_historique()
        elif choix == "3":
            afficher_stats()
        elif choix == "4":
            afficher_graphiques()
        elif choix == "0":
            print("\n👋 À demain pour ton suivi !\n")
            break
        else:
            print("  ⚠️  Choix invalide, réessaie.")


if __name__ == "__main__":
    main()
