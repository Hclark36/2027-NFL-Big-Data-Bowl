"""Known-curve and observation-boundary checks for the core comparison."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

spec=importlib.util.spec_from_file_location('player_comparison',Path(__file__).resolve().parents[1]/'scripts/player_comparison.py')
comparison=importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)

class PlayerComparisonTests(unittest.TestCase):
    def fixture(self):
        t=np.arange(31)*.1
        return t,pd.DataFrame({'time':pd.date_range('2026-01-01',periods=len(t),freq='100ms'),
                               's':1+2*t+.5*t*t})
    def test_known_signed_derivative_and_supported_edges(self):
        t,frames=self.fixture()
        for window in [5,7,9]:
            curve=comparison.attempt_curve(frames,window)
            half=window//2
            np.testing.assert_allclose(curve['acceleration'][half:-half],2+t[half:-half],atol=1e-9)
            self.assertTrue(np.isnan(curve['acceleration'][:half]).all())
            self.assertTrue(np.isnan(curve['acceleration'][-half:]).all())
            self.assertEqual(curve['peak_location'],'End boundary')
    def test_deceleration_is_negative(self):
        t,frames=self.fixture()
        frames['s']=10-2*t
        curve=comparison.attempt_curve(frames,7)
        np.testing.assert_allclose(curve['acceleration'][3:-3],-2,atol=1e-9)
    def test_duplicate_and_missing_observations_rejected(self):
        _,frames=self.fixture()
        frames.loc[4,'time']=frames.loc[3,'time']
        with self.assertRaises(ValueError):comparison.attempt_curve(frames)
        _,frames=self.fixture();frames.loc[4,'s']=np.nan
        with self.assertRaises(ValueError):comparison.attempt_curve(frames)
    def test_speed_reference_requires_observed_bracket_and_coverage(self):
        t=np.arange(21)*.1
        self.assertAlmostEqual(comparison.speed_reference(t,1+3*t),2/3)
        with self.assertRaises(ValueError):comparison.speed_reference(t,4+3*t)

class SpeedIntervalTests(unittest.TestCase):
    def test_interpolated_elapsed_time_and_no_extrapolation(self):
        t=np.arange(21)*.1
        result=comparison.observed_speed_interval(t,5*t,2,6)
        self.assertEqual(result['status'],'Measured')
        self.assertAlmostEqual(result['interval_s'],.8)
        missing=comparison.observed_speed_interval(t,3+5*t,2,6)
        self.assertNotEqual(missing['status'],'Measured')
        self.assertNotIn('interval_s',missing)
        unsupported=comparison.observed_speed_interval(t,2*t,2,8)
        self.assertNotEqual(unsupported['status'],'Measured')
        self.assertNotIn('interval_s',unsupported)

    def test_repeatability_is_separate_within_positions(self):
        records=[]
        for position,a_values,b_values in [('DB',[1,2,3],[3,2,1]),('OL',[10,20,30],[10,20,30])]:
            for i,(a,b) in enumerate(zip(a_values,b_values)):
                for attempt,value in [('1',a),('2',b)]:
                    records.append({'combine_position':position,'draft_year':'2024',
                        'nfl_id':f'{position}{i}','display_name':f'{position}{i}',
                        'method':'Raw','speed_band':'2-to-4','attempt':attempt,
                        'event_id':f'{position}{i}-{attempt}','status':'Measured','interval_s':value})
        pairs,summary=comparison.within_position_repeatability(pd.DataFrame(records),'interval_s',['method','speed_band'])
        self.assertEqual(len(pairs),6)
        values=summary.set_index('combine_position')['pearson']
        self.assertAlmostEqual(values['DB'],-1)
        self.assertAlmostEqual(values['OL'],1)

    def test_unavailable_group_is_reported_with_zero_pairs(self):
        data=pd.DataFrame([{'combine_position':'OL','draft_year':'2024','nfl_id':'x',
                           'display_name':'x','method':'Raw','speed_band':'8-to-10',
                           'attempt':'1','event_id':'x1','status':'No bracketed upper crossing'}])
        pairs,summary=comparison.within_position_repeatability(data,'interval_s',['method','speed_band'])
        self.assertTrue(pairs.empty)
        self.assertEqual(summary.iloc[0]['paired_players'],0)

if __name__=='__main__':unittest.main()
