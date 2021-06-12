from src.base_crawler import BaseCrawler
from selenium.common.exceptions import NoSuchElementException
from src.utils import rand_delay
import random


class VendorSubCategoryCrawler(BaseCrawler):
    def __init__(self, driver_path, start_url, download_dir):
        super().__init__(driver_path, start_url, download_dir)
        self.setup_crawler()

    def crawl(self):
        self.crawler.get(self.start_url)
        a_elems = self.crawler.find_elements_by_css_selector('#product-categories li > a')
        category_urls = self.join_urls(a_elems)
        subcategory_urls = []
        for url in category_urls:
            subcategory_urls += self.parse_sub_category(url)
        random.shuffle(subcategory_urls)
        return subcategory_urls

    def parse_sub_category(self, category_url):
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
            subcategory_urls = self.join_urls(a_elems)
            for url in subcategory_urls:
                urls = self.parse_sub_category(url)
                final_urls += urls
            return final_urls


class AllSubCategoryCrawler(BaseCrawler):
    def __init__(self, driver_path, start_url, download_dir):
        super().__init__(driver_path, start_url, download_dir)
        self.setup_crawler()

    def crawl(self):
        self.crawler.get(self.start_url)
        rand_delay(5, 10)
        self.scroll_to_bottom()
        a_elems = self.crawler.find_elements_by_css_selector('[data-testid="subcategories-items"]')
        subcategory_urls = self.join_urls(a_elems)
        rand_delay(2, 5)
        return subcategory_urls

