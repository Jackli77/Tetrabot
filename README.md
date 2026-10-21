# Tetrabot

Un bot Discord modulaire en Python intégrant des **Slash Commands Discord (`/`)**, un préfixe texte classique (`!`), et une base de données **MongoDB Atlas** asynchrone.

---

## 🚀 Fonctionnalités

- **Slash Commands & UI Modernes :** Support natif des commandes slash (`/`) avec autocomplétion, descriptions, et composants interactifs (boutons `discord.ui.Button` pour la pagination et l'acceptation de défis).
- **Base de données MongoDB :** Driver asynchrone Motor pour le stockage des statistiques de jeu, de l'historique et des classements.
- **Détecteurs `!` et `/` :** Deux détecteurs (`tetrabot/detectors/`) reconnaissent chaque style d'invocation, construisent le même `CommandContext`, et appellent la même logique partagée (`tetrabot/commands/`).
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
│   ├── context.py          #   CommandContext + adaptateurs de réponse (! et /)
│   ├── helpers.py          #   Petits utilitaires Discord (recherche de salon)
│   ├── detectors/          # DÉTECTEURS — un par style d'invocation
│   │   ├── base.py         #   BaseDetector + DetectionResult
│   │   ├── prefix.py       #   Détecteur ! : ignore-self → DM/serveur → parsing
│   │   └── slash.py        #   Détecteur / : arbre slash généré depuis le catalogue
│   ├── commands/           # LOGIQUE PARTAGÉE — une seule implémentation par commande
│   │   ├── logic.py        #   Les commandes simples (inc, random, aup, chat, ...)
│   │   └── duels.py        #   Les duels (gamble, crit)
│   ├── models/             # MODÈLES — accès données et règles pures
│   │   ├── db.py           #   Connexion MongoDB (Motor) et collections
│   │   ├── stats.py        #   Stats, winrate, leaderboard, enregistrement
│   │   ├── duels.py        #   Règles de duel gamble/crit (pures, testables)
│   │   └── llm.py          #   Client HTTP du LLM local Ollama
│   └── views/              # VUES — rendu et widgets interactifs
│       ├── formatting.py   #   Renderers (messages et embeds) — pur
│       └── widgets.py      #   Views Discord (boutons, pagination)
├── tests/                  # Tests pytest (par couche)
├── pyproject.toml          # Métadonnées, packaging et config pytest
├── requirements.txt        # Dépendances de production
├── run.bat                 # Lanceur Windows en un clic
└── .env.example            # Modèle de configuration sécurisé
```

> **Architecture en couches + catalogue de commandes** :
> chaque commande est implémentée **qu'une seule fois** dans
> `tetrabot/commands/` et sert aussi bien au préfixe `!` qu'aux
> slash-commands `/`. Les deux transports ne font que *reconnaître* leur
> style d'invocation et normaliser un `CommandContext` : `detectors/prefix`
> (ignore-self → routage DM/serveur → parsing du préfixe `!`) et
> `detectors/slash` (enregistrement de l'arbre `/`). Le `catalog.py` décrit
> chaque commande une seule fois, et le routeur `!`, l'arbre `/` et l'embed
> d'aide sont tous générés à partir de lui. Les modèles ne dépendent jamais
> de Discord, les vues n'accèdent jamais à la base de données, et la logique
> partagée orchestre les deux puis rend via `ctx.respond(...)`.

### Ajouter une commande

1. Écrivez `async def cmd_foo(ctx)` dans `tetrabot/commands/logic.py`.
2. Ajoutez une entrée `CommandSpec` dans `tetrabot/catalog.py`.
3. Ajoutez la fonction à `LOGIC` dans `tetrabot/commands/__init__.py`.

Les deux transports, l'aide et les tests de cohérence sont mis à jour
automatiquement.

---

## 📜 Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.
