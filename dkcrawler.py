from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
import pandas as pd
from pandas.errors import EmptyDataError, ParserError
import concurrent.futures
import traceback
import time
import random
import os
import re


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


def concat_data(in_files, out_path):
    dfs = []
    for file in in_files:
        try:
            try:
                df = pd.read_csv(file)
            except ParserError:
                df = pd.read_excel(file)
            dfs.append(df)
        except EmptyDataError:
            print(f'"{file}" is empty')
    combined_data = pd.concat(dfs, join='inner', ignore_index=True)
    combined_data.drop_duplicates(inplace=True)
    combined_data.to_excel(out_path, index=False, encoding='utf-8-sig')


def get_latest_file(_dir):
    files = get_file_list(_dir)
    files = [f for f in files if not re.search(r'_\d+$', os.path.splitext(f)[0])]
    latest_file = max(files, key=os.path.getctime)
    return latest_file


class DKCrawler:
    selectors = {
        'per-page-selector': '[data-testid="per-page-selector"] > div.MuiSelect-root',
        'per-page-100': '[data-testid="per-page-100"]',
        'in-stock': '[data-testid="filter--2-option-5"] input[type="checkbox"]',
        'normally-stocking': '[data-testid="filter--2-option-9"] input[type="checkbox"]',
        'apply-all': '[data-testid="apply-all-button"]',
        'popup-trigger': '[data-testid="download-table-popup-trigger-button"]',
        'download': '[data-testid="download-table-button"]',
        'next-page': '[data-testid="btn-next-page"]',
        'max-page': '[data-testid="per-page-selector-container"] > div:last-child > span',
        'active-parts': '[data-testid="filter-1989-option-0"]',
    }

    def __init__(self, url, driver_path, download_dir):
        self.url = url
        self.driver_path = driver_path
        self.product_category = self.url.split('/')[-2].replace('-', '_')
        self.download_dir = os.path.join(download_dir, self.product_category)
        os.makedirs(self.download_dir, exist_ok=True)
        self.browser = self._setup_browser()

    def _setup_browser(self):
        profile = webdriver.FirefoxProfile()
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference("browser.download.manager.showWhenStarting", False)

        profile.set_preference("browser.download.dir", self.download_dir)
        profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "text/csv")
        browser = webdriver.Firefox(executable_path=self.driver_path, firefox_profile=profile)
        browser.set_page_load_timeout(600)
        return browser

    def _close(self):
        rand_delay(5, 10)
        self.browser.close()
        self.browser.quit()

    def _set_page_size_100(self):
        self.browser.find_element_by_css_selector(self.selectors['per-page-selector']).click()
        rand_delay(1, 3)
        self.browser.find_element_by_css_selector(self.selectors['per-page-100']).click()
        rand_delay(1, 3)

    def _select_in_stock(self):
        in_stock = self.browser.find_element_by_css_selector(self.selectors['in-stock'])
        in_stock.click()
        rand_delay(1, 3)

        normally_stocking = self.browser.find_element_by_css_selector(self.selectors['normally-stocking'])
        normally_stocking.click()
        rand_delay(1, 3)

        apply_all = self.browser.find_element_by_css_selector(self.selectors['apply-all'])
        apply_all.click()
        rand_delay(1, 3)

    def _select_active(self):
        active_parts = self.browser.find_element_by_css_selector(self.selectors['active_parts'])
        active_parts.click()
        rand_delay(1, 3)

    def _get_max_page(self):
        max_page = self.browser.find_element_by_css_selector(self.selectors['max-page']).text
        max_page = int(max_page.split('/')[-1])
        return max_page

    def _click_download(self):
        popup_trigger = self.browser.find_element_by_css_selector(self.selectors['popup-trigger'])
        popup_trigger.click()
        rand_delay(1, 3)
        download_table_button = self.browser.find_element_by_css_selector(self.selectors['download'])
        download_table_button.click()
        rand_delay(5, 10)

    def _click_next_page(self):
        btn_next_page = self.browser.find_element_by_css_selector(self.selectors['next-page'])
        btn_next_page.click()
        rand_delay(5, 10)

    def _rename_file(self, cur_page):
        try:
            downloaded_file = get_latest_file(self.download_dir)
            print(f'Downloaded file: "{downloaded_file}"')
            renamed_file = os.path.join(self.download_dir, f'{self.product_category}_{cur_page}.csv')
            os.rename(downloaded_file, renamed_file)
            print(f'Renamed file: "{downloaded_file}" -> "{renamed_file}"')
        except ValueError:
            pass

    def _del_prev_files(self):
        files = get_file_list(self.download_dir)
        for f in files:
            os.remove(f)

    def crawl(self):
        self._del_prev_files()
        self.browser.get(self.url)
        self._set_page_size_100()
        self._select_in_stock()
        max_page = self._get_max_page()

        try:
            cur_page = 1
            while True:
                self._click_download()
                self._rename_file(cur_page)
                cur_page += 1

                if cur_page <= max_page:
                    self._click_next_page()
                else:
                    break
        except NoSuchElementException:
            traceback.print_exc()
        finally:
            in_files = get_file_list(self.download_dir)
            out_path = os.path.join(self.download_dir, f'{self.product_category}_all.xlsx')
            concat_data(in_files, out_path)
            self._close()


def run_crawler(url, driver_path, download_dir):
    crawler = DKCrawler(url, driver_path, download_dir)
    crawler.crawl()


def run_crawlers(urls, driver_path, download_dir, n_workers):
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(n_workers, len(urls))) as executor:
        for url in urls:
            executor.submit(run_crawler, url, driver_path, download_dir)
    in_files = get_file_list(download_dir, suffix='all.xlsx')
    out_path = os.path.join(download_dir, 'concat.xlsx')
    concat_data(in_files, out_path)


def main():
    driver_path = 'geckodriver.exe'
    download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')

    # urls1 = ['https://www.digikey.com/en/products/filter/rectangular-connectors-headers-receptacles-female-sockets/315',
    #          'https://www.digikey.com/en/products/filter/rectangular-connectors-board-spacers-stackers-board-to-board/400',
    #          'https://www.digikey.com/en/products/filter/terminal-blocks-headers-plugs-and-sockets/370',
    #          'https://www.digikey.com/en/products/filter/rectangular-connectors-headers-male-pins/314']

    urls2 = ['https://www.digikey.com/en/products/filter/d-shaped-centronics-cables/466',
             'https://www.digikey.com/en/products/filter/barrel-power-cables/464']

    run_crawlers(urls2, driver_path, download_dir, n_workers=4)


if __name__ == '__main__':
    main()
