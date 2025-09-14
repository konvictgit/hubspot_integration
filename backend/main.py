# backend/main.py
import os
from fastapi import FastAPI, Form, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from integrations.airtable import authorize_airtable, oauth2callback_airtable, get_airtable_credentials, get_items_airtable
from integrations.notion import authorize_notion, oauth2callback_notion, get_notion_credentials, get_items_notion
from integrations.hubspot import authorize_hubspot, oauth2callback_hubspot, get_hubspot_credentials, get_items_hubspot

app = FastAPI()

# Allow frontend on port 3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AccessTokenPayload(BaseModel):
    access_token: str


# Airtable Routes 
@app.post("/integrations/airtable/authorize")
async def airtable_authorize(user_id: str = Form(...), org_id: str = Form(...)):
    return await authorize_airtable(user_id, org_id)

@app.get("/integrations/airtable/oauth2callback")
async def airtable_callback(request: Request):
    return await oauth2callback_airtable(request)

@app.post("/integrations/airtable/credentials")
async def airtable_credentials(user_id: str = Form(...), org_id: str = Form(...)):
    return await get_airtable_credentials(user_id, org_id)

@app.post("/integrations/airtable/load")
async def airtable_load(credentials: UploadFile = Form(...)):
    creds = credentials.file.read()
    return await get_items_airtable(creds)


# Notion Routes
@app.post("/integrations/notion/authorize")
async def notion_authorize(user_id: str = Form(...), org_id: str = Form(...)):
    return await authorize_notion(user_id, org_id)

@app.get("/integrations/notion/oauth2callback")
async def notion_callback(request: Request):
    return await oauth2callback_notion(request)

@app.post("/integrations/notion/credentials")
async def notion_credentials(user_id: str = Form(...), org_id: str = Form(...)):
    return await get_notion_credentials(user_id, org_id)

@app.post("/integrations/notion/load")
async def notion_load(credentials: UploadFile = Form(...)):
    creds = credentials.file.read()
    return await get_items_notion(creds)

# HubSpot Routes
@app.post("/integrations/hubspot/authorize")
async def hubspot_authorize(user_id: str = Form(...), org_id: str = Form(...)):
    return await authorize_hubspot(user_id, org_id)

@app.get("/integrations/hubspot/oauth2callback")
async def hubspot_callback(request: Request):
    return await oauth2callback_hubspot(request)

@app.post("/integrations/hubspot/credentials")
async def hubspot_credentials(user_id: str = Form(...), org_id: str = Form(...)):
    return await get_hubspot_credentials(user_id, org_id)

# This endpoint now expects a JSON body 
@app.post("/integrations/hubspot/get_hubspot_items")
async def hubspot_load(payload: AccessTokenPayload):
    creds = {"access_token": payload.access_token}
    return await get_items_hubspot(creds)
