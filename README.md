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
  - `/chat <message>` : Envoie le message au chatbot local **Ollama** (`qwen3:4b`) et affiche sa réponse dans le salon.
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
│   │   └── llm.py          #   Client HTTP du LLM local Ollama
│   ├── views/              # V — VUES : rendu et widgets interactifs
│   │   ├── formatting.py   #   Renderers (messages et embeds) — pur
│   │   ├── widgets.py      #   Views Discord (boutons, pagination)
│   │   └── responders.py   #   Adaptateurs de sortie (message / interaction)
│   └── controllers/        # C — CONTRÔLEURS : pipeline de requête
│       ├── base.py         #   BaseController : pipeline partagé (détecter→résoudre→valider)
│       ├── context.py      #   CommandContext + ChallengeRequest
│       ├── prefix.py       #   Contrôleur `!` : ignore-self → routage → parsing
│       ├── slash.py        #   Contrôleur `/` : arbre slash généré depuis le catalogue
│       └── commands/       #   Les handlers partagés (une implémentation par commande)
│           ├── logic.py    #     Les commandes simples (inc, random, aup, chat, ...)
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

### Ajouter une commande

1. Écrivez `async def cmd_foo(ctx)` dans `tetrabot/controllers/commands/logic.py`.
2. Ajoutez une entrée `CommandSpec` dans `tetrabot/catalog.py`.
3. Ajoutez la fonction à `HANDLERS` dans `tetrabot/controllers/commands/__init__.py`.

Les deux transports, l'aide et les tests de cohérence sont mis à jour
automatiquement.

---

## 📜 Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.
