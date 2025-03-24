from dotenv import load_dotenv
import os

from starlette.exceptions import HTTPException

path = os.path.join(os.getcwd(), '.env')
if os.path.exists(path):
    load_dotenv(dotenv_path=path, override=True)


APP_TITLE = os.getenv("APP_TITLE", "Hackathon API")
TOKEN_URL = os.getenv("TOKEN_URL", "")
BASE_URL = os.getenv("BASE_URL", "")
REVIEW_URL = os.getenv("REVIEW_URL", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
CLIENT_ID = os.getenv("CLIENT_ID", "")

if not TOKEN_URL:
    raise HTTPException(status_code=400, detail="Token URL missing")

if not BASE_URL:
    raise HTTPException(status_code=400, detail="BASE URL missing")

if not CLIENT_SECRET:
    raise HTTPException(status_code=400, detail="CLIENT_SECRET missing")

if not CLIENT_ID:
    raise HTTPException(status_code=400, detail="CLIENT ID missing")



