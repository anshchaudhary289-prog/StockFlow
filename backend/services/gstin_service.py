import re

# All Indian state codes mapped to state names
STATE_CODES = {
    "01": "Jammu & Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "25": "Daman & Diu",
    "26": "Dadra & Nagar Haveli",
    "27": "Maharashtra",
    "28": "Andhra Pradesh",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman & Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh (New)",
}

# Keywords to detect state from address string
STATE_KEYWORDS = {
    "delhi": "07",
    "new delhi": "07",
    "uttar pradesh": "09",
    "up": "09",
    "maharashtra": "27",
    "mumbai": "27",
    "gujarat": "24",
    "rajasthan": "08",
    "haryana": "06",
    "punjab": "03",
    "karnataka": "29",
    "bangalore": "29",
    "bengaluru": "29",
    "tamil nadu": "33",
    "chennai": "33",
    "west bengal": "19",
    "kolkata": "19",
    "uttarakhand": "05",
    "dehradun": "05",
    "roorkee": "05",
    "telangana": "36",
    "hyderabad": "36",
    "kerala": "32",
    "bihar": "10",
    "madhya pradesh": "23",
    "mp": "23",
    "odisha": "21",
    "jharkhand": "20",
    "assam": "18",
    "goa": "30",
    "himachal pradesh": "02",
    "hp": "02",
}


def validate_gstin_format(gstin: str) -> dict:
    """
    Check if GSTIN matches the official format:
    2 digits (state) + 5 letters (PAN) + 4 digits + 1 letter + 1 alphanumeric + Z + 1 alphanumeric
    Example: 07ABCDE1234F1Z5
    """
    if not gstin:
        return {
            "valid": False,
            "error": "GSTIN is empty",
            "risk": "CRITICAL"
        }

    gstin = gstin.strip().upper()

    # Official GSTIN regex pattern
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'

    if not re.match(pattern, gstin):
        return {
            "valid": False,
            "gstin": gstin,
            "error": f"GSTIN format invalid. Expected format: 07ABCDE1234F1Z5, got: {gstin}",
            "risk": "CRITICAL"
        }

    # Extract state code from first 2 digits
    state_code = gstin[:2]
    if state_code not in STATE_CODES:
        return {
            "valid": False,
            "gstin": gstin,
            "error": f"State code '{state_code}' does not exist in India",
            "risk": "CRITICAL"
        }

    return {
        "valid": True,
        "gstin": gstin,
        "state_code": state_code,
        "state_name": STATE_CODES[state_code],
        "risk": "NONE"
    }


_GSTIN_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _gstin_check_char(first14: str) -> str:
    """
    Compute the expected 15th (checksum) character of a GSTIN using the
    Luhn Mod-36 algorithm: multiply the first 14 characters (values 0-35)
    by alternating factors 1, 2; add quotient + remainder (base 36) of each
    product; the check character brings the total to a multiple of 36.
    """
    total = 0
    factor = 1
    for ch in first14:
        digit = factor * _GSTIN_ALPHABET.index(ch)
        total += digit // 36 + digit % 36
        factor = 2 if factor == 1 else 1
    return _GSTIN_ALPHABET[(36 - total % 36) % 36]


def validate_gstin_checksum(gstin: str) -> dict:
    """
    Verify the GSTIN checksum character (15th character).
    Catches single-character misreads (e.g. by OCR) that still pass the
    format regex, as well as invented GSTINs whose last character was
    never computed.
    """
    if not gstin or len(gstin.strip()) != 15:
        return {
            "valid": False,
            "error": "GSTIN missing or wrong length for checksum check",
            "risk": "HIGH"
        }

    g = gstin.strip().upper()
    expected = _gstin_check_char(g[:14])
    if expected != g[14]:
        return {
            "valid": False,
            "gstin": g,
            "error": f"GSTIN checksum mismatch — expected last character '{expected}', got '{g[14]}' (possible misread or invalid GSTIN)",
            "risk": "HIGH"
        }

    return {"valid": True, "gstin": g, "risk": "NONE"}


def validate_state_match(gstin: str, vendor_address: str) -> dict:
    """
    Check if the state in GSTIN matches the state mentioned in vendor address.
    Example:
      GSTIN starts with 07 → Delhi
      But address says 'Mumbai, Maharashtra' → MISMATCH 🚩
    """
    if not gstin or not vendor_address:
        return {
            "match": False,
            "error": "GSTIN or address missing",
            "risk": "MEDIUM"
        }

    gstin_state_code = gstin[:2].strip()
    gstin_state_name = STATE_CODES.get(gstin_state_code, "Unknown")

    # Try to detect state from address text
    address_lower = vendor_address.lower()
    detected_state_code = None

    for keyword, code in STATE_KEYWORDS.items():
        if keyword in address_lower:
            detected_state_code = code
            break

    if detected_state_code is None:
        # Could not detect state from address — flag as medium risk
        return {
            "match": None,
            "gstin_state": gstin_state_name,
            "address_state": "Could not detect",
            "warning": "State could not be detected from address. Manual review recommended.",
            "risk": "MEDIUM"
        }

    if gstin_state_code != detected_state_code:
        address_state_name = STATE_CODES.get(detected_state_code, "Unknown")
        return {
            "match": False,
            "gstin_state": gstin_state_name,
            "address_state": address_state_name,
            "error": f"State mismatch — GSTIN says '{gstin_state_name}' but address says '{address_state_name}'",
            "risk": "HIGH"
        }

    return {
        "match": True,
        "gstin_state": gstin_state_name,
        "address_state": gstin_state_name,
        "risk": "NONE"
    }


def calculate_risk_score(format_result: dict, state_result: dict, checksum_result: dict = None) -> dict:
    """
    Calculate overall risk score based on all validation checks.
    """
    score = 0
    flags = []

    risk_weights = {
        "CRITICAL": 40,
        "HIGH": 25,
        "MEDIUM": 10,
        "LOW": 5,
        "NONE": 0
    }

    # Format check
    format_risk = format_result.get("risk", "NONE")
    score += risk_weights.get(format_risk, 0)
    if format_risk != "NONE":
        flags.append(format_result.get("error", "Format issue"))

    # State match check
    state_risk = state_result.get("risk", "NONE")
    score += risk_weights.get(state_risk, 0)
    if state_risk != "NONE":
        flags.append(state_result.get("error") or state_result.get("warning", "State issue"))

    # Checksum check (only supplied when the format itself is valid)
    if checksum_result is not None:
        checksum_risk = checksum_result.get("risk", "NONE")
        score += risk_weights.get(checksum_risk, 0)
        if checksum_risk != "NONE":
            flags.append(checksum_result.get("error", "Checksum issue"))

    # Determine overall risk level
    if score >= 61:
        level = "CRITICAL"
    elif score >= 31:
        level = "HIGH"
    elif score >= 11:
        level = "MEDIUM"
    elif score >= 1:
        level = "LOW"
    else:
        level = "NONE"

    # A structurally invalid GSTIN is a hard failure: block it outright,
    # regardless of the numeric total. (Earlier the score for a lone
    # format failure was 40, which never reached the >= 61 BLOCK
    # threshold, so "blocked" could never actually happen.)
    if format_risk == "CRITICAL":
        level = "CRITICAL"

    return {
        "score": score,
        "level": level,
        "flags": flags,
        "action": "BLOCK" if level == "CRITICAL" else
                  "MANUAL_REVIEW" if level in ["HIGH", "MEDIUM"] else
                  "AUTO_APPROVE"
    }


def run_gstin_checks(gstin: str, vendor_address: str) -> dict:
    """
    Master function — run all GSTIN checks and return full report.
    Call this from your router.
    """
    format_result = validate_gstin_format(gstin)

    # If format itself is invalid, skip state and checksum checks
    if not format_result["valid"]:
        state_result = {"risk": "NONE", "match": None}
        checksum_result = {"risk": "NONE", "valid": None}
    else:
        state_result = validate_state_match(gstin, vendor_address)
        checksum_result = validate_gstin_checksum(gstin)

    risk = calculate_risk_score(format_result, state_result, checksum_result)

    return {
        "gstin": gstin,
        "format_check": format_result,
        "state_check": state_result,
        "checksum_check": checksum_result,
        "risk_assessment": risk
    }
