#!/usr/bin/env python3
"""Récupère les cotes 1N2 de Parions Sport Point de Vente (FDJ).

Usage :
    python scraper.py                      # interroge l'API FDJ (Football + Tennis)
    python scraper.py --from-dir raw/      # re-parse des réponses brutes déjà sauvegardées

Sorties : cotes_fdj.json, cotes_fdj.csv, et les réponses brutes dans raw/.

La structure exacte du JSON FDJ n'est pas documentée publiquement et évolue ;
le parsing parcourt donc récursivement la réponse et reconnaît un « événement »
à partir de plusieurs noms de clés possibles plutôt que d'un schéma figé.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

API_URL = "https://www.pointdevente.parionssport.fdj.fr/api/1x2/market-active-by-sport/{sport_id}"
SPORTS = {100: "Football", 600: "Tennis"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.pointdevente.parionssport.fdj.fr/paris-football",
    "Origin": "https://www.pointdevente.parionssport.fdj.fr",
    "Connection": "keep-alive",
}

OUTPUT_JSON = Path("cotes_fdj.json")
OUTPUT_CSV = Path("cotes_fdj.csv")
RAW_DIR = Path("raw")
COLUMNS = ["sport", "competition", "match", "date_heure", "cote_1", "cote_N", "cote_2"]

# Noms de clés candidats, par ordre de préférence.
LABEL_KEYS = ("label", "eventLabel", "libelle", "name", "match", "affiche", "title")
COMPETITION_KEYS = ("competition", "competitionLabel", "competitionName", "league",
                    "libelleCompetition", "tournament", "championship")
DATE_KEYS = ("end", "start", "startDate", "date", "dateHeure", "eventDate",
             "beginDate", "startTime", "matchDate", "dateDebut")
OUTCOMES_KEYS = ("outcomes", "selections", "odds", "cotes", "issues", "choices", "runners")
MARKETS_KEYS = ("markets", "formules", "marketList", "paris", "bets")
HOME_KEYS = ("home", "homeTeam", "team1", "equipe1", "player1", "domicile")
AWAY_KEYS = ("away", "awayTeam", "team2", "equipe2", "player2", "exterieur")
ODD_VALUE_KEYS = ("cote", "odd", "odds", "price", "value", "decimal", "rate")
OUTCOME_LABEL_KEYS = ("label", "name", "code", "type", "libelle", "outcome", "pos")


def fetch(sport_id, retries=3):
    """Appelle l'API pour un sport et renvoie le JSON décodé (ou None)."""
    url = API_URL.format(sport_id=sport_id)
    session = requests.Session()
    session.headers.update(HEADERS)
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=20)
        except requests.RequestException as exc:
            print(f"[{sport_id}] tentative {attempt}: erreur réseau {exc}", file=sys.stderr)
        else:
            ctype = resp.headers.get("Content-Type", "")
            print(f"[{sport_id}] HTTP {resp.status_code} - {ctype} - {len(resp.content)} octets")
            if resp.ok:
                try:
                    return resp.json()
                except ValueError:
                    print(f"[{sport_id}] réponse non JSON : {resp.text[:300]!r}", file=sys.stderr)
                    return None
            print(f"[{sport_id}] corps : {resp.text[:300]!r}", file=sys.stderr)
        time.sleep(2 ** attempt)
    return None


def first(d, keys):
    for k in keys:
        if k in d and d[k] not in (None, "", [], {}):
            return d[k]
    return None


def as_text(value):
    """Réduit une valeur (str, dict {label: ...}, etc.) à un texte lisible."""
    if value is None:
        return None
    if isinstance(value, dict):
        return as_text(first(value, LABEL_KEYS))
    return str(value).strip()


def parse_odd(value):
    if isinstance(value, dict):
        value = first(value, ODD_VALUE_KEYS)
    if value is None:
        return None
    try:
        odd = float(str(value).replace(",", ".").strip())
    except ValueError:
        return None
    # Certaines API renvoient les cotes en centièmes (ex. 215 pour 2,15).
    if odd >= 100 and float(odd).is_integer():
        odd /= 100
    return odd


def parse_date(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        ts = value / 1000 if value > 1e11 else value  # millisecondes ou secondes
        return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    text = str(value).strip()
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if dt.tzinfo is not None:
        dt = dt.astimezone()
    return dt.strftime("%Y-%m-%d %H:%M")


def outcome_slot(outcome, index, count):
    """Détermine si une issue correspond à 1, N ou 2."""
    label = (as_text(first(outcome, OUTCOME_LABEL_KEYS)) or "").upper()
    if label in ("1", "HOME", "H", "DOMICILE"):
        return "1"
    if label in ("N", "X", "DRAW", "NUL", "MATCH NUL"):
        return "N"
    if label in ("2", "AWAY", "A", "EXTERIEUR", "EXTÉRIEUR"):
        return "2"
    # À défaut, on se fie à l'ordre : [1, N, 2] ou [1, 2] (tennis).
    order = ["1", "N", "2"] if count == 3 else ["1", "2"]
    return order[index] if index < len(order) else None


def extract_odds(event):
    """Renvoie {'1': .., 'N': .., '2': ..} à partir d'un événement."""
    odds = {}
    outcomes = first(event, OUTCOMES_KEYS)
    if outcomes is None:
        markets = first(event, MARKETS_KEYS)
        if isinstance(markets, dict):
            markets = list(markets.values())
        for market in markets or []:
            if isinstance(market, dict) and first(market, OUTCOMES_KEYS):
                outcomes = first(market, OUTCOMES_KEYS)
                break
    if isinstance(outcomes, dict):
        # Forme {"1": 2.1, "N": 3.2, "2": 3.5}
        for key, val in outcomes.items():
            slot = outcome_slot({"label": key}, 0, 0)
            if slot:
                odds[slot] = parse_odd(val)
        return odds
    if isinstance(outcomes, list):
        for i, outcome in enumerate(outcomes):
            if not isinstance(outcome, dict):
                outcome = {"cote": outcome}
            slot = outcome_slot(outcome, i, len(outcomes))
            if slot:
                odds[slot] = parse_odd(outcome)
    # Forme à plat : {"cote1": .., "coteN": .., "cote2": ..}
    for slot, keys in (("1", ("cote1", "odd1", "odds1", "home_odd")),
                       ("N", ("coteN", "coteX", "oddN", "oddX", "draw_odd")),
                       ("2", ("cote2", "odd2", "odds2", "away_odd"))):
        if slot not in odds and first(event, keys) is not None:
            odds[slot] = parse_odd(first(event, keys))
    return odds


def looks_like_event(node):
    if not isinstance(node, dict):
        return False
    has_name = first(node, LABEL_KEYS) is not None or (
        first(node, HOME_KEYS) is not None and first(node, AWAY_KEYS) is not None)
    return has_name and bool(extract_odds(node))


def walk(node, sport, competition=None):
    """Parcourt récursivement le JSON et produit une ligne par événement trouvé."""
    if isinstance(node, list):
        for item in node:
            yield from walk(item, sport, competition)
        return
    if not isinstance(node, dict):
        return
    if looks_like_event(node):
        yield build_row(node, sport, competition)
        return
    # Un nœud intermédiaire peut porter le nom de la compétition pour ses enfants.
    comp = as_text(first(node, COMPETITION_KEYS)) or competition
    if comp == competition and first(node, LABEL_KEYS) and any(
            isinstance(v, list) for v in node.values()):
        comp = as_text(first(node, LABEL_KEYS))
    for value in node.values():
        if isinstance(value, (dict, list)):
            yield from walk(value, sport, comp)


def build_row(event, sport, competition):
    home, away = first(event, HOME_KEYS), first(event, AWAY_KEYS)
    if home is not None and away is not None:
        match = f"{as_text(home)} - {as_text(away)}"
    else:
        match = as_text(first(event, LABEL_KEYS))
    odds = extract_odds(event)
    return {
        "sport": sport,
        "competition": as_text(first(event, COMPETITION_KEYS)) or competition,
        "match": match,
        "date_heure": parse_date(first(event, DATE_KEYS)),
        "cote_1": odds.get("1"),
        "cote_N": odds.get("N"),
        "cote_2": odds.get("2"),
    }


def describe(data, depth=0, max_depth=3):
    """Affiche un aperçu de la structure JSON pour faciliter l'adaptation du parsing."""
    pad = "  " * depth
    if depth > max_depth:
        return
    if isinstance(data, dict):
        print(f"{pad}dict({len(data)}) clés={list(data)[:15]}")
        for k, v in list(data.items())[:5]:
            if isinstance(v, (dict, list)):
                print(f"{pad} .{k}:")
                describe(v, depth + 1, max_depth)
    elif isinstance(data, list):
        print(f"{pad}list({len(data)})")
        if data:
            describe(data[0], depth + 1, max_depth)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-dir", type=Path,
                        help="re-parse les fichiers <sport_id>.json d'un dossier au lieu d'appeler l'API")
    args = parser.parse_args()

    rows = []
    for sport_id, sport in SPORTS.items():
        if args.from_dir:
            path = args.from_dir / f"{sport_id}.json"
            if not path.exists():
                print(f"[{sport_id}] {path} absent, ignoré", file=sys.stderr)
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = fetch(sport_id)
            if data is None:
                continue
            RAW_DIR.mkdir(exist_ok=True)
            (RAW_DIR / f"{sport_id}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"[{sport_id}] structure de la réponse :")
        describe(data)
        sport_rows = list(walk(data, sport))
        print(f"[{sport_id}] {sport} : {len(sport_rows)} événements extraits")
        rows.extend(sport_rows)

    if not rows:
        print("Aucun événement extrait : inspectez raw/*.json et adaptez les listes de clés.",
              file=sys.stderr)
        return 1

    df = pd.DataFrame(rows, columns=COLUMNS).drop_duplicates()
    df = df.sort_values(["sport", "date_heure", "competition"], na_position="last")
    OUTPUT_JSON.write_text(df.to_json(orient="records", force_ascii=False, indent=2),
                           encoding="utf-8")
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig", sep=";", decimal=",")
    print(f"{len(df)} lignes écrites dans {OUTPUT_JSON} et {OUTPUT_CSV}")
    print(df.head(10).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
