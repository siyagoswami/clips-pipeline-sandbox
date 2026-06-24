from pathlib import Path 
from email import policy 
from email.parser import BytesParser 
from bs4 import BeautifulSoup 
from urllib.parse import urlparse, parse_qs, unquote
import re 

EMAIL_FOLDER = Path("input/meltwater_digests")

def get_nearby_text_for_url(soup, actual_url: str) -> str | None:
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")

        decoded_href = unquote(href)
        if actual_url in decoded_href:
            current = link 
        
            for _ in range(10): 
                if current is None: 
                    break 
                
                text = clean_text(current.get_text(" "))

                if len(text) > 100:
                    return text 
                
                current = current.parent
        
        return None

def clean_text(text: str) -> str: 
    return " ".join((text or "").split()).strip()

def extract_html_from_eml(email_path: Path) -> str | None: 
    with email_path.open("rb") as f: 
        message = BytesParser(policy=policy.default).parse(f)

        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()

                if content_type == "text/html":
                    return part.get_content()
        
        else:
            if message.get_content_type() == "text/html": 
                return part.get_content()
            
        return None 

def extract_article_urls_from_raw_html(html: str) -> list[str]:
    urls = []

    decoded_html = unquote(html)
    matches = re.findall(
        r"url=(https?://[^&\"'\s<>]+)",
        decoded_html,
        flags=re.IGNORECASE,
    )

    for match in matches: 
        cleaned = unquote(match).strip()

        if is_useful_article_url(cleaned): 
            urls.append(cleaned)
    
    deduped_urls = []
    seen = set()

    for url in urls: 
        if url not in seen: 
            deduped_urls.append(url)
            seen.add(url)
    
    return deduped_urls

def is_useful_article_url(actual_url: str | None) -> bool: 
    if not actual_url: 
        return False 
    
    lowered = actual_url.lower().strip()

    if not lowered.startswith("http"): 
        return False
    
    blocked_domains_or_paths = [
        "meltwater.com",
        "similarweb.com",
        "mailto:",
        "facebook.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "instagram.com",
        "unsubscribe",
        "privacy",
        "terms",
    ]

    for item in blocked_domains_or_paths: 
        if item in lowered:
            return False
        
    image_extensions = [
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"
    ]

    for extension in image_extensions: 
        if extension in lowered:
            return False
    
    parsed = urlparse(lowered)
    path = parsed.path.strip("/")
    if path == "": 
        return False

    generic_paths = {
        "home",
        "news",
        "articles",
        "article",
        "category",
        "topics",
    }

    if path in generic_paths: 
        return False
    
    return True

def main() -> None: 
    email_files = list(EMAIL_FOLDER.glob("*.eml"))
    print(f"Found {len(email_files)} .eml files")

    for email_path in email_files:
        print("----")
        print(f"Reading: {email_path}")

        html = extract_html_from_eml(email_path)

        if not html: 
            print("No HTML body found in this email.")
            continue 

        print(f"HTML length: {len(html)} characters")
        soup = BeautifulSoup(html, "lxml")

        text = clean_text(soup.get_text(" "))
        print("TEXT PREVIEW:")
        print(text[:3000])

        # article_urls = extract_article_urls_from_raw_html(html)

        # print(f"Found {len(article_urls)} actual article URLs from raw HTML")

        # print("First 20 probable article/source links: ")
        # for url in article_urls[:5]:
        #     nearby_text = get_nearby_text_for_url(soup, url)
        #     print("----")
        #     print("URL: ")
        #     print(url)

        #     print("NEARBY TEXT: ")
        #     print(nearby_text[:1000] if nearby_text else "No nearby text found")

if __name__ == "__main__": 
    main()