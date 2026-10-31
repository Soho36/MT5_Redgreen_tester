"""Causality, volume weighting and file safety tests for the reusable exporter."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from export_vwap_labels import export,feature_labels,minute_features


def raw_minutes(n=35):
    t=pd.DatetimeIndex([pd.Timestamp('2024-01-02 01:00')+pd.Timedelta(minutes=30*i+offset) for i in range(n) for offset in (0,29)])
    close=100+np.arange(len(t))*.25
    return pd.DataFrame({'<DATE>':t.strftime('%Y.%m.%d'),'<TIME>':t.strftime('%H:%M:%S'),
        '<OPEN>':close,'<HIGH>':close+1,'<LOW>':close-1,'<CLOSE>':close,'<VOL>':np.arange(len(t))+1})


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)

    def write(self,raw):
        path=self.folder/'minutes.csv'
        raw.to_csv(path,sep='\t',index=False)
        return path

    def test_real_volume_weighting_and_chunk_boundary(self):
        r=raw_minutes(1)
        r.loc[:,['<OPEN>','<HIGH>','<LOW>','<CLOSE>']]=[[10,10,10,10],[20,20,20,20]]
        r['<VOL>']=[1,9]
        f,n=minute_features(self.write(r),chunksize=1)
        self.assertEqual(n,2)
        self.assertEqual(f.vwap.iloc[0],19)
        self.assertEqual(f.close.iloc[0],20)

    def test_no_future_price_or_volume_changes_earlier_labels(self):
        raw=raw_minutes()
        before,_=minute_features(self.write(raw),chunksize=11)
        raw.loc[60:,['<OPEN>','<HIGH>','<LOW>','<CLOSE>','<VOL>']]*=100
        after,_=minute_features(self.write(raw),chunksize=11)
        pd.testing.assert_frame_equal(feature_labels(before).iloc[:30],feature_labels(after).iloc[:30])

    def test_reset_and_completed_bar_availability(self):
        r=raw_minutes()
        f,_=minute_features(self.write(r))
        self.assertEqual(f.vwap.iloc[0],np.average(r['<CLOSE>'].iloc[:2],weights=r['<VOL>'].iloc[:2]))
        labels=feature_labels(f)
        self.assertTrue((labels.available_epoch-labels.bar_epoch).eq(1800).all())
        self.assertTrue(labels.known.iloc[:20].eq(0).all())
        self.assertTrue(labels.known.iloc[20:].eq(1).all())
        next_day=r.copy()
        next_day['<DATE>']='2024.01.03'
        next_day[['<OPEN>','<HIGH>','<LOW>','<CLOSE>']]+=1000
        both,_=minute_features(self.write(pd.concat([r,next_day],ignore_index=True)))
        self.assertAlmostEqual(both.vwap.iloc[len(f)],f.vwap.iloc[0]+1000)

    def test_invalid_volume_and_cross_chunk_duplicates_rejected(self):
        r=raw_minutes()
        r.loc[1,'<VOL>']=0
        with self.assertRaisesRegex(ValueError,'Volume'):minute_features(self.write(r))
        r=raw_minutes()
        r.loc[1,['<DATE>','<TIME>']]=r.loc[0,['<DATE>','<TIME>']]
        with self.assertRaisesRegex(ValueError,'timestamps'):minute_features(self.write(r),chunksize=1)

    def test_partial_final_bar_unknown_and_date_cutoff(self):
        raw=raw_minutes()
        f,_=minute_features(self.write(raw.iloc[:-1]))
        labels=feature_labels(f)
        self.assertEqual(labels.known.iloc[-1],0)
        self.assertEqual(labels.known.iloc[-2],1)
        next_day=raw.copy()
        next_day['<DATE>']='2024.01.03'
        source=self.write(pd.concat([raw,next_day],ignore_index=True))
        out=self.folder/'cutoff.csv'
        record=export(source,out,mode='minutes',end_before='2024-01-03')
        self.assertEqual(record['rows'],35)
        self.assertLess(pd.read_csv(out,sep='\t').bar_epoch.max(),pd.Timestamp('2024-01-03').timestamp())

    def test_end_before_uses_label_availability_at_midnight(self):
        times=pd.date_range('2024-01-02 12:00',periods=24,freq='30min')
        f=pd.DataFrame(dict(bar_time=times,available_at=times+pd.Timedelta(minutes=30),
            feature_session=times.normalize(),close=100.,vwap=100.,a20=2.,vwap_available=True))
        source=self.folder/'features.csv'
        f.to_csv(source,index=False)
        out=self.folder/'boundary.csv'
        record=export(source,out,end_before='2024-01-03')
        self.assertEqual(record['rows'],23)
        self.assertEqual(record['last_available'],'2024-01-02 23:30:00')

    def test_export_preserves_existing_file(self):
        source=self.write(raw_minutes())
        out=self.folder/'labels.csv'
        record=export(source,out,mode='minutes')
        self.assertTrue(record['known']>0)
        self.assertFalse(record['threshold_embedded'])
        before=out.read_bytes()
        with self.assertRaises(FileExistsError):export(source,out,mode='minutes')
        self.assertEqual(out.read_bytes(),before)
        frame=pd.read_csv(out,sep='\t')
        self.assertTrue(frame.loc[frame.known.eq(0),['vwap','a20']].eq(0).all().all())


if __name__=='__main__':unittest.main()
