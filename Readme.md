# JAVDB Scraper (Selenium + 节流 + 交互输入)

使用 Node.js + Selenium 自动批量爬取 JAVDB 视频信息，20 秒节流处理，自动比对本地影片是否已下载，输出 CSV 文件。

## ✅ 功能

- 支持交互输入 JAVDB 页面链接
- 打开系统文件夹选择器（Windows）选择影片文件夹，搜索文件判断下载状态
- 每部影片间隔爬取（防止封锁）
- 自动爬取最佳磁力链接和番号
- 可翻页抓取
- 输出 CSV 报表

## 🚀 安装依赖

```bash
yarn
node index.js
```
