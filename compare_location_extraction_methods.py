from pathlib import Path
import csv
import re

import spacy

INPUT_PATH = Path("output/google_doc_clips_sample.csv")
OUTPUT_PATH = Path("output/location_extraction_comparison.csv")
JURISDICTIONS_PATH = Path("input/dim_jurisdictions.csv")

GENERIC_LOCATION_WORDS = {
    "north",
    "south",
    "east",
    "west",
    "central",
    "center",
    "upper",
    "lower",
    "new",
    "old",
    "lake",
    "river",
    "mount",
    "mt",
}

ALLOWED_JURISDICTION_TYPES = {
    "state",
    "county",
    "city",
    "town",
    "township",
    "county_subdivision",
    "county subdivision",
    "place",
}

US_STATE_NAMES = {
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington",
    "west virginia",
    "wisconsin",
    "wyoming",
}

STATE_NAME_TO_ABBR = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}

STATE_NAME_TO_FIPS = {
    "alabama": "01",
    "alaska": "02",
    "arizona": "04",
    "arkansas": "05",
    "california": "06",
    "colorado": "08",
    "connecticut": "09",
    "delaware": "10",
    "florida": "12",
    "georgia": "13",
    "hawaii": "15",
    "idaho": "16",
    "illinois": "17",
    "indiana": "18",
    "iowa": "19",
    "kansas": "20",
    "kentucky": "21",
    "louisiana": "22",
    "maine": "23",
    "maryland": "24",
    "massachusetts": "25",
    "michigan": "26",
    "minnesota": "27",
    "mississippi": "28",
    "missouri": "29",
    "montana": "30",
    "nebraska": "31",
    "nevada": "32",
    "new hampshire": "33",
    "new jersey": "34",
    "new mexico": "35",
    "new york": "36",
    "north carolina": "37",
    "north dakota": "38",
    "ohio": "39",
    "oklahoma": "40",
    "oregon": "41",
    "pennsylvania": "42",
    "rhode island": "44",
    "south carolina": "45",
    "south dakota": "46",
    "tennessee": "47",
    "texas": "48",
    "utah": "49",
    "vermont": "50",
    "virginia": "51",
    "washington": "53",
    "west virginia": "54",
    "wisconsin": "55",
    "wyoming": "56",
}

def clean_text(text: str | None) -> str:
    return " ".join((text or "").split()).strip()

def normalize_text_for_matching(text: str | None) -> str:
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()

def get_state_abbr_from_doc_state(state_name: str | None) -> str: 
    normalized_state_name = normalize_text_for_matching(state_name)

    if not normalized_state_name: 
        return ""
    
    return STATE_NAME_TO_ABBR.get(normalized_state_name, "")

def normalize_state_fips(value: str | int | None) -> str: 
    if value is None: 
        return ""
    
    value = str(value).strip()

    if not value: 
        return ""
    
    if value.endswith(".0"): 
        value = value[:-2]

    if not value.isdigit():
        return ""
    
    return value.zfill(2)

def get_state_fips_from_doc_state(state_name: str | None) -> str:
    normalized_state_name = normalize_text_for_matching(state_name)

    if not normalized_state_name:
        return ""

    return STATE_NAME_TO_FIPS.get(normalized_state_name, "")

def load_jurisdictions() -> list[dict]:
    if not JURISDICTIONS_PATH.exists():
        raise FileNotFoundError(f"Could not find {JURISDICTIONS_PATH}")

    with JURISDICTIONS_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        jurisdictions = list(reader)

    print(f"Loaded {len(jurisdictions)} jurisdictions from {JURISDICTIONS_PATH}")

    return jurisdictions

def is_usable_jurisdiction_name(normalized_name: str | None) -> bool:
    normalized_name = normalize_text_for_matching(normalized_name)
    if not normalized_name: 
        return False 
    
    if normalized_name.isdigit():
        return False 
    
    if len(normalized_name) < 4: 
        return False
    
    if normalized_name in GENERIC_LOCATION_WORDS:
        return False 
    
    return True

def is_allowed_jurisdiction_type(jurisdiction_type: str | None) -> bool:
    jurisdiction_type = normalize_text_for_matching(jurisdiction_type)

    if not jurisdiction_type: 
        return False 
    
    return jurisdiction_type in ALLOWED_JURISDICTION_TYPES

def extract_location_candidates_with_spacy(article_text: str, nlp) -> list[str]:
    # spaCy labels: GPE = countries, cities, and states / LOC = non-GPE locations \ FAC = facilities/buildings
    # extracts potential location entities in the article text  

    doc = nlp(article_text)
    candidates = []

    for ent in doc.ents: 
        if ent.label_ in {"GPE", "LOC", "FAC"}:
            candidate = clean_text(ent.text)

            if candidate:
                candidates.append(candidate)

    deduped = []
    seen = set()

    for candidate in candidates:
        normalized = normalize_text_for_matching(candidate)

        if normalized not in seen:
            deduped.append(candidate)
            seen.add(normalized)    
    
    return deduped 

def get_location_candidate_variants(candidate: str) -> set[str]:
    normalized = normalize_text_for_matching(candidate)

    variants = set()

    if not normalized:
        return variants

    variants.add(normalized)

    suffixes_to_remove = [
        " county",
        " parish",
        " township",
        " town",
        " city",
        " village",
        " borough",
        " municipality",
    ]

    for suffix in suffixes_to_remove:
        if normalized.endswith(suffix):
            stripped = normalized[: -len(suffix)].strip()

            if stripped:
                variants.add(stripped)

    return variants

def infer_candidate_jurisdiction_type(candidate: str) -> str: 
    normalized = normalize_text_for_matching(candidate)

    if normalized in US_STATE_NAMES:
        return "state"

    if normalized.endswith(" county"):
        return "county"

    if normalized.endswith(" township"):
        return "township"

    if normalized.endswith(" parish"):
        return "county"

    if normalized.endswith(" city"):
        return "city"

    if normalized.endswith(" town"):
        return "town"

    if normalized.endswith(" village"):
        return "village"

    if normalized.endswith(" borough"):
        return "borough"

    return ""

def match_spacy_candidates_to_jurisdictions(spacy_candidates: list[str], jurisdictions: list[dict], doc_state_name: str | None,) -> list[dict]:
    matches = []
    seen_jurisdiction_ids = set()
    doc_state_fips = get_state_fips_from_doc_state(doc_state_name)

    candidate_lookup = {}

    for candidate in spacy_candidates: 
        inferred_type = infer_candidate_jurisdiction_type(candidate)

        for variant in get_location_candidate_variants(candidate):
            candidate_lookup[variant] = {
                "original_candidate": candidate, 
                "inferred_type": inferred_type,
                "doc_state_fips": doc_state_fips,
            }

    for jurisdiction in jurisdictions:
        normalized_name = normalize_text_for_matching(
            jurisdiction.get("normalized_name")
        )

        jurisdiction_type = normalize_text_for_matching(
            jurisdiction.get("jurisdiction_type")
        )

        jurisdiction_state_fips = normalize_state_fips(jurisdiction.get("state_fips"))

        if not is_usable_jurisdiction_name(normalized_name):
            continue

        if not is_allowed_jurisdiction_type(jurisdiction_type):
            continue

        if normalized_name not in candidate_lookup:
            continue

        candidate_info = candidate_lookup[normalized_name]
        inferred_type = candidate_info["inferred_type"]

        if inferred_type and jurisdiction_type != inferred_type:
            continue

        if doc_state_fips and jurisdiction_state_fips != doc_state_fips:
            continue

        jurisdiction_id = jurisdiction.get("jurisdiction_id")

        if not jurisdiction_id:
            continue

        if jurisdiction_id in seen_jurisdiction_ids:
            continue

        match = dict(jurisdiction)
        match["spacy_candidate_text"] = candidate_info["original_candidate"]
        match["inferred_candidate_type"] = inferred_type
        match["paired_state_fips"] = doc_state_fips

        matches.append(match)
        seen_jurisdiction_ids.add(jurisdiction_id)

    return matches

def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Could not find {INPUT_PATH}")

    nlp = spacy.load("en_core_web_sm")
    jurisdictions = load_jurisdictions()

    with INPUT_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Loaded {len(rows)} clips from {INPUT_PATH}")

    output_rows = []

    for row in rows:
        text_for_spacy = " ".join(
            [
                row.get("title", ""),
                row.get("snippet", ""),
                row.get("raw_clip_text", ""),
                row.get("state_name", ""),
                row.get("region", ""),
            ]
        )

        text_for_spacy = clean_text(text_for_spacy)

        spacy_candidates = extract_location_candidates_with_spacy(text_for_spacy, nlp)

        if not spacy_candidates:
            spacy_candidates_output = "NO_SPACY_CANDIDATES"
        else:
            spacy_candidates_output = "; ".join(spacy_candidates)

        spacy_jurisdiction_matches = match_spacy_candidates_to_jurisdictions(
            spacy_candidates=spacy_candidates, 
            jurisdictions=jurisdictions,
            doc_state_name=row.get("state_name", ""),
        )

        spacy_mapped_jurisdictions = [
        (
            f"{match.get('jurisdiction_name')} "
            f"({match.get('jurisdiction_type')}, state_fips={match.get('state_fips')}) "
            f"[from: {match.get('spacy_candidate_text')}]"
        )
        for match in spacy_jurisdiction_matches
    ]

        spacy_mapped_jurisdiction_ids = [
            match.get("jurisdiction_id", "")
            for match in spacy_jurisdiction_matches
        ]

        output_rows.append({
            "clip_id": row.get("clip_id", ""),
            "doc_date": row.get("doc_date", ""),
            "title": row.get("title", ""),
            "snippet": row.get("snippet", ""),
            "state_name": row.get("state_name", ""),
            "paired_state_name": row.get("state_name", ""), 
            "paired_state_fips": get_state_fips_from_doc_state(row.get("state_name", "")),
            "region": row.get("region", ""),
            "url": row.get("url", ""),
            "keyword_candidate_names": row.get("matched_jurisdiction_names", ""),
            "keyword_match_count": row.get("match_count", ""),
            "spacy_location_candidates": spacy_candidates_output,
            "spacy_candidate_count": len(spacy_candidates),
            "spacy_status": "found_candidates" if spacy_candidates else "no_candidates",
            "spacy_mapped_jurisdictions": "; ".join(spacy_mapped_jurisdictions),
            "spacy_mapped_jurisdiction_ids": "; ".join(spacy_mapped_jurisdiction_ids),
            "spacy_mapped_count": len(spacy_jurisdiction_matches),
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(output_rows[0].keys()) if output_rows else []

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Wrote comparison output to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()