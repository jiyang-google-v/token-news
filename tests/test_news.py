import unittest,sys,tempfile,json
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from update_news import rss_items,make_event,category,merge_feed,save_feed,read_feed
class NewsTests(unittest.TestCase):
 def test_reject_stale_future_and_missing_dates(self):
  def item(date):return f'<item><title>AI &amp; robots</title><link>https://example.com/a</link><pubDate>{date}</pubDate></item>'
  xml='<rss><channel>'+''.join(item(d) for d in ['Mon, 19 Oct 2026 00:00:00 GMT','Mon, 12 Oct 2026 00:00:00 GMT','Tue, 20 Oct 2026 00:00:00 GMT','bad'])+'</channel></rss>'
  rows=rss_items(xml.encode(),datetime(2026,10,19,12,tzinfo=timezone.utc))
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]['originalTitle'],'AI & robots')
 def test_translation_failure_never_publishes_english(self):
  x={'id':'rss-a','originalTitle':'AI robots','description':'New robots','url':'https://example.com/a','publishedAt':'2026-10-19T00:00:00Z'}
  with self.assertRaises(ValueError):make_event(x,'BBC',lambda x:x)
  event=make_event(x,'BBC',lambda x:'机器人新闻')
  self.assertEqual(event['scores'],[8,0,0,0]);self.assertEqual(event['tokens'],[])
 def test_person_not_classified_as_animal(self):
  self.assertNotEqual(category('Tiger Shroff survives shooting'),'动物 / 自然')
class PersistenceTests(unittest.TestCase):
 def test_curated_score_survives_duplicate(self):
  old={'id':'one','title':'原有研究','summary':'中文摘要','scores':[23,10,12,6]}
  feed={'events':[old],'history':[],'runs':[]}
  out=merge_feed(feed,[{**old,'scores':[8,0,0,0]}],[],0,'2026-10-19T00:00:00Z')
  self.assertEqual(out['events'][0]['scores'],old['scores'])
 def test_no_private_favorites_can_be_exported(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'news.json';p.write_text('original')
   with self.assertRaises(ValueError):save_feed(p,{'events':[{'title':'中文标题','summary':'摘要','starred':1}]})
   self.assertEqual(p.read_text(),'original')
 def test_atomic_round_trip_preserves_history(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'news.json'
   out=merge_feed({'events':[],'history':[],'runs':[]},[{'id':'new','title':'中文标题','summary':'中文摘要'}],[],0,'2026-10-19T00:00:00Z')
   save_feed(p,out);self.assertEqual(read_feed(p)['history'][0]['eventId'],'new')
if __name__=='__main__':unittest.main()
