# ArxivModuliDigest

**版本：v1.3**

每周从 arXiv 拉取近期代数几何论文，筛选与模空间相关的文章，并生成中文 Markdown 周报。项目只依赖 Python 标准库，不接入模型或 API 密钥。

## 运行

需要 Python 3.10 或更新版本，以及网络连接。

在项目目录打开 PowerShell：

```powershell
python .\arxiv_digest.py
```

默认检查最近 7 天的 `math.AG` 新论文，将报告写入 `reports\YYYY-MM-DD.md`，并将已处理的 arXiv ID 保存在 `data\seen.json`。报告里的概述是论文原摘要前两句的节选，不是模型生成的翻译或总结。

运行抓取脚本后还会写入 `papers.json`，供本地网页看板读取。双击 `start_dashboard.bat` 即可启动网页看板。也可以在 PowerShell 中运行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\start_dashboard.ps1
```

启动脚本会先刷新论文数据，再在本机开启 HTTP 服务并打开浏览器。页面支持白天/夜晚双模式，标题、作者和摘要搜索，按 arXiv 分类、发布日期、阅读状态筛选，自定义关注关键词，收藏论文和记录阅读状态。日期范围默认从当前数据最早论文到今天。论文卡片可手动勾选，之后只导出所选论文的 BibTeX 或 CSV。主题、收藏、阅读状态和自定义关键词保存在当前浏览器的 localStorage。论文卡片显示首次提交日期和最近更新日期，并提供 PDF 首页快照、论文页面和 PDF 下载链接。默认地址为 `http://127.0.0.1:8765/`；端口占用时自动使用 `8766`。

抓取按每页 100 条向 arXiv API 分页，默认最多读取 1000 篇候选论文；可用 `--max-results` 调整上限。每篇论文数据包含 `published`（首次提交日期）和 `updated`（最近更新时间）。

常用参数：

```powershell
# 每天手动运行时扩大窗口；ID 去重避免重复出现在报告
python .\arxiv_digest.py --days 14

# 包含已经处理过的论文
python .\arxiv_digest.py --include-seen

# 扩展到相邻分类
python .\arxiv_digest.py --categories math.AG,math.DG

# 指定报告位置
python .\arxiv_digest.py --output .\reports\weekly.md
```

## 本地每周自动运行

Windows 任务计划程序中新建每周任务，程序填写 `python`，参数填写脚本绝对路径，例如：

```text
D:\Codex\project\ArxivModuliDigest\arxiv_digest.py
```

“起始于”填写项目目录，这样报告和去重记录会保存在项目内。

## GitHub 托管与自动更新

仓库包含 `.github/workflows/update-digest.yml`：每天 12:17 UTC 自动抓取最近 7 天论文，更新 `papers.json`、去重记录，并覆盖 `reports/latest.md`。也可以在 GitHub 仓库的 **Actions → Update arXiv digest → Run workflow** 手动运行。

发布看板时，在仓库 **Settings → Pages → Build and deployment** 选择 **Deploy from a branch**，分支选 `main`、目录选 `/(root)` 并保存。等待 Pages 部署后，访问 `https://<你的GitHub用户名>.github.io/<仓库名>/`。仓库必须是公开仓库才能使用 GitHub Free 的公开 Pages。

首次上传的基本命令（先在 GitHub 网页创建一个空仓库，不要勾选初始化 README、License 或 `.gitignore`）：

```powershell
cd D:\Codex\project\ArxivModuliDigest
git init -b main
git add .
git commit -m "Initial ArxivModuliDigest v1.3"
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

命令中的 `<你的用户名>` 和 `<仓库名>` 必须替换成实际值，并移除尖括号。例如用户名为 `alice`、仓库名为 `ArxivModuliDigest` 时，远端地址是 `https://github.com/alice/ArxivModuliDigest.git`。GitHub 首次认证时按提示在浏览器登录。

若启用 Actions 后定时任务没有权限推送，前往 **Settings → Actions → General → Workflow permissions**，选择 **Read and write permissions** 并保存。浏览器中的收藏、阅读状态和自定义关键词使用 localStorage，只保存在当前浏览器，不会同步进 GitHub 仓库。

## 筛选说明

脚本按所选分类和分页上限读取 arXiv 记录，再筛出指定日期范围内的论文，并按标题和摘要里的模空间相关词打分。关键词规则可以在 `DEFAULT_TERMS` 中调整。关键词筛选会有漏检和误检，报告保留原摘要节选和 arXiv 链接，便于核对。
