# CLAUDE.md — Kimnovix Agri-OS Tactical Engineering Spec

## Architecture & Constraints
- **Stack:** Python 3.11, FastAPI (`whatsapp_bot.py`), Streamlit (`app.py`), Docker Compose.
- **Core Rule:** All veterinary dosing (`mg/kg`), swine Markov behavioral transitions, and crop irrigation calculations in `src/tools.py` MUST remain 100% deterministic. Never use probabilistic LLM generation for clinical math.
- **Statutory Compliance:** Every veterinary calculation routed through `src/core.py` must append the bilingual (`en`/`sw`) Kenya Veterinary Board (KVB) notice via `append_kvb_disclaimer()`.

## Verification Commands
- **Run Unit Tests (Bypassing global ROS 2 Jazzy pytest plugins):**
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest -v`
- **Validate Docker Orchestration:**
  `docker compose config && docker compose build`
