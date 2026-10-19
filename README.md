# 叙事雷达 Narrative Radar

海外事件中文观察台：来源链接、可解释评分、研究历史与收藏。

现有私人网站：https://narrative-radar.plumbean16.chatgpt.site

## GitHub 迁移状态

源码及 Actions 迁移到 https://github.com/jiyang-google-v/token-news 。Secrets 和实际 Actions 运行尚待配置/验证；不要仅凭源码上传宣称定时任务已运行。原 ChatGPT 每日研究任务要在 GitHub 首次同步读回成功后再停用。

## 每日两次更新

`.github/workflows/update-news.yml` 在 UTC 00:00、12:00（北京时间 08:00、20:00）运行，并支持 Actions 手动运行。GitHub 定时任务可能排队延迟，不能保证整点到达。

在**私有仓库**配置：

- Repository variable `SITE_URL`：上述网站地址，不带末尾斜杠。
- Repository secret `SITE_SERVICE_TOKEN`：由该站点 `get_site` 返回的服务访问令牌；仅保存到 Secrets，不写入源码、Issue、日志或工作流。

工作流通过站点原有私人服务边界写数据，不更改网站访问权限。令牌不可用时任务显式失败，需通过 Sites 获取支持的访问令牌并更新 Secret。不要使用浏览器 Cookie 或把站点公开来规避授权。

## 更新管线

1. 抓取 BBC 国际/科技、Guardian 国际、TechCrunch 的公开 RSS。
2. 限制近72小时、剔除未来或缺失日期、按链接与稳定ID去重。
3. 在 GitHub runner 本地运行 `Helsinki-NLP/opus-mt-en-zh` 将标题和最多400字符的来源摘要翻成中文。首次运行下载模型，后续使用缓存；无需第三方翻译 API Key。机器翻译可能误译姓名及专有名词。
4. 翻译失败不发布英文；成功项保存，失败项在日志中报告并下次重试。
5. POST `/api/events` 写入数据库，再 GET 读回校验。

自动 RSS 初筛评分保持保守：来源8分，传播/Meme/催化未知为0；时效0–15由页面计算。**本任务不包含大模型联网深度研究**，不把规则分伪装成 AI 判断。已有深度评分不会被 RSS 初筛覆盖。若要每日自动完成正文核查和更深入的叙事评分，需要另接有凭据的研究/模型服务。

## 本地运行与验证

```bash
python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r scripts/news-requirements.txt
python -m unittest discover -s tests -p 'test_news.py'
# 从进程环境提供 SITE_URL 和 SITE_SERVICE_TOKEN
python scripts/update_news.py
```

前端使用 Vinext / React / Cloudflare D1。源代码版本迁移到 GitHub；网站托管和数据库仍由当前 Sites 提供，GitHub Actions 更新数据不需重发网站。网站发布继续遵循 `.openai/hosting.json` 的现有项目身份与私有访问策略。

无自动交易、无收益承诺；评分只用于研究排序。
