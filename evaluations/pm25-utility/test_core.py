"""Harness regression tests use synthetic fixtures, not utility evidence."""
import importlib.util
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

spec = importlib.util.spec_from_file_location('core', Path(__file__).with_name('core.py'))
core = None
if Path(__file__).with_name('core.py').exists():
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)

class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(core, 'Evaluation core has not been implemented')

    def fixture(self, n=72):
        times = pd.date_range('2013-03-01', periods=n, freq='h')
        return pd.DataFrame({'year':times.year,'month':times.month,'day':times.day,'hour':times.hour,
                             'PM2.5':np.arange(n,dtype=float),'PM10':np.arange(n,dtype=float)+10,
                             'WSPM':np.ones(n),'station':['Fixture']*n})

    def test_features_are_past_and_target_is_next_exact_hour(self):
        frame, _ = core.prepare(self.fixture(), 'Fixture', '2013-03-01', '2013-03-03T18:00:00')
        row = frame.loc[pd.Timestamp('2013-03-01T06:00:00')]
        self.assertEqual(row[core.FEATURES].tolist(), [6.,5.,16.,1.])
        self.assertEqual(row['target'],7.)
        self.assertTrue(all(frame.index.hour % 6 == 0))

    def test_missing_hour_is_not_bridged_after_drop(self):
        raw=self.fixture().drop(index=5)
        frame,meta=core.prepare(raw,'Fixture','2013-03-01','2013-03-03T18:00:00')
        self.assertNotIn(pd.Timestamp('2013-03-01T06:00:00'),frame.index)
        self.assertGreater(meta['excluded'],0)

    def test_missing_future_label_excluded_and_counted(self):
        raw=self.fixture();raw.loc[7,'PM2.5']=np.nan
        frame,meta=core.prepare(raw,'Fixture','2013-03-01','2013-03-03T18:00:00')
        self.assertNotIn(pd.Timestamp('2013-03-01T06:00:00'),frame.index)
        self.assertEqual(meta['eligible']+meta['excluded'],meta['scheduled'])

    def test_bad_station_rejected(self):
        with self.assertRaises(ValueError):core.prepare(self.fixture(),'Other','2013-03-01','2013-03-03')

    def test_duplicate_timestamps_rejected(self):
        raw=self.fixture();raw=pd.concat([raw,raw.iloc[:1]])
        with self.assertRaises(ValueError):core.prepare(raw,'Fixture','2013-03-01','2013-03-03')

    def test_negative_and_infinite_inputs_excluded(self):
        raw=self.fixture();raw.loc[6,'WSPM']=-1;raw.loc[12,'PM10']=np.inf
        frame,_=core.prepare(raw,'Fixture','2013-03-01','2013-03-03')
        self.assertNotIn(pd.Timestamp('2013-03-01T06:00:00'),frame.index)
        self.assertNotIn(pd.Timestamp('2013-03-01T12:00:00'),frame.index)

    def test_sampling_is_deterministic_sorted_and_unique(self):
        frame,_=core.prepare(self.fixture(24*600),'Fixture','2013-03-01','2014-12-31T18:00:00')
        a=core.select_development(frame);b=core.select_development(frame.sample(frac=1,random_state=13))
        pd.testing.assert_frame_equal(a,b)
        self.assertEqual(len(a),2000)
        self.assertTrue(a.index.is_monotonic_increasing)
        self.assertEqual(len(a.drop_duplicates(subset=core.FEATURES)),2000)

    def test_too_few_development_rows_rejected(self):
        frame,_=core.prepare(self.fixture(),'Fixture','2013-03-01','2013-03-03')
        with self.assertRaises(ValueError):core.select_development(frame)

    def test_nonfinite_prediction_is_not_silently_dropped(self):
        with self.assertRaises(ValueError):core.metrics(np.array([1.,2.]),np.array([1.,np.nan]))

    def test_rmse_and_mae_match_hand_calculation(self):
        m=core.metrics(np.array([0.,2.]),np.array([1.,4.]))
        self.assertAlmostEqual(m['rmse'],np.sqrt(2.5));self.assertAlmostEqual(m['mae'],1.5)

    def test_block_bootstrap_is_paired_and_preserves_ratio(self):
        days=pd.date_range('2016-01-01',periods=366,freq='D')
        cohorts=[{'times':days,'actual':np.zeros(366),'tool':np.ones(366),'baseline':np.ones(366)*2}]*2
        result=core.bootstrap_ratio(cohorts,replicates=200)
        self.assertAlmostEqual(result['ratio'],.5)
        self.assertEqual(result['ci95'],[.5,.5])

    def test_advantage_gate_requires_both_sites(self):
        comparisons=[{'tool_rmse':9,'baseline_rmse':10,'persistence_rmse':10,'tool_mae':7,'baseline_mae':8,'persistence_mae':8},
                     {'tool_rmse':10.1,'baseline_rmse':10,'persistence_rmse':10,'tool_mae':7,'baseline_mae':8,'persistence_mae':8}]
        self.assertFalse(core.advantage_gate(comparisons,.95))
        comparisons[1]['tool_rmse']=9
        self.assertTrue(core.advantage_gate(comparisons,.95))
        self.assertFalse(core.advantage_gate(comparisons,1.01))

    def test_independent_predict_accepts_integer_intercept(self):
        from run_eval import independent_predict
        model={'intercept':0,'terms':[{'coefficient':1.5,'feature':{'op':'raw','a':0}}]}
        np.testing.assert_allclose(independent_predict(model,np.array([[2.],[4.]])),[3.,6.])

    def test_nonnegative_clipping_reports_count(self):
        out,count=core.clip_predictions(np.array([-2.,0.,3.]))
        np.testing.assert_equal(out,[0.,0.,3.]);self.assertEqual(count,1)

if __name__=='__main__':unittest.main(verbosity=2)
