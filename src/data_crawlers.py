from src.base_crawler import BaseCrawler
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.utils import rand_delay, get_file_list, get_latest_file, concat_data
import concurrent.futures
import random
import traceback
import os
import pandas as pd
import logging


class DataCrawler(BaseCrawler):
    selectors = {
        'cookie_ok': 'div.cookie-wrapper a.secondary.button',
        'per-page-selector': '[data-testid="per-page-selector"] > div.MuiSelect-root',
        'per-page-100': '[data-testid="per-page-100"]',
        'in-stock': '[data-testid="filter--2-option-5"]',
        'normally-stocking': '[data-testid="filter--2-option-9"] input[type="checkbox"]',
        'apply-all': '[data-testid="apply-all-button"]',
        'popup-trigger': '[data-testid="download-table-popup-trigger-button"]',
        'download': '[data-testid="download-table-button"]',
        'cur-page': '[data-testid="pagination-container"] > button[disabled]',
        'next-page': '[data-testid="btn-next-page"]',
        'next-page-alt': '[data-testid="pagination-container"] > button[disabled] + button',
        'max-page': '[data-testid="per-page-selector-container"] > div:last-child > span',
        'active-parts': '[data-testid="filter-1989-option-0"]',
        'digikey.com': '[track-data="Choose Your Location – Stay on US Site"] > span',
        'msg_close': 'a.header-shipping-msg-close',
        'btn-first-page': '[data-testid="btn-first-page"]',
        'dkpn-sort-asc': 'button[data-testid="sort--104-asc"] > svg',
    }

    def __init__(self, driver_path, start_url, download_dir, headless):
        super().__init__(driver_path, start_url, download_dir, headless)
        url_split = self.start_url.split('/')
        self.subcategory = url_split[-2].replace('-', '_')
        self.product_id = url_split[-1]
        self.download_dir = os.path.join(download_dir, f'{self.subcategory}_{self.product_id}')
        self.setup_crawler()
        self.downloaded_pages = []
        self.MAX_WAIT = 20

        os.makedirs(self.download_dir, exist_ok=True)
        self.del_prev_files()
        self.log_file_path = os.path.join(self.download_dir, f'{self.subcategory}.log')
        self.create_log_file()
        self.logger = self.set_up_logger()

    def create_log_file(self):
        with open(self.log_file_path, 'w+') as f:
            f.write('')

    def set_up_logger(self):
        formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s')
        logger = logging.getLogger(self.subcategory)
        if len(logger.handlers) > 0:
            logger.handlers.clear()
        logger.setLevel(logging.INFO)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        logger.addHandler(console)
        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

    def del_prev_files(self):
        files = get_file_list(self.download_dir)
        for f in files:
            os.remove(f)

    def click_element(self, keyword):
        try:
            self.crawler.find_element_by_css_selector(self.selectors[keyword]).click()
        except NoSuchElementException:
            pass
        rand_delay(1, 3)

    def get_max_page(self):
        rand_delay(15, 20)
        max_page = self.crawler.find_element_by_css_selector(self.selectors['max-page']).text
        max_page = int(max_page.split('/')[-1])
        return max_page

    def click_download(self):
        popup_trigger = self.element_to_be_clickable(self.selectors['popup-trigger'])
        popup_trigger.click()
        download_table_button = self.element_to_be_clickable(self.selectors['download'])
        download_table_button.click()
        rand_delay(8, 9)

    def click_next_page(self):
        btn_next_pages = self.crawler.find_elements_by_css_selector(self.selectors['next-page'])
        btn_next_pages += self.crawler.find_elements_by_css_selector(self.selectors['next-page-alt'])
        for btn_next_page in btn_next_pages:
            try:
                btn_next_page.click()
                break
            except ElementClickInterceptedException:
                pass
        rand_delay(5, 8)

    def rename_file(self, cur_page):
        try:
            downloaded_file = get_latest_file(self.download_dir)
            renamed_file = os.path.join(self.download_dir, f'{self.subcategory}_{cur_page}.csv')
            os.rename(downloaded_file, renamed_file)

            status = f'Renamed file: \n"{downloaded_file}" \n-> \n"{renamed_file}"'
            self.logger.info(status)
        except ValueError:
            pass

    def get_cur_page(self):
        rand_delay(1, 2)
        cur_page = int(self.crawler.find_element_by_css_selector(self.selectors['cur-page']).get_attribute('value'))
        return cur_page

    def element_to_be_clickable(self, css):
        element = WebDriverWait(self.crawler, self.MAX_WAIT).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, css))
        )
        return element

    def dkpn_sort_asc(self):
        rand_delay(1, 3)
        pos_offset = 900
        self.crawler.execute_script(f"window.scrollTo(0, {pos_offset});")
        sort_asc = self.element_to_be_clickable(self.selectors['dkpn-sort-asc'])
        sort_asc.click()

    def scroll_up_down(self):
        pos_offset = 200
        neg_offset = -200
        for offset in [pos_offset, neg_offset]:
            self.crawler.execute_script(f"window.scrollTo(0, {offset});")
            rand_delay(0, 1)

    def combine_data(self):
        in_files = get_file_list(self.download_dir, suffix='.csv')
        out_path = os.path.join(self.download_dir, f'{self.subcategory}_all.xlsx')
        combined_data = concat_data(in_files)
        if any(combined_data['Stock'].astype(str).str.contains('.', regex=False)):
            alert = 'ALERT!\nColumn "Stock" contains decimal numbers.\nColumn misaligned.\nFix data mannually. '
            self.logger.warning(alert)
        combined_data['Stock'] = combined_data['Stock'].astype(str).str.replace(',', '')
        combined_data['Stock'] = pd.to_numeric(combined_data['Stock'], errors='coerce')
        combined_data['Subcategory'] = self.subcategory
        combined_data.to_excel(out_path, index=False)

    def crawl(self):
        self.crawler.get(self.start_url)
        element_keywords = [
            'digikey.com',
            'cookie_ok',
            'msg_close',
            'per-page-selector',
            'per-page-100',
            'in-stock',
            'apply-all',
        ]
        for kw in element_keywords:
            self.click_element(kw)

        self.dkpn_sort_asc()

        download_tries = 0
        max_download_tries = 10
        max_page = self.get_max_page()
        try:
            while True:
                cur_page = self.get_cur_page()
                if cur_page not in self.downloaded_pages:
                    self.click_download()
                    self.rename_file(cur_page)
                    self.downloaded_pages.append(cur_page)
                    self.logger.info(
                        str({'Current Page': cur_page, 'Max Page': max_page}) + '\n'
                    )
                    download_tries = 0
                else:
                    self.logger.warning(f'Page {cur_page} has already been downloaded. \n')
                    self.scroll_up_down()
                    download_tries += 1
                    if download_tries > max_download_tries:
                        download_tries_msg = f'Download tries exceeded max {max_download_tries} times. Restart job. '
                        self.logger.warning(download_tries_msg)
                        self.click_element('btn-first-page')
                        download_tries = 0

                if len(self.downloaded_pages) == max_page or cur_page == max_page:
                    break
                self.click_next_page()
            self.combine_data()

        except Exception as ex:
            print(ex)
            stack_trace = traceback.format_exc()
            self.logger.error(stack_trace)
            raise
        finally:
            self.logger.info(f'Finish crawling {self.subcategory}')
            self.close()


class DataCrawlers:
    def __init__(self, driver_path, start_urls, download_dir, n_workers, headless):
        self.driver_path = driver_path
        self.start_urls = start_urls
        random.shuffle(self.start_urls)
        self.download_dir = download_dir
        self.n_workers = n_workers
        self.headless = headless

    def crawl(self, start_url):
        crawler = DataCrawler(self.driver_path, start_url, self.download_dir, self.headless)
        crawler.crawl()

    def crawl_all(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.n_workers, len(self.start_urls))) as executor:
            for url in self.start_urls:
                executor.submit(self.crawl, url)
        print('Crawl finished. ')

    def combine_subcategory_data(self):
        in_files = get_file_list(self.download_dir, suffix='all.xlsx')
        out_path = os.path.join(self.download_dir, 'combine.xlsx')
        df = concat_data(in_files)
        df.to_excel(out_path)
