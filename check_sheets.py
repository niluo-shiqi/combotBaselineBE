#!/usr/bin/env python3
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Set up Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file('combot-data-collection-8eee97e4e41f.json', scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)

# Get the first few rows to see headers
result = service.spreadsheets().values().get(
    spreadsheetId='14FpvPTgdp-YJtmvzWvxt_ksNfZJPCGkmpBDKtklytXM', 
    range='Sheet1!A1:L5'
).execute()

print('Headers and first few rows:')
for i, row in enumerate(result.get('values', [])):
    print(f'Row {i+1}: {row}') 