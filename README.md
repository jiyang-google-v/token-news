# 叙事雷达 Narrative Radar

海外事件中文观察台：来源链接、可解释评分、历史版本与私人收藏。

- 源码与公开新闻：https://github.com/jiyang-google-v/token-news
- 私人网站：https://narrative-radar.plumbean16.chatgpt.site

## 无自定义 Secret 的数据管线

GitHub Actions 抓取 RSS → runner 本地英中翻译 → 初筛评分 → 保存 `data/news.json` → 提交到 main → 网站读取公开 JSON。

**不需要配置 `SITE_SERVICE_TOKEN`、网站密码或个人 GitHub Token。** 工作流仅使用 GitHub 自动提供的 `GITHUB_TOKEN`（`contents: write`）提交数据。

工作流在北京时间每天 08:00、20:00（UTC cron `0 0,12 * * *`）运行，也支持 `workflow_dispatch`；修改采集脚本或工作流时会自动试运行。GitHub 定时任务可能排队延迟。进入仓库 Actions 查看每次运行的日志和结果。

如果仓库策略禁止 Actions 写入，需在 Settings → Actions → General → Workflow permissions 检查策略。不要因此添加个人访问令牌或公开网站权限。

## 新闻数据与隐私

`data/news.json` 是公开新闻数据，包含中文标题、摘要、来源、评分和运行日志。数据文件不含私人收藏；保存函数会拒绝带 `starred` 的记录。收藏保存在当前私人网站 D1 数据库，支持跨设备。

网站每次刷新读取 GitHub 数据，遇到网络错误时显示部署时的快照并明确提示。新闻更新无需重新部署网站。数据文件内的 `updatedAt` 和 `runs` 表示实际更新时间；配置了 cron 不等于已经成功运行。

## 更新与评分边界

- 来源：BBC 国际/科技、Guardian 国际、TechCrunch 的公开 RSS。
- 限制近72小时、过滤缺失或未来日期，按ID/链接去重。
- 本地 `Helsinki-NLP/opus-mt-en-zh` 机器翻译标题与最多400字符的来源摘要；首次运行下载模型，后续缓存。专有名词可能误译，翻译失败不发布英文。
- RSS 证据8分；传播、Meme 潜力、后续催化缺失时均记0；时效0–15由页面动态计算。保留现有深度研究，不用初筛覆盖。
- 自动任务不包含大模型联网深度研究；没有实测数据时不编造传播增长，不推测同名代币关联。
- 原子保存 JSON；成功项提交，部分失败项会使工作流报告失败并在下次重试。全部来源失败则保留原数据。
- 数据提交冲突时直接失败，不强制覆盖他人提交。

## 本地采集

```bash
python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r scripts/news-requirements.txt
python -m unittest discover -s tests -p 'test_news.py'
python scripts/update_news.py
```

新闻文件是唯一更新目标，不需要任何站点凭据。网站托管保留现有 Sites 与 D1；源码在 GitHub。前端为 Vinext / React。保留 `.openai/hosting.json` 的项目身份和网站私有访问策略。

无自动交易；评分只用于研究排序，不代表上涨概率。
