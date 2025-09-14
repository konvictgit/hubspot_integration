hubspot_integration

This project demonstrates a simple integration layer with third-party SaaS platforms (HubSpot, Airtable, Notion) using FastAPI (backend) and React + Material-UI (frontend).
The focus is on implementing and testing the HubSpot OAuth 2.0 flow end-to-end.

🚀 Features

OAuth 2.0 integration with HubSpot (fully implemented & tested).

Airtable & Notion scaffolding provided (credentials redacted).

Backend:

/authorize → Generate OAuth URL and state.

/oauth2callback → Handle HubSpot OAuth callback.

/credentials → Retrieve tokens from Redis.

/get_hubspot_items → Fetch HubSpot contacts using access_token.

Frontend:

Dropdown to choose integration.

OAuth popup flow for HubSpot.

“Load Data” button to fetch contacts and display normalized results.

Redis used for state & credential storage with short TTL.

Data normalized into IntegrationItem objects (id, name, type, timestamps).
