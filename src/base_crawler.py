from selenium.webdriver.firefox.options import Options
from selenium import webdriver
from urllib.parse import urljoin, urlsplit
from src.utils import rand_delay
import abc
import os


class BaseCrawler(metaclass=abc.ABCMeta):
    def __init__(self, driver_path, start_url, download_dir=None, headless=True):
        self.driver_path = driver_path
        self.start_url = start_url.split('?')[0]
        self.download_dir = download_dir
        self.headless = headless
        self.crawler = None

    def scroll_to_bottom(self):
        offset = 0
        while True:
            old_y_offset = self.crawler.execute_script("return window.pageYOffset;")
            offset += 900
            self.crawler.execute_script(f"window.scrollTo(0, {offset});")
            rand_delay(2, 4)
            new_y_offset = self.crawler.execute_script("return window.pageYOffset;")
            if old_y_offset == new_y_offset:
                break

    def join_urls(self, a_elems):
        relative_urls = [a.get_attribute('href') for a in a_elems]
        base_url = "{0.scheme}://{0.netloc}/".format(urlsplit(self.start_url))
        full_urls = [urljoin(base_url, url) for url in relative_urls]
        return full_urls

    @staticmethod
    def get_firefox_profile():
        try:
            firefox_profile_dir = os.path.join(
                os.path.expanduser('~'),
                r'AppData\Roaming\Mozilla\Firefox\Profiles'
            )
            firefox_profile = [_dir for _dir in os.listdir(firefox_profile_dir) if _dir.endswith('default-release')][0]
            full_firefox_profile = os.path.join(firefox_profile_dir, firefox_profile)
            return full_firefox_profile
        except Exception as ex:
            print(ex)
            return

    def setup_crawler(self):
        profile = webdriver.FirefoxProfile(self.get_firefox_profile())
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference("browser.download.manager.showWhenStarting", False)

        if self.download_dir:
            profile.set_preference("browser.download.dir", self.download_dir)
        profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "text/csv")

        options = Options()
        options.headless = self.headless
        crawler = webdriver.Firefox(executable_path=self.driver_path, firefox_profile=profile, options=options)
        crawler.set_window_size(1600, 900)
        crawler.set_page_load_timeout(600)
        crawler.maximize_window()
        self.crawler = crawler

    def close(self):
        self.crawler.close()
        self.crawler.quit()

    @abc.abstractmethod
    def crawl(self):
        pass
