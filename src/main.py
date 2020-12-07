from src.crawlers import VendorSubCategoryCrawler, AllSubCategoryCrawler, DataCrawler, DataCrawlers
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
    driver_path = 'geckodriver.exe'
    start_url = 'https://www.digikey.com/en/products/filter/barrel-power-cables/464'
    download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    crawler = DataCrawler(driver_path, start_url, download_dir)
    crawler.crawl()
    crawler.close()


def test_data_crawlers():
    driver_path = 'geckodriver.exe'
    start_urls = ['https://www.digikey.com/en/products/filter/barrel-power-cables/464',
                  'https://www.digikey.com/en/products/filter/accessories/87',
                  'https://www.digikey.com/en/products/filter/wire-ducts-raceways-accessories/487']
    download_dir = os.path.join(os.getcwd(), 'DK_Data')
    # awsw_urls = test_vendor_subcategory_crawler()
    data_crawler = DataCrawlers(driver_path, start_urls, download_dir, n_workers=3)
    data_crawler.crawl_all()


if __name__ == '__main__':
    # test_data_crawler()
    # test_all_subcategory_crawler()
    # test_vendor_subcategory_crawler()
    test_data_crawlers()
