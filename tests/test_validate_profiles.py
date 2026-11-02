"""Validate position separation, explicit time references, and missing coverage."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

spec=importlib.util.spec_from_file_location('validate_profiles',Path(__file__).resolve().parents[1]/'scripts/validate_profiles.py')
validation=importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)
KEYS=['draft_year','event_id','nfl_id','entity_type','drill_name','attempt']


def fixtures():
    peaks=[];intervals=[];references=[]
    for attempt,timing,reference in [('1',.2,.5),('2',.4,.6)]:
        meta={'draft_year':'2024','event_id':f'e{attempt}','nfl_id':'p','entity_type':'PLAYER',
              'drill_name':'FORTY_YARD_DASH','attempt':attempt,'display_name':'Player',
              'combine_position':'WR','nfl_position':'WR'}
        peaks.append({**meta,'window_frames':7,'status':'Measured',
                      'peak_acceleration_raw_per_s':6.0,'peak_time_from_recording_start_s':timing,
                      'peak_location':'Interior'})
        intervals.append({**meta,'method':'Raw','speed_band':'2-to-4','status':'Measured','interval_s':.3+timing})
        references.append({**{k:meta[k] for k in KEYS},'reference_time_s':reference,'reference_status':'Measured'})
    roster=pd.DataFrame([{'draft_year':'2024','nfl_id':'p','official_forty_hundredths':440,
                          'recordings':2,'discrepancy_review':False}])
    return pd.DataFrame(peaks),pd.DataFrame(intervals),pd.DataFrame(references),roster


class ProfileValidationTests(unittest.TestCase):
    def test_relative_peak_times_can_be_negative(self):
        p,i,r,roster=fixtures()
        values=validation.profile_feature_table(p,i,r,roster,KEYS)
        relative=values.loc[values.feature.eq('peak_time_speed3_reference_s')]
        np.testing.assert_allclose(relative.value,[-.3,-.2])
        self.assertTrue(relative.status.eq('Measured').all())
        pairs=validation.pair_features(values,KEYS)
        self.assertEqual(len(pairs),4)
        summary=validation.summarize_pairs(values,pairs,bootstraps=0)
        self.assertTrue(summary.loc[summary.metric_kind.eq('timing'),'median_absolute_difference_pct'].isna().all())

    def test_missing_reference_only_disables_that_timing(self):
        p,i,r,roster=fixtures()
        r.loc[0,'reference_status']='Unavailable';r.loc[0,'reference_time_s']=np.nan
        values=validation.profile_feature_table(p,i,r,roster,KEYS)
        relative=values.loc[values.feature.eq('peak_time_speed3_reference_s')]
        self.assertEqual(relative.status.eq('Measured').sum(),1)
        pairs=validation.pair_features(values,KEYS)
        self.assertEqual(len(pairs),3)
        self.assertIn('peak_magnitude',set(pairs.feature))
        self.assertNotIn('peak_time_speed3_reference_s',set(pairs.feature))

    def test_duplicate_estimates_rejected(self):
        p,i,r,roster=fixtures()
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            validation.profile_feature_table(pd.concat([p,p.iloc[[0]]]),i,r,roster,KEYS)

    def test_unavailable_official_times_do_not_create_exact_time_groups(self):
        p,i,r,roster=fixtures()
        values=validation.profile_feature_table(p,i,r,roster,KEYS)
        values['official_forty_hundredths']=np.nan
        _,groups=validation.exact_time_group_spread(values)
        self.assertTrue(groups.empty)

    def test_position_correlations_are_not_pooled(self):
        rows=[]
        for position,va,vb in [('DB',[1,2,3],[3,2,1]),('OL',[10,20,30],[10,20,30])]:
            for j,(a,b) in enumerate(zip(va,vb)):
                for attempt,value in [('1',a),('2',b)]:
                    rows.append({'combine_position':position,'draft_year':'2024','nfl_id':f'{position}{j}',
                        'feature':'speed_interval_2_to_4_s','method':'Raw','metric_kind':'interval','unit':'seconds',
                        'display_name':f'{position}{j}','official_forty_hundredths':450,'recordings':2,
                        'attempt':attempt,'event_id':f'{position}{j}-{attempt}','value':value,
                        'peak_boundary':False,'discrepancy_review':False,'status':'Measured'})
        values=pd.DataFrame(rows)
        pairs=validation.pair_features(values,KEYS)
        summary=validation.summarize_pairs(values,pairs,bootstraps=100)
        correlations=summary.set_index('combine_position').pearson
        self.assertAlmostEqual(correlations['DB'],-1)
        self.assertAlmostEqual(correlations['OL'],1)
        self.assertTrue(summary.conditional_median_ad_p025.isna().all())

if __name__=='__main__':unittest.main()
