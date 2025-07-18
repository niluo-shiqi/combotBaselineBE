from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Conversation
import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

@receiver(post_save, sender=Conversation)
def export_to_google_sheets(sender, instance, created, **kwargs):
    """
    Automatically export new conversations to Google Sheets
    """
    print(f"DEBUG: Signal triggered - Conversation {instance.id} created: {created}")
    
    if not created:  # Only export new conversations, not updates
        print(f"DEBUG: Skipping export - conversation was updated, not created")
        return
    
    # Check if Google Sheets integration is configured
    spreadsheet_id = getattr(settings, 'GOOGLE_SHEETS_SPREADSHEET_ID', None)
    credentials_file = getattr(settings, 'GOOGLE_SHEETS_CREDENTIALS_FILE', 'credentials.json')
    
    print(f"DEBUG: Google Sheets config - spreadsheet_id: {spreadsheet_id}")
    print(f"DEBUG: Google Sheets config - credentials_file: {credentials_file}")
    print(f"DEBUG: Google Sheets config - credentials_file exists: {os.path.exists(credentials_file) if credentials_file else False}")
    
    if not spreadsheet_id or not os.path.exists(credentials_file):
        print(f"DEBUG: Skipping export - Google Sheets not configured properly")
        return  # Skip if not configured
    
    try:
        # Set up Google Sheets API
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        
        # Prepare the new row data
        chat_log_str = json.dumps(instance.chat_log, indent=2) if instance.chat_log else ''
        
        row_data = [
            instance.id,
            instance.email,
            instance.time_spent,
            instance.test_type,
            instance.problem_type,
            instance.think_level,
            instance.feel_level,
            instance.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            chat_log_str
        ]
        
        # Append the new row to the sheet
        range_name = 'Sheet1!A:A'  # Find the next empty row
        
        body = {
            'values': [row_data]
        }
        
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        print(f"Successfully exported conversation {instance.id} to Google Sheets")
        
    except Exception as error:
        print(f"Error exporting to Google Sheets: {error}")
        print(f"DEBUG: Full error details: {type(error).__name__}: {str(error)}")
        # Don't raise the exception to avoid breaking the conversation save 