"""Input validators. Each returns the normalised value or raises ValueError(code). Codes are localised in the API."""
import re
from datetime import date, datetime

_PAN = re.compile(r"^[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]$")  # 4th char = holder type
_IFSC = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_MOBILE = re.compile(r"^[6-9]\d{9}$")

# Verhoeff tables for Aadhaar checksum
_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def verhoeff_ok(num: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(num)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def text(v: str) -> str:
    v = re.sub(r"\s+", " ", v).strip()
    if not v or len(v) > 200 or re.search(r"[<>{}]", v):
        raise ValueError("invalid_text")
    return v


def name(v: str) -> str:
    v = text(v)
    if re.search(r"\d", v) or len(v) < 2:
        raise ValueError("invalid_name")
    return v


def pincode(v: str) -> str:
    v = re.sub(r"\s", "", v)
    if not re.fullmatch(r"[1-9]\d{5}", v):
        raise ValueError("invalid_pincode")
    return v


def pan(v: str) -> str:
    v = v.strip().upper().replace(" ", "")
    if not _PAN.match(v):
        raise ValueError("invalid_pan")
    return v


def aadhaar(v: str) -> str:
    v = re.sub(r"[\s-]", "", v)
    if not re.fullmatch(r"[2-9]\d{11}", v) or not verhoeff_ok(v):
        raise ValueError("invalid_aadhaar")
    return v


def mobile(v: str) -> str:
    v = re.sub(r"[\s-]", "", v)
    v = re.sub(r"^(\+91|91|0)", "", v) if len(v) > 10 else v
    if not _MOBILE.match(v):
        raise ValueError("invalid_mobile")
    return v


def email(v: str) -> str:
    v = v.strip().lower()
    if not _EMAIL.match(v) or len(v) > 254:
        raise ValueError("invalid_email")
    return v


def ifsc(v: str) -> str:
    v = v.strip().upper()
    if not _IFSC.match(v):
        raise ValueError("invalid_ifsc")
    return v


def account_number(v: str) -> str:
    v = re.sub(r"\s", "", v)
    if not re.fullmatch(r"\d{9,18}", v):
        raise ValueError("invalid_account")
    return v


def _parse_date(v: str) -> date:
    v = v.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    raise ValueError("invalid_date")


def dob(v: str) -> str:
    d = _parse_date(v)
    today = date.today()
    if d > today:
        raise ValueError("future_date")
    age = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
    if age < 18 or age > 110:
        raise ValueError("invalid_age")
    return d.isoformat()


def any_date(v: str) -> str:
    return _parse_date(v).isoformat()


def positive_int(v: str) -> str:
    v = re.sub(r"[,\s]", "", v)
    if not re.fullmatch(r"\d{1,12}", v):
        raise ValueError("invalid_number")
    return str(int(v))


def choice(options: list[str]):
    def _c(v: str) -> str:
        v = v.strip().lower()
        if v not in options:
            raise ValueError("invalid_choice")
        return v

    return _c


def yes_no(v: str) -> str:
    v = v.strip().lower()
    if v in ("yes", "y", "haan", "ha", "হ্যাঁ", "हां", "हाँ", "true"):
        return "yes"
    if v in ("no", "n", "nahi", "na", "না", "नहीं", "false"):
        return "no"
    raise ValueError("invalid_choice")


MESSAGES = {
    "en": {
        "invalid_text": "Please enter plain text (max 200 characters).",
        "invalid_name": "Please enter a valid name without digits.",
        "invalid_pincode": "PIN code must be 6 digits and cannot start with 0.",
        "invalid_pan": "PAN must look like ABCDE1234F.",
        "invalid_aadhaar": "Aadhaar must be a valid 12-digit number.",
        "invalid_mobile": "Mobile number must be 10 digits starting with 6-9.",
        "invalid_email": "Please enter a valid email address.",
        "invalid_ifsc": "IFSC must look like SBIN0001234.",
        "invalid_account": "Account number must be 9-18 digits.",
        "invalid_date": "Please enter a date as DD/MM/YYYY.",
        "future_date": "The date cannot be in the future.",
        "invalid_age": "Applicant must be between 18 and 110 years old.",
        "invalid_number": "Please enter a whole number.",
        "invalid_choice": "Please choose one of the listed options.",
    },
    "bn": {
        "invalid_text": "অনুগ্রহ করে সাধারণ লেখা দিন (সর্বোচ্চ ২০০ অক্ষর)।",
        "invalid_name": "অঙ্ক ছাড়া সঠিক নাম দিন।",
        "invalid_pincode": "পিন কোড ৬ অঙ্কের হতে হবে, ০ দিয়ে শুরু নয়।",
        "invalid_pan": "প্যান ABCDE1234F এর মতো হতে হবে।",
        "invalid_aadhaar": "আধার একটি সঠিক ১২ অঙ্কের নম্বর হতে হবে।",
        "invalid_mobile": "মোবাইল নম্বর ৬-৯ দিয়ে শুরু হওয়া ১০ অঙ্কের হতে হবে।",
        "invalid_email": "সঠিক ইমেল ঠিকানা দিন।",
        "invalid_ifsc": "IFSC SBIN0001234 এর মতো হতে হবে।",
        "invalid_account": "অ্যাকাউন্ট নম্বর ৯-১৮ অঙ্কের হতে হবে।",
        "invalid_date": "তারিখ DD/MM/YYYY ফরম্যাটে দিন।",
        "future_date": "তারিখ ভবিষ্যতের হতে পারে না।",
        "invalid_age": "আবেদনকারীর বয়স ১৮ থেকে ১১০ বছরের মধ্যে হতে হবে।",
        "invalid_number": "একটি পূর্ণ সংখ্যা দিন।",
        "invalid_choice": "তালিকা থেকে একটি বিকল্প বেছে নিন।",
    },
    "hi": {
        "invalid_text": "कृपया सामान्य पाठ दर्ज करें (अधिकतम 200 अक्षर)।",
        "invalid_name": "कृपया अंकों के बिना सही नाम दर्ज करें।",
        "invalid_pincode": "पिन कोड 6 अंकों का होना चाहिए और 0 से शुरू नहीं हो सकता।",
        "invalid_pan": "पैन ABCDE1234F जैसा होना चाहिए।",
        "invalid_aadhaar": "आधार एक मान्य 12 अंकों का नंबर होना चाहिए।",
        "invalid_mobile": "मोबाइल नंबर 6-9 से शुरू होने वाला 10 अंकों का होना चाहिए।",
        "invalid_email": "कृपया सही ईमेल पता दर्ज करें।",
        "invalid_ifsc": "IFSC SBIN0001234 जैसा होना चाहिए।",
        "invalid_account": "खाता संख्या 9-18 अंकों की होनी चाहिए।",
        "invalid_date": "कृपया तारीख DD/MM/YYYY रूप में दर्ज करें।",
        "future_date": "तारीख भविष्य की नहीं हो सकती।",
        "invalid_age": "आवेदक की आयु 18 से 110 वर्ष के बीच होनी चाहिए।",
        "invalid_number": "कृपया पूर्ण संख्या दर्ज करें।",
        "invalid_choice": "कृपया सूची में से एक विकल्प चुनें।",
    },
}
