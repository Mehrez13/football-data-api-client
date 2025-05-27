# Documentation API Football-Data.org

## 📚 Vue d'ensemble

Cette documentation détaille l'utilisation de l'API Football-Data.org v4 avec notre client web.

## 🔗 URL de base

```
https://api.football-data.org/v4
```

## 🔐 Authentification

Toutes les requêtes nécessitent un header d'authentification :

```
X-Auth-Token: VOTRE_CLE_API
```

## 📊 Endpoints disponibles

### 1. Compétitions

#### Lister toutes les compétitions
- **Endpoint** : `/v4/competitions`
- **Méthode** : GET
- **Filtres** : 
  - `areas` : IDs des zones géographiques séparés par virgule

**Exemple d'URL** :
```
https://api.football-data.org/v4/competitions?areas=2,5,6
```

### 2. Classements

#### Obtenir les classements d'une compétition
- **Endpoint** : `/v4/competitions/{id}/standings`
- **Méthode** : GET
- **Filtres** :
  - `matchday` : Journée spécifique
  - `season` : Année de début de saison
  - `date` : Date spécifique (YYYY-MM-DD)

**Exemple d'URL** :
```
https://api.football-data.org/v4/competitions/PL/standings?season=2024&matchday=15
```

### 3. Matchs

#### Matchs d'une compétition
- **Endpoint** : `/v4/competitions/{id}/matches`
- **Méthode** : GET
- **Filtres** :
  - `dateFrom` : Date de début (YYYY-MM-DD)
  - `dateTo` : Date de fin (YYYY-MM-DD)
  - `status` : Statut du match
  - `matchday` : Journée
  - `season` : Saison

#### Matchs d'une équipe
- **Endpoint** : `/v4/teams/{id}/matches`
- **Méthode** : GET
- **Filtres** :
  - `dateFrom` : Date de début
  - `dateTo` : Date de fin
  - `season` : Saison
  - `status` : Statut du match
  - `venue` : Lieu (HOME/AWAY)
  - `limit` : Nombre de résultats

### 4. Équipes

#### Équipes d'une compétition
- **Endpoint** : `/v4/competitions/{id}/teams`
- **Méthode** : GET
- **Filtres** :
  - `season` : Saison

### 5. Buteurs

#### Meilleurs buteurs d'une compétition
- **Endpoint** : `/v4/competitions/{id}/scorers`
- **Méthode** : GET
- **Filtres** :
  - `limit` : Nombre de buteurs (défaut: 10)
  - `season` : Saison

## 🎯 Codes de compétitions populaires

| Compétition | Code | ID |
|-------------|------|-----|
| Premier League | PL | 2021 |
| Champions League | CL | 2001 |
| Bundesliga | BL1 | 2002 |
| La Liga | PD | 2014 |
| Serie A | SA | 2019 |
| Ligue 1 | FL1 | 2015 |
| Eredivisie | DED | 2003 |

## 🏆 Codes d'équipes populaires

| Équipe | ID |
|--------|-----|
| Real Madrid | 86 |
| FC Barcelona | 81 |
| Manchester United | 66 |
| Arsenal | 57 |
| Chelsea | 61 |
| Liverpool | 64 |
| Manchester City | 65 |
| Paris Saint-Germain | 524 |
| Bayern Munich | 5 |
| Juventus | 109 |

## 📅 Statuts de matchs

- `SCHEDULED` : Programmé
- `LIVE` : En direct
- `IN_PLAY` : En cours de jeu
- `PAUSED` : En pause
- `FINISHED` : Terminé
- `POSTPONED` : Reporté
- `SUSPENDED` : Suspendu
- `CANCELLED` : Annulé

## 🏟️ Lieux de match

- `HOME` : Domicile
- `AWAY` : Extérieur

## ⚠️ Limites de l'API

### Plan gratuit
- 10 requêtes par minute
- Accès limité aux données
- Certaines compétitions non disponibles

### Plans payants
- Plus de requêtes par minute
- Accès complet aux données
- Cotes de paris
- Données en temps réel

## 🔧 Gestion des erreurs

### Codes d'erreur courants

- `400` : Requête mal formée
- `403` : Clé API invalide ou limite atteinte
- `404` : Ressource non trouvée
- `429` : Trop de requêtes
- `500` : Erreur serveur

### Exemple de réponse d'erreur

```json
{
  \"message\": \"The resource you are looking for does not exist.\",
  \"errorCode\": 404
}
```

## 📝 Exemples de réponses

### Classement

```json
{
  \"standings\": [
    {
      \"stage\": \"REGULAR_SEASON\",
      \"type\": \"TOTAL\",
      \"table\": [
        {
          \"position\": 1,
          \"team\": {
            \"id\": 64,
            \"name\": \"Liverpool FC\",
            \"crest\": \"https://crests.football-data.org/64.png\"
          },
          \"points\": 38,
          \"won\": 12,
          \"draw\": 2,
          \"lost\": 1
        }
      ]
    }
  ]
}
```

### Match

```json
{
  \"id\": 456789,
  \"utcDate\": \"2024-12-15T15:00:00Z\",
  \"status\": \"FINISHED\",
  \"homeTeam\": {
    \"id\": 64,
    \"name\": \"Liverpool FC\"
  },
  \"awayTeam\": {
    \"id\": 65,
    \"name\": \"Manchester City FC\"
  },
  \"score\": {
    \"fullTime\": {
      \"home\": 2,
      \"away\": 0
    }
  }
}
```

## 🔗 Ressources utiles

- [Documentation officielle](https://www.football-data.org/documentation/quickstart)
- [Créer un compte](https://www.football-data.org/client/register)
- [Gestion des clés API](https://www.football-data.org/client/apps)