# AQI SOVEREIGN DATA TRANSFER PROTOCOL
**Date:** November 28, 2025
**Status:** ACTIVE
**Protocol:** OFFLINE / LOCAL ONLY

## 1. THE SITUATION
You have severed the connection to OneDrive.
This is a **Security Upgrade**, but it breaks the automatic sync between the Mac (RSE Agent) and Windows (Agent X).

## 2. THE NEW ARCHITECTURE
We have established a **Sovereign Ingest Directory** on the Windows machine.
*   **Path:** `C:\AQI_Data_Ingest\`
*   **Status:** Local Only. Not scanned by Microsoft.

## 3. HOW TO TRANSFER DATA (The "Air Gap" Method)
To move Excel/CSV files from the Mac to Agent X, follow this procedure:

### Option A: The "Sneakernet" (Maximum Security)
1.  **On Mac:** Export the leads from RSE Agent to a USB Drive.
2.  **On Windows:** Plug in the USB Drive.
3.  **Action:** Copy the `.xlsx` or `.csv` files into `C:\AQI_Data_Ingest\`.
4.  **Result:** Agent X will automatically detect and import them on the next run.

### Option B: The "LAN Share" (Convenience)
*Instruct your IT Consultant to set this up.*
1.  Create a Windows Network Share (SMB) for `C:\AQI_Data_Ingest`.
2.  Connect the Mac to this share over the local Wi-Fi.
3.  Save RSE exports directly to this folder.
4.  **Note:** This keeps traffic on your local router. It does not go to the Cloud.

## 4. SYSTEM UPDATE
I have updated `aqi_lead_importer.py`.
*   **OLD:** Looked for hardcoded OneDrive paths.
*   **NEW:** Scans `C:\AQI_Data_Ingest\` for *any* Excel or CSV file.

**The system is now ready for offline data ingestion.**
