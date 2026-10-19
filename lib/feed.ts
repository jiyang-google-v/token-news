import seed from '@/data/news.json';
import { eventSchema } from './model';
export const FEED_URL='https://raw.githubusercontent.com/jiyang-google-v/token-news/main/data/news.json';
export type Feed={schemaVersion:number,updatedAt:string,events:any[],runs:any[],history:any[]};
export function validateFeed(v:any):Feed{if(v?.schemaVersion!==2||!Array.isArray(v.events)||!Array.isArray(v.runs)||!Array.isArray(v.history)||!Number.isFinite(Date.parse(v.updatedAt)))throw Error('新闻数据格式无效');for(const e of v.events)eventSchema.parse(e);return v;}
let cached:{data:Feed,expires:number}|undefined;
export async function getFeed(){if(cached&&cached.expires>Date.now())return {data:cached.data,status:'live',warning:null};try{const r=await fetch(FEED_URL,{cache:'no-store',signal:AbortSignal.timeout(12000)});if(!r.ok)throw Error('HTTP '+r.status);let payload:any=await r.json();if(payload.encoding==='base64'&&typeof payload.content==='string'){const bytes=Uint8Array.from(atob(payload.content.replace(/\s/g,'')),c=>c.charCodeAt(0));payload=JSON.parse(new TextDecoder().decode(bytes));}const data=validateFeed(payload);cached={data,expires:Date.now()+60000};return {data,status:'live',warning:null};}catch(error){return {data:cached?.data||validateFeed(seed),status:'fallback',warning:'暂时无法读取 GitHub 最新数据（'+(error instanceof Error?error.message.slice(0,180):'网络错误')+'），正在显示最近的可用快照。请稍后刷新。'};}}
