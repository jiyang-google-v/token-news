import unittest,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from update_news import rss_items,make_event,category
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
if __name__=='__main__':unittest.main()
