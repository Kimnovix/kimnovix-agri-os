import re
from typing import Tuple

MAX_QUERY_LENGTH = 1000

RED_TEAM_PATTERNS = [
    r"(?i)\b(ignore\s+previous\s+instructions|system\s+prompt|jailbreak|bypass\s+guardrails)\b",
    r"(?i)\b(lethal\s+dose|euthanasia\s+home\s+mix|poison\s+livestock|cyanide|strychnine)\b",
    r"(?i)\b(illegal\s+growth\s+promoter|clenbuterol\s+feed|chloramphenicol\s+food\s+animal)\b",
    r"(?i)(\bDROP\s+TABLE\b|\bUNION\s+SELECT\b|--\s*$)",
]

KVB_DISCLAIMER_EN = (
    "\n\n---\n"
    "⚖️ **KVB Statutory Notice:** This calculation is a deterministic decision-support output "
    "under the Veterinary Surgeons and Veterinary Para-professionals Act (Cap 366). "
    "Final prescription, administration, and withdrawal verification must be authorized "
    "by a registered Kenya Veterinary Board (KVB) professional."
)

KVB_DISCLAIMER_SW = (
    "\n\n---\n"
    "⚖️ **Ilani ya Kisheria ya KVB:** Huu niadirio wa kimfumo chini ya Sheria ya Madaktari "
    "na Wataalamu wa Mifugo (Cap 366). Uthibitisho wa mwisho wa kipimo na muda wa kusubiri "
    "lazima uidhinishwe na mtaalamu aliyesajiliwa na Bodi ya Mifugo Kenya (KVB)."
)


def validate_query(query: str) -> Tuple[bool, str]:
    """Validate user input against DoS caps and red-team security patterns."""
    if not query or not query.strip():
        return False, "Query cannot be empty."

    cleaned = query.strip()
    if len(cleaned) > MAX_QUERY_LENGTH:
        return (
            False,
            f"Payload rejected: Query length ({len(cleaned)}) exceeds DoS cap of {MAX_QUERY_LENGTH} characters.",
        )

    for pattern in RED_TEAM_PATTERNS:
        if re.search(pattern, cleaned):
            return (
                False,
                "Security Guardrail Triggered: Request violates clinical safety or system integrity policy.",
            )

    return True, cleaned


def append_kvb_disclaimer(message: str, lang: str = "en") -> str:
    """Append the statutory KVB notice in English or Kiswahili."""
    if lang.lower().startswith("sw"):
        return f"{message}{KVB_DISCLAIMER_SW}"
    return f"{message}{KVB_DISCLAIMER_EN}"
