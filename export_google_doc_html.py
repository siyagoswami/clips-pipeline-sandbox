from pathlib import Path 

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
CREDENTIALS_PATH = Path("credentials/credentials.json")
TOKEN_PATH = Path("credentials/token.json")
OUTPUT_PATH = Path("input/clips_draft_workspace.html")

DOCUMENT_ID = "1cuoilHnkRcF2sVhuXz3RSnZGvgZeGw0tg5EdVLL1Oyc"

def get_credentials() -> Credentials: 
    # handles Google OAuth login 
    # open a browser and asks you to sign in  
    # reuses credentials/token.json so no need to sign in again 

    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH,
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json())

    return creds

def export_google_doc_as_html() -> None:
    # exports a Google Doc as HTML using the Google Drive API 
    # exported HTML is saved to inputs/clips_draft_workspace.html 

    print(f"DOCUMENT_ID currently is: {repr(DOCUMENT_ID)}")
    print(f"Placeholder is: {'PASTE_YOUR_GOOGLE_DOC_ID_HERE'}")
    print(f"Are they equal? {DOCUMENT_ID == 'PASTE_YOUR_GOOGLE_DOC_ID_HERE'}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    creds = get_credentials()
    print(f"Credentials object: {type(creds)}")
    print(f"Credentials valid? {creds.valid if creds else None}")

    drive_service = build("drive", "v3", credentials=creds)

    request = drive_service.files().export(
        fileId=DOCUMENT_ID,
        mimeType="text/html",
    )

    html_bytes = request.execute()

    OUTPUT_PATH.write_bytes(html_bytes)

    print(f"Exported Google Doc HTML to: {OUTPUT_PATH}")
    print(f"File size: {OUTPUT_PATH.stat().st_size} bytes")

if __name__ == "__main__":
    export_google_doc_as_html()



