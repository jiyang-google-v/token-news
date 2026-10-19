"""Twice-daily RSS ingestion. Conservative rules; never fabricate social metrics."""
import os,sys,json,re,time,hashlib,html,urllib.request,urllib.error,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
FEEDS=[('BBC 国际','https://feeds.bbci.co.uk/news/world/rss.xml'),('BBC 科技','https://feeds.bbci.co.uk/news/technology/rss.xml'),('卫报国际','https://www.theguardian.com/world/rss'),('TechCrunch','https://techcrunch.com/feed/')]
MODEL='Helsinki-NLP/opus-mt-en-zh'
def chinese(s):return bool(re.search('[\u4e00-\u9fff]',s))
def clean(s):return re.sub(r'\s+',' ',re.sub('<[^>]*>',' ',html.unescape(s or ''))).strip()
def request(url,body=None,token=None):
    headers={'User-Agent':'NarrativeRadar/2.0','Content-Type':'application/json'}
    if token:headers['OAI-Sites-Authorization']='Bearer '+token
    raw=json.dumps(body,ensure_ascii=False).encode() if body is not None else None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,data=raw,headers=headers),timeout=45) as r:return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429,500,502,503,504) or attempt==2:raise RuntimeError('HTTP '+str(e.code)) from None
        except (TimeoutError,urllib.error.URLError):
            if attempt==2:raise RuntimeError('网络访问失败') from None
        time.sleep(2**attempt)
def rss_items(xml,now=None):
    now=now or datetime.now(timezone.utc);out=[]
    for x in ET.fromstring(xml).findall('.//item')[:25]:
        title=clean(x.findtext('title'));url=(x.findtext('link') or '').strip()
        try:date=parsedate_to_datetime(x.findtext('pubDate') or '').astimezone(timezone.utc)
        except (TypeError,ValueError):continue
        age=(now-date).total_seconds()
        if not title or not url.startswith('https://') or not 0<=age<=72*3600:continue
        out.append({'id':'rss-'+hashlib.sha256(url.encode()).hexdigest()[:24],'originalTitle':title[:300],'url':url,'publishedAt':date.isoformat().replace('+00:00','Z'),'description':clean(x.findtext('description'))})
    return out
class Translator:
    def __init__(self):
        import torch
        from transformers import MarianTokenizer,MarianMTModel
        torch.set_num_threads(2)
        self.torch=torch
        self.tokenizer=MarianTokenizer.from_pretrained(MODEL)
        self.model=MarianMTModel.from_pretrained(MODEL).eval()
    def __call__(self,text):
        if chinese(text):return text
        encoded=self.tokenizer('>>cmn_Hans<< '+text,return_tensors='pt',max_length=400,truncation=True)
        with self.torch.inference_mode():result=self.model.generate(**encoded,max_new_tokens=350,num_beams=4)
        output=self.tokenizer.decode(result[0],skip_special_tokens=True).strip()
        if not chinese(output):raise ValueError('翻译未输出中文')
        return output

def category(title):
    if re.search(r'\bAI\b|artificial intelligence|robot|tech|nasa|OpenAI|Anthropic',title,re.I):return 'AI / 科技'
    if re.search(r'\b(trump|macron|president|election|putin|minister)\b',title,re.I):return '政治人物'
    if re.search(r'\b(animal|wildlife|zoo|penguin|seal|tiger)\b',title,re.I) and not re.search('Tiger Shroff',title,re.I):return '动物 / 自然'
    if re.search(r'\b(meme|viral|tiktok|documentary|music)\b',title,re.I):return '网络文化'
    if re.search(r'\b(market|stocks|tariff|economy|GDP|funding)\b',title,re.I):return '商业 / 宏观'
    return '其他'
def make_event(x,name,translate):
    title=translate(x['originalTitle'])[:220]
    # Translate only a bounded excerpt; do not republish full RSS articles.
    excerpt=x['description'][:400]
    summary=(translate(excerpt) if excerpt else '新闻线索：'+title+'。来源未提供摘要。')[:740]
    summary+='（机器翻译；尚未完成正文核查。）'
    if not chinese(title) or not chinese(summary):raise ValueError('中文字段校验失败')
    return {'id':x['id'],'title':title,'originalTitle':x['originalTitle'],'summary':summary,'category':category(x['originalTitle']),'publishedAt':x['publishedAt'],'eventAt':'未核实；报道时间不等于事件发生时间','sources':[{'name':name,'url':x['url']}],'keywords':[],'scores':[8,0,0,0],'reasons':['公开 RSS 来源标题与摘要；未核查正文，规则固定为8分。','没有独立社交传播数据，记0分。','自动采集不主观推测 Meme 潜力，待研究评分。','未核实后续催化，记0分。'],'risks':['英文内容经本地模型机器翻译，人名及专有名词可能有误差','仅来源摘要初筛，不能视为事实核查或买入信号','未执行链上安全、持仓或流动性检查'],'status':'仅标题初筛','tokenEvidence':'未核实任何代币关联；同名不等于官方授权。','tokens':[]}

def main():
    base=os.environ.get('SITE_URL','').rstrip('/');token=os.environ.get('SITE_SERVICE_TOKEN','')
    if not base.startswith('https://') or not token:raise RuntimeError('请配置 SITE_URL 变量及 SITE_SERVICE_TOKEN Secret')
    existing=json.loads(request(base+'/api/events',token=token))['events']
    ids={x['id'] for x in existing};urls={s['url'] for x in existing for s in x['sources']}
    candidates=[];reports=[]
    for name,url in FEEDS:
        try:
            found=rss_items(request(url));fresh=[]
            for x in found:
                if x['id'] in ids or x['url'] in urls:continue
                ids.add(x['id']);urls.add(x['url']);fresh.append(x)
            candidates.extend((x,name) for x in fresh);reports.append({'source':name,'ok':True,'new':len(fresh)})
        except Exception as e:reports.append({'source':name,'ok':False,'error':str(e)[:100]})
    if not any(r['ok'] for r in reports):raise RuntimeError('全部来源失败；未写入虚假成功记录')
    candidates=sorted(candidates,key=lambda pair:pair[0]['publishedAt'],reverse=True)[:100]
    rows=[];failed=0
    if candidates:
        translate=Translator()
        for x,name in candidates:
            try:rows.append(make_event(x,name,translate))
            except Exception:failed+=1
    detail=json.dumps({'runner':'GitHub Actions','schedule':'Asia/Shanghai 08:00 / 20:00','sources':reports,'translationFailures':failed,'scoring':'RSS证据8；传播/Meme/催化未知0；时效由网站动态计算。保留既有深度评分，不以初筛覆盖。'},ensure_ascii=False)
    body={'events':rows,'detail':detail}
    result=json.loads(request(base+'/api/events',body,token))
    if result.get('count')!=len(rows):raise RuntimeError('写入数量不符')
    saved={e['id']:e for e in json.loads(request(base+'/api/events',token=token))['events']}
    if any(e['id'] not in saved or saved[e['id']]['title']!=e['title'] or not chinese(saved[e['id']]['summary']) for e in rows):raise RuntimeError('读回验证失败')
    summary=f'## 叙事雷达更新\n\n新增 {len(rows)} 条中文事件，翻译失败 {failed} 条。\n\n评分为保守初筛；未伪造社交增长数据。\n\n'+detail
    if os.environ.get('GITHUB_STEP_SUMMARY'):Path(os.environ['GITHUB_STEP_SUMMARY']).write_text(summary)
    print(json.dumps({'saved':len(rows),'translationFailures':failed,'sources':reports},ensure_ascii=False))
    if failed or not all(r['ok'] for r in reports):raise RuntimeError('部分采集/翻译失败；已保存成功项，失败项下次重试')
if __name__=='__main__':
    try:main()
    except Exception as e:print('更新失败：'+str(e),file=sys.stderr);sys.exit(1)
