#!/usr/bin/env python3
import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Set up Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file('combot-data-collection-8eee97e4e41f.json', scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)

# Test data
headers = [
    'ID', 'Email', 'Time Spent (seconds)', 'Test Type', 'Problem Type', 
    'Think Level', 'Feel Level', 'Endpoint Type', 'Created At', 'Chat Log', 'Message Type Log', 'Product Type Breakdown'
]

# Test row with product_type_breakdown data
test_row = [
    '999', 'test@example.com', '120', 'Basic', 'C', 'High', 'High', 'N/A', 
    '2025-08-03 09:00:00', '[]', '[]', 
    json.dumps({'A': 0.1, 'B': 0.2, 'C': 0.6, 'Other': 0.1}, indent=2)
]

data = [headers, test_row]

print(f"Headers: {headers}")
print(f"Number of headers: {len(headers)}")
print(f"Test row: {test_row}")
print(f"Number of columns in test row: {len(test_row)}")

# Clear the sheet and write test data
service.spreadsheets().values().clear(
    spreadsheetId='14FpvPTgdp-YJtmvzWvxt_ksNfZJPCGkmpBDKtklytXM',
    range='Sheet1'
).execute()

body = {
    'values': data
}

result = service.spreadsheets().values().update(
    spreadsheetId='14FpvPTgdp-YJtmvzWvxt_ksNfZJPCGkmpBDKtklytXM',
    range='Sheet1!A1',
    valueInputOption='RAW',
    body=body
).execute()

print(f"Updated {result.get('updatedCells')} cells")
print("Test data written to Google Sheets") 