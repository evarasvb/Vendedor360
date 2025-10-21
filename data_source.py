import os
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

SHEET_NAME = os.getenv('SHEET_NAME', 'Vendedor360_DataHub')

def fetch(tab):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'], scope)
    gs = gspread.authorize(creds)
    ws = gs.open(SHEET_NAME).worksheet(tab)
    return pd.DataFrame(ws.get_all_records())
