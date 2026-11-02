# Kimnovix Agri-OS

Offline-first decision support for Kimnovix livestock and crop operations: deterministic
veterinary dose arithmetic, a swine behaviour Markov simulation, a crop irrigation/compost
calculator, and keyword retrieval over local field telemetry logs. Two front ends share one
router (`src/core.py`): a Streamlit terminal (`app.py`) and a FastAPI WhatsApp webhook
(`whatsapp_bot.py`).

> **Status: prototype.** Every formulary, Markov and agronomy constant in `src/tools.py` is
> marked `verified: False` with an `UNVERIFIED` source. Outputs say so. Do not dose animals
> from this tool until a KVB-registered vet has confirmed each formulary entry against the
> registered product label.

## Layout

| Path | Role |
|---|---|
| `src/tools.py` | Formularies and deterministic calculations (dose, Markov, agronomy) |
| `src/core.py` | Query router; parses numbers by unit and errors on missing dosing inputs |
| `src/guardrails.py` | Length cap, red-team patterns, bilingual KVB notice |
| `src/rag_engine.py` | Token-overlap retrieval over `data/telemetry_logs.json` |
| `app.py` | Streamlit terminal (port 8501) |
| `whatsapp_bot.py` | FastAPI webhook: `GET /health`, `POST /webhook/whatsapp` (port 8000) |
| `tests/` | Pytest suite |

## Query format (router)

Dosing queries must name the species, the compound, and values **with units**. Nothing is
assumed.

- Swine: `sow ivermectin 180 kg`, `iron dextran piglet 1.5 kg`, `oxytetracycline LA 90 kg pig`
- Poultry: `broilers amoxicillin 100 birds 1.5 kg`, `kuku 100 tylosin 1.8kg`
- Markov: `markov behaviour at 32c for 6 steps` (missing steps/temperature use disclosed defaults)
- Crop: `maize irrigation 2 ha at 45%`
- Anything else falls through to telemetry retrieval.

## Run locally (Linux Mint)

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest -v
.venv/bin/streamlit run app.py
.venv/bin/uvicorn whatsapp_bot:app --port 8000
```

## Docker

```bash
cp .env.example .env
docker compose config && docker compose up --build
```
