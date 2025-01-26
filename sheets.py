#! /usr/bin/python3

import os.path
import json
from datetime import date

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = "19bmBmZd-dQ8CGZg3O8gBbKMUMu8YmwrgNPQG43xkstc"
RANGE = "A2:A4"
SHEET_NAME = "Sheet1"

def append_row(service, spreadsheet_id, sheet_name, json_data):
  """
  Appends a row to the google sheet

  Args:
      service (_type_): _description_
      spreadsheet_id (_type_): _description_
      sheet_name (_type_): _description_
      json_data (_type_): _description_
  """
  # Map JSON data to row values TODO

  row_values = [json_data["date"],
    json_data["company"],
    json_data["job_title"],
    json_data["location"],
    json_data["posting"], # replace with actual site
    json_data["salary"]["annually"], # format salary in a better way
    "", # figure out how to modify status dropdown through api
    json_data["notes"]
  ]

  # Create payload TODO format correctly with google sheets formats e.g. stringValue
  body = {
      "values": [row_values]
  }
  print(body)


  # Append the row
  result = service.spreadsheets().values().append(
      spreadsheetId=spreadsheet_id,
      range=sheet_name,
      valueInputOption="RAW",  # Use "USER_ENTERED" to process formulas
      insertDataOption="INSERT_ROWS",
      body=body
  ).execute()
  print(f"Appended row: {result}")

  return True

def main(json_data):
  """
  Gain access and append to google sheet
  """
  creds = check_credentials()
  if creds:
    try:
      service = build("sheets", "v4", credentials=creds)
      if append_row(service, SPREADSHEET_ID, SHEET_NAME, json_data):
        return True

    except HttpError as err:
      print(err)

  else:
    print("Can not find credentials--make sure token.json exists")
    return False

def check_credentials():
  """
  Verifies that we have a token.json file that holds the user's google drive access token
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())
    
  return creds

if __name__ == "__main__":
  json_data = ""
  with open("job_info.json") as f:
    json_data = json.load(f)
  main(json_data)
