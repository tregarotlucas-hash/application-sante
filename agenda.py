#!/usr/bin/env python3
"""
Lit Google Calendar et ajoute un placeholder "Pause déjeuner" à midi
si le créneau 12h-13h est libre.

Première utilisation :
  1. Créer un projet sur https://console.cloud.google.com
  2. Activer l'API Google Calendar
  3. Créer des identifiants OAuth 2.0 (type "Application de bureau")
  4. Télécharger le fichier credentials.json dans ce dossier
  5. Lancer : python agenda.py
"""

import os
import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

LUNCH_TITLE = "🍽️ Pause déjeuner"
LUNCH_START_HOUR = 12
LUNCH_END_HOUR = 13


def get_credentials():
    creds = None
    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def get_today_bounds():
    today = datetime.date.today()
    start = datetime.datetime(today.year, today.month, today.day, 0, 0, 0)
    end = datetime.datetime(today.year, today.month, today.day, 23, 59, 59)
    tz = datetime.timezone.utc
    return start.replace(tzinfo=tz), end.replace(tzinfo=tz)


def list_today_events(service):
    start, end = get_today_bounds()
    result = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return result.get("items", [])


def is_lunch_slot_free(events):
    today = datetime.date.today()
    lunch_start = datetime.datetime(today.year, today.month, today.day, LUNCH_START_HOUR, 0, tzinfo=datetime.timezone.utc)
    lunch_end = datetime.datetime(today.year, today.month, today.day, LUNCH_END_HOUR, 0, tzinfo=datetime.timezone.utc)

    for event in events:
        # Ignorer les événements toute la journée
        start_info = event.get("start", {})
        if "date" in start_info and "dateTime" not in start_info:
            continue

        title = event.get("summary", "")
        # Ignorer les placeholders déjeuner déjà existants
        if title == LUNCH_TITLE:
            return False

        ev_start = _parse_dt(start_info.get("dateTime"))
        ev_end = _parse_dt(event.get("end", {}).get("dateTime"))

        if ev_start is None or ev_end is None:
            continue

        # Chevauchement avec 12h-13h
        if ev_start < lunch_end and ev_end > lunch_start:
            return False

    return True


def _parse_dt(dt_str):
    if not dt_str:
        return None
    from dateutil import parser
    return parser.parse(dt_str)


def create_lunch_placeholder(service):
    today = datetime.date.today()
    event = {
        "summary": LUNCH_TITLE,
        "description": "Créneaux réservé automatiquement pour la pause déjeuner.",
        "start": {
            "dateTime": datetime.datetime(today.year, today.month, today.day, LUNCH_START_HOUR, 0).isoformat(),
            "timeZone": "Europe/Paris",
        },
        "end": {
            "dateTime": datetime.datetime(today.year, today.month, today.day, LUNCH_END_HOUR, 0).isoformat(),
            "timeZone": "Europe/Paris",
        },
        "colorId": "5",  # banane/jaune
        "reminders": {"useDefault": False},
    }
    created = service.events().insert(calendarId="primary", body=event).execute()
    return created.get("htmlLink")


def print_events(events):
    if not events:
        print("  Aucun événement aujourd'hui.")
        return
    for ev in events:
        start = ev.get("start", {})
        dt = start.get("dateTime", start.get("date", "?"))
        title = ev.get("summary", "(sans titre)")
        print(f"  {dt[:16]}  {title}")


def main():
    if not Path(CREDENTIALS_FILE).exists():
        print(f"❌  Fichier '{CREDENTIALS_FILE}' introuvable.")
        print("   Téléchargez vos identifiants OAuth depuis Google Cloud Console")
        print("   et placez-les dans ce dossier sous le nom 'credentials.json'.")
        return

    print("🔑  Connexion à Google Calendar...")
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    print(f"\n📅  Événements du {datetime.date.today().strftime('%A %d %B %Y')} :")
    events = list_today_events(service)
    print_events(events)

    if is_lunch_slot_free(events):
        print("\n✅  Le créneau midi (12h-13h) est libre.")
        link = create_lunch_placeholder(service)
        print(f"🍽️   Placeholder déjeuner créé : {link}")
    else:
        print("\nℹ️   Le créneau midi (12h-13h) est déjà occupé — aucun placeholder ajouté.")


if __name__ == "__main__":
    main()
