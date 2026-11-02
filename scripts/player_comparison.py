"""Observed 40-yard acceleration profiles and notebook comparison controls.

These measurements do not establish physical launch/finish boundaries or units.
"""
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter


def attempt_curve(frames, window=7):
    """Return direct polynomial derivatives only for complete centered windows."""
    if window not in (5, 7, 9):
        raise ValueError("Choose a checked smoothing window: 5, 7, or 9 frames")
    frames = frames.sort_values('time').copy()
    time = pd.to_datetime(frames['time'], errors='coerce')
    if time.isna().any() or len(frames) < window + 2:
        raise ValueError('Invalid timestamps or insufficient frames')
    t = (time-time.iloc[0]).dt.total_seconds().to_numpy()
    speed = pd.to_numeric(frames['s'], errors='coerce').to_numpy(dtype=float, na_value=np.nan)
    dt = np.diff(t)
    if (not np.isfinite(speed).all() or (speed < 0).any() or (dt <= 0).any()
            or not np.allclose(dt, np.median(dt), atol=.001, rtol=0)):
        raise ValueError('Invalid speed, duplicate timestamps, or irregular sampling')
    half = window//2
    smooth = savgol_filter(speed, window, 2, mode='interp')
    derivative = savgol_filter(speed, window, 2, deriv=1, delta=float(np.median(dt)), mode='interp')
    eligible = np.arange(half, len(t)-half)
    peak = int(eligible[np.argmax(derivative[eligible])])
    visible = np.full(len(t), np.nan)
    visible[eligible] = derivative[eligible]
    return {'t':t, 'speed':speed, 'smoothed_speed':smooth, 'acceleration':visible,
            'peak_index':peak, 'peak_acceleration_raw_per_s':float(derivative[peak]),
            'peak_time_from_recording_start_s':float(t[peak]),
            'peak_location':('Start boundary' if peak==eligible[0] else
                             'End boundary' if peak==eligible[-1] else 'Interior'),
            'valid_start_s':float(t[eligible[0]]), 'valid_end_s':float(t[eligible[-1]])}


def measure_all_attempts(frames, group_columns, windows=(5,7,9)):
    records=[]
    for key, group in frames.groupby(group_columns, dropna=False, sort=False):
        metadata=dict(zip(group_columns,key))
        for column in ['display_name','combine_position','nfl_position','official_forty_hundredths']:
            metadata[column]=group[column].iloc[0]
        for window in windows:
            row={**metadata,'window_frames':window,'n_frames':len(group),
                 'launch_coverage':'Unverified','finish_coverage':'Unverified'}
            try:
                curve=attempt_curve(group,window)
                row.update(status='Measured',**{k:curve[k] for k in [
                    'peak_acceleration_raw_per_s','peak_time_from_recording_start_s',
                    'peak_location','valid_start_s','valid_end_s']})
            except ValueError as exc:
                row.update(status='Review required',review_reason=str(exc))
            records.append(row)
    return pd.DataFrame(records)


def speed_reference(t,speed,threshold=3.0):
    """First observed upward crossing followed by .3 s above the threshold."""
    indices=np.flatnonzero((speed[:-1]<threshold)&(speed[1:]>=threshold))+1
    for i in indices:
        end=np.searchsorted(t,t[i]+.3-1e-8)
        if end < len(t) and np.all(speed[i:end+1]>=threshold):
            return float(t[i-1]+(threshold-speed[i-1])/(speed[i]-speed[i-1])*(t[i]-t[i-1]))
    raise ValueError('No supported 3-unit speed crossing; choose recording-start reference')



SPEED_BANDS = [(2.0, 4.0), (4.0, 6.0), (6.0, 8.0), (8.0, 10.0), (3.0, 7.0)]


def observed_speed_interval(t, speed, lower, upper, hold_seconds=0.3):
    """Elapsed time between bracketed speed crossings; no launch inference."""
    t=np.asarray(t,dtype=float);speed=np.asarray(speed,dtype=float)
    if not 0 <= lower < upper or hold_seconds <= 0:
        raise ValueError('Invalid thresholds or hold duration')
    if len(t)<2 or len(t)!=len(speed) or not np.isfinite(t).all() or not np.isfinite(speed).all():
        return {'status':'Invalid or insufficient observations'}
    if (np.diff(t)<=0).any():
        return {'status':'Non-increasing timestamps'}
    dt=np.diff(t)
    if not np.allclose(dt,np.median(dt),atol=.001,rtol=0):
        return {'status':'Irregular sampling'}
    crossings=np.flatnonzero((speed[:-1]<upper)&(speed[1:]>=upper))+1
    if not len(crossings):
        return {'status':'No bracketed upper crossing'}
    high=None
    for i in crossings:
        end=np.searchsorted(t,t[i]+hold_seconds-1e-8)
        if end<len(t) and np.all(speed[i:end+1]>=upper):
            high=int(i);break
    if high is None:
        return {'status':'Upper crossing lacks sustained observed coverage'}
    lows=np.flatnonzero((speed[:-1]<=lower)&(speed[1:]>lower))+1
    lows=lows[lows<=high]
    if not len(lows):
        return {'status':'No bracketed lower crossing before upper crossing'}
    low=int(lows[-1])
    if (speed[low:high+1]<lower).any():
        return {'status':'Speed fell below lower threshold'}
    def crossing(i,value):
        return float(t[i-1]+(value-speed[i-1])/(speed[i]-speed[i-1])*(t[i]-t[i-1]))
    first=crossing(low,lower);last=crossing(high,upper)
    return {'status':'Measured','lower_crossing_from_recording_start_s':first,
            'upper_crossing_from_recording_start_s':last,'interval_s':last-first}


def measure_all_intervals(frames,group_columns,bands=None):
    """Retain every method/band/attempt, including unsupported measurements."""
    bands=SPEED_BANDS if bands is None else bands
    records=[]
    for key,group in frames.groupby(group_columns,dropna=False,sort=False):
        group=group.sort_values('time')
        metadata=dict(zip(group_columns,key))
        for col in ['display_name','combine_position','nfl_position','official_forty_hundredths']:
            metadata[col]=group[col].iloc[0]
        curves={}
        try:
            checked=attempt_curve(group,9)
            curves['Raw']=(checked['t'],checked['speed'])
            for window in [5,7,9]:
                curve=checked if window==9 else attempt_curve(group,window)
                half=window//2
                curves[f'{window}-frame']=(curve['t'][half:-half],curve['smoothed_speed'][half:-half])
            reason=None
        except ValueError as exc:
            reason=str(exc)
        for method in ['Raw','5-frame','7-frame','9-frame']:
            for lower,upper in bands:
                measured=({'status':'Review required','review_reason':reason} if reason is not None else
                          observed_speed_interval(*curves[method],lower,upper))
                records.append({**metadata,'method':method,'speed_band':f'{lower:g}-to-{upper:g}',
                                'lower_speed_raw':lower,'upper_speed_raw':upper,'hold_seconds':.3,**measured})
    return pd.DataFrame(records)


def comparison_widget(frames,roster,group_columns):
    """Position -> exact official time -> players -> attempts, without NFL filters."""
    import ipywidgets as widgets
    import matplotlib.pyplot as plt
    from IPython.display import display, clear_output
    positions=sorted(roster['combine_position'].dropna().unique())
    position=widgets.Dropdown(options=positions,value='WR' if 'WR' in positions else positions[0],description='Position:')
    cross=widgets.Checkbox(value=False,description='Enable cross-position comparison',indent=False)
    cross_positions=widgets.SelectMultiple(options=positions,value=(position.value,),description='Groups:',disabled=True,rows=len(positions))
    years=widgets.Dropdown(options=[('All draft years','ALL')]+[(str(y),str(y)) for y in sorted(roster.draft_year.unique())],description='Draft year:')
    times=widgets.Dropdown(description='Official 40:')
    players=widgets.SelectMultiple(description='Players:',rows=9,layout=widgets.Layout(width='95%'))
    attempts=widgets.SelectMultiple(description='Attempts:',rows=7,layout=widgets.Layout(width='95%'))
    smoothing=widgets.Dropdown(options=[('5 frames',5),('7 frames',7),('9 frames',9)],value=7,description='Smoothing:')
    reference=widgets.Dropdown(options=[('First recorded frame (launch unverified)','recording'),
                                        ('Observed 3-unit speed crossing (not launch)','speed3')],
                               value='recording',description='Time zero:',layout=widgets.Layout(width='95%'))
    bands=widgets.SelectMultiple(options=[(f'{lo:g} → {hi:g} raw speed units',f'{lo:g}-to-{hi:g}') for lo,hi in SPEED_BANDS],
                                 value=('2-to-4','4-to-6','6-to-8','8-to-10'),description='Speed bands:',rows=5,
                                 layout=widgets.Layout(width='95%'))
    out=widgets.Output()
    busy={'value':False}
    def filtered_roster():
        groups=list(cross_positions.value) if cross.value else [position.value]
        rows=roster.loc[roster.combine_position.isin(groups)]
        if years.value!='ALL':rows=rows.loc[rows.draft_year.astype(str).eq(years.value)]
        return rows
    def selected_roster():
        rows=filtered_roster()
        if times.value is not None and times.value!=-1:
            rows=rows.loc[rows.official_forty_hundredths.eq(times.value)]
        return rows
    def render(*_):
        if busy['value']:return
        with out:
            clear_output(wait=True)
            if not players.value or not attempts.value:
                print('Select players and at least one recorded attempt.');return
            if len(players.value)>8:
                print('For a readable plot, select up to eight players at once.');return
            selected=frames.loc[frames.nfl_id.isin(players.value)]
            groups=list(selected.groupby(group_columns,dropna=False,sort=False))
            groups=[(key,g) for key,g in groups if tuple(str(v) for v in key) in attempts.value]
            if not groups:print('No selected recordings.');return
            fig,axes=plt.subplots(1,2,figsize=(14,5),constrained_layout=True)
            palette=plt.get_cmap('tab10')
            colors={player:palette(i) for i,player in enumerate(players.value)}
            player_counts={};rows=[];interval_rows=[];warnings=[]
            for key,g in groups:
                g=g.sort_values('time');first=g.iloc[0]
                try:
                    curve=attempt_curve(g,smoothing.value)
                    offset=0.0 if reference.value=='recording' else speed_reference(curve['t'],curve['speed'])
                except ValueError as exc:
                    warnings.append(f"{first.display_name}, attempt {first.attempt}: {exc}");continue
                player=str(first.nfl_id);number=player_counts.get(player,0);player_counts[player]=number+1
                style=['-','--',':','-.'][number%4];color=colors[player]
                label=f"{first.display_name} ({first.combine_position}, {first.draft_year}) — attempt {first.attempt}"
                t=curve['t']-offset;peak=curve['peak_index']
                axes[0].plot(t,curve['speed'],color=color,linestyle=style,label=label)
                axes[1].plot(t,curve['acceleration'],color=color,linestyle=style,label=label)
                axes[1].scatter(t[peak],curve['peak_acceleration_raw_per_s'],color=color,s=45)
                axes[1].annotate(f"{t[peak]:.1f} s",(t[peak],curve['peak_acceleration_raw_per_s']),
                                 xytext=(4,6),textcoords='offset points',fontsize=8)
                rows.append({'player':first.display_name,'combine_position':first.combine_position,
                             'draft_year':first.draft_year,'official_forty_s':int(first.official_forty_hundredths)/100,
                             'attempt':first.attempt,'peak_acceleration_raw_per_s':curve['peak_acceleration_raw_per_s'],
                             'peak_time_from_recording_start_s':curve['peak_time_from_recording_start_s'],
                             'peak_time_from_selected_reference_s':float(t[peak]),'peak_location':curve['peak_location'],
                             'launch_coverage':'Unverified'})
                for lower,upper in SPEED_BANDS:
                    band=f'{lower:g}-to-{upper:g}'
                    if band not in bands.value:
                        continue
                    result=observed_speed_interval(curve['t'],curve['speed'],lower,upper)
                    interval_rows.append({
                        'player':first.display_name,'position':first.combine_position,
                        'draft_year':first.draft_year,'attempt':first.attempt,
                        'speed_band_raw':band,**result,
                    })
            xlabel=('Seconds since first recorded frame (not confirmed launch)' if reference.value=='recording'
                    else 'Seconds relative to observed 3-unit speed crossing (not launch)')
            axes[0].set(title='Recorded speed',ylabel='Speed (raw units)',xlabel=xlabel)
            axes[1].set(title='Signed acceleration — markers indicate observed peaks',
                         ylabel='Raw speed units / second',xlabel=xlabel)
            axes[1].axhline(0,color='gray',linewidth=.8)
            guides=sorted({value for lo,hi in SPEED_BANDS if f'{lo:g}-to-{hi:g}' in bands.value for value in (lo,hi)})
            for value in guides:
                axes[0].axhline(value,color='gray',linewidth=.6,linestyle=':',alpha=.35)
            for ax in axes:
                ax.grid(alpha=.2)
                if rows:ax.legend(fontsize=7)
            fig.suptitle('40-yard profiles: separate attempts; no timing stretched to match a finish')
            plt.show()
            if rows:
                table=pd.DataFrame(rows)
                display(table.round(3))
                if table.draft_year.nunique()>1:
                    print('Multiple draft years: recording/processing differences may affect comparisons.')
                if table.peak_location.ne('Interior').any():
                    print('Boundary peak flagged: the peak may extend beyond the supported observation region.')
            if interval_rows:
                print('Speed-building intervals: raw supplied speed, seconds between observed thresholds.')
                interval_table=pd.DataFrame(interval_rows)
                display(interval_table.round(3))
                print('Unsupported intervals stay unavailable; they are not filled with zero. Smoothing controls peak estimation, not this raw-speed interval table.')
            for warning in warnings:print(warning)
            print('Observed peaks only. Physical launch, full-40 finish coverage, and physical units remain unverified.')
    def refresh_attempts():
        selected=frames.loc[frames.nfl_id.isin(players.value)]
        options=[]
        for key,g in selected.groupby(group_columns,dropna=False,sort=False):
            first=g.iloc[0]
            label=f"{first.display_name} ({first.draft_year}) — attempt {first.attempt} — event {first.event_id}"
            options.append((label,tuple(str(v) for v in key)))
        attempts.options=options;attempts.value=tuple(value for _,value in options)
    def player_change(*_):
        if busy['value']:return
        busy['value']=True
        try:refresh_attempts()
        finally:busy['value']=False
        render()
    def refresh_players():
        rows=selected_roster().sort_values(['official_forty_hundredths','display_name','draft_year'])
        options=[(f"{r.display_name} | {r.combine_position} | {r.draft_year} | {int(r.official_forty_hundredths)/100:.2f} s | {r.recordings} recording(s)",str(r.nfl_id)) for r in rows.itertuples()]
        old=[v for v in players.value if v in {value for _,value in options}]
        players.options=options;players.value=tuple(old if old else [v for _,v in options[:2]])
        refresh_attempts()
    def time_change(*_):
        if busy['value']:return
        busy['value']=True
        try:refresh_players()
        finally:busy['value']=False
        render()
    def filters_change(*_):
        if busy['value']:return
        busy['value']=True
        try:
            cross_positions.disabled=not cross.value
            position.disabled=cross.value
            rows=filtered_roster()
            counts=rows.official_forty_hundredths.dropna().astype(int).value_counts()
            options=[('All official times',-1)]+[(f'{value/100:.2f} s ({int(counts[value])} players)',int(value)) for value in sorted(counts.index)]
            previous=times.value
            times.options=options
            times.value=previous if previous in set(v for _,v in options) else (int(counts.idxmax()) if len(counts) else -1)
            refresh_players()
        finally:busy['value']=False
        render()
    for control in [position,cross,cross_positions,years]:control.observe(filters_change,names='value')
    times.observe(time_change,names='value');players.observe(player_change,names='value')
    for control in [attempts,smoothing,reference,bands]:control.observe(render,names='value')
    controls=widgets.VBox([widgets.HTML('<b>Position → official 40 time → players → recorded attempts</b>'),
                           widgets.HBox([position,years]),cross,cross_positions,times,players,attempts,
                           smoothing,reference,bands,out])
    filters_change()
    return controls


def within_position_repeatability(measurements,metric,feature_columns):
    """Paired agreement and rank consistency within each Combine position."""
    good=measurements.loc[measurements['status'].eq('Measured')].copy()
    pairs=[]
    group_columns=['combine_position','draft_year','nfl_id']+list(feature_columns)
    for key,rows in good.groupby(group_columns,dropna=False,sort=False):
        if len(rows)!=2:
            continue
        rows=rows.assign(_order=pd.to_numeric(rows['attempt'],errors='raise')).sort_values(['_order','event_id'])
        a,b=rows.iloc[0],rows.iloc[1]
        va,vb=float(a[metric]),float(b[metric]);mean=(va+vb)/2
        pairs.append({**dict(zip(group_columns,key)),'display_name':a['display_name'],
                      'attempt_a':a['attempt'],'attempt_b':b['attempt'],
                      'value_a':va,'value_b':vb,'absolute_difference':abs(vb-va),
                      'absolute_difference_pct':100*abs(vb-va)/abs(mean) if abs(mean)>1e-10 else np.nan})
    paired=pd.DataFrame(pairs)
    summary_keys=['combine_position']+list(feature_columns)
    scaffold=measurements[summary_keys].drop_duplicates()
    if paired.empty:
        empty_summary=scaffold.copy()
        empty_summary['paired_players']=0
        for col in ['pearson','spearman','median_absolute_difference','median_absolute_difference_pct','p90_absolute_difference_pct']:
            empty_summary[col]=np.nan
        return paired,empty_summary
    summaries=[]
    for key,rows in paired.groupby(['combine_position']+list(feature_columns),dropna=False,sort=False):
        summaries.append({**dict(zip(['combine_position']+list(feature_columns),key if isinstance(key,tuple) else (key,))),
                          'paired_players':len(rows),
                          'pearson':rows.value_a.corr(rows.value_b) if len(rows)>=3 and rows.value_a.std()>0 and rows.value_b.std()>0 else np.nan,
                          'spearman':rows.value_a.corr(rows.value_b,method='spearman') if len(rows)>=3 and rows.value_a.std()>0 and rows.value_b.std()>0 else np.nan,
                          'median_absolute_difference':rows.absolute_difference.median(),
                          'median_absolute_difference_pct':rows.absolute_difference_pct.median(),
                          'p90_absolute_difference_pct':rows.absolute_difference_pct.quantile(.9)})
    summary=scaffold.merge(pd.DataFrame(summaries),on=summary_keys,how='left',validate='one_to_one')
    summary['paired_players']=summary['paired_players'].fillna(0).astype(int)
    return paired,summary
