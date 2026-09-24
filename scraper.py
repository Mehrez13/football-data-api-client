"""Scraper de cotes 1N2 (Football / Tennis) via The Odds API.

L'ancienne API "Point de vente" de la FDJ (pointdevente.parionssport.fdj.fr)
n'existe plus (404) et le site grand public parionssport.fdj.fr redirige
desormais vers unibet.fr, dont l'API interne (plateforme Kambi) est
protegee et interdite au scraping par son robots.txt.

Ce script utilise donc The Odds API (https://the-odds-api.com), un
fournisseur tiers legitime avec une API REST publique et documentee,
couvrant les principaux championnats de football europeen et le tennis,
avec les cotes des bookmakers europeens (dont ceux operant en France).

Necessite une cle API gratuite (plan Starter, 500 credits/mois), a fournir
via la variable d'environnement ODDS_API_KEY.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("odds_scraper")

API_BASE = "https://api.the-odds-api.com/v4"
API_KEY = os.environ.get("ODDS_API_KEY", "")

# 1 marche x 1 region = 1 credit par competition interrogee.
REGIONS = os.environ.get("ODDS_API_REGIONS", "eu")
MARKETS = os.environ.get("ODDS_API_MARKETS", "h2h")
ODDS_FORMAT = "decimal"

# Groupes The Odds API a couvrir (voir GET /v4/sports, champ "group").
SPORT_GROUPS = {
    "Football": "Soccer",
    "Tennis": "Tennis",
}

# Le groupe "Soccer" de The Odds API couvre le monde entier (Bresil, Coree,
# Mexique, MLS...). On limite volontairement aux championnats les plus
# couverts par les bookmakers licencies FR, pour economiser le quota gratuit
# (chaque competition interrogee coute 1 credit, 500/mois en offre gratuite).
EUROPEAN_FOOTBALL_KEYS = {
    "soccer_epl", "soccer_fa_cup",
    "soccer_france_ligue_one", "soccer_france_ligue_two", "soccer_france_coupe_de_france",
    "soccer_germany_bundesliga",
    "soccer_italy_serie_a",
    "soccer_spain_la_liga",
    "soccer_netherlands_eredivisie", "soccer_portugal_primeira_liga",
}

JSON_OUTPUT = Path("cotes_fdj.json")
CSV_OUTPUT = Path("cotes_fdj.csv")


@dataclass
class Cote:
    sport: str
    competition: str
    affiche: str
    date_heure: str | None
    cote_1: float | None
    cote_n: float | None
    cote_2: float | None
    bookmaker: str | None


def list_active_sports(session: requests.Session) -> list[dict]:
    """GET /v4/sports : liste des sports actifs. Ne consomme pas de quota."""
    url = f"{API_BASE}/sports"
    response = session.get(url, params={"apiKey": API_KEY}, timeout=15)
    logger.info("GET %s -> %s", url, response.status_code)
    response.raise_for_status()
    return response.json()


def fetch_odds(session: requests.Session, sport_key: str) -> list[dict]:
    """GET /v4/sports/{sport}/odds pour une competition donnee."""
    url = f"{API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT,
        "dateFormat": "iso",
    }
    response = session.get(url, params=params, timeout=15)
    logger.info(
        "GET %s -> %s (credits utilises: %s, restants: %s)",
        url,
        response.status_code,
        response.headers.get("x-requests-last"),
        response.headers.get("x-requests-remaining"),
    )

    if response.status_code != 200:
        logger.warning(
            "Reponse non exploitable (%s) pour %s: %s",
            response.status_code,
            sport_key,
            response.text[:300].replace("\n", " "),
        )
        return []

    return response.json()


def parse_events(events: list[dict], sport: str, competition: str) -> list[Cote]:
    cotes: list[Cote] = []
    for event in events:
        home = event.get("home_team")
        away = event.get("away_team")
        affiche = f"{home} - {away}" if home and away else event.get("id", "Match inconnu")
        date_heure = event.get("commence_time")

        for bookmaker in event.get("bookmakers", []):
            cote_1, cote_n, cote_2 = _extract_h2h(bookmaker, home, away)
            if cote_1 is None and cote_n is None and cote_2 is None:
                continue
            cotes.append(
                Cote(
                    sport=sport,
                    competition=competition,
                    affiche=str(affiche),
                    date_heure=date_heure,
                    cote_1=cote_1,
                    cote_n=cote_n,
                    cote_2=cote_2,
                    bookmaker=bookmaker.get("title"),
                )
            )
    return cotes


def _extract_h2h(bookmaker: dict, home: str | None, away: str | None) -> tuple[float | None, float | None, float | None]:
    for market in bookmaker.get("markets", []):
        if market.get("key") != "h2h":
            continue
        cote_1 = cote_n = cote_2 = None
        for outcome in market.get("outcomes", []):
            name = outcome.get("name")
            price = outcome.get("price")
            if name == home:
                cote_1 = price
            elif name == away:
                cote_2 = price
            elif name == "Draw":
                cote_n = price
        return cote_1, cote_n, cote_2
    return None, None, None


def scrape_all() -> list[Cote]:
    if not API_KEY:
        logger.error(
            "ODDS_API_KEY n'est pas definie. Cree une cle gratuite sur "
            "https://the-odds-api.com et exporte-la : export ODDS_API_KEY=xxxx"
        )
        return []

    all_cotes: list[Cote] = []
    with requests.Session() as session:
        try:
            active_sports = list_active_sports(session)
        except requests.RequestException as exc:
            logger.error("Impossible de recuperer la liste des sports actifs: %s", exc)
            return []

        for sport_label, group_name in SPORT_GROUPS.items():
            competitions = [s for s in active_sports if s.get("group") == group_name and not s.get("has_outrights")]

            if sport_label == "Football":
                competitions = [
                    s for s in competitions
                    if s["key"] in EUROPEAN_FOOTBALL_KEYS or s["key"].startswith("soccer_uefa_")
                ]

            logger.info("%s: %d competition(s) active(s) trouvee(s)", sport_label, len(competitions))

            for competition in competitions:
                sport_key = competition["key"]
                events = fetch_odds(session, sport_key)
                parsed = parse_events(events, sport_label, competition.get("title", sport_key))
                logger.info("  - %s: %d cote(s) extraite(s)", sport_key, len(parsed))
                all_cotes.extend(parsed)

    return all_cotes


def save_results(cotes: list[Cote]) -> None:
    records = [asdict(c) for c in cotes]

    JSON_OUTPUT.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("JSON sauvegarde: %s (%d enregistrement(s))", JSON_OUTPUT, len(records))

    columns = ["sport", "competition", "affiche", "date_heure", "cote_1", "cote_n", "cote_2", "bookmaker"]
    df = pd.DataFrame(records, columns=columns)
    df.to_csv(CSV_OUTPUT, index=False, encoding="utf-8-sig")
    logger.info("CSV sauvegarde: %s (%d ligne(s))", CSV_OUTPUT, len(df))


def main() -> int:
    cotes = scrape_all()
    save_results(cotes)
    if not cotes:
        logger.warning("Aucune cote recuperee (voir les logs ci-dessus).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
