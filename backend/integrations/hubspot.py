# backend/integrations/hubspot.py
import os
import json
import secrets
import base64
import asyncio
from urllib.parse import quote_plus

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
from dotenv import load_dotenv

from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

# Load env vars from backend/.env
load_dotenv()

CLIENT_ID = os.getenv("HUBSPOT_CLIENT_ID")
CLIENT_SECRET = os.getenv("HUBSPOT_CLIENT_SECRET")
REDIRECT_URI = os.getenv(
    "HUBSPOT_REDIRECT_URI",
    "http://localhost:8000/integrations/hubspot/oauth2callback"
)

# Scopes must match your HubSpot app settings
scope = "crm.objects.contacts.read crm.objects.contacts.write crm.schemas.contacts.read crm.schemas.contacts.write"
# Build authorization URL (encode redirect & scope)
authorization_url = (
    f"https://app.hubspot.com/oauth/authorize"
    f"?client_id={CLIENT_ID}"
    f"&redirect_uri={quote_plus(REDIRECT_URI)}"
    f"&scope={quote_plus(scope)}"
    f"&response_type=code"
)

# -------------------------
# Step 1: start OAuth -> return URL with state
# -------------------------
async def authorize_hubspot(user_id, org_id):
    """
    Generate a random state_id, save that to redis (CSRF protection), return the HubSpot
    authorize URL with a base64-encoded payload that includes the state + user/org.
    """
    state_id = secrets.token_urlsafe(32)
    state_data = {"state": state_id, "user_id": user_id, "org_id": org_id}
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode("utf-8")).decode("utf-8")

    # Save only the random state_id for validation
    await add_key_value_redis(f"hubspot_state:{org_id}:{user_id}", state_id, expire=600)

    print(f"[DEBUG] Saved state_id={state_id} for {user_id}/{org_id}")
    return f"{authorization_url}&state={encoded_state}"


# -------------------------
# Step 2: callback -> exchange code for tokens
# -------------------------
async def oauth2callback_hubspot(request: Request):
    """
    HubSpot redirects here. We decode the state, validate it against redis, then exchange
    the code for tokens and save them in redis for the frontend to fetch.
    """
    if request.query_params.get("error"):
        raise HTTPException(status_code=400, detail=request.query_params.get("error_description") or "OAuth error")

    code = request.query_params.get("code")
    encoded_state = request.query_params.get("state")
    if not code or not encoded_state:
        raise HTTPException(status_code=400, detail="Missing code or state.")

    # Decode the base64 state payload
    try:
        state_data = json.loads(base64.urlsafe_b64decode(encoded_state).decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid state.")

    state_id = state_data.get("state")
    user_id = state_data.get("user_id")
    org_id = state_data.get("org_id")

    # Read saved state from redis and normalize types
    saved_state = await get_value_redis(f"hubspot_state:{org_id}:{user_id}")
    if isinstance(saved_state, bytes):
        saved_state = saved_state.decode("utf-8")

    print(f"[DEBUG] Callback received state_id={state_id}")
    print(f"[DEBUG] Redis saved_state={saved_state}")

    if not saved_state or state_id != saved_state:
        # Keep it explicit so you can inspect logs during debugging
        raise HTTPException(status_code=400, detail="State does not match.")

    # Exchange code for tokens
    token_url = "https://api.hubapi.com/oauth/v1/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=data, headers=headers)
        if resp.status_code >= 400:
            # clear state so you don't get stuck
            await delete_key_redis(f"hubspot_state:{org_id}:{user_id}")
            raise HTTPException(status_code=400, detail=f"Failed to obtain token: {resp.text}")
        token_response = resp.json()

    # Save credentials temporarily for frontend to pick up and delete state
    await asyncio.gather(
        add_key_value_redis(f"hubspot_credentials:{org_id}:{user_id}", json.dumps(token_response), expire=600),
        delete_key_redis(f"hubspot_state:{org_id}:{user_id}")
    )

    # Close the popup window
    return HTMLResponse(content="<html><script>window.close();</script></html>")


# -------------------------
# Step 3: frontend polls to get credentials
# -------------------------
async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f"hubspot_credentials:{org_id}:{user_id}")
    if not credentials:
        raise HTTPException(status_code=400, detail="No credentials found.")
    if isinstance(credentials, bytes):
        credentials = credentials.decode("utf-8")
    credentials = json.loads(credentials)
    await delete_key_redis(f"hubspot_credentials:{org_id}:{user_id}")
    return credentials


# -------------------------
# Step 4: use tokens to fetch items
# -------------------------
async def get_items_hubspot(credentials):
    """
    Accepts either a dict {'access_token': '...'} or a JSON string.
    Returns a list of IntegrationItem dicts.
    """
    if isinstance(credentials, str):
        try:
            credentials = json.loads(credentials)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid credentials JSON.")

    access_token = credentials.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token provided.")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    url = "https://api.hubapi.com/crm/v3/objects/contacts"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers, params={"limit": 100})
        if resp.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"Failed to fetch HubSpot contacts: {resp.text}")
        data = resp.json()

    items = []
    for result in data.get("results", []):
        item_id = result.get("id")
        props = result.get("properties", {}) or {}
        first = props.get("firstname", "") or ""
        last = props.get("lastname", "") or ""
        email = props.get("email", "")
        display_name = (first + " " + last).strip() or email or item_id
        created_at = result.get("createdAt") or props.get("createdate") or None
        updated_at = result.get("updatedAt") or None

        # IMPORTANT: the project's IntegrationItem does NOT accept 'integration' or 'raw'
        # fields; construct the item using the accepted kwargs (see integrations/integration_item.py).
        item = IntegrationItem(
            id=item_id,
            type="contact",
            name=display_name,
            creation_time=created_at,
            last_modified_time=updated_at,
            parent_id=None,
        )
        items.append(item.__dict__)

    return items
