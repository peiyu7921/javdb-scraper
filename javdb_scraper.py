import os
import re
import json
import time
import pandas as pd
from tqdm import tqdm
from DrissionPage import ChromiumPage
from CloudflareBypasser import CloudflareBypasser
from subprocess import check_output
from multiprocessing import Pool
# === 设置 ===
SLEEP_TIME = 5  # 每个番号页面等待秒数
CSV_FILENAME = "result.csv"
COOKIE_FILE = "cookies.json"  # 存储Cookie的文件名

def select_folder_dialog():
    if os.name == "nt":
        script = """
        Add-Type -AssemblyName System.Windows.Forms
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $null = $dialog.ShowDialog()
        $dialog.SelectedPath
        """
        try:
            output = check_output(["powershell", "-Command", script], text=True)
            return output.strip()
        except Exception:
            pass
    folder = input("请输入影片文件夹路径：").strip()
    while not os.path.exists(folder):
        folder = input("❌ 文件夹不存在，请重新输入：").strip()
    return folder

def worker(path):
    """独立的worker函数（必须定义在模块层级）"""
    return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

def collect_all_filenames(folder):
    # 先检查路径有效性
    if not os.path.isdir(folder):
        raise ValueError(f"路径不存在或不是目录: {folder}")

    start_time = time.time()
    all_files = set()

    try:
        # 单进程快速扫描（适用于普通规模）
        if sum(len(files) for _, _, files in os.walk(folder)) < 100000:
            for root, _, files in os.walk(folder):
                all_files.update(files)
        else:
            # 多进程扫描（超大规模文件）
            with Pool(processes=min(8, os.cpu_count())) as pool:
                dirs_to_scan = []
                for root, dirs, _ in os.walk(folder):
                    dirs_to_scan.extend(os.path.join(root, d) for d in dirs)
                
                # 添加根目录
                dirs_to_scan.append(folder)
                
                # 分块处理避免内存问题
                chunk_size = max(1, len(dirs_to_scan), (os.cpu_count() * 2))
                results = pool.map(worker, dirs_to_scan, chunksize=chunk_size)
                
                for files in results:
                    all_files.update(files)
                    
        print(f"扫描完成，共 {len(all_files)} 个文件，耗时 {time.time()-start_time:.2f} 秒")
        return all_files
        
    except Exception as e:
        print(f"扫描出错，改用保守方案: {e}")
        # 降级方案
        return set(f for _, _, files in os.walk(folder) for f in files)

def prompt_url():
    url = input("请输入JAVDB页面链接：").strip()
    if "?t=" not in url:
        url += "?t=d"
    return url

def parse_size(text):
    match = re.search(r"([\d.]+)\s*(GB|MB)", text, re.IGNORECASE)
    if not match:
        return 0
    size = float(match[1])
    unit = match[2].upper()
    return size * 1024 if unit == "GB" else size

def is_login_page(page):
    try:
        login_form = page.ele('xpath://form[contains(@action, "user_sessions")]', timeout=3)
        login_text = page.ele('xpath://*[contains(text(), "登入") or contains(text(), "登录")]', timeout=3)
        password_input = page.ele('xpath://input[@type="password"]', timeout=3)
        return sum([bool(login_form), bool(login_text), bool(password_input)]) >= 2
    except:
        return False

def load_cookies(page):
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, 'r') as f:
                cookies = json.load(f)
                page.set.cookies(cookies)
                print("✅ Cookie加载成功")
                return True
        except Exception as e:
            print(f"❌ Cookie加载失败: {e}")
    return False

def save_cookies(page):
    try:
        cookies = page.cookies()
        with open(COOKIE_FILE, 'w') as f:
            json.dump(cookies, f)
        print("✅ Cookie已保存")
        return True
    except Exception as e:
        print(f"❌ 保存Cookie失败: {e}")
        return False

def handle_login(page):
    if is_login_page(page):
        print("\n🔒 检测到需要登录")
        print("1. 请在浏览器中手动完成登录")
        print("2. 登录成功后不要关闭页面")
        print("3. 返回此窗口按回车继续...")
        input()
        if not is_login_page(page):
            save_cookies(page)
            return True
        else:
            print("❌ 登录失败，请重试")
            return False
    return True

def main():
    url = prompt_url()
    folder = select_folder_dialog()
    local_files = collect_all_filenames(folder)
    print(f"📁 本地共发现 {len(local_files)} 个文件\n")
    page = ChromiumPage()
    browser = page.browser
    if not load_cookies(page):
        cf = CloudflareBypasser(page)
        page.get("https://javdb.com/login")
        cf.bypass()
        if not handle_login(page):
            print("❌ 登录失败，程序终止")
            return
    results = []
    while url:
        print(f"\n🌐 正在加载页面：{url}")
        page.get(url)
        items = page.eles("css:div.item a.box")
        if not items:
            print("⚠️ 未找到任何番号，可能页面加载失败")
            break

        for item in tqdm(items, desc="📃 列表进度", unit="部"):
            title = item.attr("title")
            href = item.attr("href")
            code_text = item.ele(".video-title").text
            code = code_text.split(" ")[0]

            print(f"\n📄 抓取番号：{code}：{href}")
            tab = page.new_tab(href)
            browser.activate_tab(tab_id=tab.tab_id)
            try:
                # 等待磁力链接区域加载 - 使用正确的方法
                magnets_container = tab.ele('#magnets-content')
                # 获取所有磁力链接并选择最大的
                magnets = magnets_container.eles('.:item')
                best_magnet = ""
                max_size = 0
                for m in magnets:
                    try:
                        # 从复制按钮获取磁力链接
                        copy_btn = m.ele('.:copy-to-clipboard')
                        magnet = copy_btn.attr('data-clipboard-text')
                        
                        # 获取大小信息
                        size_text = m.ele('.:meta').text
                        size = parse_size(size_text)


                        if not best_magnet:
                            best_magnet = magnet
                        if size > max_size:
                            max_size = size
                            best_magnet = magnet
                        print(f"🔗 磁力链接: {magnet} ({size_text})")
                    except Exception as e:
                        print(f"❌ 解析磁力出错: {e}")
                        continue

                code_btn = tab.ele("css:.panel-block.first-block a.button.copy-to-clipboard")
                code_real = code_btn.attr("data-clipboard-text") if code_btn else code
                matched_file = next((f for f in local_files if code_real in f), "")
                status = "已下载" if matched_file else "未下载"

                results.append({
                    "番号": code_real,
                    "标题": title,
                    "磁力链接": best_magnet or "无磁力链接",
                    "状态": status,
                    "匹配文件名": matched_file,
                })

                print(f"✅ 完成抓取：{code_real}（{status}），等待 {SLEEP_TIME} 秒...")
                time.sleep(SLEEP_TIME)
            except Exception as e:
                print(f"⚠️ 跳过 {code}，出错：{e}")
            finally:
                page.close_tabs(tab)

        next_btn = page.ele('css:nav.pagination a[rel=next]', timeout=2)
        url = next_btn.attr("href") if next_btn else None

    df = pd.DataFrame(results)
    df.to_csv(CSV_FILENAME, index=False, encoding="utf-8-sig")
    print(f"\n✅ 所有任务完成，结果保存为 {CSV_FILENAME}")

if __name__ == "__main__":
    main()
