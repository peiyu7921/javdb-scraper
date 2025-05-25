# JAVDB 磁力信息抓取器

📥 本脚本基于 Python 和 [DrissionPage](https://github.com/CliftonYan/DrissionPage) 实现，支持自动登录 JAVDB 并抓取视频页面中的番号、标题、磁力链接，结合本地已有视频文件判断是否已下载，并导出为 CSV 文件。

## ✨ 功能特色

- 自动打开 Chromium 浏览器，模拟人工访问
- 自动识别登录页并支持手动登录 + Cookie 保存
- 自动识别每部影片的最大磁力链接
- 支持翻页抓取所有番号页面信息
- 判断本地是否已下载对应影片（基于文件名）
- 结果导出为 `result.csv` 文件
- 支持绕过 Cloudflare 验证（基于 [CloudflareBypasser](https://github.com/sarperavci/CloudflareBypassForScraping)）

## 📦 环境依赖

- Python 3.8+
- [DrissionPage](https://github.com/CliftonYan/DrissionPage)
- [CloudflareBypasser](https://github.com/sarperavci/CloudflareBypassForScraping)
- 其他依赖包：

```bash
pip install beautifulsoup4 tqdm pandas
```

## ⚙️ 使用方法

双击 setup_and_run.bat

## 🧠 使用说明

1. 启动脚本后，输入要抓取的 JAVDB 页面链接（例如 `https://javdb.com/v/X1234` 或分类页）。
2. 选择本地影片文件夹（用于判断是否已下载）。
3. 如果首次运行，会自动打开登录页面：
   - 手动在浏览器中完成登录
   - 回到终端窗口按回车继续
   - 脚本将自动保存 Cookie
4. 程序开始抓取信息，包括番号、标题、磁力链接、文件匹配状态。
5. 程序会自动翻页，抓取所有可见的番号。
6. 最终结果保存为 `result.csv`，支持 Excel 打开。

## 📁 文件说明

| 文件名             | 描述                     |
| ------------------ | ------------------------ |
| `start.bat`        | 快捷运行脚本             |
| `javdb_scraper.py` | 主程序脚本               |
| `cookies.json`     | 登录 Cookie 存储文件     |
| `result.csv`       | 抓取结果输出（自动生成） |

## 📝 配置项

你可以在 `javdb_scraper.py` 顶部修改以下常量：

```python
SLEEP_TIME = 5  # 每部番号页面抓取后的等待时间（秒）
CSV_FILENAME = "result.csv"  # 导出文件名
COOKIE_FILE = "cookies.json"  # Cookie 文件名
```

## ⚠️ 注意事项

- 脚本模拟浏览器行为，若长时间运行，建议勿做其他操作以防被登出。
- 若 Cookie 失效，请删除 `cookies.json` 重新运行程序登录。
- 本脚本仅用于学习交流，请勿用于非法用途。
