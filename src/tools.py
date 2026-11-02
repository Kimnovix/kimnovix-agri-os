from datetime import datetime, timezone
from typing import Any, Dict, List

POULTRY_FORMULARY: Dict[str, Dict[str, Any]] = {
    "amoxicillin": {
        "dosage_rate_mg_kg": 15.0,
        "concentration_mg_g": 500.0,  # 50% w/w soluble powder (500 mg active per gram)
        "route": "Drinking Water (Soluble Powder 50% w/w)",
        "withdrawal_days": 5,
        "egg_safe": False,
    },
    "oxytetracycline": {
        "dosage_rate_mg_kg": 20.0,
        "concentration_mg_g": 200.0,  # 20% w/w soluble powder
        "route": "Drinking Water (Soluble Powder 20% w/w)",
        "withdrawal_days": 7,
        "egg_safe": True,
    },
    "tylosin": {
        "dosage_rate_mg_kg": 25.0,
        "concentration_mg_g": 1000.0,  # 100% tartrate soluble powder
        "route": "Drinking Water (Soluble Powder)",
        "withdrawal_days": 3,
        "egg_safe": True,
    },
    "enrofloxacin": {
        "dosage_rate_mg_kg": 10.0,
        "concentration_mg_g": 100.0,  # 10% oral solution (100 mg/mL equivalent)
        "route": "Drinking Water (10% Oral Solution)",
        "withdrawal_days": 8,
        "egg_safe": False,
    },
}

LIVESTOCK_FORMULARY: Dict[str, Dict[str, Any]] = {
    "oxytetracycline_la": {
        "dosage_rate_mg_kg": 20.0,
        "concentration_mg_ml": 200.0,
        "route": "Deep Intramuscular (IM)",
        "withdrawal_meat_days": 28,
    },
    "ivermectin": {
        "dosage_rate_mg_kg": 0.3,
        "concentration_mg_ml": 10.0,
        "route": "Subcutaneous (SC) Neck",
        "withdrawal_meat_days": 28,
    },
    "iron_dextran": {
        "dosage_rate_mg_kg": 100.0,
        "concentration_mg_ml": 200.0,
        "route": "Intramuscular (IM) Piglet Day 3",
        "withdrawal_meat_days": 0,
    },
}

SWINE_STATES: List[str] = ["RESTING", "FEEDING", "FORAGING", "STRESS_VOCALIZATION"]

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
    powder_required_g = round(total_daily_dose_mg / spec["concentration_mg_g"], 2)

    return {
        "drug": drug_key,
        "flock_size": int(flock_size),
        "avg_bird_weight_kg": round(avg_bird_weight_kg, 2),
        "flock_biomass_kg": flock_biomass_kg,
        "dosage_rate_mg_kg": spec["dosage_rate_mg_kg"],
        "dose_per_bird_mg": dose_per_bird_mg,
        "total_daily_dose_mg": total_daily_dose_mg,
        "powder_required_g": powder_required_g,
        "route": spec["route"],
        "withdrawal_days": spec["withdrawal_days"],
        "egg_safe": spec["egg_safe"],
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
    thermal_stress = ambient_temp_c > 28.0

    for _ in range(steps):
        next_dist = {s: 0.0 for s in SWINE_STATES}
        for current_s, prob in dist.items():
            for target_s, trans_p in BASE_MARKOV_MATRIX[current_s].items():
                next_dist[target_s] += prob * trans_p

        if thermal_stress:
            shift = 0.08
            next_dist["STRESS_VOCALIZATION"] = min(1.0, next_dist["STRESS_VOCALIZATION"] + shift)
            next_dist["FEEDING"] = max(0.0, next_dist["FEEDING"] - (shift / 2))
            next_dist["FORAGING"] = max(0.0, next_dist["FORAGING"] - (shift / 2))

        total = sum(next_dist.values())
        dist = {k: round(v / total, 4) for k, v in next_dist.items()}

    anomaly_flag = dist["STRESS_VOCALIZATION"] >= 0.15
    return {
        "initial_state": state_key,
        "steps": steps,
        "ambient_temp_c": round(ambient_temp_c, 1),
        "probabilities": dist,
        "dominant_state": max(dist, key=dist.get),
        "anomaly_detected": anomaly_flag,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def calculate_crop_agronomy(
    crop: str,
    area_ha: float,
    current_moisture_pct: float,
    target_moisture_pct: float = 65.0,
) -> Dict[str, Any]:
    """Calculate deterministic crop irrigation volume and organic compost requirement."""
    if area_ha <= 0 or area_ha > 5000:
        raise ValueError("Area must be between 0.01 and 5,000 hectares.")
    if not (0.0 <= current_moisture_pct <= 100.0) or not (0.0 < target_moisture_pct <= 100.0):
        raise ValueError("Moisture percentages must be between 0 and 100.")

    moisture_deficit_pct = max(0.0, round(target_moisture_pct - current_moisture_pct, 2))
    # 1% root-zone moisture deficit across 1 ha (~30cm active root depth) ≈ 30,000 liters
    irrigation_liters = round(moisture_deficit_pct * area_ha * 30000.0, 1)
    irrigation_m3 = round(irrigation_liters / 1000.0, 2)
    compost_tons = round(area_ha * 4.5, 2)

    return {
        "crop": crop.strip().lower(),
        "area_ha": round(area_ha, 2),
        "current_moisture_pct": round(current_moisture_pct, 2),
        "target_moisture_pct": round(target_moisture_pct, 2),
        "moisture_deficit_pct": moisture_deficit_pct,
        "irrigation_required_liters": irrigation_liters,
        "irrigation_required_m3": irrigation_m3,
        "compost_required_tons": compost_tons,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
