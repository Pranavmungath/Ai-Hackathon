import os

import uvicorn

APP_PORT = os.getenv("APP_PORT_ANALYZER", "8084")

def run_server():
    uvicorn.run("app.main:app", host="localhost", port=int(APP_PORT), reload=True, reload_dirs=['app'])

if __name__ == "__main__":
    run_server()
