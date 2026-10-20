"""Test a range-only API write on a disposable Readout duplicate, then remove it."""
import json, os, uuid
from copy import deepcopy
from pathlib import Path
import gspread
import elo_chart_range as m

client=gspread.service_account_from_dict(json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON']))
book=client.open_by_key(m.BOOKS['FAFL'][0])
before=m.read_charts(book,'FAFL')
teams=m.read_current(book,'FAFL')[1]
styles=m.exported_styles(book,'FAFL')
sheet_id=book.worksheet('Readout').id
name='_EloRangeTest_'+uuid.uuid4().hex[:8]
copy_id=None
report={}
try:
    reply=book.batch_update({'requests':[{'duplicateSheet':{'sourceSheetId':sheet_id,'newSheetName':name}}]})
    copy_id=reply['replies'][0]['duplicateSheet']['properties']['sheetId']
    book.batch_update({'requests':[{'updateSheetProperties':{'properties':{'sheetId':copy_id,'hidden':True},'fields':'hidden'}}]})
    cloned=m.exported_styles(book,'FAFL',name)
    if cloned!=styles: raise ValueError('Duplicating the sheet altered native chart styles')
    metadata=book.fetch_sheet_metadata()
    charts=next(s for s in metadata['sheets'] if s['properties']['sheetId']==copy_id)['charts']
    lower,upper=m.bounds(list(teams.values()))
    desired,requests=m.plan(charts,lower,upper)
    book.batch_update({'requests':requests})
    after=m.exported_styles(book,'FAFL',name)
    report={'preserves_styles':after==styles,'expected_styles':styles,'actual_styles':after}
    print('Direct Sheets API preserves native chart colors and text styles:',after==styles,flush=True)
finally:
    if copy_id is not None:
        book.batch_update({'requests':[{'deleteSheet':{'sheetId':copy_id}}]})
        print('Temporary Readout duplicate removed.',flush=True)
    report['original_charts_unchanged']=m.read_charts(book,'FAFL')==before
    report['original_ratings_unchanged']=m.read_current(book,'FAFL')[1]==teams
    report['original_styles_unchanged']=m.exported_styles(book,'FAFL')==styles
    Path('artifacts/chart-api-probe').mkdir(parents=True,exist_ok=True)
    Path('artifacts/chart-api-probe/result.json').write_text(json.dumps(report,indent=2))
    print({k:v for k,v in report.items() if k.endswith('_unchanged')},flush=True)
