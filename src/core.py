import os
import re
from datetime import datetime, timezone
from typing import Any, Dict

from src.guardrails import append_kvb_disclaimer, validate_query
from src.rag_engine import TelemetryRAGEngine
from src.tools import (
    POULTRY_FORMULARY,
    calculate_crop_agronomy,
    calculate_livestock_dosage,
    calculate_poultry_dosage,
    simulate_swine_markov,
)


class KimnovixAgriOS:
    """Central deterministic orchestrator for Kimnovix Agri-OS."""

    def __init__(
        self,
        mode: str | None = None,
        telemetry_path: str = "data/telemetry_logs.json",
    ) -> None:
        self.mode = (mode or os.getenv("KIMNOVIX_MODE", "offline")).lower()
        self.rag = TelemetryRAGEngine(log_path=telemetry_path)

    @staticmethod
    def _extract_floats(text: str) -> list[float]:
        return [float(x) for x in re.findall(r"\b\d+(?:\.\d+)?\b", text)]

    def process_query(self, query: str, lang: str = "en") -> Dict[str, Any]:
        """Validate, route, and execute agricultural/clinical queries deterministically."""
        is_valid, cleaned_or_err = validate_query(query)
        if not is_valid:
            return {
                "status": "BLOCKED",
                "mode": self.mode,
                "category": "SECURITY_GUARDRAIL",
                "data": None,
                "response": f"⛔ {cleaned_or_err}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        q_lower = cleaned_or_err.lower()

        # 1. Poultry Dosage Intent Routing
        if any(k in q_lower for k in ("poultry", "bird", "birds", "flock", "kuku", "broiler", "layer")) or any(
            d in q_lower for d in POULTRY_FORMULARY
        ):
            drug = next((d for d in POULTRY_FORMULARY if d in q_lower), "amoxicillin")
            nums = self._extract_floats(q_lower)
            flock_size = int(nums[0]) if len(nums) >= 1 else 100
            avg_weight = float(nums[1]) if len(nums) >= 2 else 1.5

            try:
                poultry_result = calculate_poultry_dosage(
                    drug=drug, flock_size=flock_size, avg_bird_weight_kg=avg_weight
                )
                egg_note_en = (
                    "\n- ✅ Egg Withdrawal: Safe for laying flocks"
                    if poultry_result["egg_safe"]
                    else "\n- ⚠️ Do NOT administer to birds producing eggs for human consumption"
                )
                egg_note_sw = (
                    "\n- ✅ Mayai: Salama kwa kuku wa mayai"
                    if poultry_result["egg_safe"]
                    else "\n- ⚠️ Haifai kwa kuku wanaotaga mayai ya chakula"
                )

                if lang.lower().startswith("sw"):
                    msg = (
                        f"✅ **Kipimo cha Dawa ya Kuku ({poultry_result['drug'].title()}):**\n"
                        f"- Idadi ya Kuku: {poultry_result['flock_size']} (wastani {poultry_result['avg_bird_weight_kg']} kg)\n"
                        f"- Kiwango kwa Kuku Mmoja: {poultry_result['dose_per_bird_mg']} mg\n"
                        f"- Kiwango cha Kundi kwa Siku: {poultry_result['total_daily_dose_mg']} mg\n"
                        f"- Unga wa Dawa: **{poultry_result['powder_required_g']} g** ({poultry_result['route']})\n"
                        f"- Muda wa Kusubiri Nyama: Siku {poultry_result['withdrawal_days']}"
                        f"{egg_note_sw}"
                    )
                else:
                    msg = (
                        f"✅ **Deterministic Poultry Dosage ({poultry_result['drug'].title()}):**\n"
                        f"- Flock: {poultry_result['flock_size']} birds @ {poultry_result['avg_bird_weight_kg']} kg avg "
                        f"({poultry_result['flock_biomass_kg']} kg biomass)\n"
                        f"- Dose per Bird: {poultry_result['dose_per_bird_mg']} mg ({poultry_result['dosage_rate_mg_kg']} mg/kg)\n"
                        f"- Daily Flock Dose: {poultry_result['total_daily_dose_mg']} mg\n"
                        f"- Soluble Powder Required: **{poultry_result['powder_required_g']} g** via {poultry_result['route']}\n"
                        f"- Meat Withdrawal Period: {poultry_result['withdrawal_days']} days"
                        f"{egg_note_en}"
                    )

                return {
                    "status": "SUCCESS",
                    "mode": self.mode,
                    "category": "ANALYTICAL_POULTRY_DOSAGE",
                    "data": poultry_result,
                    "response": append_kvb_disclaimer(msg, lang=lang),
                    "timestamp": poultry_result["timestamp"],
                }
            except ValueError as exc:
                return {
                    "status": "ERROR",
                    "mode": self.mode,
                    "category": "ANALYTICAL_POULTRY_DOSAGE",
                    "data": None,
                    "response": f"⚠️ Calculation Error: {exc}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        # 2. Swine/Livestock Injectable Dosage Routing
        if any(k in q_lower for k in ("dose", "dosage", "inject", "ivermectin", "iron_dextran", "oxytetracycline_la")):
            drug = "ivermectin" if "ivermectin" in q_lower else (
                "iron_dextran" if "iron" in q_lower else "oxytetracycline_la"
            )
            nums = self._extract_floats(q_lower)
            weight_kg = nums[0] if nums else 120.0
            try:
                res = calculate_livestock_dosage(drug=drug, weight_kg=weight_kg, species="swine")
                msg = (
                    f"✅ **Deterministic Livestock Dosage ({res['drug'].upper()}):**\n"
                    f"- Bodyweight: {res['weight_kg']} kg ({res['species'].title()})\n"
                    f"- Total Active Dose: {res['total_dose_mg']} mg ({res['dosage_rate_mg_kg']} mg/kg)\n"
                    f"- Injection Volume: **{res['volume_ml']} mL** via {res['route']}\n"
                    f"- Meat Withdrawal: {res['withdrawal_meat_days']} days"
                )
                return {
                    "status": "SUCCESS",
                    "mode": self.mode,
                    "category": "ANALYTICAL_LIVESTOCK_DOSAGE",
                    "data": res,
                    "response": append_kvb_disclaimer(msg, lang=lang),
                    "timestamp": res["timestamp"],
                }
            except ValueError as exc:
                return {
                    "status": "ERROR",
                    "mode": self.mode,
                    "category": "ANALYTICAL_LIVESTOCK_DOSAGE",
                    "data": None,
                    "response": f"⚠️ Calculation Error: {exc}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        # 3. Swine Markov Behavioral Digital Twin Routing
        if any(k in q_lower for k in ("markov", "behavior", "behaviour", "vocalization", "farrowing", "stress")):
            state = "STRESS_VOCALIZATION" if "stress" in q_lower else "RESTING"
            nums = self._extract_floats(q_lower)
            steps = int(nums[0]) if len(nums) >= 1 and 1 <= nums[0] <= 48 else 6
            temp_c = float(nums[1]) if len(nums) >= 2 else 24.0
            sim = simulate_swine_markov(initial_state=state, steps=steps, ambient_temp_c=temp_c)
            probs_str = ", ".join(f"{k}: {v * 100:.1f}%" for k, v in sim["probabilities"].items())
            alert = "🚨 ANOMALY DETECTED" if sim["anomaly_detected"] else "🟢 NOMINAL"
            msg = (
                f"🐖 **Swine Markov Behavioral Twin ({alert}):**\n"
                f"- Initial State: `{sim['initial_state']}` | Horizon: {sim['steps']} steps @ {sim['ambient_temp_c']}°C\n"
                f"- Dominant State: **{sim['dominant_state']}**\n"
                f"- Distribution: {probs_str}"
            )
            return {
                "status": "SUCCESS",
                "mode": self.mode,
                "category": "SWINE_MARKOV_TWIN",
                "data": sim,
                "response": msg,
                "timestamp": sim["timestamp"],
            }

        # 4. Crop Agronomy & Irrigation Routing
        if any(k in q_lower for k in ("crop", "irrigation", "moisture", "compost", "hectare", "maize")):
            nums = self._extract_floats(q_lower)
            area_ha = nums[0] if len(nums) >= 1 else 2.0
            moisture = nums[1] if len(nums) >= 2 else 45.0
            agro = calculate_crop_agronomy(crop="maize", area_ha=area_ha, current_moisture_pct=moisture)
            msg = (
                f"🌱 **Deterministic Crop Agronomy ({agro['crop'].title()}):**\n"
                f"- Area: {agro['area_ha']} ha | Soil Moisture: {agro['current_moisture_pct']}% "
                f"(Target: {agro['target_moisture_pct']}%)\n"
                f"- Moisture Deficit: {agro['moisture_deficit_pct']}%\n"
                f"- Irrigation Required: **{agro['irrigation_required_m3']} m³** ({agro['irrigation_required_liters']:,.0f} L)\n"
                f"- Compost Baseline: **{agro['compost_required_tons']} tons**"
            )
            return {
                "status": "SUCCESS",
                "mode": self.mode,
                "category": "CROP_AGRONOMY",
                "data": agro,
                "response": msg,
                "timestamp": agro["timestamp"],
            }

        # 5. Default Fallback: Deterministic Telemetry RAG
        records = self.rag.retrieve(cleaned_or_err, top_k=3)
        bullet_lines = [
            f"- **[{r.get('timestamp', 'N/A')}] {r.get('section', 'Field')} ({r.get('species', 'General')}):** "
            f"{r.get('observation', '')} → *Action:* {r.get('action_taken', 'Logged')}"
            for r in records
        ]
        summary = "\n".join(bullet_lines) if bullet_lines else "- No matching local telemetry logs found."
        msg = f"📡 **Offline Telemetry RAG Synthesis:**\n{summary}"
        return {
            "status": "SUCCESS",
            "mode": self.mode,
            "category": "TELEMETRY_RAG",
            "data": {"matched_records": records},
            "response": msg,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
