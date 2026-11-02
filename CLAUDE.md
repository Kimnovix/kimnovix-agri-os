# CLAUDE.md — Kimnovix Agri-OS Tactical Engineering Spec

## Architecture & Constraints
- **Stack:** Python 3.11, FastAPI (`whatsapp_bot.py`), Streamlit (`app.py`), Docker Compose.
- **Core Rule:** All veterinary dosing (`mg/kg`), swine Markov behavioral transitions, and crop irrigation calculations in `src/tools.py` MUST remain 100% deterministic. Never use probabilistic LLM generation for clinical math.
- **No invented numbers:** Every formulary, Markov and agronomy constant carries `verified`/`source`. Never add or change a value without a cited source; dosing paths must error on missing inputs, never default.
- **Statutory Compliance:** Every veterinary calculation routed through `src/core.py` must append the bilingual (`en`/`sw`) Kenya Veterinary Board (KVB) notice via `append_kvb_disclaimer()`.

## Verification Commands
- **Setup:** `python3.11 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`
- **Run Unit Tests (Bypassing global ROS 2 Jazzy pytest plugins):**
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest -v`
- **Validate Docker Orchestration:**
  `docker compose config && docker compose build`
