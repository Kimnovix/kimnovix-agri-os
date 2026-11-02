from datetime import datetime, timezone
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# PROVENANCE: every numeric constant in this module was supplied by the
# Gemini-generated v1.0.0 code with no cited source. None has been checked
# against a product label, the KVB/VMD register, or field data.
# Each entry carries `verified: False` and a `source` string until a
# registered vet (formulary) or the farm owner (model/agronomy constants)
# confirms it. Do NOT edit a number without recording its source.
# ---------------------------------------------------------------------------
UNVERIFIED_SOURCE = "UNVERIFIED: Gemini-generated v1.0.0 value, no cited source"

# concentration_mg_per_unit = mg active per product_unit (g of powder or mL of solution).
# TODO(vet): confirm dose rate, concentration, meat withdrawal and egg_safe per registered product.
POULTRY_FORMULARY: Dict[str, Dict[str, Any]] = {
    "amoxicillin": {
        "dosage_rate_mg_kg": 15.0,
        "concentration_mg_per_unit": 500.0,  # 50% w/w soluble powder (500 mg active per gram)
        "route": "Drinking Water (Soluble Powder 50% w/w)",
        "withdrawal_days": 5,
        "egg_safe": False,
        "product_form": "powder",
        "product_unit": "g",
        "verified": False,
        "source": UNVERIFIED_SOURCE,
    },
    "oxytetracycline": {
        "dosage_rate_mg_kg": 20.0,
        "concentration_mg_per_unit": 200.0,  # 20% w/w soluble powder
        "route": "Drinking Water (Soluble Powder 20% w/w)",
        "withdrawal_days": 7,
        "egg_safe": True,
        "product_form": "powder",
        "product_unit": "g",
        "verified": False,
        "source": UNVERIFIED_SOURCE,
    },
    "tylosin": {
        "dosage_rate_mg_kg": 25.0,
        "concentration_mg_per_unit": 1000.0,  # 100% tartrate soluble powder
        "route": "Drinking Water (Soluble Powder)",
        "withdrawal_days": 3,
        "egg_safe": True,
        "product_form": "powder",
        "product_unit": "g",
        "verified": False,
        "source": UNVERIFIED_SOURCE,
    },
    "enrofloxacin": {
        "dosage_rate_mg_kg": 10.0,
        "concentration_mg_per_unit": 100.0,  # 10% oral solution (mg per mL)
        "route": "Drinking Water (10% Oral Solution)",
        "withdrawal_days": 8,
        "egg_safe": False,
        "product_form": "solution",
        "product_unit": "mL",
        "verified": False,
        "source": UNVERIFIED_SOURCE,
    },
}

# TODO(vet): confirm every value. iron_dextran is modelled per kg here; many piglet
# protocols use a fixed mg per piglet. Do not trust its output until confirmed.
LIVESTOCK_FORMULARY: Dict[str, Dict[str, Any]] = {
    "oxytetracycline_la": {
        "dosage_rate_mg_kg": 20.0,
        "concentration_mg_ml": 200.0,
        "route": "Deep Intramuscular (IM)",
        "withdrawal_meat_days": 28,
        "verified": False,
        "source": UNVERIFIED_SOURCE,
    },
    "ivermectin": {
        "dosage_rate_mg_kg": 0.3,
        "concentration_mg_ml": 10.0,
        "route": "Subcutaneous (SC) Neck",
        "withdrawal_meat_days": 28,
        "verified": False,
        "source": UNVERIFIED_SOURCE,
    },
    "iron_dextran": {
        "dosage_rate_mg_kg": 100.0,
        "concentration_mg_ml": 200.0,
        "route": "Intramuscular (IM) Piglet Day 3",
        "withdrawal_meat_days": 0,
        "verified": False,
        "source": UNVERIFIED_SOURCE,
    },
}

SWINE_STATES: List[str] = ["RESTING", "FEEDING", "FORAGING", "STRESS_VOCALIZATION"]

# TODO(owner): transition probabilities are not fitted to any Kimnovix herd data.
BASE_MARKOV_MATRIX: Dict[str, Dict[str, float]] = {
    "RESTING": {
        "RESTING": 0.60,
        "FEEDING": 0.20,
        "FORAGING": 0.15,
        "STRESS_VOCALIZATION": 0.05,
    },
    "FEEDING": {
        "RESTING": 0.45,
        "FEEDING": 0.35,
        "FORAGING": 0.15,
        "STRESS_VOCALIZATION": 0.05,
    },
    "FORAGING": {
        "RESTING": 0.40,
        "FEEDING": 0.30,
        "FORAGING": 0.25,
        "STRESS_VOCALIZATION": 0.05,
    },
    "STRESS_VOCALIZATION": {
        "RESTING": 0.20,
        "FEEDING": 0.10,
        "FORAGING": 0.20,
        "STRESS_VOCALIZATION": 0.50,
    },
}

MARKOV_SOURCE = UNVERIFIED_SOURCE
THERMAL_STRESS_THRESHOLD_C = 28.0  # TODO(owner): unverified
THERMAL_STRESS_SHIFT = 0.08  # TODO(owner): unverified per-step probability shift
STRESS_ANOMALY_THRESHOLD = 0.15  # TODO(owner): unverified alert threshold

AGRONOMY_SOURCE = UNVERIFIED_SOURCE
# Arithmetic holds only if moisture is VOLUMETRIC % over a 0.30 m root zone:
# 10,000 m2 * 0.30 m * 1% = 30 m3 = 30,000 L. If the probe reports % of field
# capacity (a 65% target suggests it does), this conversion is wrong.
LITERS_PER_PCT_PER_HA = 30000.0  # TODO(owner): confirm probe unit and root depth
COMPOST_TONS_PER_HA = 4.5  # TODO(owner): unverified flat rate, ignores soil test
DEFAULT_TARGET_MOISTURE_PCT = 65.0  # TODO(owner): unverified


def calculate_poultry_dosage(
    drug: str, flock_size: int, avg_bird_weight_kg: float
) -> Dict[str, Any]:
    """Calculate deterministic poultry flock dosage and soluble powder requirement."""
    drug_key = drug.strip().lower()
    if drug_key not in POULTRY_FORMULARY:
        supported = ", ".join(sorted(POULTRY_FORMULARY.keys()))
        raise ValueError(f"Unsupported poultry compound '{drug}'. Supported: {supported}")

    if flock_size <= 0 or flock_size > 100000:
        raise ValueError("Flock size must be between 1 and 100,000 birds.")
    if avg_bird_weight_kg <= 0.02 or avg_bird_weight_kg > 15.0:
        raise ValueError("Average bird weight must be between 0.02 kg and 15.0 kg.")

    spec = POULTRY_FORMULARY[drug_key]
    flock_biomass_kg = round(flock_size * avg_bird_weight_kg, 2)
    dose_per_bird_mg = round(avg_bird_weight_kg * spec["dosage_rate_mg_kg"], 2)
    total_daily_dose_mg = round(flock_biomass_kg * spec["dosage_rate_mg_kg"], 2)
    product_required = round(total_daily_dose_mg / spec["concentration_mg_per_unit"], 2)

    return {
        "drug": drug_key,
        "flock_size": int(flock_size),
        "avg_bird_weight_kg": round(avg_bird_weight_kg, 2),
        "flock_biomass_kg": flock_biomass_kg,
        "dosage_rate_mg_kg": spec["dosage_rate_mg_kg"],
        "dose_per_bird_mg": dose_per_bird_mg,
        "total_daily_dose_mg": total_daily_dose_mg,
        "product_required": product_required,
        "product_unit": spec["product_unit"],
        "product_form": spec["product_form"],
        "route": spec["route"],
        "withdrawal_days": spec["withdrawal_days"],
        "egg_safe": spec["egg_safe"],
        "verified": spec["verified"],
        "source": spec["source"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def calculate_livestock_dosage(
    drug: str, weight_kg: float, species: str = "swine"
) -> Dict[str, Any]:
    """Calculate deterministic injectable dosage for swine/livestock."""
    drug_key = drug.strip().lower()
    if drug_key not in LIVESTOCK_FORMULARY:
        supported = ", ".join(sorted(LIVESTOCK_FORMULARY.keys()))
        raise ValueError(f"Unsupported livestock compound '{drug}'. Supported: {supported}")

    if weight_kg <= 0.5 or weight_kg > 1200.0:
        raise ValueError("Animal weight must be between 0.5 kg and 1,200.0 kg.")

    spec = LIVESTOCK_FORMULARY[drug_key]
    total_dose_mg = round(weight_kg * spec["dosage_rate_mg_kg"], 2)
    volume_ml = round(total_dose_mg / spec["concentration_mg_ml"], 2)

    return {
        "species": species.lower(),
        "drug": drug_key,
        "weight_kg": round(weight_kg, 2),
        "dosage_rate_mg_kg": spec["dosage_rate_mg_kg"],
        "total_dose_mg": total_dose_mg,
        "volume_ml": volume_ml,
        "route": spec["route"],
        "withdrawal_meat_days": spec["withdrawal_meat_days"],
        "verified": spec["verified"],
        "source": spec["source"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def simulate_swine_markov(
    initial_state: str = "RESTING", steps: int = 6, ambient_temp_c: float = 24.0
) -> Dict[str, Any]:
    """Propagate swine behavioral state probabilities across N steps with thermal stress adjustment."""
    state_key = initial_state.strip().upper()
    if state_key not in SWINE_STATES:
        raise ValueError(f"Invalid initial state '{initial_state}'. Valid states: {SWINE_STATES}")
    if steps < 1 or steps > 48:
        raise ValueError("Simulation steps must be between 1 and 48.")

    dist: Dict[str, float] = {s: (1.0 if s == state_key else 0.0) for s in SWINE_STATES}
    thermal_stress = ambient_temp_c > THERMAL_STRESS_THRESHOLD_C

    for _ in range(steps):
        next_dist = {s: 0.0 for s in SWINE_STATES}
        for current_s, prob in dist.items():
            for target_s, trans_p in BASE_MARKOV_MATRIX[current_s].items():
                next_dist[target_s] += prob * trans_p

        if thermal_stress:
            shift = THERMAL_STRESS_SHIFT
            next_dist["STRESS_VOCALIZATION"] = min(1.0, next_dist["STRESS_VOCALIZATION"] + shift)
            next_dist["FEEDING"] = max(0.0, next_dist["FEEDING"] - (shift / 2))
            next_dist["FORAGING"] = max(0.0, next_dist["FORAGING"] - (shift / 2))

        total = sum(next_dist.values())
        dist = {k: round(v / total, 4) for k, v in next_dist.items()}

    anomaly_flag = dist["STRESS_VOCALIZATION"] >= STRESS_ANOMALY_THRESHOLD
    return {
        "initial_state": state_key,
        "steps": steps,
        "ambient_temp_c": round(ambient_temp_c, 1),
        "probabilities": dist,
        "dominant_state": max(dist, key=dist.get),
        "anomaly_detected": anomaly_flag,
        "verified": False,
        "source": MARKOV_SOURCE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def calculate_crop_agronomy(
    crop: str,
    area_ha: float,
    current_moisture_pct: float,
    target_moisture_pct: float = DEFAULT_TARGET_MOISTURE_PCT,
) -> Dict[str, Any]:
    """Calculate deterministic crop irrigation volume and organic compost requirement."""
    if area_ha <= 0 or area_ha > 5000:
        raise ValueError("Area must be greater than 0 and at most 5,000 hectares.")
    if not (0.0 <= current_moisture_pct <= 100.0) or not (0.0 < target_moisture_pct <= 100.0):
        raise ValueError("Moisture percentages must be between 0 and 100.")

    moisture_deficit_pct = max(0.0, round(target_moisture_pct - current_moisture_pct, 2))
    irrigation_liters = round(moisture_deficit_pct * area_ha * LITERS_PER_PCT_PER_HA, 1)
    irrigation_m3 = round(irrigation_liters / 1000.0, 2)
    compost_tons = round(area_ha * COMPOST_TONS_PER_HA, 2)

    return {
        "crop": crop.strip().lower(),
        "area_ha": round(area_ha, 2),
        "current_moisture_pct": round(current_moisture_pct, 2),
        "target_moisture_pct": round(target_moisture_pct, 2),
        "moisture_deficit_pct": moisture_deficit_pct,
        "irrigation_required_liters": irrigation_liters,
        "irrigation_required_m3": irrigation_m3,
        "compost_required_tons": compost_tons,
        "verified": False,
        "source": AGRONOMY_SOURCE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
