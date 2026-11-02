"""Small synthetic fixtures test audit behavior, not football hypotheses."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

spec = importlib.util.spec_from_file_location('audit_data', Path(__file__).resolve().parents[1] / 'scripts' / 'audit_data.py')
audit_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_data)


class AuditTests(unittest.TestCase):
    def test_full_and_sample_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tracking.csv'
            path.write_text('id,speed\n001,0\n002,\n003,inf\n004,7\n')
            sample = audit_data.profile_csv(path, chunk_size=1, max_rows=2)
            full = audit_data.profile_csv(path, chunk_size=2, max_rows=None)
            self.assertEqual(sample['rows_scanned'], 2)
            self.assertIn('sample', sample['scan_scope'])
            self.assertEqual(sample['columns'][0]['examples'][0], '001')
            self.assertEqual(full['rows_scanned'], 4)
            self.assertEqual(full['scan_scope'], 'full file')
            speed = full['columns'][1]
            self.assertEqual(speed['missing'], 1)
            self.assertEqual(speed['missing_pct'], 25)
            self.assertEqual(speed['nonfinite_numeric'], 1)
            self.assertEqual(speed['numeric_max'], 7)

    def test_tracking_missing_duplicate_and_gap(self):
        data = pd.DataFrame({'id': ['a']*7 + [None], 'rep': ['1']*8,
            't': ['0', '100', '100', '200', '500', None, 'bad', '600'],
            's': ['0', '1', '1', '2', 'inf', '3', '4', '5']}, dtype='string')
        summary, quality = audit_data.tracking_diagnostics(data, ['id', 'rep'], 't', 's', time_scale=.001)
        self.assertEqual(quality['invalid_time_rows'], 2)
        self.assertEqual(quality['missing_group_key_rows'], 1)
        self.assertEqual(quality['excluded_rows'], 3)
        self.assertEqual(quality['rows_in_duplicate_timestamps'], 2)
        self.assertEqual(quality['s_invalid_rows'], 1)
        row = summary.iloc[0]
        self.assertEqual(row.n_frames, 5)
        self.assertAlmostEqual(row.median_step_s, .1)
        self.assertAlmostEqual(row.estimated_hz, 10)
        self.assertAlmostEqual(row.observed_duration_s, .5)
        self.assertEqual(row.gaps_over_1_5x_median, 1)
        self.assertTrue(np.isnan(row.last_observed_speed))

    def test_datetime_and_attempt_separation(self):
        data = pd.DataFrame({'id':['a','a','b','b'], 'rep':['1']*4,
            't':pd.to_datetime(['2026-01-01T00:00:00Z', '2026-01-01T00:00:00.100Z',
                                '2026-01-01T00:00:00Z', None], format='mixed', utc=True)})
        summary, quality = audit_data.tracking_diagnostics(data, ['id','rep'], 't')
        self.assertEqual(len(summary), 2)
        self.assertEqual(quality['invalid_time_rows'], 1)
        self.assertEqual(quality['rows_in_duplicate_timestamps'], 0)
        self.assertAlmostEqual(summary.iloc[0].observed_duration_s, .1, places=5)

    def test_missing_columns_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Columns not found'):
            audit_data.tracking_diagnostics(pd.DataFrame({'t':[0]}), ['player'], 't')


if __name__ == '__main__':
    unittest.main()
