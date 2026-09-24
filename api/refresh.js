const API_BASE = "https://api.the-odds-api.com/v4";
const REGIONS = "eu";
const MARKETS = "h2h";

const SPORT_GROUPS = { Football: "Soccer", Tennis: "Tennis" };

// Liste volontairement restreinte aux championnats les plus couverts par les
// bookmakers licencies FR, pour limiter le nombre de requetes (donc de credits
// The Odds API, 500/mois en offre gratuite) consommees a chaque actualisation.
const EUROPEAN_FOOTBALL_KEYS = new Set([
  "soccer_epl", "soccer_fa_cup",
  "soccer_france_ligue_one", "soccer_france_ligue_two", "soccer_france_coupe_de_france",
  "soccer_germany_bundesliga",
  "soccer_italy_serie_a",
  "soccer_spain_la_liga",
  "soccer_netherlands_eredivisie", "soccer_portugal_primeira_liga",
]);

const EXCHANGES = new Set(["Betfair", "Matchbook", "Smarkets"]);
const FRENCH_LICENSED_BOOKMAKERS = new Set(["Winamax (FR)", "Betclic (FR)", "Unibet (FR)", "PMU (FR)"]);

const KELLY_FRACTION = 0.25;
const MAX_STAKE_PCT = 0.05;

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${url} -> ${res.status} ${text.slice(0, 200)}`);
  }
  return res.json();
}

function devigOutcomes(bookmaker, expectedOutcomes) {
  const market = (bookmaker.markets || []).find((m) => m.key === "h2h");
  if (!market) return null;
  const outcomes = market.outcomes || [];
  if (outcomes.length < expectedOutcomes) return null;
  const inv = outcomes.map((o) => ({ name: o.name, inv: 1 / o.price }));
  const total = inv.reduce((s, o) => s + o.inv, 0);
  if (total <= 0) return null;
  return Object.fromEntries(inv.map((o) => [o.name, o.inv / total]));
}

function kellyStake(bestOdds, fairProb) {
  const b = bestOdds - 1;
  if (b <= 0) return 0;
  const edge = b * fairProb - (1 - fairProb);
  if (edge <= 0) return 0;
  return Math.max(0, edge / b);
}

function analyzeEvent(event, sport) {
  const home = event.home_team;
  const away = event.away_team;
  const affiche = home && away ? `${home} - ${away}` : event.id;
  const expectedOutcomes = sport === "Tennis" ? 2 : 3;

  const bookmakers = (event.bookmakers || []).filter((b) => !EXCHANGES.has(b.title));

  const fairSums = {};
  const fairCounts = {};
  for (const bm of bookmakers) {
    const devig = devigOutcomes(bm, expectedOutcomes);
    if (!devig) continue;
    for (const [name, prob] of Object.entries(devig)) {
      fairSums[name] = (fairSums[name] || 0) + prob;
      fairCounts[name] = (fairCounts[name] || 0) + 1;
    }
  }
  const fairProb = {};
  for (const name of Object.keys(fairSums)) {
    fairProb[name] = fairSums[name] / fairCounts[name];
  }
  if (Object.keys(fairProb).length === 0) return [];

  const legalBooks = bookmakers.filter((b) => FRENCH_LICENSED_BOOKMAKERS.has(b.title));
  const best = {};
  for (const bm of legalBooks) {
    const market = (bm.markets || []).find((m) => m.key === "h2h");
    if (!market) continue;
    for (const outcome of market.outcomes || []) {
      const current = best[outcome.name];
      if (!current || outcome.price > current.odds) {
        best[outcome.name] = { odds: outcome.price, bookmaker: bm.title };
      }
    }
  }

  const results = [];
  for (const [name, info] of Object.entries(best)) {
    const p = fairProb[name];
    if (p == null) continue;
    const evPct = (info.odds * p - 1) * 100;
    const stakeFraction = Math.min(kellyStake(info.odds, p) * KELLY_FRACTION, MAX_STAKE_PCT);
    const issue = name === home ? "1" : name === away ? "2" : "N";

    results.push({
      sport,
      competition: event._competitionTitle,
      affiche,
      date_heure: event.commence_time,
      issue,
      meilleure_cote: Math.round(info.odds * 1000) / 1000,
      bookmaker: info.bookmaker,
      probabilite_marche_pct: Math.round(p * 10000) / 100,
      ev_pct: Math.round(evPct * 100) / 100,
      stake_fraction_pct: Math.round(stakeFraction * 100000) / 1000,
      arbitrage: false,
    });
  }

  if (Object.keys(best).length >= 2) {
    const invSum = Object.values(best).reduce((s, v) => s + 1 / v.odds, 0);
    if (invSum < 1) results.forEach((r) => { r.arbitrage = true; });
  }

  return results;
}

module.exports = async (req, res) => {
  const apiKey = process.env.ODDS_API_KEY;
  if (!apiKey) {
    res.status(500).json({ error: "ODDS_API_KEY n'est pas configuree sur ce projet Vercel." });
    return;
  }

  try {
    const sports = await fetchJson(`${API_BASE}/sports?apiKey=${apiKey}`);
    const now = Date.now();

    const tasks = [];
    for (const [sportLabel, groupName] of Object.entries(SPORT_GROUPS)) {
      let competitions = sports.filter((s) => s.group === groupName && !s.has_outrights);
      if (sportLabel === "Football") {
        competitions = competitions.filter(
          (s) => EUROPEAN_FOOTBALL_KEYS.has(s.key) || s.key.startsWith("soccer_uefa_")
        );
      }
      for (const comp of competitions) {
        const url = `${API_BASE}/sports/${comp.key}/odds?apiKey=${apiKey}&regions=${REGIONS}&markets=${MARKETS}&oddsFormat=decimal&dateFormat=iso`;
        tasks.push(
          fetchJson(url)
            .then((events) =>
              events
                .filter((e) => new Date(e.commence_time).getTime() > now)
                .map((e) => ({ ...e, _competitionTitle: comp.title }))
                .flatMap((e) => analyzeEvent(e, sportLabel))
            )
            .catch((err) => {
              console.error(`Erreur sur ${comp.key}: ${err.message}`);
              return [];
            })
        );
      }
    }

    const chunks = await Promise.all(tasks);
    const allResults = chunks.flat().sort((a, b) => b.ev_pct - a.ev_pct);

    res.setHeader("Cache-Control", "no-store");
    res.status(200).json(allResults);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
};
