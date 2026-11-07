"""G. Submission checklist and renewal info. The citizen performs every submission step themselves."""
from app.kb.catalog import LICENCES

# Indicative renewal periods in months (None = no periodic renewal). Verify with the authority.
RENEWAL_MONTHS = {"fssai": 12, "trade_licence": 12, "fire_noc": 12, "shops_est": 12, "pollution_consent": 12}


def submission_checklist(plan: dict, form_ids_ready: set[str]) -> list[dict]:
    items = []
    for step in plan.get("steps", []):
        lic = LICENCES[step["licence"]]
        claims = step.get("claims", {})
        cite = claims.get
        actions = []
        if step["depends_on"]:
            names = ", ".join(LICENCES[d]["name"] for d in step["depends_on"])
            actions.append(f"Complete first: {names}")
        actions.append("Gather the documents listed below (originals + clear scans)")
        if step["form"] and step["form"] in form_ids_ready:
            actions.append("Download your filled form PDF, check every field, and sign it yourself")
        else:
            actions.append("This step has no pre-filled form here: complete the application on the official portal")
        if step["portal_login_required"]:
            actions.append("Log in to the official portal yourself (OTP/captcha are completed by you; this tool never bypasses them)")
        actions.append("Pay the fee on the official portal and keep the receipt")
        actions.append("Submit the application yourself and note the application/reference number")
        items.append({
            "order": step["order"], "licence": step["licence"], "name": step["name"],
            "portal_url": (cite("form_link") or {}).get("source_url"),
            "authority": ((cite("authority") or {}).get("data") or {}).get("value"),
            "fee": (cite("fee") or {}).get("text"), "timeline": (cite("timeline") or {}).get("text"),
            "documents": ((cite("documents") or {}).get("data") or {}).get("value", lic["documents"]),
            "actions": actions, "conditional": step["conditional"],
            "renewal_months": RENEWAL_MONTHS.get(step["licence"]),
            "citations": [{"key": c["key"], "source_url": c["source_url"], "fetched_at": c["fetched_at"], "confidence": c["confidence"], "needs_verification": c["needs_verification"]} for c in claims.values()],
            "municipal_data_missing": step.get("municipal_data_missing", False),
        })
    return items
