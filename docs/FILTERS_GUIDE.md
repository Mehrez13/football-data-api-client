# Guide des filtres - Football Data API

## 🎯 Vue d'ensemble

Ce guide détaille tous les filtres disponibles pour chaque endpoint de l'API Football-Data.org.

## 📊 Types de filtres

### 🔢 Filtres numériques

#### `id` - Identifiant
- **Type** : Integer
- **Format** : `/[0-9]+/`
- **Description** : L'ID d'une ressource
- **Exemple** : `86` (Real Madrid)

#### `limit` - Limite de résultats
- **Type** : Integer
- **Format** : `/\\d+/`
- **Description** : Nombre maximum de résultats
- **Défaut** : 10
- **Maximum** : 100
- **Exemple** : `20`

#### `matchday` - Journée
- **Type** : Integer
- **Format** : `/[1-4]+[0-9]*/`
- **Description** : Numéro de la journée
- **Exemple** : `15`, `38`
- **Plage** : 1-38 (selon la compétition)

### 📅 Filtres de date

#### `date` - Date spécifique
- **Type** : String
- **Format** : `yyyy-MM-dd`
- **Description** : Date exacte
- **Exemple** : `2024-12-15`

#### `dateFrom` - Date de début
- **Type** : String
- **Format** : `yyyy-MM-dd`
- **Description** : Date de début de la période
- **Exemple** : `2024-12-01`

#### `dateTo` - Date de fin
- **Type** : String
- **Format** : `yyyy-MM-dd`
- **Description** : Date de fin de la période
- **Exemple** : `2024-12-31`

#### `season` - Saison
- **Type** : String
- **Format** : `yyyy`
- **Description** : Année de début de saison
- **Exemple** : `2024` (pour la saison 2024-2025)
- **Plage** : 2000-2030

### 🎪 Filtres énumérés

#### `status` - Statut du match
- **Type** : Enum
- **Format** : `/[A-Z]+/`
- **Valeurs possibles** :
  - `SCHEDULED` : Programmé
  - `LIVE` : En direct
  - `IN_PLAY` : En cours de jeu
  - `PAUSED` : En pause
  - `FINISHED` : Terminé
  - `POSTPONED` : Reporté
  - `SUSPENDED` : Suspendu
  - `CANCELLED` : Annulé

#### `venue` - Lieu du match
- **Type** : Enum
- **Format** : `/[A-Z]+/`
- **Valeurs possibles** :
  - `HOME` : Domicile
  - `AWAY` : Extérieur

### 📍 Filtres de liste

#### `competitions` - Compétitions
- **Type** : String
- **Format** : `/\\d+,\\d+/`
- **Description** : IDs de compétitions séparés par virgule
- **Exemple** : `2021,2001,2002` (PL, CL, Bundesliga)

#### `areas` - Zones géographiques
- **Type** : String
- **Format** : `/\\d+,\\d+/`
- **Description** : IDs de zones séparés par virgule
- **Exemple** : `2072,2081,2088` (Angleterre, Allemagne, Espagne)

## 🔍 Filtres par endpoint

### Compétitions (`/competitions`)
- ✅ `areas`

### Classements (`/competitions/{id}/standings`)
- ✅ `matchday`
- ✅ `season`
- ✅ `date`

### Matchs de compétition (`/competitions/{id}/matches`)
- ✅ `dateFrom`
- ✅ `dateTo`
- ✅ `status`
- ✅ `matchday`
- ✅ `season`

### Équipes de compétition (`/competitions/{id}/teams`)
- ✅ `season`

### Buteurs (`/competitions/{id}/scorers`)
- ✅ `limit`
- ✅ `season`

### Matchs d'équipe (`/teams/{id}/matches`)
- ✅ `dateFrom`
- ✅ `dateTo`
- ✅ `season`
- ✅ `status`
- ✅ `venue`
- ✅ `limit`

## 💡 Conseils d'utilisation

### 📅 Filtres de date

```javascript
// Matchs du mois courant
dateFrom: '2024-12-01'
dateTo: '2024-12-31'

// Matchs des 7 derniers jours
const today = new Date();
const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
dateFrom: weekAgo.toISOString().split('T')[0]
dateTo: today.toISOString().split('T')[0]
```

### 🔢 Filtres numériques

```javascript
// Top 20 buteurs
limit: 20

// Journée actuelle
matchday: 16

// Saison en cours
season: 2024
```

### 📊 Combinaisons utiles

```javascript
// Prochains matchs d'une équipe à domicile
status: 'SCHEDULED'
venue: 'HOME'
dateFrom: '2024-12-15'

// Matchs terminés d'une compétition cette saison
status: 'FINISHED'
season: '2024'

// Classement après une journée spécifique
matchday: 15
season: '2024'
```

## ⚠️ Limitations et bonnes pratiques

### Limites
- Maximum 100 résultats par requête (`limit`)
- Les dates doivent être au format ISO (YYYY-MM-DD)
- Certains filtres ne sont pas compatibles entre eux

### Bonnes pratiques
- Utilisez toujours `season` pour des données cohérentes
- Limitez les plages de dates pour de meilleures performances
- Combinez `status` et `dateFrom`/`dateTo` pour des requêtes précises
- Utilisez `limit` pour éviter des réponses trop volumineuses

### Exemples d'erreurs courantes

```javascript
// ❌ Format de date incorrect
date: '15/12/2024'

// ✅ Format correct
date: '2024-12-15'

// ❌ ID invalide
team-id: 'arsenal'

// ✅ ID correct
team-id: 57
```

## 🔗 Ressources

- [Documentation officielle des filtres](https://www.football-data.org/documentation/api)
- [Liste des codes de compétitions](https://www.football-data.org/documentation/api#competitions)
- [Liste des IDs d'équipes](https://www.football-data.org/documentation/api#teams)