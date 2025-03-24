from fastapi import FastAPI, Request, Response
from app import config

# controllers
from .controller import locationController

app = FastAPI(docs_url="/docs", redoc_url="/re-docs", title="Hackathon API")

@app.get("/", tags=['Information'])
async def root():
   return {"message": "Service is running...", "result": True}
    
   
controllers = [locationController]
 
for controller in controllers:
   app.include_router(controller.router)