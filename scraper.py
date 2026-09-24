"""Scraper pour les cotes 1N2 de Parions Sport (FDJ).

Interroge l'API "Point de vente" de la FDJ pour Football et Tennis,
extrait affiche / competition / date / cotes 1-N-2, et sauvegarde le
resultat en JSON et CSV.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("fdj_scraper")

BASE_URL = "https://www.pointdevente.parionssport.fdj.fr/api/1x2/market-active-by-sport/{sport_id}"

SPORTS = {
    "Football": 100,
    "Tennis": 600,
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Referer": "https://www.pointdevente.parionssport.fdj.fr/",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
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


def fetch_markets(session: requests.Session, sport_id: int) -> Any:
    """Recupere la reponse JSON brute de l'API pour un sport donne."""
    url = BASE_URL.format(sport_id=sport_id)
    response = session.get(url, headers=HEADERS, timeout=15)
    logger.info("GET %s -> %s", url, response.status_code)

    if response.status_code != 200:
        logger.warning(
            "Reponse non exploitable (%s) pour le sport %s: %s",
            response.status_code,
            sport_id,
            response.text[:300].replace("\n", " "),
        )
        return None

    try:
        return response.json()
    except ValueError:
        logger.warning("Reponse non-JSON pour le sport %s: %s", sport_id, response.text[:300])
        return None


def _iter_events(payload: Any) -> Iterable[dict]:
    """Normalise les differentes formes possibles de la reponse FDJ en une
    liste d'evenements/matchs, quelle que soit la structure d'enveloppe
    (liste brute, dict avec 'competitions'/'events'/'data', etc.).
    """
    if payload is None:
        return

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and _looks_like_competition(item):
                yield from _iter_events(item)
            else:
                yield item
        return

    if isinstance(payload, dict):
        for key in ("events", "matches", "rencontres", "results", "data"):
            if key in payload and isinstance(payload[key], list):
                for item in payload[key]:
                    yield from _iter_events(item) if _looks_like_competition(item) else [item]
                return

        for key in ("competitions", "categories", "groups"):
            if key in payload and isinstance(payload[key], list):
                for comp in payload[key]:
                    yield from _iter_events(comp)
                return

        if _looks_like_competition(payload):
            for key in ("events", "matches", "rencontres"):
                if key in payload and isinstance(payload[key], list):
                    for item in payload[key]:
                        item.setdefault("_competition_name", payload.get("nom") or payload.get("name") or payload.get("libelle"))
                        yield item
                    return

        yield payload


def _looks_like_competition(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    has_children = any(k in item for k in ("events", "matches", "rencontres"))
    return has_children


def _first(d: dict, *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in d and d[key] not in (None, ""):
            return d[key]
    return default


def _extract_odds(event: dict) -> tuple[float | None, float | None, float | None]:
    """Cherche les cotes 1 / N / 2 dans plusieurs structures possibles."""
    for key in ("cotes", "odds", "outcomes", "selections", "marches", "markets"):
        candidate = event.get(key)
        if candidate is not None:
            odds = _odds_from_candidate(candidate)
            if odds != (None, None, None):
                return odds

    direct = (
        _first(event, "cote1", "odd1", "home_odds"),
        _first(event, "coteN", "oddN", "draw_odds"),
        _first(event, "cote2", "odd2", "away_odds"),
    )
    return direct


def _odds_from_candidate(candidate: Any) -> tuple[float | None, float | None, float | None]:
    if isinstance(candidate, dict):
        return (
            _first(candidate, "1", "cote1", "home", "domicile"),
            _first(candidate, "N", "n", "coteN", "nul", "draw"),
            _first(candidate, "2", "cote2", "away", "exterieur"),
        )
    if isinstance(candidate, list):
        mapping = {"1": None, "N": None, "2": None}
        for outcome in candidate:
            if not isinstance(outcome, dict):
                continue
            label = str(_first(outcome, "libelle", "label", "type", "name", default="")).upper()
            value = _first(outcome, "cote", "odd", "value", "prix")
            if label in ("1", "DOMICILE", "HOME"):
                mapping["1"] = value
            elif label in ("N", "NUL", "DRAW"):
                mapping["N"] = value
            elif label in ("2", "EXTERIEUR", "AWAY"):
                mapping["2"] = value
        return mapping["1"], mapping["N"], mapping["2"]
    return None, None, None


def parse_events(payload: Any, sport: str) -> list[Cote]:
    cotes: list[Cote] = []
    for event in _iter_events(payload):
        if not isinstance(event, dict):
            continue

        competition = _first(
            event,
            "_competition_name",
            "competition",
            "nomCompetition",
            "categorie",
            "league",
            default="Inconnue",
        )

        equipe_dom = _first(event, "equipe1", "domicile", "home", "participant1")
        equipe_ext = _first(event, "equipe2", "exterieur", "away", "participant2")
        if equipe_dom and equipe_ext:
            affiche = f"{equipe_dom} - {equipe_ext}"
        else:
            affiche = _first(event, "libelle", "name", "nom", "affiche", default="Match inconnu")

        date_heure = _first(event, "dateHeure", "date", "startDate", "dateEvenement")

        cote_1, cote_n, cote_2 = _extract_odds(event)

        cotes.append(
            Cote(
                sport=sport,
                competition=str(competition) if competition else "Inconnue",
                affiche=str(affiche),
                date_heure=str(date_heure) if date_heure else None,
                cote_1=_to_float(cote_1),
                cote_n=_to_float(cote_n),
                cote_2=_to_float(cote_2),
            )
        )
    return cotes


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def scrape_all() -> list[Cote]:
    all_cotes: list[Cote] = []
    with requests.Session() as session:
        for sport_name, sport_id in SPORTS.items():
            payload = fetch_markets(session, sport_id)
            events = parse_events(payload, sport_name)
            logger.info("%s: %d rencontre(s) extraite(s)", sport_name, len(events))
            all_cotes.extend(events)
    return all_cotes


def save_results(cotes: list[Cote]) -> None:
    records = [asdict(c) for c in cotes]

    JSON_OUTPUT.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("JSON sauvegarde: %s (%d enregistrement(s))", JSON_OUTPUT, len(records))

    columns = ["sport", "competition", "affiche", "date_heure", "cote_1", "cote_n", "cote_2"]
    df = pd.DataFrame(records, columns=columns)
    df.to_csv(CSV_OUTPUT, index=False, encoding="utf-8-sig")
    logger.info("CSV sauvegarde: %s (%d ligne(s))", CSV_OUTPUT, len(df))


def main() -> int:
    cotes = scrape_all()
    save_results(cotes)
    if not cotes:
        logger.warning(
            "Aucune cote recuperee : l'API FDJ n'a renvoye aucune donnee exploitable "
            "(voir les logs ci-dessus pour le code HTTP et la reponse brute)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
