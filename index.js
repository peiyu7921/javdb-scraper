import fs from "fs";
import path from "path";
import { Builder, By, until } from "selenium-webdriver";
import chrome from "selenium-webdriver/chrome.js";
import inquirer from "inquirer";
import { createObjectCsvWriter } from "csv-writer";
import { exec } from "child_process";
import { promisify } from "util";
import { javdbCookie, sleepTime } from "./config.js";
const execPromise = promisify(exec);

// 🧩 选择文件夹：弹出资源管理器对话框（仅 Windows）
async function selectFolderDialog() {
  if (process.platform === "win32") {
    const script = [
      "Add-Type -AssemblyName System.Windows.Forms",
      "$dialog = New-Object System.Windows.Forms.FolderBrowserDialog",
      "$null = $dialog.ShowDialog()",
      "$dialog.SelectedPath",
    ].join("; ");

    const { stdout } = await execPromise(
      `powershell -NoProfile -Command "${script}"`
    );
    return stdout.trim();
  } else {
    const { folder } = await inquirer.prompt([
      {
        type: "input",
        name: "folder",
        message: "请输入影片文件夹路径（当前平台不支持 GUI 选择）",
        validate: (input) => (fs.existsSync(input) ? true : "文件夹不存在"),
      },
    ]);
    return folder;
  }
}

// 🧩 用户输入
async function promptUser() {
  const { url } = await inquirer.prompt([
    {
      type: "input",
      name: "url",
      message: "请输入 JAVDB 页面链接：",
      validate: (input) =>
        input.startsWith("http") ? true : "请输入有效的 URL",
    },
  ]);

  // 使用 URL 类安全添加参数
  const u = new URL(url);
  u.searchParams.set("t", "d"); // 设置或替换 t=d
  return u.toString();
}

// 🐢 节流函数
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function collectAllFilenames(folder) {
  const fileNames = new Set();

  function walk(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(fullPath);
      } else if (entry.isFile()) {
        fileNames.add(entry.name);
      }
    }
  }

  walk(folder);
  return fileNames;
}

(async function main() {
  const url = await promptUser();
  const folder = await selectFolderDialog();
  const csvWriter = createObjectCsvWriter({
    path: "result.csv",
    header: [
      { id: "code", title: "番号" },
      { id: "title", title: "标题" },
      { id: "magnet", title: "磁力链接" },
      { id: "status", title: "状态" },
      { id: "filename", title: "匹配文件名" },
    ],
  });

  console.time("scan");
  console.log("📁 正在扫描本地影片文件夹...");
  const fileNameSet = collectAllFilenames(folder);
  console.log(`📄 共发现 ${fileNameSet.size} 个文件`);
  console.timeEnd("scan");

  const options = new chrome.Options();
  options.addArguments(
    `--user-data-dir=D:/User Data`,
    `--profile-directory=Default` // 或 Profile 1，Profile 2
  );
  const driver = await new Builder()
    .forBrowser("chrome")
    .setChromeOptions(options)
    .build();

  let results = [];

  try {
    let currentUrl = url;

    while (currentUrl) {
      await driver.get("https://javdb.com"); // 必须先访问一次

      await driver.manage().addCookie({
        name: "_jdb_session",
        value: javdbCookie,
        domain: "javdb.com",
        path: "/",
        secure: true,
        httpOnly: true,
      });
      await driver.get(currentUrl);
      await driver.wait(until.elementLocated(By.css("div.item")), 10000);

      const items = await driver.findElements(By.css("div.item a.box"));

      for (const item of items) {
        const href = await item.getAttribute("href");
        const title = await item.getAttribute("title");
        console.log(`👌开始抓取页面：${href}`);
        await driver.executeScript("window.open(arguments[0]);", href);
        const tabs = await driver.getAllWindowHandles();
        await driver.switchTo().window(tabs[1]);

        await driver.wait(
          until.elementLocated(
            By.css('.copy-to-clipboard[data-clipboard-text^="magnet"]')
          ),
          10000
        );

        // 获取所有磁力项元素
        const magnetItems = await driver.findElements(
          By.css("#magnets-content .item.columns.is-desktop")
        );

        let maxSize = 0;
        let bestMagnet = "";

        for (const item of magnetItems) {
          try {
            const magnetBtn = await item.findElement(
              By.css(".copy-to-clipboard")
            );
            const magnet = await magnetBtn.getAttribute("data-clipboard-text");

            const sizeElem = await item.findElement(
              By.css(".magnet-name .meta")
            );
            const sizeText = await sizeElem.getText(); // 例：6.09GB、700MB

            // 解析大小
            let sizeInMB = 0;
            const sizeMatch = sizeText.match(/([\d.]+)\s*(GB|MB)/i);
            if (sizeMatch) {
              const sizeVal = parseFloat(sizeMatch[1]);
              const unit = sizeMatch[2].toUpperCase();
              sizeInMB = unit === "GB" ? sizeVal * 1024 : sizeVal;
            }

            if (sizeInMB > maxSize) {
              maxSize = sizeInMB;
              bestMagnet = magnet;
            }
          } catch (e) {
            console.warn("⚠️ 跳过无效磁链项:", e.message);
          }
        }

        const codeElem = await driver.findElement(
          By.css(".panel-block.first-block a.button.copy-to-clipboard")
        );
        const code = await codeElem.getAttribute("data-clipboard-text");

        const matchedFile = Array.from(fileNameSet).find((name) =>
          name.includes(code)
        );
        const status = matchedFile ? "已下载" : "未下载";

        results.push({
          code,
          title,
          magnet: bestMagnet || "无磁力链接",
          status,
          filename: matchedFile || "",
        });
        console.log(
          `✅ 已抓取：${code}，状态:${status}，等待 ${sleepTime / 1000} 秒...`
        );
        await sleep(sleepTime);
        await driver.close();
        await driver.switchTo().window(tabs[0]);
      }

      const nextBtn = await driver.findElements(
        By.css("nav.pagination a[rel=next]")
      );
      if (nextBtn.length > 0) {
        currentUrl = await nextBtn[0].getAttribute("href");
        if (!currentUrl.startsWith("http"))
          currentUrl = "https://javdb.com" + currentUrl;
      } else {
        currentUrl = null;
      }
    }

    await csvWriter.writeRecords(results);
    console.log("\n✅ 全部完成！CSV 文件已保存为 result.csv");
  } catch (err) {
    console.error("❌ 出错:", err);
  } finally {
    await driver.quit();
  }
})();
