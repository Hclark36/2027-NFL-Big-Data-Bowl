"""Build the local report, figures, and offline all-position comparison.

Usage: python scripts/build_report.py
No API login, network access, model refitting, or publication is performed.
"""
from pathlib import Path
import base64
import hashlib
import html
import json
import re
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from player_comparison import attempt_curve, speed_reference

POSITIONS=['DB','DL','OL','TE','WR']
COLORS=['#147d75','#d06b32','#426ab0','#9971aa','#7c8230','#a34b67']


def read_manifest(folder):
    path=folder/'manifest.json'
    if not path.is_file():
        raise FileNotFoundError(f'Run the source notebook before the report: {path}')
    manifest=json.loads(path.read_text())
    if manifest.get('schema_version')!=1:
        raise ValueError(f'Unsupported manifest schema: {path}')
    for name,info in manifest['files'].items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=info['sha256']:
            raise ValueError(f'Changed source: {folder/name}; regenerate source outputs')
    return manifest


def clean_json(value):
    if isinstance(value,dict):return {str(k):clean_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple,np.ndarray)):return [clean_json(v) for v in value]
    if isinstance(value,(np.integer,)):return int(value)
    if isinstance(value,(np.floating,float)):return float(value) if np.isfinite(value) else None
    if isinstance(value,(np.bool_,)):return bool(value)
    if value is pd.NA or value is pd.NaT:return None
    return value


def inline_markdown(text):
    text=html.escape(text,quote=False)
    text=re.sub(r'\[([^\]]+)\]\((https://[^\s)]+)\)',r'<a href="\2" target="_blank" rel="noopener">\1</a>',text)
    text=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',text)
    text=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'<em>\1</em>',text)
    text=re.sub(r'`([^`]+)`',r'<code>\1</code>',text)
    return text


def render_writeup(markdown,report_dir):
    lines=markdown.splitlines();blocks=[];toc=[];paragraph=[];i=0
    def flush():
        if paragraph:
            blocks.append('<p>'+inline_markdown(' '.join(paragraph))+'</p>');paragraph.clear()
    while i<len(lines):
        line=lines[i].strip()
        if not line:flush();i+=1;continue
        if line.startswith('# '):flush();i+=1;continue
        if line.startswith('## '):
            flush();title=line[3:];id_=re.sub(r'[^a-z0-9]+','-',title.lower()).strip('-')
            blocks.append(f'<h2 id="{id_}">{html.escape(title)}</h2>');toc.append((id_,title));i+=1;continue
        image=re.fullmatch(r'!\[(.*)\]\(([^)]+)\)',line)
        if image:
            flush();caption,path=image.groups();target=report_dir/path
            encoded=base64.b64encode(target.read_bytes()).decode('ascii')
            alt=caption.split('. ',1)[-1]
            blocks.append(f'<figure><img src="data:image/png;base64,{encoded}" alt="{html.escape(alt,quote=True)}"><figcaption>{inline_markdown(caption)}</figcaption></figure>')
            i+=1;continue
        if line.startswith('|'):
            flush();rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',x) for x in row):rows.append(row)
                i+=1
            header='<thead><tr>'+''.join(f'<th scope="col">{inline_markdown(c)}</th>' for c in rows[0])+'</tr></thead>'
            body='<tbody>'+''.join('<tr>'+''.join('<td>'+inline_markdown(c)+'</td>' for c in row)+'</tr>' for row in rows[1:])+'</tbody>'
            blocks.append('<div class="table-scroll"><table>'+header+body+'</table></div>');continue
        paragraph.append(line);i+=1
    flush()
    navigation='<nav aria-label="Report contents">'+''.join(f'<a href="#{id_}">{html.escape(title)}</a>' for id_,title in toc)+'</nav>'
    return '\n'.join(blocks),navigation


def build_report(root):
    root=Path(root).resolve();report=root/'report';figures=report/'figures';figures.mkdir(parents=True,exist_ok=True)
    prepared=root/'outputs/prepared_all_positions';profiles=root/'outputs/all_position_profiles';validation=root/'outputs/all_position_validation'
    pm=read_manifest(prepared);prm=read_manifest(profiles);vm=read_manifest(validation)
    if prm['source_all_position_manifest_sha256']!=hashlib.sha256((prepared/'manifest.json').read_bytes()).hexdigest():
        raise ValueError('Notebook 03 is stale relative to Notebook 02; rerun it before reporting')
    if vm['source_profile_manifest_sha256']!=hashlib.sha256((profiles/'manifest.json').read_bytes()).hexdigest():
        raise ValueError('Notebook 05 is stale relative to Notebook 03; rerun it before reporting')
    pilot=root/'outputs/validation';pilot_manifest=read_manifest(pilot)
    keys=pm['group_columns'];types={c:'string' for c in keys}
    roster=pd.read_csv(profiles/'comparison_roster.csv',dtype=types)
    frames=pd.read_csv(prepared/'all_forty_frames.csv',dtype=types);frames['time']=pd.to_datetime(frames['time'],errors='raise')
    peaks=pd.read_csv(profiles/'observed_peak_profiles.csv',dtype=types)
    intervals=pd.read_csv(profiles/'all_position_speed_intervals.csv',dtype=types)
    coverage=pd.read_csv(profiles/'speed_band_coverage.csv')
    repeated=pd.read_csv(validation/'within_position_repeatability.csv')
    pairs=pd.read_csv(validation/'paired_feature_values.csv',dtype={'nfl_id':'string'})
    pilot_summary=pd.read_csv(pilot/'validation_summary.csv')
    primary_pilot=pilot_summary.loc[pilot_summary['analysis'].eq('Primary context-adjusted')].iloc[0]
    # The prose is a fixed research draft: fail rather than silently retain stale facts.
    expected={'DB':(102,195),'DL':(93,177),'OL':(95,179),'TE':(34,66),'WR':(94,176)}
    actual=roster.groupby('combine_position').agg(players=('nfl_id','size'),recordings=('recordings','sum'))
    if len(roster)!=418 or len(frames)!=41500 or sum(roster.recordings)!=793 or int(roster.recordings.eq(2).sum())!=375:
        raise ValueError('Cohort changed; update the fixed draft facts before rebuilding')
    if {p:(int(actual.loc[p,'players']),int(actual.loc[p,'recordings'])) for p in POSITIONS}!=expected:
        raise ValueError('Position coverage changed; revise the draft table')
    if int(primary_pilot.players)!=43 or not np.isclose(primary_pilot.baseline_rmse,.31205,atol=.000005):
        raise ValueError('Archived pilot result changed; revise the draft interpretation')
    if int(roster.official_forty_hundredths.isna().sum())!=0:
        raise ValueError('Official-time coverage changed; revise prose')
    raw_coverage=coverage.loc[coverage.method.eq('Raw')].set_index(['combine_position','speed_band'])
    if int(raw_coverage.loc[('DL','8-to-10'),'measured_recordings'])!=92 or int(raw_coverage.loc[('OL','8-to-10'),'measured_recordings'])!=6:
        raise ValueError('Interval coverage changed; revise draft findings')
    for position in ['WR','DB']:
        if not raw_coverage.loc[position,'available_pct'].eq(100).all():
            raise ValueError('WR/DB interval coverage changed; revise draft findings')
    repeat_primary=repeated.loc[repeated.scope.eq('All measured pairs')&repeated.method.eq('7-frame')]
    magnitude=repeat_primary.loc[repeat_primary.feature.eq('peak_magnitude')].set_index('combine_position')
    if not np.isclose(magnitude.loc['WR','spearman'],.256,atol=.0005) or not np.isclose(magnitude.loc['DL','spearman'],.693,atol=.0005):
        raise ValueError('Peak repeatability changed; revise draft findings')
    timing=repeat_primary.loc[repeat_primary.feature.eq('peak_time_recording_start_s')].set_index('combine_position')
    for position in POSITIONS:
        expected_time=.2 if position=='TE' else .1
        if not np.isclose(timing.loc[position,'median_absolute_difference'],expected_time):
            raise ValueError('Timing agreement changed; revise draft findings')
    ref_audit=pd.read_csv(validation/'timing_reference_audit.csv')
    if ref_audit.reference_status.eq('Measured').sum()!=792:
        raise ValueError('Observed reference coverage changed; revise draft findings')
    definition_audit=pd.read_csv(prepared/'acceleration_definition_checks.csv')
    if int(definition_audit.falling_speed_frames.sum())!=230 or int(definition_audit.falling_speed_with_positive_a.sum())!=230:
        raise ValueError('Acceleration-definition diagnostic changed; revise draft findings')
    for column,value in [('expanded_rmse',.31249),('year_mean_rmse',.30023),('conditional_gain_p025',-.01303),('conditional_gain_p975',.01318)]:
        if not np.isclose(primary_pilot[column],value,atol=.000005):
            raise ValueError('Pilot validation changed; revise draft findings')
    wr=roster.loc[roster.combine_position.eq('WR')]
    groups=wr.groupby(['draft_year','official_forty_hundredths']).size().reset_index(name='players')
    choice=groups.loc[groups.players.ge(2)].sort_values(['players','draft_year','official_forty_hundredths'],ascending=[False,True,True]).iloc[0]
    example=wr.loc[wr.draft_year.eq(choice.draft_year)&wr.official_forty_hundredths.eq(choice.official_forty_hundredths)].sort_values('display_name')
    if set(example.display_name)!=set(['Cedric Tillman','Elijah Higgins','Ronnie Bell','Joseph Ngata']):
        raise ValueError('Illustrative group changed; revise prose before generating figures')
    example_ids=set(example.nfl_id)
    example_peaks=peaks.loc[peaks.nfl_id.isin(example_ids)&peaks.window_frames.eq(7)]
    if not np.isclose(example_peaks.peak_time_from_recording_start_s.min(),.3) or not np.isclose(example_peaks.peak_time_from_recording_start_s.max(),.6):
        raise ValueError('Illustrative timing range changed')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'axes.edgecolor':'#bcc7c3','axes.labelcolor':'#263c43','text.color':'#18333f','xtick.color':'#52676d','ytick.color':'#52676d','savefig.facecolor':'white'})
    def save(fig,name):
        fig.savefig(figures/name,dpi=160,bbox_inches='tight');plt.close(fig)
    # Figure 1: choose the whole exact-time group, independently of peak differences/NFL outcomes.
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),constrained_layout=True)
    for (player,color) in zip(example.itertuples(),COLORS):
        subset=frames.loc[frames.nfl_id.eq(player.nfl_id)]
        for j,(key,g) in enumerate(subset.groupby(keys,dropna=False,sort=True)):
            curve=attempt_curve(g,7);g=g.sort_values('time');label=f'{player.display_name} · attempt {g.attempt.iloc[0]}'
            axes[0].plot(curve['t'],curve['speed'],color=color,linestyle=['-','--'][j%2],label=label)
            axes[1].plot(curve['t'],curve['acceleration'],color=color,linestyle=['-','--'][j%2])
            axes[1].scatter(curve['peak_time_from_recording_start_s'],curve['peak_acceleration_raw_per_s'],color=color,
                            marker='o' if curve['peak_location']=='Interior' else '^',s=35)
    axes[0].set(title='Recorded speed',ylabel='Speed (raw units)');axes[1].set(title='Observed signed acceleration',ylabel='Raw speed units / second')
    for ax in axes:ax.set_xlabel('Seconds since recording start — not confirmed launch');ax.grid(alpha=.2)
    axes[0].legend(fontsize=7,loc='lower right');axes[1].axhline(0,color='gray',linewidth=.7)
    fig.suptitle('Same published 4.54 s 40 · Combine WR · 2023\nSeparate attempts; circles = interior peaks, triangles = supported-region boundary peaks')
    save(fig,'01_same_time_profiles.png')
    # Figure 2: common thresholds expose differences in observation support.
    raw=coverage.loc[coverage.method.eq('Raw')]
    bands=['2-to-4','4-to-6','6-to-8','8-to-10']
    matrix=raw.pivot(index='combine_position',columns='speed_band',values='available_pct').reindex(index=POSITIONS,columns=bands)
    fig,ax=plt.subplots(figsize=(8,4.6),constrained_layout=True);im=ax.imshow(matrix,cmap='YlGnBu',vmin=0,vmax=100,aspect='auto')
    for i,p in enumerate(POSITIONS):
        for j,b in enumerate(bands):
            value=matrix.loc[p,b];ax.text(j,i,f'{value:.1f}%',ha='center',va='center',color='white' if value>65 else '#18333f',fontsize=11)
    ax.set(xticks=range(4),xticklabels=[b.replace('-to-',' → ') for b in bands],yticks=range(5),
           yticklabels=[f'{p} (n={expected[p][1]} recordings)' for p in POSITIONS],xlabel='Raw speed band',title='Observed raw-speed interval availability')
    fig.colorbar(im,ax=ax,label='Recordings meeting the measurement rule (%)',shrink=.85)
    save(fig,'02_speed_band_coverage.png')
    # Figure 3: associations within groups, not an athlete ranking across positions.
    peak_pairs=pairs.loc[pairs.feature.eq('peak_magnitude')&pairs.method.eq('7-frame')]
    lo=peak_pairs[['value_a','value_b']].min().min()-.2;hi=peak_pairs[['value_a','value_b']].max().max()+.2
    fig,axes=plt.subplots(1,5,figsize=(15,3.5),sharex=True,sharey=True,constrained_layout=True)
    for ax,p,color in zip(axes,POSITIONS,COLORS):
        subset=peak_pairs.loc[peak_pairs.combine_position.eq(p)]
        ax.scatter(subset.value_a,subset.value_b,s=17,alpha=.65,color=color)
        ax.plot([lo,hi],[lo,hi],color='gray',linestyle='--',linewidth=.9)
        ax.set(title=f'{p} · {len(subset)} players',xlabel='Recording A peak',xlim=(lo,hi),ylim=(lo,hi));ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.15)
    axes[0].set_ylabel('Recording B peak')
    fig.suptitle('Observed peak magnitude repeats unevenly across attempts\n7-frame direct derivative; raw speed units / second')
    save(fig,'03_peak_repeatability.png')
    # Figure 4: reference-dependent agreement, with conditional paired-player intervals.
    primary=repeated.loc[repeated.scope.eq('All measured pairs')&repeated.method.eq('7-frame')]
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),constrained_layout=True)
    for ax,feature,title in zip(axes,['peak_time_recording_start_s','peak_time_speed3_reference_s'],['Recording-start reference','Observed 3-unit speed reference']):
        table=primary.loc[primary.feature.eq(feature)].set_index('combine_position').reindex(POSITIONS)
        ys=np.arange(5);ax.hlines(ys,table.conditional_median_ad_p025,table.conditional_median_ad_p975,color=COLORS[0]);ax.scatter(table.median_absolute_difference,ys,color=COLORS[0],s=28)
        ax.set(yticks=ys,yticklabels=[f'{p} (n={int(n)})' for p,n in zip(POSITIONS,table.paired_players)],title=title,
               xlabel='Median absolute difference between attempts (seconds)',xlim=(0,.25));ax.invert_yaxis();ax.grid(alpha=.2)
    fig.suptitle('Peak-timing agreement depends on the observed reference\nNeither reference confirms physical launch; intervals condition on measured pairs')
    save(fig,'04_timing_agreement.png')
    # Figure 5: preserve the limited null pilot result, never imply all-position NFL validation.
    fig,ax=plt.subplots(figsize=(8,3.8),constrained_layout=True)
    labels=['Draft-year mean\nreference','Context-adjusted\nbaseline','Baseline +\n3–7 interval']
    values=[primary_pilot.year_mean_rmse,primary_pilot.baseline_rmse,primary_pilot.expanded_rmse]
    bars=ax.bar(labels,values,color=['#8c9d9e',COLORS[0],COLORS[1]],width=.55)
    for bar,value in zip(bars,values):ax.text(bar.get_x()+bar.get_width()/2,value+.004,f'{value:.5f}',ha='center',fontsize=10)
    ax.set(ylabel='Held-out RMSE (raw speed units)',ylim=(0,.37),title='Archived WR pilot · 43 players · first-second GO-route speed gain')
    ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    save(fig,'05_wr_pilot_result.png')
    # Offline companion data. Keep per-attempt curves, references, flags, and unsupported intervals.
    interval_lookup={tuple(row[c] for c in keys):{} for _,row in intervals.iterrows()}
    for _,row in intervals.loc[intervals.method.eq('Raw')].iterrows():
        interval_lookup[tuple(row[c] for c in keys)][row.speed_band]={'status':row.status,'duration':row.get('interval_s',np.nan)}
    attempts={};record_keys={str(p):[] for p in roster.nfl_id}
    for key,g in frames.groupby(keys,dropna=False,sort=True):
        first=g.iloc[0];player=str(first.nfl_id);recording_key='|'.join(str(v) for v in key)
        entry={'player':player,'attempt':str(first.attempt),'curves':{},'intervals':interval_lookup[key]}
        for window in [5,7,9]:
            try:
                curve=attempt_curve(g,window)
            except ValueError:
                continue
            entry.setdefault('t',np.round(curve['t'],6));entry.setdefault('speed',np.round(curve['speed'],6))
            entry['curves'][str(window)]={'values':np.round(curve['acceleration'],6),'peakIndex':curve['peak_index'],
                'peakTime':curve['peak_time_from_recording_start_s'],'peakValue':curve['peak_acceleration_raw_per_s'],
                'boundary':curve['peak_location']!='Interior'}
        if 't' not in entry:
            entry['t']=[];entry['speed']=[]
        try:entry['reference3']=speed_reference(np.asarray(entry['t']),np.asarray(entry['speed']))
        except ValueError:entry['reference3']=None
        attempts[recording_key]=entry;record_keys[player].append(recording_key)
    people=[]
    for row in roster.sort_values(['combine_position','display_name']).itertuples():
        people.append({'id':str(row.nfl_id),'name':row.display_name,'position':row.combine_position,
                       'nflPosition':row.nfl_position,'year':str(row.draft_year),'forty':int(row.official_forty_hundredths),
                       'records':record_keys[str(row.nfl_id)]})
    dataset={'people':people,'attempts':attempts,'defaults':{'position':'WR','year':str(choice.draft_year),
        'forty':int(choice.official_forty_hundredths),'players':list(example.nfl_id)},
        'meta':{'players':len(roster),'recordings':len(attempts),'status':'Exploratory research draft'}}
    data_json=json.dumps(clean_json(dataset),ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('</','<\\/')
    markdown=(report/'templates/writeup.md').read_text()
    words=len(markdown.split());figure_count=len(re.findall(r'^!\[',markdown,re.M));table_count=len(re.findall(r'^\|[-:| ]+\|\s*$',markdown,re.M))
    if words>2000 or figure_count+table_count>8:
        raise ValueError('Draft exceeds the working word/visual budget')
    (report/'writeup.md').write_text(markdown)
    body,toc=render_writeup(markdown,report)
    css=(report/'assets/report.css').read_text();js=(report/'assets/report.js').read_text()
    shell=(report/'templates/report.html').read_text()
    generated=datetime.now(timezone.utc).strftime('%Y-%m-%d')
    for placeholder,value in {'__CSS__':css,'__JS__':js,'__REPORT__':body,'__TOC__':toc,
                              '__DATA__':data_json,'__WORD_COUNT__':str(words),'__GENERATED_DATE__':generated}.items():
        shell=shell.replace(placeholder,value)
    if re.search(r'__[A-Z_]+__',shell):raise ValueError('Unresolved report template field')
    (report/'index.html').write_text(shell)
    report_manifest={'schema_version':1,'created_utc':datetime.now(timezone.utc).isoformat(),
        'status':'Research draft; all-position NFL linkage and physical-unit checks incomplete',
        'markdown_word_count':words,'figures':figure_count,'tables':table_count,'players':len(roster),'recordings':len(attempts),
        'example_selection':'Largest same-year exact-time Combine WR group; ties by year and official time',
        'source_manifests':{str(folder.relative_to(root))+'/manifest.json':hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest()
                            for folder in [prepared,profiles,validation,pilot]},'files':{}}
    for target in [report/'writeup.md',report/'index.html',*sorted(figures.glob('*.png'))]:
        report_manifest['files'][str(target.relative_to(report))]={'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    (report/'report_manifest.json').write_text(json.dumps(report_manifest,indent=2)+'\n')
    return report_manifest


if __name__=='__main__':
    result=build_report(Path(__file__).resolve().parents[1])
    print(f"Built report: {result['markdown_word_count']} words, {result['figures']} figures, {result['tables']} table.")
    print(f"Offline comparison: {result['players']} players and {result['recordings']} recordings.")
    print('Open report/index.html. Status: research draft; all-position NFL linkage remains unfinished.')
