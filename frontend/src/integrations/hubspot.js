import { useState, useEffect } from "react";
import { Box, Button, TextField } from "@mui/material";
import axios from "axios";

export const HubspotIntegration = ({
  user,
  org,
  integrationParams,
  setIntegrationParams,
}) => {
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Cleanup if component unmounts
    return () => {
      setLoading(false);
    };
  }, []);

  const handleAuthorize = async () => {
    setLoading(true);
    try {
      // Step 1: ask backend for HubSpot OAuth URL
      const resp = await axios.post(
        "http://localhost:8000/integrations/hubspot/authorize",
        new URLSearchParams({ user_id: user, org_id: org })
      );
      const url = resp.data;

      // Step 2: open OAuth popup
      const popup = window.open(url, "hubspot-oauth", "width=800,height=600");

      // Step 3: poll backend for credentials
      const interval = setInterval(async () => {
        try {
          const credsResp = await axios.post(
            "http://localhost:8000/integrations/hubspot/credentials",
            new URLSearchParams({ user_id: user, org_id: org })
          );

          // Success: credentials available
          setIntegrationParams({
            type: "HubSpot",
            credentials: credsResp.data,
          });
          clearInterval(interval);
          if (popup) popup.close();
          setLoading(false);
        } catch (err) {
          // ignore 400 until credentials are ready
        }
      }, 1500);

      // Step 4: stop polling after 2 minutes max
      setTimeout(() => {
        clearInterval(interval);
        setLoading(false);
      }, 120000);
    } catch (e) {
      console.error("HubSpot auth error:", e);
      setLoading(false);
      alert(e?.response?.data?.detail || e.message);
    }
  };

  return (
    <Box display="flex" flexDirection="column" sx={{ width: 400 }}>
      <TextField
        label="Integration"
        value="HubSpot"
        sx={{ mt: 2 }}
        InputLabelProps={{ shrink: true }}
        disabled
      />
      <Button
        onClick={handleAuthorize}
        sx={{ mt: 2 }}
        variant="contained"
        disabled={loading}
      >
        {loading ? "Authorizing HubSpot..." : "Connect HubSpot"}
      </Button>
    </Box>
  );
};
