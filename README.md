# Tetrabot

Un bot Discord modulaire en Python intégrant des **Slash Commands Discord (`/`)**, un préfixe texte classique (`!`), et une base de données **MongoDB Atlas** asynchrone.

---

## 🚀 Fonctionnalités

- **Slash Commands & UI Modernes :** Support natif des commandes slash (`/`) avec autocomplétion, descriptions, et composants interactifs (boutons `discord.ui.Button` pour la pagination et l'acceptation de défis).
- **Base de données MongoDB :** Driver asynchrone Motor pour le stockage des statistiques de jeu, de l'historique et des classements.
- **Filtres de messages :** Pipeline composable (`filters/`) — ignore les messages du bot, route DM vs serveur, puis parse le préfixe `!`.
- **Jeux d'argent & Duels :**
  - `/gamble <limite>` : Défi de roulette cappée contre un autre joueur.
  - `/crit <somme> [odds]` : Duel de coups critiques (chafer) avec relance automatique en cas d'égalité.
  - `/incscore` (ou `/leaderboard`) : Tableau des scores et classement par équité avec pagination par boutons.
  - `/random [min] [max]` : Tirage de nombres aléatoires.
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
.venv\Scripts\python tetrabot.py
```

### 4. Lancer les tests
```bash
python tests\run_all.py
```

---

## 📂 Structure du Projet

```text
Tetrabot/
├── config/              # CONFIG/START — démarrage et réglages
│   ├── settings.py      #   Variables d'environnement (.env) et constantes
│   ├── utils.py         #   Helpers partagés (recherche de salons, ...)
│   └── start.py         #   Fabrique du bot : intents, events, slash tree
├── filters/             # FILTRES — pipeline des messages entrants
│   ├── base.py          #   FilterResult + classe de base MessageFilter
│   ├── self_messages.py #   Ignore les messages du bot lui-même
│   ├── direct_messages.py # Route DM vs serveur
│   ├── prefix.py        #   Parse le préfixe !command args
│   └── pipeline.py      #   Chaînage (default_pipeline)
├── controllers/         # CONTRÔLEURS — logique métier des commandes
│   ├── context.py       #   CommandContext + fabriques de "respond" (! et /)
│   ├── commands.py      #   Les fonctions cmd_* (source unique pour ! et /)
│   ├── registry.py      #   Registre LOGIC (auto-collecte des cmd_*)
│   ├── slash.py         #   Adapteurs Slash natifs (/), thin wrappers
│   ├── prefix/          #   Adapteurs préfixe (!gamble, !crit, !clean, etc.)
│   │   ├── base_command.py # Classe de base + dispatch générique vers LOGIC
│   │   ├── router.py    #   Routage des messages préfixe vers les commandes
│   │   └── ...
│   └── dm/              #   Commandes spécifiques aux messages privés
│       ├── base_dm.py
│       ├── router.py    #   Routage des messages privés
│       └── hot.py
├── models/              # MODÈLES — accès données et règles pures
│   ├── db.py            #   Connexion MongoDB Atlas (Motor) et collections
│   ├── stats.py         #   Stats, winrate, leaderboard, enregistrement
│   └── duels.py         #   Règles de duel gamble/crit (pures, testables)
├── views/               # VUES — rendu pur, jamais d'accès BDD
│   ├── formatting.py    #   Renderers (messages et embeds)
│   ├── leaderboard.py   #   View de pagination du classement
│   └── challenge.py     #   Views de défi (boutons Gamble/Crit)
├── tests/               # Tests par couche (modèles, renderers, transports, filtres)
│   └── run_all.py       #   python tests\run_all.py
├── tetrabot.py          # Point d'entrée (délègue à config.start)
├── run.bat              # Lanceur Windows en un clic
├── requirements.txt     # Dépendances Python modernes
└── .env.example         # Modèle de configuration sécurisé
```

> **Architecture MVC (Model-View-Controller) + Filtres + Config/Start** :
> chaque commande n'est implémentée **qu'une seule fois** dans
> `controllers/commands.py` et sert aussi bien au préfixe `!` qu'aux
> slash-commands `/`. Les modèles ne dépendent jamais de Discord, les vues
> n'accèdent jamais à la base de données, et les contrôleurs orchestrent les
> deux puis rendent via `ctx.respond(...)`. En amont, chaque message `!`
> traverse le pipeline `filters/` (ignore-self → routage DM/serveur →
> parsing du préfixe) et le démarrage vit dans `config/start.py`.


---

## 📜 Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.

