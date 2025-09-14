import { useState } from "react";
import { Box, TextField, Button } from "@mui/material";
import axios from "axios";

const endpointMapping = {
  Notion: "notion",
  Airtable: "airtable",
  HubSpot: "hubspot/get_hubspot_items",
};

export const DataForm = ({ integrationType, credentials }) => {
  const [loadedData, setLoadedData] = useState(null);
  const endpoint = endpointMapping[integrationType];

  const handleLoad = async () => {
    try {
      let response;

      if (integrationType === "HubSpot") {
        // HubSpot expects JSON with access_token
        response = await axios.post(
          `http://localhost:8000/integrations/${endpoint}`,
          { access_token: credentials.access_token },
          { headers: { "Content-Type": "application/json" } }
        );
      } else {
        // Airtable & Notion expect FormData with credentials
        const formData = new FormData();
        formData.append("credentials", JSON.stringify(credentials));

        const url = endpoint.includes("/")
          ? `http://localhost:8000/integrations/${endpoint}`
          : `http://localhost:8000/integrations/${endpoint}/load`;

        response = await axios.post(url, formData);
      }

      setLoadedData(JSON.stringify(response.data, null, 2));
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    }
  };

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      flexDirection="column"
      width="100%"
    >
      <Box display="flex" flexDirection="column" width="100%">
        <TextField
          label="Loaded Data"
          value={loadedData || ""}
          sx={{ mt: 2 }}
          InputLabelProps={{ shrink: true }}
          multiline
          minRows={6}
          disabled
        />
        <Button onClick={handleLoad} sx={{ mt: 2 }} variant="contained">
          Load Data
        </Button>
        <Button
          onClick={() => setLoadedData(null)}
          sx={{ mt: 1 }}
          variant="outlined"
        >
          Clear Data
        </Button>
      </Box>
    </Box>
  );
};
