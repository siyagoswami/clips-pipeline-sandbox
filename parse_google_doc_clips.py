from pathlib import Path 
from bs4 import BeautifulSoup 
from urllib.parse import urlparse, urlunparse, parse_qs, unquote, parse_qsl, urlencode

import csv 
import re 
from datetime import datetime 
import hashlib

HTML_PATH = Path("input/clips_draft_workspace.html")
OUTPUT_PATH = Path("output/google_doc_clips_sample.csv")
JURISDICTIONS_PATH = Path("input/dim_jurisdictions.csv")

REGIONS = {
    "NORTHEAST", 
    "NORTH-CENTRAL", 
    "CENTRAL-CENTRAL", 
    "SOUTH-CENTRAL",
    "PLAINS", 
    "PACIFIC NORTHWEST", 
    "NORTHERN ROCKIES",
    "MID-ATLANTIC", 
    "SOUTHEAST", 
    "MIDWEST", 
    "CO/NM/NV",
    "AZ/UT", 
    "OH/PA"
    "CALIFORNIA"
}

STATE_NAMES = {
    "ALABAMA", "ALASKA", "ARIZONA", "ARKANSAS", "CALIFORNIA", "COLORADO",
    "CONNECTICUT", "DELAWARE", "FLORIDA", "GEORGIA", "IDAHO", "ILLINOIS",
    "INDIANA", "IOWA", "KANSAS", "KENTUCKY", "LOUISIANA", "MAINE",
    "MARYLAND", "MASSACHUSETTS", "MICHIGAN", "MINNESOTA", "MISSISSIPPI",
    "MISSOURI", "MONTANA", "NEBRASKA", "NEVADA", "NEW HAMPSHIRE",
    "NEW JERSEY", "NEW MEXICO", "NEW YORK", "NORTH CAROLINA",
    "NORTH DAKOTA", "OHIO", "OKLAHOMA", "OREGON", "PENNSYLVANIA",
    "RHODE ISLAND", "SOUTH CAROLINA", "SOUTH DAKOTA", "TENNESSEE",
    "TEXAS", "UTAH", "VERMONT", "VIRGINIA", "WASHINGTON",
    "WEST VIRGINIA", "WISCONSIN", "WYOMING",
}

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
    "place",
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

def normalize_url_for_id(url: str | None) -> str | None: 
    # normalizes URL so the same article receives same clip_id each time parser runs 
    # same normalized URL in results in same hashed clip_id result 

    if not url: 
        return None 
    
    url = url.strip()
    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    tracking_prefixes = (
        "utm", 
    )

    tracking_params = {
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
    }

    cleaned_query_params = []

    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        key_lower = key.lower()

        if key_lower.startswith(tracking_prefixes):
            continue

        if key_lower in tracking_params:
            continue

        cleaned_query_params.append((key, value))

    cleaned_query = urlencode(cleaned_query_params)

    normalized = urlunparse(
        (
            scheme,
            netloc,
            path,
            "",
            cleaned_query,
            "",
        )
    )

    return normalized

def generate_clip_id(url: str | None, title: str | None, publisher: str | None, published_date: str | None, ) -> str: 
        # clip_id using url
        # fallback is title + publisher + published date 

        normalized_url = normalize_url_for_id(url)
        if normalized_url: 
            id_source = normalized_url 
        else: 
            id_source = "|".join(
                [
                    clean_text(title or "").lower(),
                    clean_text(publisher or "").lower(),
                    clean_text(published_date or "").lower(),
                ]
            )

        hashed = hashlib.sha256(id_source.encode("utf-8")).hexdigest()[:12]

        return f"clip_{hashed}"

def clean_text(text: str) -> str: 
    return " ".join((text or "").split()).strip()

def clean_google_redirect_url(url: str | None) -> str | None: 
    if not url: 
        return None 
    
    parsed = urlparse(url)

    if parsed.netloc == "www.google.com" and parsed.path == "/url": 
        query_params = parse_qs(parsed.query)
        real_url = query_params.get("q", [None])[0]

        return unquote(real_url) if real_url else url 

    return url 

def is_probable_full_clip(text: str, links: list[str]) -> bool: 
    # full clip appears to have: one hyperlink, colon separating title from summary, final bracket metadata

    if not links: 
        return False 

    if len(text) < 80: 
        return False
    
    has_link_metadata = re.search(
        r"\[[^\]]*link\s+to\s+article[^\]]*\]",
        text,
        flags=re.IGNORECASE,
    )

    has_link_to_article_text = "link to article" in text.lower()

    if not has_link_metadata and not has_link_to_article_text:
        return False
    
    return True 

def extract_metadata(text: str) -> tuple[str | None, str | None, str]: 
    # example input: [PV Tech, 6/12/2026, link to article]
    # output: publisher = PV Tech, published_date = "6/12/2026", body = title, summary text 

    metadata = ""
    body = text.strip()

    bracket_match = re.search(
        r"\[([^\]]*link\s+to\s+article[^\]]*)\]",
        text,
        flags=re.IGNORECASE,
    )

    if bracket_match: 
        metadata = bracket_match.group(1)
        body = text[:bracket_match.start()].strip()
    else: 
        metadata = ""
        body = text.strip()

    date_pattern = re.compile(
        r"("
        r"\d{1,2}/\d{1,2}/\d{2,4}"
        r"|"
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2},?\s+\d{4}"
        r"|"
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{4}"
        r")",
        flags=re.IGNORECASE,
    )

    date_match = date_pattern.search(metadata)
    published_date = date_match.group(1) if date_match else None
    publisher = None 

    if metadata: 
        if date_match: 
            publisher = metadata[:date_match.start()].strip(" ,")
        else: 
            publisher_candidate = re.split(
                r"link\s+to\s+article",
                metadata,
                flags=re.IGNORECASE,
            )[0]
            publisher = publisher_candidate.strip(" ,") or None

    return publisher, published_date, body 

def get_state_abbr_from_doc_state(state_name: str | None) -> str: 
    normalized_state_name = normalize_text_for_matching(state_name)

    if not normalized_state_name: 
        return ""
    
    return STATE_NAME_TO_ABBR.get(normalized_state_name, "")

def get_initial_bold_title(block) -> str | None:
    # title is bolded in most clips - extracting title based on this criteria 

    bold_pieces = []

    for tag in block.find_all(["b", "strong", "span"]):
        text = clean_text(tag.get_text(" "))
        if not text:
            continue

        style = tag.get("style", "").lower().replace(" ", "")

        is_bold_tag = tag.name in ["b", "strong"]
        is_bold_span = (
            "font-weight:700" in style
            or "font-weight:bold" in style
            or "font-weight:600" in style
        )

        if is_bold_tag or is_bold_span:
            bold_pieces.append(text)

    if not bold_pieces:
        return None

    deduped = []
    for piece in bold_pieces:
        if piece not in deduped:
            deduped.append(piece)

    bold_text = clean_text(" ".join(deduped))

    return bold_text or None
    
def parse_title_and_snippet(body: str, block=None) -> tuple[str | None, str | None]:
    # based on if a colon exists or not - if not, the first quotation is found to signal the start of a clip

    if ":" in body:
        title, snippet = body.split(":", 1)
        return clean_text(title), clean_text(snippet)
    
    quote_positions = []
    for quote_char in ['"', '“']:
        position = body.find(quote_char)
    
        if position != -1: 
            quote_positions.append(position)
        
        if quote_positions:
            first_quote_position = min(quote_positions)

            title = body[:first_quote_position].strip()
            snippet = body[first_quote_position:].strip()

            return clean_text(title), clean_text(snippet)

    return clean_text(body), None

def extract_doc_date_header(text: str) -> str | None: 
    cleaned = clean_text(text)

    if len(cleaned) > 80: 
        return None 
    
    if not cleaned.lower().startswith("daily"):
        return None 
    
    match = re.search(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", cleaned)

    if match: 
        return match.group(0)
    
    return None

def build_searchable_location_text(title: str | None, snippet: str | None, raw_clip_text: str | None, state_name: str | None, region: str | None,) -> str: 
    # builds one combined text field for location matching 
    # takes multiple clip fields, removes blanks, joins everything into one searchable string

    parts = [
        title, 
        snippet, 
        raw_clip_text, 
        state_name, 
        region,
    ]

    cleaned_parts = []
    for part in parts: 
        cleaned = clean_text(part or "")

        if cleaned: 
            cleaned_parts.append(cleaned)
    
    return " ".join(cleaned_parts)

def normalize_text_for_matching(text: str | None) -> str: 
    # lowercase and remove whitespace

    if not text: 
        return ""

    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    text = re.sub(r"\s+", " ", text)
    return text.strip()

def load_jurisdictions() -> list[dict]:
    if not JURISDICTIONS_PATH.exists():
        raise FileNotFoundError(f"Could not find {JURISDICTIONS_PATH}")

    jurisdictions = []

    with JURISDICTIONS_PATH.open("r", encoding="utf-8") as f: 
        reader = csv.DictReader(f)

        for row in reader: 
            jurisdictions.append(row)
        
        print(f"Loaded {len(jurisdictions)} jurisdictions")

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

def find_exact_jurisdiction_matches(normalized_searchable_location_text: str, jurisdictions: list[dict]) -> list[dict]: 
    # finds jurisdictions whose normalized_name appears exactly in the clip text 
    
    matches = []
    searchable_text = f" {normalized_searchable_location_text} "

    for jurisdiction in jurisdictions: 
        normalized_name = normalize_text_for_matching(
            jurisdiction.get("normalized_name")
        )

        jurisdiction_type = jurisdiction.get("jurisdiction_type")

        if not is_usable_jurisdiction_name(normalized_name): 
            continue 

        if not is_allowed_jurisdiction_type(jurisdiction_type):
            continue

        search_name = f" {normalized_name} "
        if search_name in searchable_text: 
            matches.append(jurisdiction)
        

    return matches 

def dedupe_matches_by_jurisdiction_id(matches: list[dict]) -> list[dict]:
    deduped = []
    seen_ids = set()

    for match in matches: 
        jurisdiction_id = match.get("jurisdiction_id")

        if not jurisdiction_id: 
            continue 

        if jurisdiction_id in seen_ids: 
            continue 

        deduped.append(match)
        seen_ids.add(jurisdiction_id)

    return deduped 

def main () -> None: 
    # reads Google Doc HTML, walks through HTML blocks in order, tracks the current date/region/state, finds full clips, extracts fields, writes output to CSV

    if not HTML_PATH.exists(): 
        raise FileNotFoundError(f"Could not find {HTML_PATH}")
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    html = HTML_PATH.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    blocks = soup.find_all(["p", "h1", "h2", "h3", "li", "td", "span", "div"])
    
    rows = []
    jurisdictions = load_jurisdictions()
    started_running_daily_clips = False
    current_region = None 
    current_state = None 
    current_doc_date = None 

    for block in blocks: 
        text = clean_text(block.get_text(" "))

        if not text: 
            continue 

        if not started_running_daily_clips:
            if "running daily clips" in text.lower():
                started_running_daily_clips = True 
                print("Found Running Daily Clips - starting parser from here: ")
            continue 

        upper = text.upper().strip()

        doc_date_header = extract_doc_date_header(text)
        if doc_date_header:
            current_doc_date = doc_date_header

        if upper in REGIONS: 
            current_region = upper.title()
            current_state = None 
            print(f"Found region: {current_region}")
            continue 

        if upper in STATE_NAMES: 
            current_state = upper.title()
            continue 

        links = [a.get("href") for a in block.find_all("a", href=True)]

        if not is_probable_full_clip(text, links):
            continue

        publisher, published_date, body = extract_metadata(text)
        title, snippet = parse_title_and_snippet(body, block)
        url = clean_google_redirect_url(links[0]) if links else None 

        source_record_id = f"google_doc_{len(rows) + 1}"
        clip_id = generate_clip_id(url=url, title=title, publisher=publisher, published_date=published_date)
        
        searchable_location_text = build_searchable_location_text(title=title, snippet=snippet, raw_clip_text=text, state_name=current_state, region=current_region)
        normalized_searchable_location_text = normalize_text_for_matching(searchable_location_text)
        jurisdiction_matches = find_exact_jurisdiction_matches(normalized_searchable_location_text=normalized_searchable_location_text, jurisdictions=jurisdictions)
        jurisdiction_matches = dedupe_matches_by_jurisdiction_id(jurisdiction_matches)

        matched_jurisdiction_names = [
            f"{match.get('jurisdiction_name')} ({match.get('jurisdiction_type')}, {match.get('state_abbr')})"
            for match in jurisdiction_matches
            ]

        matched_jurisdiction_ids = [
            match.get("jurisdiction_id")
            for match in jurisdiction_matches
        ]

        rows.append({
            "clip_id": clip_id,
            "source_system": "clips_draft_workspace",
            "source_record_id": source_record_id, 
            "doc_date": current_doc_date, 
            "region": current_region, 
            "state_name": current_state, 
            "title": title, 
            "snippet": snippet, 
            "publisher": publisher, 
            "published_date": published_date, 
            "url": url, 
            "raw_clip_text": text, 
            "searchable_location_text": searchable_location_text,
            "normalized_searchable_location_text": normalized_searchable_location_text,
            "matched_jurisdiction_names": "; ".join(matched_jurisdiction_names),
            "matched_jurisdiction_ids": "; ".join(matched_jurisdiction_ids), 
            "match_count": len(jurisdiction_matches),
            "created_at": datetime.utcnow().isoformat(),
        })
    
    if not started_running_daily_clips: 
        print("WARNING: Did not find 'Running Daily Clips' section in the document.")

    print(f"Parsed {len(rows)} clips")
    if rows: 
        fieldnames = list(rows[0].keys())
    
        with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f: 
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"Wrote parsed clips to {OUTPUT_PATH}")
        print()

        print("First parsed row:")
        for key, value in rows[0].items(): 
            print(f"{key}: {value}")

if __name__ == "__main__": 
    main()