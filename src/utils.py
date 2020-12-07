import time
import random
import os
import re
import pandas as pd
from pandas.errors import EmptyDataError, ParserError
from selenium.webdriver.firefox.options import Options
from selenium import webdriver


def rand_delay(low, high):
    time.sleep(random.uniform(low, high))


def get_file_list(_dir, suffix=None):
    files = []
    for dirpath, dirnames, filenames in os.walk(_dir):
        for filename in filenames:
            files.append(os.path.join(dirpath, filename))

    if suffix:
        files = [f for f in files if f.endswith(suffix)]
    return files


def get_latest_file(root):
    files = get_file_list(root)
    files = [f for f in files if not re.search(r'_\d+$', os.path.splitext(f)[0])]
    latest_file = max(files, key=os.path.getctime)
    return latest_file


def get_latest_dir_index(root):
    dirs = os.listdir(root)
    dirs = [os.path.join(root, _dir) for _dir in dirs]
    try:
        latest_dir = max(dirs, key=os.path.getctime)
        latest_index = int(latest_dir.split('\\')[-1].replace('session', ''))
        return latest_index
    except ValueError:
        return 0


def concat_data(in_files):
    dfs = []
    for file in in_files:
        try:
            try:
                df = pd.read_csv(file)
            except (ParserError, UnicodeDecodeError):
                df = pd.read_excel(file, engine='openpyxl')
            dfs.append(df)
        except EmptyDataError:
            print(f'"{file}" is empty')
    combined_data = pd.concat(dfs, join='inner', ignore_index=True)
    combined_data.drop_duplicates(inplace=True)
    return combined_data


def setup_browser(driver_path, download_dir=None):
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.download.folderList", 2)
    profile.set_preference("browser.download.manager.showWhenStarting", False)

    if download_dir:
        profile.set_preference("browser.download.dir", download_dir)
    profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "text/csv")

    options = Options()
    options.headless = True
    browser = webdriver.Firefox(executable_path=driver_path, firefox_profile=profile, options=options)
    browser.set_window_size(1920, 1080)
    browser.set_page_load_timeout(600)
    return browser
