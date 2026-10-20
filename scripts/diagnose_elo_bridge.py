"""Read-only bridge diagnostics. Never output credentials or project source."""
import json
import os
import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession
from elo_chart_range import PAYOUTS

info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'])
client = gspread.service_account_from_dict(info)
for league, book_id in PAYOUTS.items():
    ref = client.open_by_key(book_id).worksheet('Reference')
    for cell in ['Z14', 'Z15']:
        raw = ref.acell(cell).value
        data = json.loads(raw) if raw else {}
        safe = {k:data[k] for k in ['request_id','status','league','week','lower','upper','error','rollback_error','at','created_at'] if k in data}
        print(league, cell, json.dumps(safe), flush=True)
creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/script.projects.readonly'])
session = AuthorizedSession(creds)
response = session.get('https://script.googleapis.com/v1/projects/1n-MffRElmzpY4wZg41_a5KiHdk-qWZijMh8EyZ2-9VlciGzIvWS7hwM4/content', timeout=45)
print('Apps Script project API HTTP', response.status_code)
if response.ok:
    print('Project files:', [f['name'] for f in response.json().get('files',[])])
else:
    err=response.json().get('error',{})
    print('Project API access:', err.get('status'), [d.get('reason') for d in err.get('details',[]) if d.get('reason')])
drive = AuthorizedSession(Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/drive.readonly','https://www.googleapis.com/auth/drive.scripts']))
response=drive.get('https://www.googleapis.com/drive/v3/files/1n-MffRElmzpY4wZg41_a5KiHdk-qWZijMh8EyZ2-9VlciGzIvWS7hwM4', params={'fields':'capabilities(canEdit)'},timeout=45)
print('Known Elo bridge Drive API HTTP',response.status_code)
if response.ok:
    print('Known Elo bridge editable:',response.json().get('capabilities',{}).get('canEdit'))
else:
    err=response.json().get('error',{})
    print('Drive access:',err.get('status'),[d.get('reason') for d in err.get('details',[]) if d.get('reason')])
cloud=AuthorizedSession(Credentials.from_service_account_info(info,scopes=['https://www.googleapis.com/auth/cloud-platform']))
response=cloud.post('https://cloudresourcemanager.googleapis.com/v1/projects/'+info['project_id']+':testIamPermissions',json={'permissions':['serviceusage.services.enable']},timeout=45)
print('Automation account can enable its project APIs:',response.ok and 'serviceusage.services.enable' in response.json().get('permissions',[]))
