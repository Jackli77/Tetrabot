# Tetrabot

> Un agent IA qui **vit dans un salon Discord** : il écoute la conversation,
> décide quand avoir besoin de facts, va les chercher avec des outils, puis
> répond — en montrant comment il a trouvé sa réponse.

Un bot Discord modulaire en Python, avec **Slash Commands (`/`)**, un préfixe
texte classique (`!`), une base **MongoDB** asynchrone, et un **agent** qui
tourne sur un modèle local (Ollama) sans jamais envoyer vos données à un
service tiers.

---

## ⚡ Voir l'agent travailler en 5 secondes

Aucune installation, aucun token, aucun modèle, aucun réseau :

```bash
python -m tetrabot demo
```

```text
🤖  Tetrabot — agent demo (scripted, no network needed)

  user › What's the weather like in Paris right now?

  💭 think (0ms)
      I need the weather and the time in Paris.
  🔧 tool get_weather (0ms)
      {"city": "Paris"}
  👁 observation get_weather (0ms)
      {"ok": true, "result": {"found": true, "city": "Paris", ...}}
  🔧 tool get_datetime (0ms)
      {"timezone": "Europe/Paris"}
  👁 observation get_datetime (0ms)
      {"ok": true, "result": {"date": "2024-01-15", "time": "14:32:07", ...}}
  🤖 answer (0ms)
      It is 14°C and partly cloudy in Paris, and the time there is 14:32. ...

  ── 2 round(s) · 2 tool call(s) · 0ms ──
```

C'est le vrai agent : la boucle, les outils et la trace sont les mêmes que
ceux qui tournent en production. Seul le *raisonnement* est scripté — c'est
ce qui rend la démo instantanée, déterministe, et testable.

| Commande | Ce qu'elle fait | Besoin de setup ? |
|---|---|---|
| `python -m tetrabot demo` | Conversation scriptée, étape par étape | **Non** |
| `python -m tetrabot eval` | La suite d'évaluation de l'agent | **Non** |
| `python -m tetrabot tools` | Les outils disponibles et leurs schémas | **Non** |
| `python -m tetrabot chat "..."` | Le vrai agent, dans le terminal | Ollama |
| `python -m tetrabot` | Le bot Discord | Token + MongoDB + Ollama |

---

## 🧠 L'agent

### La boucle : raisonner → agir → observer → répondre

Un chatbot répond. Un agent *agit*. Le cœur du projet
(`tetrabot/models/agent.py`) est la boucle **reason → act → observe** :

```text
        ┌──────────────────────────────────────────────┐
        │                                              │
        ▼                                              │
  ┌───────────┐   demande un outil   ┌──────────┐     │
  │  Répondre │◀──────────────────────│ Exécuter │─────┘
  └───────────┘   observation        │  l'outil │
        ▲                              └──────────┘
        │                                    ▲
        │         outils disponibles          │
        └────────────────────────────────────┘
                    (schémas JSON)
```

1. Le modèle reçoit la question, le contexte, et les **schémas** des outils ;
2. s'il demande un outil, l'outil tourne et son résultat lui est renvoyé ;
3. le modèle lit l'observation et décide à nouveau ;
4. quand il ne demande plus d'outil, il rédige la réponse.

### Ce qui en fait un *bon* agent

| Propriété | Implémentation | Pourquoi |
|---|---|---|
| **Outils en parallèle** | `asyncio.gather` sur les appels d'un même tour | Un modèle veut souvent la météo *et* l'heure : il ne les attend pas l'une après l'autre. |
| **Cache par exécution** | Clé `nom + arguments` | Un modèle confus ne peut pas marteler une API publique. |
| **Budget borné** | `CHAT_MAX_TOOL_ROUNDS` | La boucle se termine, et le modèle doit **répondre** avec ce qu'il a. |
| **Outils qui ne lèvent jamais** | `ToolResult(ok=False, error=...)` | Une API en panne est *expliquée* à l'utilisateur, elle ne casse pas la réponse. |
| **Trace complète** | `AgentTrace` | Chaque étape est mesurée et affichable. |

### La trace : voir le raisonnement

C'est la différence entre « le bot a dit quelque chose » et « voici comment il
l'a trouvé ». Chaque exécution produit une **trace** : le raisonnement, les
outils appelés, leurs arguments, leurs résultats, et la durée de chaque étape.

- **Dans Discord** : la commande `/trace` affiche la trace du dernier agent
  du salon, sous forme d'embed lisible.
- **Dans le terminal** : `python -m tetrabot demo` l'affiche étape par étape.
- **Dans les tests** : `AgentTrace` est une structure de données, donc
  assertable.

```python
trace = await agent.run("Quel temps fait-il à Paris ?")
trace.tools_used   # ['get_weather']
trace.tool_calls   # 1
trace.duration_ms  # 812
trace.steps        # [think, tool, observation, answer]
```

### Les outils

Le bot n'invente pas les faits : il les **cherche**. Ollama gère le
*function calling* nativement ; le bot décrit ses outils au modèle et exécute
ceux qu'il demande.

| Outil | Ce qu'il fait | Source |
|---|---|---|
| `get_weather` | Météo actuelle + prévision sur 3 jours | Open-Meteo (sans clé) |
| `search_wikipedia` | Résumé de l'article + autres résultats | Wikipédia (5 langues) |
| `search_web` | Réponse courte et sourcée | DuckDuckGo |
| `get_datetime` | Date et heure, avec le fuseau demandé | Horloge système |

Aucun de ces outils ne demande de clé API : le bot fonctionne *out of the box*.

---

## 🏗️ Architecture

```text
   Discord                    tetrabot/                     Ollama
   ────────                  ──────────                     ──────
  message  ──▶ prefix.py  ─┐
  slash    ──▶ slash.py   ─┼─▶ CommandContext ──▶ commands/ ──▶ models/agent.py
  (channel) ─▶ listen.py  ─┘                          │              │
                            │                          ▼              ▼
                            └──────────────────────▶ views/      models/llm.py
                                     (rendu)                      │
                                                                    ▼
                                                              models/tools/
                                                            (météo, wiki, web)
```

Quatre couches, des dépendances à sens unique, **vérifiées par un test**
(`tests/test_controllers.py::TestArchitecture`) :

| Couche | Rôle | Ne dépend jamais de |
|---|---|---|
| `models/` | Agent, LLM, outils, données, règles métier | Discord |
| `views/` | Rendu : messages, embeds, widgets | La base, les contrôleurs |
| `controllers/` | Transports (`!`, `/`, écoute) + handlers partagés | — |
| `catalog.py` | La **source de vérité** des commandes | — |

Trois transports, **un seul** `CommandContext`, **un seul** handler par
commande. Une commande ne peut donc pas exister sur un seul transport par
inadvertance : le catalogue est le générateur du routeur `!`, de l'arbre `/`
*et* de l'embed d'aide.

### L'agent est transportable

`models/agent.py` ne connaît ni Discord, ni le terminal. Il prend une
question, rend une trace. Le *backend* est un petit protocole
(`AgentBackend`), ce qui permet de l'exécuter :

- contre **Ollama** en production (`OllamaBackend`) ;
- contre un **script** pour la démo et les tests (`ScriptedBackend`) ;
- contre n'importe quoi d'autre, sans toucher à la boucle.

C'est ce qui rend la démo instantanée et la suite de tests déterministe.

---

## 🚀 Fonctionnalités

- **Agent outillé** : boucle raison → action → observation, outils en parallèle, cache par exécution, budget borné, trace complète (`/trace`).
- **Écoute active** : le bot répond à **chaque** message du salon `Tetrabot` — pas de commande `/chat` à taper. Le salon se change dans `CHAT_CHANNEL`, et `CHAT_LISTEN="0"` le fait taire.
- **Une réponse à la fois** : les messages d'un salon sont mis en file d'attente et traités dans l'ordre, pour ne jamais solliciter le modèle local en parallèle.
- **Il ne se répond pas à lui-même** : ses propres messages sont ignorés, et le contexte qu'il reçoit ne contient jamais ses réponses précédentes.
- **Réponse en streaming** : le texte s'écrit dans le salon au fur et à mesure, plus un indicateur « le bot écrit ».
- **Mémoire de conversation** : le bot se souvient des échanges du salon (TTL de 6 h), donc « et lui ? » fonctionne enfin.
- **Contexte intelligent** : messages vides, commandes, doublons et bruit du salon sont écartés avant d'envoyer quoi que ce soit au modèle.
- **Budget de tokens adapté** : les modèles « raisonnants » consomment leur budget en réflexion et renvoient parfois une réponse *vide* — le bot relance avec un budget plus large au lieu d'abandonner.
- **Erreurs explicites** : serveur injoignable, modèle absent, délai dépassé et réponse vide ont chacun leur message actionnable.
- **Rendu soigné** : les réponses longues deviennent un embed, et les blocs de code sont extraits et affichés avec leur langage.
- **Slash Commands & UI modernes** : autocomplétion, descriptions, composants interactifs (`discord.ui.Button`) pour la pagination et l'acceptation de défis.
- **MongoDB asynchrone** : driver Motor pour les statistiques, l'historique et les classements.
- **Jeux & duels** : `/gamble <limite>`, `/crit <somme> [odds]`, `/incscore`, `/random [min] [max]`.
- **Utilitaires serveur** : `/clean <nombre>` (purge avec confirmation éphémère), `/commands` (aide interactive), surveillance vocale, log des messages supprimés.

---

## 🧪 Évaluation

Un demo de chatbot ne prouve pas grand-chose : le modèle peut répondre de
mémoire et avoir l'air brillant. La question intéressante est de savoir si
l'agent **agit** bien — et ça se mesure.

```bash
python -m tetrabot eval
```

```text
🧪  Tetrabot — agent evaluation

[PASS] weather-lookup — ok
[PASS] wikipedia-lookup — ok
[PASS] web-lookup — ok
[PASS] two-tools-at-once — ok
[PASS] no-tool-needed — ok
[PASS] failing-tool — ok

6/6 cases passed
```

Chaque cas indique les outils **attendus** et les outils **interdits**. La
suite tourne contre des *outils bouchons* (`models/tools/stubs.py`) : elle est
donc reproductible, sans réseau, et une régression apparaît comme un échec
de l'agent — jamais comme une panne d'API.

---

## 🛠️ Installation & Démarrage

### Prérequis
- Python 3.10+ (compatible Python 3.14)
- Un bot Discord créé sur le [Discord Developer Portal](https://discord.com/developers/applications/) avec l'intent `Message Content` et les permissions `applications.commands` et `bot`.
- Un cluster MongoDB (ex: MongoDB Atlas gratuit).
- [Ollama](https://ollama.com/) avec un modèle de chat (`ollama pull qwen3:4b`).

> Pour la démo et les tests, ni Discord, ni MongoDB, ni Ollama ne sont
> nécessaires.

### 1. Configuration
Copiez le modèle d'environnement :
```bash
cp .env.example .env
```
Puis éditez `.env` avec vos identifiants :
```env
BOT_TOKEN="votre-token-discord"
MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net"
OLLAMA_MODEL="qwen3:4b"
```

### 2. Dépendances
Créez l'environnement virtuel et installez les dépendances :
```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 3. Lancer
```bash
python -m tetrabot              # le bot Discord
python -m tetrabot demo         # la démo, sans setup
```
Sur Windows, double-cliquez simplement sur **`run.bat`**.

### 4. Tester
```bash
python -m pytest                # 234 tests
python -m ruff check tetrabot tests
```

### Les variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `BOT_TOKEN` | — | Le token du bot Discord (obligatoire) |
| `MONGODB_URI` | — | La chaîne de connexion MongoDB |
| `OLLAMA_HOST` | `http://localhost:11434` | Le serveur Ollama |
| `OLLAMA_MODEL` | `qwen3:4b` | Le modèle de chat utilisé |
| `CHAT_CHANNEL` | `Tetrabot` | Le salon que le bot écoute |
| `CHAT_LISTEN` | `1` | `0` pour que le bot se taise |
| `CHAT_MAX_TOOL_ROUNDS` | `3` | Le budget d'outils par question |
| `CHAT_TOOLS` | tous | Les outils activés, séparés par des virgules |

---

## 📂 Structure du Projet

```text
Tetrabot/
├── tetrabot/               # Le paquet principal
│   ├── __main__.py         #   Point d'entrée : python -m tetrabot [demo|eval|chat|tools]
│   ├── cli.py              #   La ligne de commande (démo, évaluation, terminal)
│   ├── app.py              #   Fabrique du bot : intents, événements, arbre slash
│   ├── config.py           #   Réglages (variables d'environnement et constantes)
│   ├── catalog.py          #   CATALOGUE — la description de chaque commande
│   ├── helpers.py          #   Petits utilitaires Discord (recherche de salon)
│   ├── models/             # M — MODÈLES : accès données et règles pures
│   │   ├── agent.py        #   ★ L'AGENT : boucle raison→action→observation + trace
│   │   ├── scripted.py     #   Un modèle scripté (démo et tests, sans réseau)
│   │   ├── evals.py        #   La suite d'évaluation de l'agent
│   │   ├── db.py           #   Connexion MongoDB (Motor) et collections
│   │   ├── stats.py        #   Stats, winrate, leaderboard, enregistrement
│   │   ├── duels.py        #   Règles de duel gamble/crit (pures, testables)
│   │   ├── llm.py          #   Client HTTP du LLM local Ollama (+ streaming, outils)
│   │   ├── memory.py       #   Mémoire de conversation (par salon, avec TTL)
│   │   ├── context.py      #   Sélection du contexte envoyé au modèle
│   │   └── tools/          #   Les outils de recherche du chatbot
│   │       ├── base.py     #     Le contrat d'un outil (nom, schéma, appel)
│   │       ├── lookup.py   #     Météo, Wikipédia, web, date et heure
│   │       ├── registry.py #     Les outils activés et leurs schémas
│   │       └── stubs.py    #     Les mêmes outils, bouchons, pour l'évaluation
│   ├── views/              # V — VUES : rendu et widgets interactifs
│   │   ├── formatting.py   #   Renderers (messages et embeds) — pur
│   │   ├── chat.py         #   Rendu du chatbot (embeds, code, erreurs, trace)
│   │   ├── widgets.py      #   Views Discord (boutons, pagination)
│   │   └── responders.py   #   Adaptateurs de sortie (message / interaction)
│   └── controllers/        # C — CONTRÔLEURS : pipeline de requête
│       ├── base.py         #   BaseController : pipeline partagé (détecter→résoudre→valider)
│       ├── context.py      #   CommandContext + ChallengeRequest
│       ├── prefix.py       #   Contrôleur `!` : ignore-self → routage → parsing
│       ├── slash.py        #   Contrôleur `/` : arbre slash généré depuis le catalogue
│       ├── listen.py       #   Contrôleur « écoute » : répond à chaque message du salon
│       └── commands/       #   Les handlers partagés (une implémentation par commande)
│           ├── logic.py    #     Les commandes simples (inc, random, aup, ...)
│           ├── chat.py     #     L'agent en salon (streaming, mémoire, trace)
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
> slash-commands `/`. Les transports ne font que *reconnaître* leur
> style d'invocation et normaliser un `CommandContext` : `controllers/prefix`
> (ignore-self → routage DM/serveur → parsing du préfixe `!`),
> `controllers/slash` (enregistrement de l'arbre `/`) et
> `controllers/listen` (détection du salon écouté → file d'attente par
> salon). Le `catalog.py` décrit
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

### Ajouter un outil

1. Écrivez `async def ma_fonction(...) -> ToolResult` dans
   `tetrabot/models/tools/lookup.py`.
2. Ajoutez un `Tool(name=..., description=..., parameters=..., handler=...)`
   dans `tetrabot/models/tools/registry.py`.

La description est la partie la plus importante : c'est *tout* ce que le
modèle sait de l'outil, et c'est ce qui décide s'il l'utilisera.

### Ajouter une commande

1. Écrivez `async def cmd_foo(ctx)` dans `tetrabot/controllers/commands/logic.py`.
2. Ajoutez une entrée `CommandSpec` dans `tetrabot/catalog.py`.
3. Ajoutez la fonction à `HANDLERS` dans `tetrabot/controllers/commands/__init__.py`.

Les deux transports, l'aide et les tests de cohérence sont mis à jour
automatiquement.

---

## 🧭 Choix de conception

Les décisions qui ont le plus influencé le projet, et pourquoi.

| Décision | Alternative rejetée | Pourquoi |
|---|---|---|
| **Ollama en local** | Une API cloud (OpenAI, Anthropic) | Aucune donnée ne sort de la machine, et le bot fonctionne hors ligne. Le prix : il faut un GPU. |
| **Un `AgentBackend` injectable** | Appeler Ollama directement dans la boucle | La boucle devient testable et la démo instantanée, sans mocker le HTTP. |
| **Les outils ne lèvent jamais** | Laisser les exceptions remonter | Le modèle peut alors *expliquer* la panne à l'utilisateur au lieu de disparaître. |
| **Le budget se termine par une réponse** | Rendre les mains à l'utilisateur | Un agent qui se tait est un agent qui a échoué ; il doit répondre avec ce qu'il a, ou dire qu'il ne sait pas. |
| **Une trace par exécution** | Logger en console | Une trace est une *donnée* : affichable, testable, comparable. C'est ce qui rend l'agent lisible. |
| **Un catalogue de commandes** | Déclarer les commandes dans chaque transport | Une commande ne peut plus exister sur un seul transport par inadvertance. |
| **Les couches vérifiées par un test** | Une discipline implicite | Une règle qui n'est pas testée finit par être violée. |
| **File d'attente par salon** | Répondre en parallèle | Un modèle local sature vite ; les réponses se chevaucheraient. |

### Limites assumées

- **Le raisonnement est aussi bon que le modèle.** Avec un petit modèle
  local (`qwen3:4b`), l'agent rate parfois un outil. La boucle, elle, est
  solide et mesurable — c'est ce que l'évaluation vérifie.
- **La mémoire est en mémoire.** Les échanges d'un salon vivent en RAM
  (TTL 6 h) : le bot oublie au redémarrage. Une persistance MongoDB des
  faits long-terme est la suite naturelle.
- **Pas de contrôle d'accès fin.** N'importe qui dans le salon déclenche une
  requête au modèle local ; un quota par utilisateur serait la suite
  logique.
- **Les outils sont en lecture seule.** Rien n'écrit dans un système
  externe : le bot ne peut pas casser grand-chose.

---

## 📜 Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.
