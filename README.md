# Tetrabot

A modular Python bot built to handle commands, scheduled cron events, direct messages, and custom message handlers.

## Features

* **Command Handling:** Built-in command module featuring base classes and individual command extensions (`aup`, `clean`, `gamble`, `top`, `random`, `rig`, etc.).
* **Cron Events:** Automated periodic task execution managed under `cronevents/`.
* **Direct Message Support:** DM handlers to process incoming private messages and specific DM commands.
* **Database Initialization:** Setup script (`database_init.py`) included to initialize local storage.
* **Deployment Ready:** Includes `Procfile` for Heroku or similar PaaS deployment.

## Getting Started

### Prerequisites

* Python 3.x
* Dependencies listed in `requirements.txt`

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/your-username/Tetrabot.git
cd Tetrabot

```


2. **Install dependencies:**
```bash
pip install -r requirements.txt

```


3. **Initialize the database:**
```bash
python database_init.py

```



### Configuration

Edit `settings.py` to add your bot credentials, database URIs, API key, and configuration options.

### Running the Bot

Start the main application entry point:

```bash
python tetrabot.py

```

## Project Structure

```text
Tetrabot/
├── commands/         # Command implementations and handlers
├── cronevents/       # Cron event routines and base models
├── dms/              # DM routing and commands
├── events/           # Event handlers
├── database_init.py  # Database initialization script
├── message_handler.py# Core message routing logic
├── settings.py       # Configuration and environment settings
├── tetrabot.py       # Main bot execution file
├── requirements.txt  # Project dependencies
└── Procfile          # Deployment configuration

```

## License

This project is licensed under the terms of the [LICENSE](https://www.google.com/search?q=LICENSE) file included in the repository.
