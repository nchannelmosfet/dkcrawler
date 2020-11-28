from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from urllib.parse import urljoin, urlsplit
from utils import rand_delay, get_file_list, get_latest_file, concat_data
import concurrent.futures
import random
import traceback
import abc
import os


class BaseCrawler(metaclass=abc.ABCMeta):
    def __init__(self, driver_path, start_url, download_dir=None):
        self.driver_path = driver_path
        self.start_url = start_url.split('?')[0]
        self.download_dir = download_dir
        self.crawler = None

    def _scroll_to_bottom(self):
        offset = 0
        while True:
            old_y_offset = self.crawler.execute_script("return window.pageYOffset;")
            offset += 900
            self.crawler.execute_script(f"window.scrollTo(0, {offset});")
            rand_delay(2, 4)
            new_y_offset = self.crawler.execute_script("return window.pageYOffset;")
            if old_y_offset == new_y_offset:
                break

    def _join_urls(self, a_elems):
        relative_urls = [a.get_attribute('href') for a in a_elems]
        base_url = "{0.scheme}://{0.netloc}/".format(urlsplit(self.start_url))
        full_urls = [urljoin(base_url, url) for url in relative_urls]
        return full_urls

    def _setup_crawler(self):
        profile = webdriver.FirefoxProfile()
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference("browser.download.manager.showWhenStarting", False)

        if self.download_dir:
            profile.set_preference("browser.download.dir", self.download_dir)
        profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "text/csv")

        options = Options()
        options.headless = True
        crawler = webdriver.Firefox(executable_path=self.driver_path, firefox_profile=profile, options=options)
        crawler.set_window_size(1600, 900)
        crawler.set_page_load_timeout(600)
        self.crawler = crawler

    def close(self):
        self.crawler.close()
        self.crawler.quit()

    @abc.abstractmethod
    def crawl(self):
        pass


class VendorSubCategoryCrawler(BaseCrawler):
    def __init__(self, driver_path, start_url, download_dir):
        super().__init__(driver_path, start_url, download_dir)
        self._setup_crawler()

    def crawl(self):
        self.crawler.get(self.start_url)
        a_elems = self.crawler.find_elements_by_css_selector('#product-categories li > a')
        category_urls = self._join_urls(a_elems)
        subcategory_urls = []
        for url in category_urls:
            subcategory_urls += self.__parse_sub_category(url)
        random.shuffle(subcategory_urls)
        return subcategory_urls

    def __parse_sub_category(self, category_url):
        self.crawler.get(category_url)
        cur_url = self.crawler.current_url
        rand_delay(2, 3)

        try:
            print('Processing', cur_url)
            min_qty = self.crawler.find_element_by_css_selector('[data-atag="tr-minQty"] > span > div:last-child').text
            print('min_qty', min_qty)
            if min_qty == 'Non-Stock':
                return []
        except NoSuchElementException:
            pass

        final_urls = []
        if 'filter' in cur_url:
            final_urls += cur_url.split('?')[0:1]
            return final_urls
        elif 'products/detail' in cur_url:
            return []
        else:
            a_elems = self.crawler.find_elements_by_css_selector('[data-testid="subcategories-items"]')
            subcategory_urls = self._join_urls(a_elems)
            for url in subcategory_urls:
                urls = self.__parse_sub_category(url)
                final_urls += urls
            return final_urls


class AllSubCategoryCrawler(BaseCrawler):
    def __init__(self, driver_path, start_url, download_dir):
        super().__init__(driver_path, start_url, download_dir)
        self._setup_crawler()

    def crawl(self):
        self.crawler.get(self.start_url)
        rand_delay(5, 10)
        self._scroll_to_bottom()
        a_elems = self.crawler.find_elements_by_css_selector('[data-testid="subcategories-items"]')
        subcategory_urls = self._join_urls(a_elems)
        rand_delay(2, 5)
        return subcategory_urls


class DataCrawler(BaseCrawler):
    __selectors = {
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

    def __init__(self, driver_path, start_url, download_dir):
        super().__init__(driver_path, start_url, download_dir)
        url_split = self.start_url.split('/')
        self.subcategory = url_split[-2].replace('-', '_')
        self.product_id = url_split[-1]
        self.download_dir = os.path.join(download_dir, f'{self.subcategory}_{self.product_id}')
        self.log_text = ''
        self._setup_crawler()

    def __del_prev_files(self):
        files = get_file_list(self.download_dir)
        for f in files:
            os.remove(f)

    def __set_page_size_100(self):
        self.crawler.find_element_by_css_selector(self.__selectors['per-page-selector']).click()
        rand_delay(1, 3)
        self.crawler.find_element_by_css_selector(self.__selectors['per-page-100']).click()
        rand_delay(1, 3)

    def __select_in_stock(self):
        in_stock = self.crawler.find_element_by_css_selector(self.__selectors['in-stock'])
        in_stock.click()
        rand_delay(1, 3)

        normally_stocking = self.crawler.find_element_by_css_selector(self.__selectors['normally-stocking'])
        normally_stocking.click()
        rand_delay(1, 3)

        apply_all = self.crawler.find_element_by_css_selector(self.__selectors['apply-all'])
        apply_all.click()
        rand_delay(1, 3)

    def __select_active(self):
        active_parts = self.crawler.find_element_by_css_selector(self.__selectors['active_parts'])
        active_parts.click()
        rand_delay(1, 3)

    def __get_max_page(self):
        max_page = self.crawler.find_element_by_css_selector(self.__selectors['max-page']).text
        max_page = int(max_page.split('/')[-1])
        return max_page

    def __click_download(self):
        popup_trigger = self.crawler.find_element_by_css_selector(self.__selectors['popup-trigger'])
        popup_trigger.click()
        rand_delay(1, 3)
        download_table_button = self.crawler.find_element_by_css_selector(self.__selectors['download'])
        download_table_button.click()
        rand_delay(5, 10)

    def __click_next_page(self):
        btn_next_page = self.crawler.find_element_by_css_selector(self.__selectors['next-page'])
        btn_next_page.click()
        rand_delay(5, 10)

    def __rename_file(self, cur_page):
        try:
            downloaded_file = get_latest_file(self.download_dir)
            renamed_file = os.path.join(self.download_dir, f'{self.subcategory}_{cur_page}.csv')
            os.rename(downloaded_file, renamed_file)

            status = f'Renamed file: \n"{downloaded_file}" \n-> \n"{renamed_file}"\n\n'
            self.log_text += status
            print(status)
        except ValueError:
            pass

    def crawl(self):
        self.__del_prev_files()
        self.crawler.get(self.start_url)
        self.__set_page_size_100()
        self.__select_in_stock()
        max_page = self.__get_max_page()

        try:
            cur_page = 1
            while True:
                self.__click_download()
                self.__rename_file(cur_page)
                cur_page += 1

                if cur_page <= max_page:
                    self.__click_next_page()
                else:
                    break
            in_files = get_file_list(self.download_dir)
            out_path = os.path.join(self.download_dir, f'{self.subcategory}_all.xlsx')
            add_col = {'Subcategory': self.subcategory}
            combined_data = concat_data(in_files, out_path, add_col)
            if any(combined_data['Stock'].astype(str).str.contains('.')):
                alert = 'ALERT!\nColumn "Stock" contains decimal numbers.\nColumn misaligned.\nFix data mannually. '
                self.log_text += alert
        except:
            stack_trace = traceback.format_exc()
            self.log_text += stack_trace
            traceback.print_exc()
        finally:
            log_file_path = os.path.join(self.download_dir, f'{self.subcategory}.log')
            with open(log_file_path, 'w') as f:
                f.write(self.log_text)


class DataCrawlers:
    def __init__(self, driver_path, start_urls, download_dir, n_workers=1):
        self.driver_path = driver_path
        self.start_urls = start_urls
        random.shuffle(self.start_urls)
        self.download_dir = download_dir
        self.n_workers = n_workers

    def __crawl(self, start_url):
        crawler = DataCrawler(self.driver_path, start_url, self.download_dir)
        crawler.crawl()
        crawler.close()

    def crawl_all(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.n_workers, len(self.start_urls))) as executor:
            for url in self.start_urls:
                executor.submit(self.__crawl, url)

        in_files = get_file_list(self.download_dir, suffix='all.xlsx')
        out_path = os.path.join(self.download_dir, 'concat.xlsx')
        concat_data(in_files, out_path)
