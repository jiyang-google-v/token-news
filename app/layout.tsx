import type { Metadata } from 'next';
import './globals.css';
export const metadata:Metadata={title:'叙事雷达 · 海外事件观察',description:'从海外事件到可追溯的 Meme 叙事研究。每日采集、证据评分与观察清单。'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="zh-CN"><body>{children}</body></html>}
