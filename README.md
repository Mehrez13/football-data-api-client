# ⚽ Football Data API Client

Interface web moderne pour interroger l'API Football-Data.org avec des filtres personnalisés et un téléchargement automatique des résultats.

## 🚀 Fonctionnalités

- **Interface intuitive** : Design moderne et responsive
- **Multiples endpoints** : Accès à tous les principaux endpoints de l'API
- **Filtres avancés** : Filtrage par date, saison, statut, etc.
- **Téléchargement automatique** : Les résultats sont automatiquement téléchargés en JSON
- **Validation** : Vérification des champs obligatoires
- **Gestion d'erreurs** : Messages d'état clairs

## 📋 Endpoints disponibles

1. **Compétitions** - Liste toutes les compétitions disponibles
2. **Classements** - Classements d'une compétition spécifique
3. **Matchs d'une compétition** - Tous les matchs d'une compétition
4. **Équipes d'une compétition** - Toutes les équipes d'une compétition
5. **Meilleurs buteurs** - Top scoreurs d'une compétition
6. **Matchs d'une équipe** - Tous les matchs d'une équipe spécifique

## 🛠️ Installation et utilisation

### Option 1: Utilisation directe
1. Clonez ce dépôt :
   ```bash
   git clone https://github.com/Mehrez13/football-data-api-client.git
   cd football-data-api-client
   ```

2. Ouvrez `index.html` dans votre navigateur

3. Entrez votre clé API Football-Data.org

4. Sélectionnez l'endpoint désiré et configurez les filtres

5. Cliquez sur "Exécuter" pour lancer la requête

### Option 2: Serveur local
Pour éviter les problèmes CORS, vous pouvez utiliser un serveur local :

```bash
# Avec Python 3
python -m http.server 8000

# Avec Node.js (si vous avez http-server installé)
npx http-server .

# Avec PHP
php -S localhost:8000
```

Puis accédez à `http://localhost:8000`

## 🔑 Obtenir une clé API

1. Rendez-vous sur [Football-Data.org](https://www.football-data.org/)
2. Créez un compte gratuit
3. Obtenez votre clé API dans votre dashboard
4. La version gratuite permet 10 requêtes/minute

## 📁 Structure du projet

```
football-data-api-client/
├── index.html          # Interface principale
├── js/
│   └── app.js         # Logique JavaScript
├── examples/
│   ├── competitions.json    # Exemple de réponse compétitions
│   ├── standings.json       # Exemple de classements
│   ├── matches.json         # Exemple de matchs
│   ├── teams.json          # Exemple d'équipes
│   ├── scorers.json        # Exemple de buteurs
│   └── team_matches.json   # Exemple de matchs d'équipe
├── docs/
│   ├── API_DOCUMENTATION.md # Documentation de l'API
│   └── FILTERS_GUIDE.md    # Guide des filtres
├── tests/
│   └── test_examples.html  # Page de test avec exemples
└── README.md
```

## 🎯 Exemples d'utilisation

### Obtenir le classement de la Premier League
- Sélectionner "Classements d'une compétition"
- Choisir "Premier League" (PL)
- Optionnel: spécifier une saison (ex: 2024)
- Cliquer "Exécuter"

### Obtenir les prochains matchs du Real Madrid
- Sélectionner "Matchs d'une équipe"
- Entrer l'ID: 86 (Real Madrid)
- Sélectionner statut: "Programmé"
- Cliquer "Exécuter"

### Obtenir les meilleurs buteurs de la Ligue 1
- Sélectionner "Meilleurs buteurs"
- Choisir "Ligue 1" (FL1)
- Définir limite: 10
- Cliquer "Exécuter"

## 🔧 Codes d'équipes populaires

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

## 🏆 Codes de compétitions

| Compétition | Code |
|-------------|------|
| Premier League | PL |
| Champions League | CL |
| Bundesliga | BL1 |
| La Liga | PD |
| Serie A | SA |
| Ligue 1 | FL1 |
| Eredivisie | DED |

## 🐛 Résolution des problèmes

### Erreur CORS
Utilisez un serveur local ou testez avec des exemples hors ligne.

### Erreur 403 (Forbidden)
Vérifiez votre clé API et les limites de votre plan.

### Erreur 404 (Not Found)
Vérifiez les IDs de compétition ou d'équipe.

### Pas de données
Certaines compétitions peuvent ne pas avoir de données pour toutes les saisons.

## 📞 Support

- **Issues GitHub** : [Créer une issue](https://github.com/Mehrez13/football-data-api-client/issues)
- **Documentation API** : [Football-Data.org Docs](https://www.football-data.org/documentation/quickstart)

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :

1. Fork le projet
2. Créer une branche pour votre fonctionnalité
3. Commit vos changements
4. Push vers la branche
5. Ouvrir une Pull Request

---

**Note** : Cette application nécessite une clé API Football-Data.org pour fonctionner. L'API gratuite a des limitations de taux (10 requêtes/minute).