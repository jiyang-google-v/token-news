import { z } from 'zod';
const url=z.string().url().refine(v=>new URL(v).protocol==='https:','Only HTTPS sources');
export const categories=['全部','政治人物','AI / 科技','动物 / 自然','网络文化','商业 / 宏观','其他'];
export const labels=['来源证据','传播证据','Meme 可塑性','后续催化'];
export const maxima=[25,25,20,15];
export const eventSchema=z.object({id:z.string().regex(/^[a-zA-Z0-9_-]{1,100}$/),title:z.string().min(3).max(220).regex(/[\u4e00-\u9fff]/,'标题必须包含中文'),originalTitle:z.string().max(300).default(''),summary:z.string().max(900).regex(/[\u4e00-\u9fff]/,'摘要必须包含中文'),category:z.enum(['政治人物','AI / 科技','动物 / 自然','网络文化','商业 / 宏观','其他']),publishedAt:z.string().datetime().nullable(),eventAt:z.string().max(100).default('未核实'),sources:z.array(z.object({name:z.string().max(80),url,publishedAt:z.string().max(80).optional()})).min(1).max(12),keywords:z.array(z.string().max(60)).max(12),scores:z.tuple([z.number().int().min(0).max(25),z.number().int().min(0).max(25),z.number().int().min(0).max(20),z.number().int().min(0).max(15)]),reasons:z.array(z.string().max(300)).length(4),risks:z.array(z.string().max(300)).max(10),status:z.enum(['已核查','待核实','仅标题初筛']),tokenEvidence:z.string().max(500).default('未核实任何代币关联；同名不代表官方。'),tokens:z.array(z.object({name:z.string().max(80),address:z.string().regex(/^[1-9A-HJ-NP-Za-km-z]{32,44}$/),evidenceUrl:url})).max(10).default([])});
export type EventData=z.infer<typeof eventSchema> & {firstSeen?:string,updatedAt?:string,starred?:number};
export function freshness(p:string|null,now=Date.now()){if(!p)return 0;let h=(now-Date.parse(p))/3600000;if(h<0)return 0;return h<=6?15:h<=24?12:h<=48?8:h<=72?4:0;}
export function score(e:EventData){return e.scores.reduce((a,b)=>a+b,0)+freshness(e.publishedAt);}
