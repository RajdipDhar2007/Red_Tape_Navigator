"""Canonical field catalogue shared by the interview engine and the form templates.

Form template field maps reference these keys (`source` in the JSON). Questions are available in en/bn/hi.
"""
from dataclasses import dataclass, field
from typing import Callable

from app.interview import validators as v


@dataclass(frozen=True)
class FieldDef:
    key: str
    group: str
    validate: Callable[[str], str]
    q: dict[str, str]  # question text per language
    label: dict[str, str]
    sensitive: bool = False
    options: tuple[str, ...] = field(default_factory=tuple)


def _f(key, group, validate, en, bn, hi, label_en, label_bn, label_hi, sensitive=False, options=()):
    return FieldDef(key, group, validate, {"en": en, "bn": bn, "hi": hi}, {"en": label_en, "bn": label_bn, "hi": label_hi}, sensitive, tuple(options))


# Order = interview order within the priority groups: identity -> contact -> business -> premises -> finance.
_DEFS = [
    _f("applicant_name", "identity", v.name, "What is your full name (as on your ID)?", "আপনার পূর্ণ নাম কী (পরিচয়পত্র অনুযায়ী)?", "आपका पूरा नाम क्या है (पहचान पत्र के अनुसार)?", "Applicant name", "আবেদনকারীর নাম", "आवेदक का नाम"),
    _f("father_name", "identity", v.name, "What is your father's or spouse's name?", "আপনার বাবা বা স্বামী/স্ত্রীর নাম কী?", "आपके पिता या जीवनसाथी का नाम क्या है?", "Father/spouse name", "বাবা/স্বামী-স্ত্রীর নাম", "पिता/जीवनसाथी का नाम"),
    _f("dob", "identity", v.dob, "What is your date of birth (DD/MM/YYYY)?", "আপনার জন্ম তারিখ কী (DD/MM/YYYY)?", "आपकी जन्म तिथि क्या है (DD/MM/YYYY)?", "Date of birth", "জন্ম তারিখ", "जन्म तिथि"),
    _f("gender", "identity", v.choice(["male", "female", "other"]), "What is your gender (male / female / other)?", "আপনার লিঙ্গ কী (male / female / other)?", "आपका लिंग क्या है (male / female / other)?", "Gender", "লিঙ্গ", "लिंग", options=("male", "female", "other")),
    _f("social_category", "identity", v.choice(["general", "sc", "st", "obc"]), "Social category (general / sc / st / obc)?", "সামাজিক শ্রেণি (general / sc / st / obc)?", "सामाजिक श्रेणी (general / sc / st / obc)?", "Social category", "সামাজিক শ্রেণি", "सामाजिक श्रेणी", options=("general", "sc", "st", "obc")),
    _f("aadhaar", "identity", v.aadhaar, "What is your 12-digit Aadhaar number? (stored encrypted)", "আপনার ১২ অঙ্কের আধার নম্বর কী? (এনক্রিপ্ট করে রাখা হবে)", "आपका 12 अंकों का आधार नंबर क्या है? (एन्क्रिप्टेड रखा जाएगा)", "Aadhaar number", "আধার নম্বর", "आधार नंबर", sensitive=True),
    _f("pan", "identity", v.pan, "What is your PAN? (stored encrypted)", "আপনার প্যান কী? (এনক্রিপ্ট করে রাখা হবে)", "आपका पैन क्या है? (एन्क्रिप्टेड रखा जाएगा)", "PAN", "প্যান", "पैन", sensitive=True),
    _f("mobile", "contact", v.mobile, "What is your 10-digit mobile number?", "আপনার ১০ অঙ্কের মোবাইল নম্বর কী?", "आपका 10 अंकों का मोबाइल नंबर क्या है?", "Mobile", "মোবাইল", "मोबाइल"),
    _f("email", "contact", v.email, "What is your email address?", "আপনার ইমেল ঠিকানা কী?", "आपका ईमेल पता क्या है?", "Email", "ইমেল", "ईमेल"),
    _f("residence_address", "contact", v.text, "What is your residential address (house, street, locality)?", "আপনার বাসস্থানের ঠিকানা কী (বাড়ি, রাস্তা, এলাকা)?", "आपका निवास पता क्या है (मकान, गली, इलाका)?", "Residential address", "বাসস্থানের ঠিকানা", "निवास का पता"),
    _f("residence_pincode", "contact", v.pincode, "What is your residence PIN code?", "আপনার বাসস্থানের পিন কোড কী?", "आपके निवास का पिन कोड क्या है?", "Residence PIN", "বাসস্থানের পিন", "निवास पिन"),
    _f("business_name", "business", v.text, "What name will your business use?", "আপনার ব্যবসার নাম কী হবে?", "आपके व्यवसाय का नाम क्या होगा?", "Business name", "ব্যবসার নাম", "व्यवसाय का नाम"),
    _f("organisation_type", "business", v.choice(["proprietorship", "partnership", "llp", "company"]), "Type of organisation (proprietorship / partnership / llp / company)?", "সংস্থার ধরন (proprietorship / partnership / llp / company)?", "संगठन का प्रकार (proprietorship / partnership / llp / company)?", "Organisation type", "সংস্থার ধরন", "संगठन का प्रकार", options=("proprietorship", "partnership", "llp", "company")),
    _f("date_of_commencement", "business", v.any_date, "When will the business start (DD/MM/YYYY)?", "ব্যবসা কবে শুরু হবে (DD/MM/YYYY)?", "व्यवसाय कब शुरू होगा (DD/MM/YYYY)?", "Date of commencement", "শুরুর তারিখ", "शुरुआत की तारीख"),
    _f("food_products", "business", v.text, "Which food products will you make or sell?", "আপনি কোন খাবার তৈরি বা বিক্রি করবেন?", "आप कौन से खाद्य उत्पाद बनाएंगे या बेचेंगे?", "Food products", "খাদ্য পণ্য", "खाद्य उत्पाद"),
    _f("num_employees", "business", v.positive_int, "How many people will work in the business (including you)?", "ব্যবসায় (আপনাসহ) কতজন কাজ করবেন?", "व्यवसाय में (आपके साथ) कितने लोग काम करेंगे?", "Number of employees", "কর্মীর সংখ্যা", "कर्मचारियों की संख्या"),
    _f("annual_turnover", "business", v.positive_int, "Expected yearly turnover in rupees?", "প্রত্যাশিত বার্ষিক টার্নওভার কত টাকা?", "अपेक्षित वार्षिक टर्नओवर कितने रुपये?", "Expected annual turnover (INR)", "প্রত্যাশিত বার্ষিক টার্নওভার (টাকা)", "अपेक्षित वार्षिक टर्नओवर (रु.)"),
    _f("investment_amount", "business", v.positive_int, "How much will you invest in machinery/equipment (rupees)?", "যন্ত্রপাতিতে কত টাকা বিনিয়োগ করবেন?", "मशीनरी/उपकरण में कितने रुपये निवेश करेंगे?", "Investment in equipment (INR)", "যন্ত্রপাতিতে বিনিয়োগ (টাকা)", "उपकरण में निवेश (रु.)"),
    _f("premises_address", "premises", v.text, "What is the address of the shop/premises (house, street, locality)?", "দোকান/প্রাঙ্গণের ঠিকানা কী (বাড়ি, রাস্তা, এলাকা)?", "दुकान/परिसर का पता क्या है (मकान, गली, इलाका)?", "Premises address", "প্রাঙ্গণের ঠিকানা", "परिसर का पता"),
    _f("premises_pincode", "premises", v.pincode, "PIN code of the premises?", "প্রাঙ্গণের পিন কোড?", "परिसर का पिन कोड?", "Premises PIN", "প্রাঙ্গণের পিন", "परिसर पिन"),
    _f("premises_ownership", "premises", v.choice(["owned", "rented"]), "Is the premises owned or rented (owned / rented)?", "প্রাঙ্গণ কি নিজের না ভাড়া (owned / rented)?", "परिसर अपना है या किराये का (owned / rented)?", "Premises ownership", "প্রাঙ্গণের মালিকানা", "परिसर का स्वामित्व", options=("owned", "rented")),
    _f("premises_area_sqft", "premises", v.positive_int, "Approximate area of the premises in square feet?", "প্রাঙ্গণের আনুমানিক ক্ষেত্রফল (বর্গফুট)?", "परिसर का अनुमानित क्षेत्रफल (वर्ग फुट)?", "Premises area (sq ft)", "প্রাঙ্গণের ক্ষেত্রফল (বর্গফুট)", "परिसर क्षेत्रफल (वर्ग फुट)"),
    _f("bank_account_number", "finance", v.account_number, "What is your business bank account number?", "আপনার ব্যবসার ব্যাংক অ্যাকাউন্ট নম্বর কী?", "आपका व्यावसायिक बैंक खाता नंबर क्या है?", "Bank account number", "ব্যাংক অ্যাকাউন্ট নম্বর", "बैंक खाता संख्या", sensitive=True),
    _f("bank_ifsc", "finance", v.ifsc, "What is the bank's IFSC code?", "ব্যাংকের IFSC কোড কী?", "बैंक का IFSC कोड क्या है?", "Bank IFSC", "ব্যাংক IFSC", "बैंक IFSC"),
]

FIELDS: dict[str, FieldDef] = {f.key: f for f in _DEFS}
ORDER = {f.key: i for i, f in enumerate(_DEFS)}
# Keys filled from the parsed goal; never asked.
DERIVED = {"city", "state", "business_type"}
SENSITIVE_KEYS = {k for k, f in FIELDS.items() if f.sensitive}
