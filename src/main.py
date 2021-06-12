from src.data_crawlers import DataCrawler, DataCrawlers
from src.category_crawlers import VendorSubCategoryCrawler, AllSubCategoryCrawler
from src.utils import get_latest_session_index, get_file_list, concat_data
import os


def test_vendor_subcategory_crawler():
    driver_path = 'geckodriver.exe'
    start_url = 'https://www.digikey.com/en/supplier-centers/assmann-wsw-components'
    download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    crawler = VendorSubCategoryCrawler(driver_path, start_url, download_dir)
    subcategory_urls = crawler.crawl()
    print(subcategory_urls)
    crawler.close()
    return subcategory_urls


def test_all_subcategory_crawler():
    driver_path = 'geckodriver.exe'
    start_url = 'https://www.digikey.com/en/products'
    download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    crawler = AllSubCategoryCrawler(driver_path, start_url, download_dir)
    subcategory_urls = crawler.crawl()
    print(subcategory_urls)
    print(len(subcategory_urls))
    crawler.close()


def test_data_crawler():
    dk_data_dir = os.path.join(os.path.dirname(os.getcwd()), 'DK_Data_By_URLs')
    session_index = get_latest_session_index(dk_data_dir) + 1
    download_dir = os.path.join(dk_data_dir, f'session1')
    os.makedirs(download_dir, exist_ok=True)
    driver_path = 'geckodriver.exe'
    start_url = 'https://www.digikey.com/en/products/filter/barrel-power-cables/464'
    crawler = DataCrawler(driver_path, start_url, download_dir, headless=False)
    crawler.crawl()


def test_data_crawlers():
    driver_path = 'geckodriver.exe'
    # https://www.digikey.com/en/products/filter/thermal-pads-sheets/218
    # 'https://www.digikey.com/en/products/filter/thermal-heat-sinks/219'
    start_urls = ['https://www.digikey.com/en/products/filter/accessories/159']
    dk_data_dir = os.path.join(os.path.dirname(os.getcwd()), 'DK_Data_By_URLs')
    session_index = get_latest_session_index(dk_data_dir) + 1
    download_dir = os.path.join(dk_data_dir, f'session{session_index}')
    os.makedirs(download_dir, exist_ok=True)
    data_crawler = DataCrawlers(driver_path, start_urls, download_dir, n_workers=3, headless=False)
    data_crawler.crawl_all()


if __name__ == '__main__':
    test_data_crawler()

    # test_all_subcategory_crawler()
    # test_vendor_subcategory_crawler()
    # test_data_crawlers()
    # in_files = get_file_list(_dir, suffix='.csv')
    # combined_data = concat_data(in_files)
    # outfile = os.path.join(_dir, 'thermal_heat_sinks_all.xlsx')
    # combined_data.to_excel(outfile)
