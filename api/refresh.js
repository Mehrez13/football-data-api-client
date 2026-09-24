const API_BASE = "https://api.the-odds-api.com/v4";
const REGIONS = "eu";
const MARKETS = "h2h";

const SPORT_GROUPS = { Football: "Soccer" };

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
// La probabilite "de marche" (devig) reste calculee sur tout le panel de
// bookmakers non-exchange pour rester statistiquement fiable, mais la cote
// affichee/jouable ne vient plus que de PMU (FR) : c'est le seul operateur
// utilise (mises passees en bureau de tabac). Si PMU ne cote pas un match,
// il n'apparait simplement pas - pas de repli vers un autre bookmaker.
const BETTING_BOOKMAKER = "PMU (FR)";

const KELLY_FRACTION = 0.25;
const MAX_STAKE_PCT = 0.05;

// Marche secondaire (over/under buts) : l'API ne le fournit que via
// l'endpoint par match (1 credit par marche par match interroge), contre 1
// credit par championnat entier pour le 1N2. Pour ne pas exploser le quota
// gratuit, on ne va le chercher QUE pour les matchs ou une issue 1N2 a deja
// une probabilite tres elevee (favori tres marque).
// BTTS, double chance, remboursé-si-nul et handicap ont ete testes et
// retires : au 2026-09, aucun des 4 bookmakers agrees FR (Winamax, Betclic,
// Unibet FR, PMU FR) ne les propose via cette API - seul PMU (FR) expose le
// marche "totals". A revoir si l'API ou PMU elargit sa couverture.
const SECONDARY_MARKETS = "totals";
const SECONDARY_MARKETS_PROB_THRESHOLD = 75;
// Plafond de securite : les appels se font en sequence (rate-limit de l'API),
// donc on borne le nombre de matchs interroges pour rester dans le temps
// d'execution de la fonction serverless.
const SECONDARY_MARKETS_MAX_EVENTS = 15;

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${url} -> ${res.status} ${text.slice(0, 200)}`);
  }
  return res.json();
}

function devigMarket(bookmakers, marketKey, expectedOutcomes) {
  const fairSums = {};
  const fairCounts = {};
  for (const bm of bookmakers) {
    const market = (bm.markets || []).find((m) => m.key === marketKey);
    if (!market) continue;
    const outcomes = market.outcomes || [];
    if (outcomes.length < expectedOutcomes) continue;
    const inv = outcomes.map((o) => ({ name: o.name, inv: 1 / o.price }));
    const total = inv.reduce((s, o) => s + o.inv, 0);
    if (total <= 0) continue;
    for (const o of inv) {
      const fair = o.inv / total;
      fairSums[o.name] = (fairSums[o.name] || 0) + fair;
      fairCounts[o.name] = (fairCounts[o.name] || 0) + 1;
    }
  }
  const fairProb = {};
  for (const name of Object.keys(fairSums)) {
    fairProb[name] = fairSums[name] / fairCounts[name];
  }
  return fairProb;
}

function pmuOddsForMarket(bookmakers, marketKey) {
  const pmu = bookmakers.find((b) => b.title === BETTING_BOOKMAKER);
  if (!pmu) return {};
  const market = (pmu.markets || []).find((m) => m.key === marketKey);
  if (!market) return {};
  const odds = {};
  for (const outcome of market.outcomes || []) {
    odds[outcome.name] = { odds: outcome.price, bookmaker: pmu.title, point: outcome.point };
  }
  return odds;
}

function kellyStake(bestOdds, fairProb) {
  const b = bestOdds - 1;
  if (b <= 0) return 0;
  const edge = b * fairProb - (1 - fairProb);
  if (edge <= 0) return 0;
  return Math.max(0, edge / b);
}

function buildRows(event, marketKey, best, fairProb, issueLabels) {
  const results = [];
  for (const [name, info] of Object.entries(best)) {
    const p = fairProb[name];
    if (p == null) continue;
    const evPct = (info.odds * p - 1) * 100;
    const stakeFraction = Math.min(kellyStake(info.odds, p) * KELLY_FRACTION, MAX_STAKE_PCT);
    const issue = issueLabels ? issueLabels(name, info) : name;

    results.push({
      marche: marketKey,
      competition: event._competitionTitle,
      affiche: event._affiche,
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

function analyzeH2h(event) {
  const home = event.home_team;
  const away = event.away_team;
  const bookmakers = (event.bookmakers || []).filter((b) => !EXCHANGES.has(b.title));

  const fairProb = devigMarket(bookmakers, "h2h", 3);
  if (Object.keys(fairProb).length === 0) return [];

  const pmuOdds = pmuOddsForMarket(bookmakers, "h2h");
  if (Object.keys(pmuOdds).length === 0) return [];
  return buildRows(event, "1N2", pmuOdds, fairProb, (name) => (name === home ? "1" : name === away ? "2" : "N"));
}

function analyzeTotals(event) {
  const bookmakers = (event.bookmakers || []).filter((b) => !EXCHANGES.has(b.title));
  const fairProb = devigMarket(bookmakers, "totals", 2);
  if (Object.keys(fairProb).length === 0) return [];
  const pmuOdds = pmuOddsForMarket(bookmakers, "totals");
  if (Object.keys(pmuOdds).length === 0) return [];
  return buildRows(event, "Buts", pmuOdds, fairProb, (name, info) => {
    const line = info.point != null ? info.point : "2.5";
    return name === "Over" ? `+ de ${line} buts` : `- de ${line} buts`;
  });
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

    const competitions = sports.filter(
      (s) =>
        s.group === SPORT_GROUPS.Football &&
        !s.has_outrights &&
        (EUROPEAN_FOOTBALL_KEYS.has(s.key) || s.key.startsWith("soccer_uefa_"))
    );

    // Etape 1 : 1N2 par lot (1 credit par championnat).
    const h2hTasks = competitions.map((comp) => {
      const url = `${API_BASE}/sports/${comp.key}/odds?apiKey=${apiKey}&regions=${REGIONS}&markets=${MARKETS}&oddsFormat=decimal&dateFormat=iso`;
      return fetchJson(url)
        .then((events) =>
          events
            .filter((e) => new Date(e.commence_time).getTime() > now)
            .map((e) => ({
              ...e,
              _competitionTitle: comp.title,
              _sportKey: comp.key,
              _affiche: e.home_team && e.away_team ? `${e.home_team} - ${e.away_team}` : e.id,
            }))
        )
        .catch((err) => {
          console.error(`Erreur sur ${comp.key}: ${err.message}`);
          return [];
        });
    });

    const eventsByCompetition = await Promise.all(h2hTasks);
    const allEvents = eventsByCompetition.flat();
    const h2hRows = allEvents.flatMap((e) => analyzeH2h(e));

    // Etape 2 : marches secondaires (BTTS, buts) uniquement pour les matchs
    // ayant deja une issue 1N2 tres favorite (>= seuil), pour limiter le
    // nombre d'appels par match (chacun coute des credits en plus).
    const flaggedEvents = allEvents
      .filter((e) =>
        h2hRows.some(
          (r) =>
            r.affiche === e._affiche &&
            r.date_heure === e.commence_time &&
            r.probabilite_marche_pct >= SECONDARY_MARKETS_PROB_THRESHOLD
        )
      )
      .slice(0, SECONDARY_MARKETS_MAX_EVENTS);

    // Appels sequentiels (pas Promise.all) : l'endpoint par match est
    // sensible au rate-limit de The Odds API (429 EXCEEDED_FREQ_LIMIT) des
    // qu'on tire plusieurs requetes en parallele.
    const secondaryRows = [];
    for (const e of flaggedEvents) {
      const url = `${API_BASE}/sports/${e._sportKey}/events/${e.id}/odds?apiKey=${apiKey}&regions=${REGIONS}&markets=${SECONDARY_MARKETS}&oddsFormat=decimal&dateFormat=iso`;
      try {
        const full = await fetchJson(url);
        const enriched = { ...full, _competitionTitle: e._competitionTitle, _affiche: e._affiche };
        if (process.env.DEBUG_MARKETS) {
          const summary = (full.bookmakers || [])
            .map((b) => `${b.title}:[${(b.markets || []).map((m) => m.key).join(",")}]`)
            .join(" | ");
          console.error(`DEBUG ${e._affiche} (${e.id}): ${summary || "aucun bookmaker retourne"}`);
        }
        secondaryRows.push(...analyzeTotals(enriched));
      } catch (err) {
        console.error(`Erreur marches secondaires sur ${e.id}: ${err.message}`);
      }
      await new Promise((r) => setTimeout(r, 550));
    }

    const allResults = [...h2hRows, ...secondaryRows].sort(
      (a, b) => b.probabilite_marche_pct - a.probabilite_marche_pct
    );

    res.setHeader("Cache-Control", "no-store");
    res.status(200).json(allResults);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
};
