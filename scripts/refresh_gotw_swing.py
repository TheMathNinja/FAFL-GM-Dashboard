"""Recalculate only GoTW matchup stakes from the published weekly source."""
import pandas as pd
import build

if __name__ == '__main__':
    meta,divmap,opp,home,current,week,status=build.load_source()
    if not 1 <= week < 12:
        raise ValueError('GoTW swing requires an upcoming regular-season matchup')
    _,_,swing=build.forecast(build.historical(),current,meta,divmap,opp,home,week,12000)
    frame=pd.DataFrame(swing)
    if len(frame)!=16 or frame.combined_seed_swing.isna().any():
        raise ValueError('Incomplete conditional seed swing')
    frame.to_csv(build.ROOT/'data/playoff_swing.csv',index=False)
    print('Updated Game of the Week swing data only.')
