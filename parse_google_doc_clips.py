from pathlib import Path 
from bs4 import BeautifulSoup 
from urllib.parse import urlparse, parse_qs, unquote 

import csv 
import re 
from datetime import datetime 

HTML_PATH = Path("input/clips_draft_workspace.html")
OUTPUT_PATH = Path("output/google_doc_clips_sample.csv")

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
        metadta = ""
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

def debug_bold_detection(block, body: str) -> None:
    print("\nDEBUG: No colon found and snippet is coming back None")
    print("BODY PREVIEW:")
    print(body[:500])

    print("\nHTML pieces inside this block:")
    for i, tag in enumerate(block.find_all(["b", "strong", "span"])[:20]):
        text = clean_text(tag.get_text(" "))
        style = tag.get("style", "")

        if text:
            print("----")
            print(f"TAG {i}: <{tag.name}>")
            print(f"TEXT: {text[:200]}")
            print(f"STYLE: {style}")

def get_initial_bold_title(block) -> str | None:

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

def main () -> None: 
    # reads Google Doc HTML, walks through HTML blocks in order, tracks the current date/region/state, finds full clips, extracts fields, writes output to CSV

    if not HTML_PATH.exists(): 
        raise FileNotFoundError(f"Could not find {HTML_PATH}")
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    html = HTML_PATH.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    blocks = soup.find_all(["p", "h1", "h2", "h3", "li", "td", "span", "div"])
    
    rows = []
    current_region = None 
    current_state = None 
    current_doc_date = None 

    for block in blocks: 
        text = clean_text(block.get_text(" "))

        if not text: 
            continue 

        upper = text.upper().strip()
        # date_match = re.search(r"Daily Template\s+(\d{1,2}/\d{1,2})", text, flags=re.IGNORECASE)

        # if date_match: 
        #     current_doc_date = date_match.group(1)
        #     continue 

        doc_date_header = extract_doc_date_header(text)
        if doc_date_header:
            current_doc_date = doc_date_header

        if upper in REGIONS: 
            current_region = upper.title()
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

        rows.append({
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
            "created_at": datetime.utcnow().isoformat(),
        })
    
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