# Agenda Google — Placeholder déjeuner

Lit votre Google Calendar et ajoute automatiquement un événement **"🍽️ Pause déjeuner"**
de 12h à 13h si le créneau est libre.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration (une seule fois)

1. Ouvrez [Google Cloud Console](https://console.cloud.google.com)
2. Créez un projet (ou sélectionnez-en un existant)
3. Activez l'**API Google Calendar**
4. Allez dans **APIs & Services → Credentials**
5. Créez un identifiant **OAuth 2.0** de type **"Application de bureau"**
6. Téléchargez le fichier JSON et renommez-le `credentials.json` dans ce dossier

## Utilisation

```bash
python agenda.py
```

La première fois, un navigateur s'ouvre pour vous authentifier.
Le token est ensuite sauvegardé dans `token.json` (ne le partagez pas).

## Automatisation (optionnel)

Pour que le script tourne chaque jour à 8h (Linux/macOS) :

```bash
crontab -e
# Ajouter :
0 8 * * 1-5 cd /chemin/vers/application-sante && python agenda.py
```
