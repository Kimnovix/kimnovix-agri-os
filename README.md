# 🦁 Kimnovix Agri-OS

**Offline-first, fully deterministic clinical and agronomic decision support for farms.**

Kimnovix Agri-OS turns plain-language questions ("dose for 500 broilers at 1.8 kg", "irrigation for 3 hectares of maize at 30% moisture") into exact, repeatable answers, in English or Kiswahili. It runs on a farm-edge machine with no cloud dependency, through a Streamlit command terminal or a WhatsApp webhook.

![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)
![Docker](https://img.shields.io/badge/deploy-Docker%20Compose-2496ED)

---

## Why deterministic?

Veterinary dosing is not a place for guesswork. Every number Agri-OS returns comes from plain arithmetic and fixed formularies, never from LLM text generation.

- **Clinical math** (`mg/kg` dosing, powder and injection volumes) is computed by pure functions in [src/tools.py](src/tools.py).
- **Swine behavior** is modeled with a fixed Markov transition matrix.
- **Crop irrigation** and compost baselines are formula-driven.
- **Retrieval** over field logs uses token overlap, with no embeddings and no model calls.

The same input always gives the same output, which makes the system testable, auditable, and safe to run offline.

## Features

| Capability | What it does |
|---|---|
| 🐔 **Poultry dosing** | Flock-level dose, soluble powder required, meat withdrawal period, and egg-safety flag for amoxicillin, oxytetracycline, tylosin, and enrofloxacin |
| 🐖 **Livestock dosing** | Per-animal dose and injection volume for oxytetracycline LA, ivermectin, and iron dextran, with route and withdrawal period |
| 📈 **Swine Markov twin** | Simulates behavioral state distributions (`RESTING`, `FEEDING`, `FORAGING`, `STRESS_VOCALIZATION`) and flags anomalies |
| 🌱 **Crop agronomy** | Moisture deficit, irrigation volume (m³ and litres), and compost requirement for maize |
| 📡 **Telemetry RAG** | Offline retrieval over structured farm logs in [data/telemetry_logs.json](data/telemetry_logs.json) |
| 🛡️ **Guardrails** | Rejects empty or oversized queries (1,000-character cap), prompt-injection and SQL-style patterns, and unsafe clinical requests |
| ⚖️ **KVB compliance** | Every veterinary calculation carries a bilingual Kenya Veterinary Board statutory notice |
| 🌍 **Bilingual** | English (`en`) and Kiswahili (`sw`) responses |

## Quick start

### Docker (recommended)

```bash
docker compose up --build
```

| Service | URL | Purpose |
|---|---|---|
| Terminal (Streamlit) | http://localhost:8501 | Interactive command terminal |
| Webhook (FastAPI) | http://localhost:8000 | WhatsApp integration; interactive docs at `/docs` |

### Local development

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Command terminal
streamlit run app.py

# WhatsApp webhook (separate shell)
uvicorn whatsapp_bot:app --host 0.0.0.0 --port 8000
```

### Configuration

| Variable | Default | Description |
|---|---|---|
| `KIMNOVIX_MODE` | `offline` | Runtime mode, shown in the UI and in `/health` |

## Using the webhook

```bash
curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"sender": "+254700000000", "message": "amoxicillin dose for 500 broilers at 1.8 kg", "lang": "en"}'
```

The reply contains `recipient`, `status`, `category`, `reply`, and `timestamp`.

- `GET /health` is a liveness probe.
- `lang` accepts `en` or `sw`.
- Calculation errors return HTTP `422`.
- Queries blocked by guardrails return `status: "BLOCKED"`.

## How queries are routed

[src/core.py](src/core.py) validates each query and routes it by keyword, in this order:

1. **Poultry dosage**: poultry terms or a formulary drug name
2. **Livestock dosage**: "dose", "inject", "ivermectin", and similar
3. **Swine Markov twin**: "behavior", "stress", "farrowing", and similar
4. **Crop agronomy**: "crop", "irrigation", "maize", and similar
5. **Telemetry RAG**: the fallback for everything else

Numbers in the query are read positionally (for example, flock size and then average weight), with sensible defaults when omitted.

## Project layout

```
.
├── app.py                 # Streamlit command terminal
├── whatsapp_bot.py        # FastAPI WhatsApp webhook
├── src/
│   ├── core.py            # Orchestrator: validation, routing, response formatting
│   ├── tools.py           # Deterministic formularies and calculators
│   ├── guardrails.py      # Input validation and KVB disclaimers
│   └── rag_engine.py      # Offline telemetry retrieval
├── data/telemetry_logs.json
├── tests/test_kimnovix.py
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Testing

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest -v
```

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` keeps globally installed pytest plugins (such as ROS 2 ones) from interfering. The same suite runs in CI on every push and pull request to `main`.

To validate the container setup:

```bash
docker compose config && docker compose build
```

## Contributing

Contributions are welcome. Please keep these project rules in mind:

1. **Clinical math stays deterministic.** No probabilistic or LLM-generated values for dosing, Markov transitions, or irrigation in `src/tools.py`.
2. **Veterinary calculations routed through `src/core.py` must append the KVB notice** via `append_kvb_disclaimer()`.
3. **Add or update tests** and make sure the suite passes before opening a pull request.

## ⚖️ Disclaimer

Kimnovix Agri-OS is a decision-support tool, not a substitute for professional judgment. Final prescription, administration, and withdrawal verification must be authorized by a registered Kenya Veterinary Board (KVB) professional.
