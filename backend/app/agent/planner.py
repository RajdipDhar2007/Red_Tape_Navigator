"""C. Requirement checklist: ordered plan in dependency order with forms and documents."""
from graphlib import TopologicalSorter

from app.kb.catalog import ACTIVITIES, CITIES, LICENCES, NATIONAL_FALLBACK, REQUIRED_OVERRIDES


def licences_for(activity: str) -> list[str]:
    wanted = set(ACTIVITIES[activity]["licences"])
    # include transitive dependencies that are in the wanted set only (deps outside are soft)
    graph = {lid: [d for d in LICENCES[lid]["depends_on"] if d in wanted] for lid in wanted}
    TopologicalSorter(graph).prepare()  # raises CycleError on a cyclic catalogue
    rank = {lid: i for i, lid in enumerate(LICENCES)}
    return _stable_topo(graph, rank)


def _stable_topo(graph: dict[str, list[str]], rank: dict[str, int]) -> list[str]:
    done: list[str] = []
    remaining = set(graph)
    while remaining:
        ready = sorted((n for n in remaining if all(d in done for d in graph[n])), key=lambda n: rank[n])
        done.append(ready[0])
        remaining.discard(ready[0])
    return done


def city_scope(city_label: str | None) -> str | None:
    for key, c in CITIES.items():
        if city_label and c["label"].lower() == city_label.lower():
            return key
    return None


def scope_for(lid: str, city_label: str | None) -> str | None:
    """Claim scope for a licence: 'national' or a city key; None when we have no municipal data."""
    if lid in REQUIRED_OVERRIDES or LICENCES[lid].get("by_city"):
        return city_scope(city_label) or ("national" if lid in NATIONAL_FALLBACK else None)
    return "national"


def build_plan(parsed: dict, claims_by_key: dict[str, dict]) -> dict:
    activity = parsed.get("activity")
    if activity not in ACTIVITIES:
        return {"steps": [], "activity": activity, "note": "Activity not recognised; escalate to a CSC operator."}
    steps = []
    for n, lid in enumerate(licences_for(activity), start=1):
        lic = LICENCES[lid]
        scope = scope_for(lid, parsed.get("city"))
        prefix = f"{lid}:{scope}:" if scope else None
        cites = {a: claims_by_key.get(f"{prefix}{a}") for a in ("requirement", "authority", "fee", "timeline", "documents", "form_link")} if prefix else {}
        steps.append({
            "order": n,
            "licence": lid,
            "name": lic["name"],
            "form": lic["form"],
            "depends_on": [d for d in lic["depends_on"] if d in ACTIVITIES[activity]["licences"]],
            "conditional": lid == "gst",
            "claims": {k: v for k, v in cites.items() if v},
            "municipal_data_missing": scope is None,
            "portal_login_required": lic["portal_login"],
        })
    return {"activity": activity, "steps": steps}
