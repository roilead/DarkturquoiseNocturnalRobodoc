import json

def append_order_to_sheet(order: dict, sheet_id: str, creds_json: str):
    if not sheet_id or not creds_json:
        raise RuntimeError("Missing Google Sheets credentials or sheet id")

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except Exception as e:
        raise RuntimeError(
            "Google libraries are missing. Install google-api-python-client and google-auth."
        ) from e

    try:
        creds_info = json.loads(creds_json)
    except Exception as e:
        raise RuntimeError("GOOGLE_CREDS_JSON is not valid JSON") from e

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)

    service = build("sheets", "v4", credentials=creds, cache_discovery=False)

    values = [[
        order.get("created_at", ""),
        order.get("full_name", ""),
        order.get("username", ""),
        order.get("phone", ""),
        order.get("address", ""),
        ", ".join(order.get("items", [])),
        order.get("total", 0),
        order.get("user_id", "")
    ]]

    body = {"values": values}

    return service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range="Orders!A:H",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()