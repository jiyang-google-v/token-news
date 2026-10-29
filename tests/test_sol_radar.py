import sys,time,unittest,importlib.util
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'/'sol_radar'))
import run as runner
class CollectionTests(unittest.TestCase):
 def setUp(self):
  self.now=int(time.time()*1000);self.mint='9195ZJ8dks1534LePW1xDCQVpy4Kdp1s1sA7hr5rpump';self.row={'contractAddress':self.mint,'chainId':'CT_501','protocol':1001,'migrateStatus':1,'migrateTime':self.now-3600000,'holders':50,'price':.00001,'liquidity':10000,'snapshotAt':self.now-300000,'_track':True,'historyCheck':{'source':'Binance USD OHLCV','complete':True,'high':.0001,'from':self.now-3600000,'through':self.now-300000}}
 def test_historical_cap_and_exact_boundaries(self):
  self.assertFalse(runner.excluded(self.row));self.assertTrue(runner.excluded({**self.row,'holders':49}));self.assertTrue(runner.excluded({**self.row,'price':.0008}));self.assertTrue(runner.excluded({**self.row,'_peak':.0008}));self.assertFalse(runner.excluded({**self.row,'price':.000003}));self.assertTrue(runner.excluded({**self.row,'price':.0000029}))
 def test_fast_updates_can_observe_holders_below_50(self):
  def response(url,body=None,headers=None):
   self.assertNotIn('holdersMin',body);return {'code':'000000','data':[{**self.row,'holders':12}]}
  with patch.object(runner.base,'request_json',side_effect=response):d=runner.fast_collect([self.row])
  self.assertEqual(d['rows'][0]['holders'],12);self.assertTrue(runner.excluded(d['rows'][0]))
 def test_incremental_candles_do_not_clear_gap_and_keep_peak(self):
  start=((self.now-300000)//300000)*300000
  def bar(t):return [.00001,.00002,.000009,.000015,1,t,1]
  with patch.object(runner.base,'request_json',return_value={'status':{'error_code':0},'data':[bar(start)]}):h=runner.incremental_history(self.row,self.row)
  self.assertTrue(h['complete']);self.assertEqual(h['high'],.0001)
  old={**self.row,'historyCheck':{**self.row['historyCheck'],'through':self.now-1200000}}
  with patch.object(runner.base,'request_json',return_value={'status':{'error_code':0},'data':[bar(start)]}):h=runner.incremental_history(self.row,old)
  self.assertFalse(h['complete']);self.assertIsNone(h['from']);self.assertEqual(h['high'],.0001)
 def test_fast_failure_does_not_stamp_old_rows_fresh_or_drop_targets(self):
  previous={'rows':[self.row],'lastDiscoveryAt':self.now-60000}
  d={'rows':[],'requests':1,'saturated':0,'rejected':0,'errors':['missing'],'collectedAt':self.now,'source':'Binance Meme Rush'}
  with patch.object(runner,'fast_collect',return_value=d):out=runner.produce(previous)
  self.assertEqual(out['mode'],'priority');self.assertEqual(out['rows'][0]['snapshotAt'],self.row['snapshotAt']);self.assertIn(self.mint,out['focusMints'])
 def test_discovery_due_after_quarter_hour_and_expired_rows_removed(self):
  previous={'rows':[{**self.row,'migrateTime':self.now-31*3600000}],'lastDiscoveryAt':self.now-900001}
  d={'rows':[],'requests':4,'saturated':0,'rejected':0,'errors':[],'collectedAt':self.now,'source':'Binance Meme Rush'}
  with patch.object(runner.base,'collect',return_value=d):out=runner.produce(previous)
  self.assertEqual(out['mode'],'discovery');self.assertEqual(out['rows'],[])
 def test_fifteen_minute_boundary_keeps_five_minute_priority_runs(self):
  for elapsed,expected in [(899999,'priority'),(900000,'discovery')]:
   d={'rows':[],'requests':0,'saturated':0,'rejected':0,'errors':[],'collectedAt':self.now,'source':'Binance Meme Rush'}
   with patch.object(runner.time,'time',return_value=self.now/1000),patch.object(runner.base,'collect',return_value=dict(d)),patch.object(runner,'fast_collect',return_value=dict(d)):
    out=runner.produce({'rows':[],'lastDiscoveryAt':self.now-elapsed})
   self.assertEqual(out['mode'],expected)
if __name__=='__main__':unittest.main()
