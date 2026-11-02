import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.guardrails import append_kvb_disclaimer, validate_query
from src.rag_engine import DEFAULT_TELEMETRY_PATH, TelemetryRAGEngine
from src.tools import (
    LIVESTOCK_FORMULARY,
    POULTRY_FORMULARY,
    calculate_crop_agronomy,
    calculate_livestock_dosage,
    calculate_poultry_dosage,
    simulate_swine_markov,
)

POULTRY_TERMS = ("poultry", "birds?", "chickens?", "flock", "kuku", "broilers?", "layers?", "hens?")
SWINE_TERMS = ("pigs?", "swine", "sows?", "piglets?", "boars?", "gilts?", "weaners?", "nguruwe")
DOSING_TERMS = ("dose", "dosage", "dosing", "inject", "injection", "kipimo")
MARKOV_TERMS = ("markov", "behaviou?r", "vocali[sz]ation")
CROP_TERMS = ("crop", "irrigation", "moisture", "compost", "hectares?", "maize")

NUM = r"(\d+(?:\.\d+)?)"
WEIGHT_RE = re.compile(NUM + r"\s*(?:kgs?|kilos?|kilograms?)\b")
FLOCK_RE = re.compile(r"(?<![\d.])(\d+)[\s-]*(?:birds?|chickens?|broilers?|layers?|hens?|kuku)\b")
FLOCK_PREFIX_RE = re.compile(r"\b(?:kuku|flock(?:\s+of)?)\s+(\d+)\b(?![\d.]|\s*kg)")
STEPS_RE = re.compile(r"(\d+)\s*steps?\b")
TEMP_RE = re.compile(NUM + r"\s*(?:°\s*c|deg(?:rees)?\s*c?|c)\b")
AREA_RE = re.compile(NUM + r"\s*(?:ha|hectares?)\b")
PERCENT_RE = re.compile(NUM + r"\s*%")

MARKOV_DEFAULTS = {"steps": 6, "ambient_temp_c": 24.0}

UNVERIFIED_NOTE = {
    "en": "\n- ⚠️ UNVERIFIED formulary entry: confirm dose rate, concentration and withdrawal on the product label.",
    # TODO(owner): native-speaker review.
    "sw": "\n- ⚠️ Thamani hizi hazijathibitishwa: hakiki kipimo, nguvu ya dawa na muda wa kusubiri kwenye lebo.",
}


def _has_term(text: str, terms: Iterable[str]) -> bool:
    return re.search(r"\b(?:" + "|".join(terms) + r")\b", text) is not None


def _match_drug(text: str, formulary: Dict[str, Any]) -> Optional[str]:
    """Longest formulary key present as whole words; underscores match space/hyphen/underscore."""
    for key in sorted(formulary, key=len, reverse=True):
        if re.search(r"\b" + re.escape(key).replace("_", r"[\s_-]+") + r"\b", text):
            return key
    return None


def _single(values: List[float], label: str) -> float:
    """Return the one distinct value given, or raise when missing or ambiguous."""
    distinct = sorted(set(values))
    if not distinct:
        raise ValueError(f"Missing {label}.")
    if len(distinct) > 1:
        raise ValueError(f"Ambiguous {label}: found {', '.join(str(v) for v in distinct)}. Give exactly one.")
    return distinct[0]


def _is_sw(lang: str) -> bool:
    return lang.lower().startswith("sw")


class KimnovixAgriOS:
    """Central deterministic orchestrator for Kimnovix Agri-OS."""

    def __init__(
        self,
        mode: str | None = None,
        telemetry_path: str | Path = DEFAULT_TELEMETRY_PATH,
    ) -> None:
        self.mode = (mode or os.getenv("KIMNOVIX_MODE", "offline")).lower()
        self.rag = TelemetryRAGEngine(log_path=str(telemetry_path))

    def _result(
        self,
        status: str,
        category: str,
        response: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "status": status,
            "mode": self.mode,
            "category": category,
            "data": data,
            "response": response,
            "timestamp": (data or {}).get("timestamp") or datetime.now(timezone.utc).isoformat(),
        }

    def _error(self, category: str, exc: Exception) -> Dict[str, Any]:
        return self._result("ERROR", category, f"⚠️ Calculation Error: {exc}")

    # ------------------------------------------------------------------ routing
    def process_query(self, query: str, lang: str = "en") -> Dict[str, Any]:
        """Validate, route, and execute agricultural/clinical queries deterministically."""
        is_valid, cleaned_or_err = validate_query(query)
        if not is_valid:
            return self._result("BLOCKED", "SECURITY_GUARDRAIL", f"⛔ {cleaned_or_err}")

        # Normalise thousands separators ("2,000 birds") before number parsing.
        text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", cleaned_or_err.lower())

        poultry_drug = _match_drug(text, POULTRY_FORMULARY)
        livestock_drug = _match_drug(text, LIVESTOCK_FORMULARY)
        dosing = poultry_drug or livestock_drug or _has_term(text, DOSING_TERMS)

        if dosing:
            return self._route_dosing(text, lang, poultry_drug, livestock_drug)
        if _has_term(text, MARKOV_TERMS):
            return self._route_markov(text)
        if _has_term(text, CROP_TERMS):
            return self._route_crop(text)
        return self._route_rag(cleaned_or_err)

    def _route_dosing(
        self, text: str, lang: str, poultry_drug: Optional[str], livestock_drug: Optional[str]
    ) -> Dict[str, Any]:
        is_poultry = _has_term(text, POULTRY_TERMS)
        is_swine = _has_term(text, SWINE_TERMS)
        if is_poultry == is_swine:
            return self._error(
                "ANALYTICAL_DOSAGE",
                ValueError(
                    "State exactly one species: poultry (birds/kuku/broilers/layers) or swine "
                    "(pig/sow/piglet/nguruwe). No species is assumed."
                ),
            )
        if is_poultry:
            return self._route_poultry(text, lang, poultry_drug)
        return self._route_livestock(text, lang, livestock_drug)

    def _route_poultry(self, text: str, lang: str, drug: Optional[str]) -> Dict[str, Any]:
        category = "ANALYTICAL_POULTRY_DOSAGE"
        try:
            if drug is None:
                raise ValueError(f"Name the compound. Supported: {', '.join(sorted(POULTRY_FORMULARY))}.")
            counts = [int(m) for m in FLOCK_RE.findall(text) + FLOCK_PREFIX_RE.findall(text)]
            flock_size = int(_single(counts, "flock size (e.g. '100 birds' or 'kuku 100')"))
            weight = _single([float(w) for w in WEIGHT_RE.findall(text)], "average bird weight (e.g. '1.5 kg')")
            res = calculate_poultry_dosage(drug=drug, flock_size=flock_size, avg_bird_weight_kg=weight)
        except ValueError as exc:
            return self._error(category, exc)
        return self._result(category=category, status="SUCCESS", data=res,
                            response=append_kvb_disclaimer(self._format_poultry(res, lang), lang=lang))

    def _route_livestock(self, text: str, lang: str, drug: Optional[str]) -> Dict[str, Any]:
        category = "ANALYTICAL_LIVESTOCK_DOSAGE"
        try:
            if drug is None:
                raise ValueError(f"Name the compound. Supported: {', '.join(sorted(LIVESTOCK_FORMULARY))}.")
            weight = _single([float(w) for w in WEIGHT_RE.findall(text)], "body weight (e.g. '180 kg')")
            res = calculate_livestock_dosage(drug=drug, weight_kg=weight, species="swine")
        except ValueError as exc:
            return self._error(category, exc)
        return self._result(category=category, status="SUCCESS", data=res,
                            response=append_kvb_disclaimer(self._format_livestock(res, lang), lang=lang))

    def _route_markov(self, text: str) -> Dict[str, Any]:
        category = "SWINE_MARKOV_TWIN"
        state = "STRESS_VOCALIZATION" if "stress" in text else "RESTING"
        parsed = {"steps": [int(s) for s in STEPS_RE.findall(text)],
                  "ambient_temp_c": [float(t) for t in TEMP_RE.findall(text)]}
        try:
            args = {k: _single(v, k) if v else MARKOV_DEFAULTS[k] for k, v in parsed.items()}
            sim = simulate_swine_markov(initial_state=state, steps=int(args["steps"]),
                                        ambient_temp_c=float(args["ambient_temp_c"]))
        except ValueError as exc:
            return self._error(category, exc)
        sim["defaults_applied"] = [k for k, v in parsed.items() if not v]
        return self._result("SUCCESS", category, self._format_markov(sim), sim)

    def _route_crop(self, text: str) -> Dict[str, Any]:
        category = "CROP_AGRONOMY"
        try:
            area = _single([float(a) for a in AREA_RE.findall(text)], "field area (e.g. '2 ha')")
            moisture = _single([float(p) for p in PERCENT_RE.findall(text)], "current soil moisture (e.g. '45%')")
            crop = "maize" if "maize" in text else "unspecified"
            agro = calculate_crop_agronomy(crop=crop, area_ha=area, current_moisture_pct=moisture)
        except ValueError as exc:
            return self._error(category, exc)
        return self._result("SUCCESS", category, self._format_crop(agro), agro)

    def _route_rag(self, query: str) -> Dict[str, Any]:
        records = self.rag.retrieve(query, top_k=3)
        bullet_lines = [
            f"- **[{r.get('timestamp', 'N/A')}] {r.get('section', 'Field')} ({r.get('species', 'General')}):** "
            f"{r.get('observation', '')} → *Action:* {r.get('action_taken', 'Logged')}"
            for r in records
        ]
        summary = "\n".join(bullet_lines) if bullet_lines else "- No matching local telemetry logs found."
        return self._result("SUCCESS", "TELEMETRY_RAG", f"📡 **Offline Telemetry RAG Synthesis:**\n{summary}",
                            {"matched_records": records})

    # --------------------------------------------------------------- formatting
    @staticmethod
    def _format_poultry(r: Dict[str, Any], lang: str) -> str:
        product = f"{r['product_required']} {r['product_unit']}"
        if _is_sw(lang):
            egg = ("\n- ✅ Mayai: Salama kwa kuku wa mayai" if r["egg_safe"]
                   else "\n- ⚠️ Haifai kwa kuku wanaotaga mayai ya chakula")
            msg = (
                f"✅ **Kipimo cha Dawa ya Kuku ({r['drug'].title()}):**\n"
                f"- Idadi ya Kuku: {r['flock_size']} (wastani {r['avg_bird_weight_kg']} kg)\n"
                f"- Kiwango kwa Kuku Mmoja: {r['dose_per_bird_mg']} mg\n"
                f"- Kiwango cha Kundi kwa Siku: {r['total_daily_dose_mg']} mg\n"
                f"- Kiasi cha Dawa: **{product}** ({r['route']})\n"
                f"- Muda wa Kusubiri Nyama: Siku {r['withdrawal_days']}{egg}"
            )
        else:
            egg = ("\n- ✅ Egg Withdrawal: Safe for laying flocks" if r["egg_safe"]
                   else "\n- ⚠️ Do NOT administer to birds producing eggs for human consumption")
            msg = (
                f"✅ **Deterministic Poultry Dosage ({r['drug'].title()}):**\n"
                f"- Flock: {r['flock_size']} birds @ {r['avg_bird_weight_kg']} kg avg "
                f"({r['flock_biomass_kg']} kg biomass)\n"
                f"- Dose per Bird: {r['dose_per_bird_mg']} mg ({r['dosage_rate_mg_kg']} mg/kg)\n"
                f"- Daily Flock Dose: {r['total_daily_dose_mg']} mg\n"
                f"- Product Required ({r['product_form']}): **{product}** via {r['route']}\n"
                f"- Meat Withdrawal Period: {r['withdrawal_days']} days{egg}"
            )
        return msg + ("" if r["verified"] else UNVERIFIED_NOTE["sw" if _is_sw(lang) else "en"])

    @staticmethod
    def _format_livestock(r: Dict[str, Any], lang: str) -> str:
        msg = (
            f"✅ **Deterministic Livestock Dosage ({r['drug'].upper()}):**\n"
            f"- Bodyweight: {r['weight_kg']} kg ({r['species'].title()})\n"
            f"- Total Active Dose: {r['total_dose_mg']} mg ({r['dosage_rate_mg_kg']} mg/kg)\n"
            f"- Injection Volume: **{r['volume_ml']} mL** via {r['route']}\n"
            f"- Meat Withdrawal: {r['withdrawal_meat_days']} days"
        )
        return msg + ("" if r["verified"] else UNVERIFIED_NOTE["sw" if _is_sw(lang) else "en"])

    @staticmethod
    def _format_markov(sim: Dict[str, Any]) -> str:
        probs_str = ", ".join(f"{k}: {v * 100:.1f}%" for k, v in sim["probabilities"].items())
        alert = "🚨 THRESHOLD EXCEEDED" if sim["anomaly_detected"] else "🟢 BELOW THRESHOLD"
        defaults = (f"\n- Defaults applied (not in query): {', '.join(sim['defaults_applied'])}"
                    if sim["defaults_applied"] else "")
        return (
            f"🐖 **Swine Markov Behavioral Twin ({alert}):**\n"
            f"- Initial State: `{sim['initial_state']}` | Horizon: {sim['steps']} steps @ {sim['ambient_temp_c']}°C\n"
            f"- Dominant State: **{sim['dominant_state']}**\n"
            f"- Distribution: {probs_str}{defaults}\n"
            f"- ⚠️ Simulated from an uncalibrated matrix, not observed herd behaviour."
        )

    @staticmethod
    def _format_crop(agro: Dict[str, Any]) -> str:
        return (
            f"🌱 **Deterministic Crop Agronomy ({agro['crop'].title()}):**\n"
            f"- Area: {agro['area_ha']} ha | Soil Moisture: {agro['current_moisture_pct']}% "
            f"(Target: {agro['target_moisture_pct']}%)\n"
            f"- Moisture Deficit: {agro['moisture_deficit_pct']}%\n"
            f"- Irrigation Required: **{agro['irrigation_required_m3']} m³** ({agro['irrigation_required_liters']:,.0f} L)\n"
            f"- Compost Baseline: **{agro['compost_required_tons']} tons**\n"
            f"- ⚠️ UNVERIFIED constants: assumes volumetric moisture over a 0.30 m root zone and a flat compost rate."
        )
