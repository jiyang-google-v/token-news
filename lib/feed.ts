import seed from '@/data/news.json';
import { eventSchema } from './model';
export const FEED_URL='https://raw.githubusercontent.com/jiyang-google-v/token-news/main/data/news.json';
export type Feed={schemaVersion:number,updatedAt:string,events:any[],runs:any[],history:any[]};
export function validateFeed(v:any):Feed{if(v?.schemaVersion!==2||!Array.isArray(v.events)||!Array.isArray(v.runs)||!Array.isArray(v.history)||!Number.isFinite(Date.parse(v.updatedAt)))throw Error('新闻数据格式无效');for(const e of v.events)eventSchema.parse(e);return v;}
export async function getFeed(){try{const r=await fetch(FEED_URL,{cache:'no-store',signal:AbortSignal.timeout(12000)});if(!r.ok)throw Error('HTTP '+r.status);return {data:validateFeed(await r.json()),status:'live',warning:null};}catch{return {data:validateFeed(seed),status:'fallback',warning:'暂时无法读取 GitHub 最新数据，正在显示部署时的快照。请稍后刷新。'};}}
