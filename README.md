# Tetrabot

Un bot Discord modulaire en Python intégrant des **Slash Commands Discord (`/`)**, un préfixe texte classique (`!`), et une base de données **MongoDB Atlas** asynchrone.

---

## 🚀 Fonctionnalités

- **Slash Commands & UI Modernes :** Support natif des commandes slash (`/`) avec autocomplétion, descriptions, et composants interactifs (boutons `discord.ui.Button` pour la pagination et l'acceptation de défis).
- **Base de données MongoDB :** Driver asynchrone Motor pour le stockage des statistiques de jeu, de l'historique et des classements.
- **Architecture MVC :** Le code est réparti en trois couches à dépendances strictes — `models/` (données et règles métier), `views/` (rendu, widgets, adaptateurs de sortie) et `controllers/` (pipeline de requête et handlers partagés). Un test automatisé (`tests/test_controllers.py::TestArchitecture`) vérifie qu'aucune couche ne dépend d'une couche supérieure.
- **Contrôleurs `!` et `/` :** Deux contrôleurs (`tetrabot/controllers/`) reconnaissent chaque style d'invocation, construisent le même `CommandContext`, et appellent le même handler partagé (`tetrabot/controllers/commands/`).
- **Catalogue de commandes :** Une seule source de vérité (`tetrabot/catalog.py`) décrit chaque commande ; le routeur `!`, l'arbre `/` et l'embed d'aide en sont générés. Une commande ne peut donc pas exister sur un seul transport par inadvertance.
- **Jeux d'argent & Duels :**
  - `/gamble <limite>` : Défi de roulette cappée contre un autre joueur.
  - `/crit <somme> [odds]` : Duel de coups critiques (chafer) avec relance automatique en cas d'égalité.
  - `/incscore` (ou `/leaderboard`) : Tableau des scores et classement par équité avec pagination par boutons.
  - `/random [min] [max]` : Tirage de nombres aléatoires.
- **Chatbot (`/chat <message>`) :** Un vrai chatbot, pas une simple requête :
  - **Réponse en streaming** : le texte s'écrit dans le salon au fur et à mesure, plus un indicateur « le bot écrit » — plus de silence de 20 secondes.
  - **Outils de recherche** : le bot *cherche* les informations qu'il ne peut pas connaître, via le **function calling** d'Ollama :
    - `get_weather` — la météo actuelle et les jours à venir (Open-Meteo, sans clé API) ;
    - `search_wikipedia` — le résumé de l'article Wikipédia (fr/en/de/es/it) ;
    - `search_web` — une réponse courte et sourcée (DuckDuckGo) ;
    - `get_datetime` — la date et l'heure actuelles, avec le bon fuseau.
  - **Boucle d'outils** : le modèle demande un outil, le bot l'exécute et lui renvoie le résultat, puis le modèle rédige la vraie réponse. Le nombre de tours est borné, et un outil qui échoue est expliqué à l'utilisateur au lieu de casser la réponse.
  - **Mémoire de conversation** : le bot se souvient des échanges du salon (TTL de 6 h), donc « et lui ? » fonctionne enfin.
  - **Contexte intelligent** : les messages vides, les commandes, les doublons et le bruit du salon sont écartés avant d'envoyer quoi que ce soit au modèle.
  - **Budget de tokens adapté** : les modèles « raisonnants » consomment leur budget en réflexion et renvoient parfois une réponse *vide* — le bot relance alors avec un budget plus large au lieu d'abandonner.
  - **Erreurs explicites** : serveur injoignable, modèle absent, délai dépassé et réponse vide ont chacun leur message actionnable.
  - **Rendu soigné** : les réponses longues deviennent un embed, et les blocs de code sont extraits et affichés avec leur langage.
  - `/forget` : oublie la conversation en cours.
- **Utilitaires serveur :**
  - `/clean <nombre>` : Purge rapide et silencieuse de messages avec confirmation éphémère.
  - `/commands` : Menu d'aide interactif complet sous forme d'Embed.
  - Surveillance vocale et log des messages supprimés.

---

## 🛠️ Installation & Démarrage

### Prérequis
- Python 3.10+ (compatible Python 3.14)
- Un bot Discord créé sur le [Discord Developer Portal](https://discord.com/developers/applications/) avec les intents `Message Content` et les permissions Slash Commands (`applications.commands` et `bot`).
- Un cluster MongoDB (ex: MongoDB Atlas gratuit).

### 1. Configuration
Copiez le modèle d'environnement :
```bash
cp .env.example .env
```
Puis éditez `.env` avec vos identifiants :
```env
BOT_TOKEN="votre-token-discord"
MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net"
```

### 2. Dépendances
Créez l'environnement virtuel et installez les dépendances :
```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 3. Lancer le Bot
Sur Windows, double-cliquez simplement sur **`run.bat`** ou exécutez :
```bash
.venv\Scripts\python -m tetrabot
```

### 4. Lancer les tests
```bash
.venv\Scripts\python -m pytest
```

---

## 📂 Structure du Projet

```text
Tetrabot/
├── tetrabot/               # Le paquet principal
│   ├── __main__.py         #   Point d'entrée : python -m tetrabot
│   ├── app.py              #   Fabrique du bot : intents, événements, arbre slash
│   ├── config.py           #   Réglages (variables d'environnement et constantes)
│   ├── catalog.py          #   CATALOGUE — la description de chaque commande
│   ├── helpers.py          #   Petits utilitaires Discord (recherche de salon)
│   ├── models/             # M — MODÈLES : accès données et règles pures
│   │   ├── db.py           #   Connexion MongoDB (Motor) et collections
│   │   ├── stats.py        #   Stats, winrate, leaderboard, enregistrement
│   │   ├── duels.py        #   Règles de duel gamble/crit (pures, testables)
│   │   ├── llm.py          #   Client HTTP du LLM local Ollama (+ streaming, outils)
│   │   ├── memory.py       #   Mémoire de conversation (par salon, avec TTL)
│   │   ├── context.py      #   Sélection du contexte envoyé au modèle
│   │   └── tools/          #   Les outils de recherche du chatbot
│   │       ├── base.py     #     Le contrat d'un outil (nom, schéma, appel)
│   │       ├── lookup.py   #     Météo, Wikipédia, web, date et heure
│   │       └── registry.py #     Les outils activés et leurs schémas
│   ├── views/              # V — VUES : rendu et widgets interactifs
│   │   ├── formatting.py   #   Renderers (messages et embeds) — pur
│   │   ├── chat.py         #   Rendu du chatbot (embeds, code, erreurs)
│   │   ├── widgets.py      #   Views Discord (boutons, pagination)
│   │   └── responders.py   #   Adaptateurs de sortie (message / interaction)
│   └── controllers/        # C — CONTRÔLEURS : pipeline de requête
│       ├── base.py         #   BaseController : pipeline partagé (détecter→résoudre→valider)
│       ├── context.py      #   CommandContext + ChallengeRequest
│       ├── prefix.py       #   Contrôleur `!` : ignore-self → routage → parsing
│       ├── slash.py        #   Contrôleur `/` : arbre slash généré depuis le catalogue
│       └── commands/       #   Les handlers partagés (une implémentation par commande)
│           ├── logic.py    #     Les commandes simples (inc, random, aup, ...)
│           ├── chat.py     #     Le chatbot (streaming, mémoire, relance)
│           └── duels.py    #     Les duels (gamble, crit)
├── tests/                  # Tests pytest (par couche)
├── pyproject.toml          # Métadonnées, packaging et config pytest
├── requirements.txt        # Dépendances de production
├── run.bat                 # Lanceur Windows en un clic
└── .env.example            # Modèle de configuration sécurisé
```

> **Architecture MVC + catalogue de commandes** :
> chaque commande est implémentée **qu'une seule fois** dans
> `tetrabot/controllers/commands/` et sert aussi bien au préfixe `!` qu'aux
> slash-commands `/`. Les deux transports ne font que *reconnaître* leur
> style d'invocation et normaliser un `CommandContext` : `controllers/prefix`
> (ignore-self → routage DM/serveur → parsing du préfixe `!`) et
> `controllers/slash` (enregistrement de l'arbre `/`). Le `catalog.py` décrit
> chaque commande une seule fois, et le routeur `!`, l'arbre `/` et l'embed
> d'aide sont tous générés à partir de lui. Le **Modèle** ne dépend jamais
> de Discord, la **Vue** n'accède jamais à la base de données ni au
> Contrôleur, et les handlers partagés orchestrent les deux puis rendent via
> `ctx.respond(...)`.

### Les outils du chatbot

Le chatbot n'invente pas les faits : il les **cherche**. Ollama gère le
*function calling* nativement, le bot décrit ses outils au modèle et exécute
ceux qu'il demande.

| Outil | Ce qu'il fait | Source |
|---|---|---|
| `get_weather` | Météo actuelle + prévision sur 3 jours | Open-Meteo (sans clé) |
| `search_wikipedia` | Résumé de l'article + autres résultats | Wikipédia (5 langues) |
| `search_web` | Réponse courte et sourcée | DuckDuckGo |
| `get_datetime` | Date et heure, avec le fuseau demandé | Horloge système |

La boucle est bornée (`CHAT_MAX_TOOL_ROUNDS`) et chaque outil **ne lève
jamais** : un échec est renvoyé au modèle comme une donnée, pour qu'il
puisse l'expliquer à l'utilisateur.

Pour activer ou désactiver un outil :

```env
CHAT_TOOLS="get_weather,search_wikipedia"
```

### Ajouter une commande

1. Écrivez `async def cmd_foo(ctx)` dans `tetrabot/controllers/commands/logic.py`.
2. Ajoutez une entrée `CommandSpec` dans `tetrabot/catalog.py`.
3. Ajoutez la fonction à `HANDLERS` dans `tetrabot/controllers/commands/__init__.py`.

Les deux transports, l'aide et les tests de cohérence sont mis à jour
automatiquement.

---

## 📜 Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.
