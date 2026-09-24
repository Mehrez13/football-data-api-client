"""Analyse des cotes 1N2 (cotes_fdj.csv) pour l'aide a la decision de paris.

Pour chaque match, compare les cotes de tous les bookmakers recuperees par
scraper.py et calcule :
  - la meilleure cote disponible par issue (1 / N / 2) et son bookmaker,
  - une probabilite "de marche" par issue, obtenue en retirant la marge
    (overround) de chaque bookmaker puis en moyennant entre bookmakers,
  - l'esperance de gain (EV) de prendre la meilleure cote face a cette
    probabilite de marche,
  - une mise suggeree en Kelly fractionnaire (prudent par defaut),
  - un signal d'arbitrage si les meilleures cotes combinees garantissent
    un gain quel que soit le resultat.

Ceci reste une estimation statistique basee sur le consensus des
bookmakers, pas une prediction fiable du resultat. Les paris sportifs
comportent un risque de perte en capital.

Genere paris_data.json, consomme par paris_dashboard.html.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("analyze")

CSV_INPUT = Path("cotes_fdj.csv")
JSON_OUTPUT = Path("paris_data.json")

OUTCOMES = ("cote_1", "cote_n", "cote_2")
KELLY_FRACTION = 0.25  # Kelly fractionnaire par defaut : reduit la variance.
MAX_STAKE_PCT = 0.05  # Plafond de securite : jamais plus de 5% de la bankroll sur un pari.

# Places de marche (exchanges) : le prix affiche n'est garanti que pour une
# mise limitee (liquidite du carnet d'ordres) et ne se compare pas a une
# cote ferme de bookmaker. On les exclut de tout le comparatif.
EXCHANGES = {"Betfair", "Matchbook", "Smarkets"}

# Operateurs agrees par l'ANJ (Autorite Nationale des Jeux) en France. Les
# "meilleures cotes" proposees ne portent que sur ces bookmakers : le reste
# du panel (1xBet, Pinnacle, Betsson, William Hill...) n'est pas accessible
# ou pas legal depuis la France et ne sert qu'a affiner l'estimation de la
# probabilite de marche.
FRENCH_LICENSED_BOOKMAKERS = {"Winamax (FR)", "Betclic (FR)", "Unibet (FR)", "PMU (FR)"}


def load_matches() -> pd.DataFrame:
    if not CSV_INPUT.exists():
        raise FileNotFoundError(f"{CSV_INPUT} introuvable. Lance d'abord scraper.py.")
    df = pd.read_csv(CSV_INPUT)
    for col in OUTCOMES:
        if col not in df.columns:
            df[col] = None

    df = df[~df["bookmaker"].isin(EXCHANGES)]

    commence = pd.to_datetime(df["date_heure"], utc=True, errors="coerce")
    now = pd.Timestamp.now(tz=timezone.utc)
    before = len(df)
    df = df[commence > now]
    logger.info("Matchs deja commences retires: %d ligne(s) (analyse limitee au pre-match)", before - len(df))

    return df


def devigged_probs(row: pd.Series, expected_outcomes: int) -> dict[str, float]:
    present = {col: row[col] for col in OUTCOMES if pd.notna(row[col]) and row[col] > 0}
    if len(present) < expected_outcomes:
        return {}  # cotes incompletes : on ne s'en sert pas pour estimer la probabilite de marche.
    inv = {col: 1.0 / v for col, v in present.items()}
    total = sum(inv.values())
    return {col: v / total for col, v in inv.items()}


def kelly_stake(best_odds: float, fair_prob: float) -> float:
    b = best_odds - 1
    if b <= 0:
        return 0.0
    edge = b * fair_prob - (1 - fair_prob)
    if edge <= 0:
        return 0.0
    return max(0.0, edge / b)


def analyze() -> list[dict]:
    df = load_matches()
    group_cols = ["sport", "competition", "affiche", "date_heure"]
    results: list[dict] = []

    for keys, group in df.groupby(group_cols, dropna=False):
        sport, competition, affiche, date_heure = keys
        expected_outcomes = 2 if sport == "Tennis" else 3

        fair_by_outcome: dict[str, list[float]] = defaultdict(list)
        for _, row in group.iterrows():
            for outcome, prob in devigged_probs(row, expected_outcomes).items():
                fair_by_outcome[outcome].append(prob)
        fair_prob = {
            outcome: sum(values) / len(values)
            for outcome, values in fair_by_outcome.items()
            if values
        }
        if not fair_prob:
            continue

        legal_group = group[group["bookmaker"].isin(FRENCH_LICENSED_BOOKMAKERS)]

        best = {}
        for outcome in OUTCOMES:
            valid = legal_group[legal_group[outcome].notna() & (legal_group[outcome] > 0)]
            if valid.empty:
                continue
            best_row = valid.loc[valid[outcome].idxmax()]
            best[outcome] = {
                "odds": float(best_row[outcome]),
                "bookmaker": best_row["bookmaker"],
            }

        arbitrage = False
        if len(best) >= 2:
            inv_sum = sum(1.0 / v["odds"] for v in best.values())
            arbitrage = inv_sum < 1.0

        for outcome, info in best.items():
            p = fair_prob.get(outcome)
            if p is None:
                continue
            ev_pct = (info["odds"] * p - 1) * 100
            stake_fraction = kelly_stake(info["odds"], p) * KELLY_FRACTION
            stake_fraction = min(stake_fraction, MAX_STAKE_PCT)

            results.append(
                {
                    "sport": sport,
                    "competition": competition,
                    "affiche": affiche,
                    "date_heure": date_heure,
                    "issue": {"cote_1": "1", "cote_n": "N", "cote_2": "2"}[outcome],
                    "meilleure_cote": round(info["odds"], 3),
                    "bookmaker": info["bookmaker"],
                    "probabilite_marche_pct": round(p * 100, 2),
                    "ev_pct": round(ev_pct, 2),
                    "stake_fraction_pct": round(stake_fraction * 100, 3),
                    "arbitrage": arbitrage,
                }
            )

    results.sort(key=lambda r: r["probabilite_marche_pct"], reverse=True)
    return results


def main() -> int:
    results = analyze()
    JSON_OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Analyse sauvegardee: %s (%d ligne(s))", JSON_OUTPUT, len(results))

    value_bets = [r for r in results if r["ev_pct"] > 0]
    arbitrages = [r for r in results if r["arbitrage"]]
    logger.info("%d pari(s) a EV positive (selon le consensus des bookmakers)", len(value_bets))
    if arbitrages:
        logger.warning("%d opportunite(s) d'arbitrage detectee(s) (a verifier manuellement)", len(arbitrages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
