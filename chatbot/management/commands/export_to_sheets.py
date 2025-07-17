from django.core.management.base import BaseCommand
from django.utils import timezone
from chatbot.models import Conversation
import json
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class Command(BaseCommand):
    help = 'Export conversation data to Google Sheets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--spreadsheet-id',
            type=str,
            help='Google Sheets spreadsheet ID',
        )
        parser.add_argument(
            '--credentials-file',
            type=str,
            default='credentials.json',
            help='Path to Google Sheets API credentials file',
        )

    def handle(self, *args, **options):
        spreadsheet_id = options['spreadsheet_id']
        credentials_file = options['credentials_file']
        
        if not spreadsheet_id:
            self.stdout.write(
                self.style.ERROR('Please provide a spreadsheet ID with --spreadsheet-id')
            )
            return
        
        if not os.path.exists(credentials_file):
            self.stdout.write(
                self.style.ERROR(f'Credentials file not found: {credentials_file}')
            )
            return
        
        try:
            # Set up Google Sheets API
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
            service = build('sheets', 'v4', credentials=creds)
            
            # Get all conversations
            conversations = Conversation.objects.all().order_by('created_at')
            
            # Prepare data for export
            data = []
            headers = [
                'ID', 'Email', 'Time Spent (seconds)', 'Test Type', 'Problem Type', 
                'Think Level', 'Feel Level', 'Created At', 'Chat Log'
            ]
            data.append(headers)
            
            for conv in conversations:
                # Format chat log as JSON string
                chat_log_str = json.dumps(conv.chat_log, indent=2) if conv.chat_log else ''
                
                row = [
                    conv.id,
                    conv.email,
                    conv.time_spent,
                    conv.test_type,
                    conv.problem_type,
                    conv.think_level,
                    conv.feel_level,
                    conv.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    chat_log_str
                ]
                data.append(row)
            
            # Clear existing data and write new data
            range_name = 'Sheet1!A1'
            
            # Clear the sheet first
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range='Sheet1'
            ).execute()
            
            # Write the data
            body = {
                'values': data
            }
            
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully exported {len(conversations)} conversations to Google Sheets!'
                )
            )
            self.stdout.write(f'Updated {result.get("updatedCells")} cells')
            
        except HttpError as error:
            self.stdout.write(
                self.style.ERROR(f'Google Sheets API error: {error}')
            )
        except Exception as error:
            self.stdout.write(
                self.style.ERROR(f'Error: {error}')
            ) 