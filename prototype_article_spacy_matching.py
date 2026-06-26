from pathlib import Path 
import csv 
import re 

import requests 
from bs4 import BeautifulSoup 
import spacy 

JURISDICTIONS_PATH = Path("input/mock_dim_jurisdictions.csv")
ARTICLE_URLS = [
    "https://www.masslive.com/westfieldnews/2026/06/residents-pack-council-chambers-as-westfield-halts-new-data-centers.html",
    "https://www.wnem.com/2026/06/16/jupiter-power-receives-approval-build-battery-storage-facility-saginaw-county/",
]

def clean_text(text: str | None) -> str:
    return " ".join((text or "").split()).strip()

def normalize_text_for_matching(text: str | None) -> str:
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()

def load_jurisdictions() -> list[dict]:
    jurisdictions = []

    with JURISDICTIONS_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            jurisdictions.append(row)

    print(f"Loaded {len(jurisdictions)} jurisdictions")

    return jurisdictions

def fetch_article_text(url: str) -> str: 
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    for tag in soup(["script", "style", "noscript"]): 
        tag.decompose()
    
    text = clean_text(soup.get_text(" "))
    return text 

def extract_location_candidates_with_spacy(article_text: str, nlp) -> list[str]:
    # spaCy labels: GPE = countries, cities, and states / LOC = non-GPE locations \ FAC = facilities/buildings
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

def match_candidates_to_jurisdictions(candidates: list[str], jurisdictions: list[dict],) -> list[dict]:
    matches = []
    normalized_candidates = {
        normalize_text_for_matching(candidate): candidate
        for candidate in candidates
    }

    for jurisdiction in jurisdictions: 
        jurisdiction_normalized_name = normalize_text_for_matching(jurisdiction.get("normalized_name"))

        if not jurisdiction_normalized_name: 
            continue 

        if jurisdiction_normalized_name in normalized_candidates:
            matches.append({
                "candidate_text": normalized_candidates[jurisdiction_normalized_name],
                "jurisdiction_id": jurisdiction.get("jurisdiction_id"),
                "jurisdiction_name": jurisdiction.get("jurisdiction_name"),
                "jurisdiction_type": jurisdiction.get("jurisdiction_type"),
                "census_geoid": jurisdiction.get("census_geoid"),
                "state_fips": jurisdiction.get("state_fips"),
                "state_abbr": jurisdiction.get("state_abbr"),
                "county_name": jurisdiction.get("county_name"),
                "county_geoid": jurisdiction.get("county_geoid"),
        })
            
    return matches 

def main() -> None: 
    nlp = spacy.load("en_core_web_sm")
    jurisdictions = load_jurisdictions()

    for url in ARTICLE_URLS: 
        if "PASTE_ARTICLE_URL" in url: 
            print("Please replace ARTICLE_URLS with real article URLs first.")
            return
    
        print("-------")
        print(f"URL: {url}")
        
        try:
            article_text = fetch_article_text(url)
        except Exception as e:
            print(f"Could not fetch article: {e}")
            continue

        print(f"Fetched article text length: {len(article_text)} characters")
        print("Article text preview:")
        print(article_text[:1000])

        candidates = extract_location_candidates_with_spacy(article_text, nlp)
        print()
        print("spaCy location candidates:")
        for candidate in candidates[:30]:
            print(f"- {candidate}")

        matches = match_candidates_to_jurisdictions(
            candidates=candidates,
            jurisdictions=jurisdictions,
        )

        print()
        print("Jurisdiction matches:")
        if not matches:
            print("No exact jurisdiction matches found.")
        else:
            for match in matches:
                print(
                    f"- {match['jurisdiction_name']} "
                    f"({match['jurisdiction_type']}, {match['state_abbr']}) "
                    f"→ {match['jurisdiction_id']} / {match['census_geoid']}"
                )

if __name__ == "__main__":
    main()