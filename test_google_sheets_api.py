#!/usr/bin/env python3
"""
Test Google Sheets API functionality
"""

import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def test_google_sheets_api():
    """Test Google Sheets API connection and write access"""
    
    # Configuration
    spreadsheet_id = "14FpvPTgdp-YJtmvzWvxt_ksNfZJPCGkmpBDKtklytXM"
    credentials_file = "combot-data-collection-8eee97e4e41f.json"
    
    print("🔍 Testing Google Sheets API...")
    print(f"Spreadsheet ID: {spreadsheet_id}")
    print(f"Credentials file: {credentials_file}")
    print(f"Credentials file exists: {os.path.exists(credentials_file)}")
    
    if not os.path.exists(credentials_file):
        print("❌ Credentials file not found!")
        return False
    
    try:
        # Set up Google Sheets API
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        
        print("✅ Google Sheets API client created successfully")
        
        # Test reading from the spreadsheet
        print("📖 Testing read access...")
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='Sheet1!A1:A5'
        ).execute()
        
        print(f"✅ Read test successful - Found {len(result.get('values', []))} rows")
        
        # Test writing to the spreadsheet
        print("✍️  Testing write access...")
        test_data = [
            ["TEST", "Google Sheets API Test", "2025-08-07", "API Test", "Working"]
        ]
        
        body = {
            'values': test_data
        }
        
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range='Sheet1!A:A',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        print("✅ Write test successful!")
        print(f"Updated range: {result.get('updates', {}).get('updatedRange', 'Unknown')}")
        
        return True
        
    except HttpError as error:
        print(f"❌ Google Sheets API error: {error}")
        return False
    except Exception as error:
        print(f"❌ Unexpected error: {error}")
        return False

if __name__ == "__main__":
    success = test_google_sheets_api()
    if success:
        print("\n🎉 Google Sheets API is working correctly!")
    else:
        print("\n❌ Google Sheets API test failed!") 