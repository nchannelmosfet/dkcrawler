from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import traceback
import time
import random


def rand_delay(low, high):
    time.sleep(random.uniform(low, high))


def setup_browser(driver_path):
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.download.folderList", 2)
    profile.set_preference("browser.download.manager.showWhenStarting", False)
    profile.set_preference("browser.download.dir", r'C:\Users\wujun\Downloads')
    profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "text/csv")

    browser = webdriver.Firefox(executable_path=driver_path, firefox_profile=profile)
    browser.set_page_load_timeout(600)
    return browser


def crawl(url):
    driver_path = 'geckodriver.exe'
    browser = setup_browser(driver_path)
    browser.get(url)

    browser.find_element_by_css_selector('[data-testid="per-page-selector"] > div.MuiSelect-root').click()
    rand_delay(1, 3)
    browser.find_element_by_css_selector('[data-testid="per-page-100"]').click()
    rand_delay(1, 3)

    in_stock = browser.find_element_by_css_selector('[data-testid="filter--2-option-5"] input[type="checkbox"]')
    in_stock.click()
    rand_delay(1, 3)

    normally_stocking = browser.find_element_by_css_selector('[data-testid="filter--2-option-9"] input[type="checkbox"]')
    normally_stocking.click()
    rand_delay(1, 3)

    apply_all = browser.find_element_by_css_selector('[data-testid="apply-all-button"]')
    apply_all.click()
    rand_delay(1, 3)

    try:
        while True:
            popup_trigger = browser.find_element_by_css_selector('[data-testid="download-table-popup-trigger-button"]')
            popup_trigger.click()
            rand_delay(1, 3)

            download_table_button = browser.find_element_by_css_selector('[data-testid="download-table-button"]')
            download_table_button.click()
            rand_delay(5, 10)

            try:
                btn_next_page = browser.find_element_by_css_selector('[data-testid="btn-next-page"]')
                btn_next_page.click()
                rand_delay(5, 10)
            except NoSuchElementException:
                break

    except NoSuchElementException:
        traceback.print_stack()

    finally:
        rand_delay(5, 10)
        browser.close()
        browser.quit()


def main():
    urls = {'dsub_cable': 'https://www.digikey.com/en/products/filter/d-sub-cables/461',
            'usb_cable': 'https://www.digikey.com/en/products/filter/usb-cables/455'}

    for url in urls.values():
        crawl(url)


if __name__ == '__main__':
    main()
