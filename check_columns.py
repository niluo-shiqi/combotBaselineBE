#!/usr/bin/env python3
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Set up Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file('combot-data-collection-8eee97e4e41f.json', scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)

# Get the first row to see headers
result = service.spreadsheets().values().get(
    spreadsheetId='14FpvPTgdp-YJtmvzWvxt_ksNfZJPCGkmpBDKtklytXM', 
    range='Sheet1!A1:Z1'
).execute()

headers = result.get('values', [[]])[0]
print(f'Number of columns: {len(headers)}')
print(f'Headers: {headers}')

# Check if Product Type Breakdown is in the headers
if 'Product Type Breakdown' in headers:
    print('✅ Product Type Breakdown column found!')
else:
    print('❌ Product Type Breakdown column NOT found!') 