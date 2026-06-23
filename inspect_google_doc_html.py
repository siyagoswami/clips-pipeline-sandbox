from pathlib import Path
from bs4 import BeautifulSoup

print("Script started")

HTML_PATH = Path("input/clips_draft_workspace.html")

print(f"Looking for file at: {HTML_PATH.resolve()}")
print(f"File exists? {HTML_PATH.exists()}")

if not HTML_PATH.exists():
    raise FileNotFoundError(
        f"Could not find {HTML_PATH}. Make sure your exported Google Doc HTML "
        "is saved as input/clips_draft_workspace.html"
    )

html = HTML_PATH.read_text(encoding="utf-8", errors="replace")

print(f"HTML file length: {len(html)} characters")
print("First 300 characters of file:")
print(html[:300])

soup = BeautifulSoup(html, "lxml")

blocks = soup.find_all(["p", "h1", "h2", "h3", "li", "td", "span", "div"])

print(f"Found {len(blocks)} possible text blocks.")

for i, block in enumerate(blocks[:100]):
    text = " ".join(block.get_text(" ").split())
    links = [a.get("href") for a in block.find_all("a", href=True)]

    if not text and not links:
        continue

    print("----")
    print(f"BLOCK {i}")
    print(text[:800])

    if links:
        print("LINKS:")
        for link in links:
            print(f"  - {link}")