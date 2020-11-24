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
    # drop malformed data
    combined_data.to_excel(out_path, index=False)


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
        url_split = self.url.split('/')
        self.product_category = url_split[-2].replace('-', '_')
        self.product_id = url_split[-1]
        self.download_dir = os.path.join(download_dir, f'{self.product_category}_{self.product_id}')
        os.makedirs(self.download_dir, exist_ok=True)
        self.browser = self._setup_browser()
        self.log_text = ''

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
            renamed_file = os.path.join(self.download_dir, f'{self.product_category}_{cur_page}.csv')
            os.rename(downloaded_file, renamed_file)

            status = f'Renamed file: \n"{downloaded_file}" \n-> \n"{renamed_file}"\n\n'
            self.log_text += status
            print(status)
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
            in_files = get_file_list(self.download_dir)
            out_path = os.path.join(self.download_dir, f'{self.product_category}_all.xlsx')
            concat_data(in_files, out_path)
        except:
            stack_trace = traceback.format_exc()
            self.log_text += stack_trace
            traceback.print_exc()
        finally:
            log_file_path = os.path.join(self.download_dir, f'{self.product_category}.log')
            with open(log_file_path, 'w') as f:
                f.write(self.log_text)
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

    all_urls = [
        'https://www.digikey.com/en/products/filter/accessories/159',
        'https://www.digikey.com/en/products/filter/alarms-buzzers-and-sirens/157',
        'https://www.digikey.com/en/products/filter/amplifiers/998',
        'https://www.digikey.com/en/products/filter/buzzer-elements-piezo-benders/160',
        'https://www.digikey.com/en/products/filter/guitar-parts-accessories/1001',
        'https://www.digikey.com/en/products/filter/microphones/158',
        'https://www.digikey.com/en/products/filter/speakers/156',
        'https://www.digikey.com/en/products/filter/vacuum-tubes/1004',
        'https://www.digikey.com/en/products/filter/accessories/87',
        'https://www.digikey.com/en/products/filter/batteries-non-rechargeable-primary/90',
        'https://www.digikey.com/en/products/filter/batteries-rechargeable-secondary/91',
        'https://www.digikey.com/en/products/filter/battery-chargers/85',
        'https://www.digikey.com/en/products/filter/battery-holders-clips-contacts/86',
        'https://www.digikey.com/en/products/filter/battery-packs/89',
        'https://www.digikey.com/en/products/filter/cigarette-lighter-assemblies/88',
        'https://www.digikey.com/en/products/filter/backplanes/589',
        'https://www.digikey.com/en/products/filter/box-accessories/595',
        'https://www.digikey.com/en/products/filter/box-components/596',
        'https://www.digikey.com/en/products/filter/boxes/594',
        'https://www.digikey.com/en/products/filter/cams/960',
        'https://www.digikey.com/en/products/filter/card-guide-accessories/600',
        'https://www.digikey.com/en/products/filter/card-guides/591',
        'https://www.digikey.com/en/products/filter/card-rack-accessories/601',
        'https://www.digikey.com/en/products/filter/card-racks/588',
        'https://www.digikey.com/en/products/filter/evaluation-development-board-enclosures/975',
        'https://www.digikey.com/en/products/filter/handles/590',
        'https://www.digikey.com/en/products/filter/latches-locks/973',
        'https://www.digikey.com/en/products/filter/patchbay-jack-panel-accessories/593',
        'https://www.digikey.com/en/products/filter/patchbay-jack-panels/592',
        'https://www.digikey.com/en/products/filter/rack-accessories/598',
        'https://www.digikey.com/en/products/filter/rack-components/599',
        'https://www.digikey.com/en/products/filter/rack-thermal-management/602',
        'https://www.digikey.com/en/products/filter/racks/597',
        'https://www.digikey.com/en/products/filter/barrel-audio-cables/463',
        'https://www.digikey.com/en/products/filter/barrel-power-cables/464',
        'https://www.digikey.com/en/products/filter/between-series-adapter-cables/459',
        'https://www.digikey.com/en/products/filter/circular-cable-assemblies/448',
        'https://www.digikey.com/en/products/filter/coaxial-cables-rf/456',
        'https://www.digikey.com/en/products/filter/d-shaped-centronics-cables/466',
        'https://www.digikey.com/en/products/filter/d-sub-cables/461',
        'https://www.digikey.com/en/products/filter/fiber-optic-cables/449',
        'https://www.digikey.com/en/products/filter/firewire-cables-ieee-1394/454',
        'https://www.digikey.com/en/products/filter/flat-flex-jumpers-cables-ffc-fpc/458',
        'https://www.digikey.com/en/products/filter/flat-flex-ribbon-jumpers-cables/457',
        'https://www.digikey.com/en/products/filter/jumper-wires-pre-crimped-leads/453',
        'https://www.digikey.com/en/products/filter/lgh-cables/465',
        'https://www.digikey.com/en/products/filter/modular-cables/451',
        'https://www.digikey.com/en/products/filter/pluggable-cables/460',
        'https://www.digikey.com/en/products/filter/power-line-cables-and-extension-cords/452',
        'https://www.digikey.com/en/products/filter/rectangular-cable-assemblies/450',
        'https://www.digikey.com/en/products/filter/smart-cables/468',
        'https://www.digikey.com/en/products/filter/solid-state-lighting-cables/469',
        'https://www.digikey.com/en/products/filter/specialized-cable-assemblies/467',
        'https://www.digikey.com/en/products/filter/usb-cables/455',
        'https://www.digikey.com/en/products/filter/video-cables-dvi-hdmi/462',
        'https://www.digikey.com/en/products/filter/accessories/479',
        'https://www.digikey.com/en/products/filter/bushings-grommets/491',
        'https://www.digikey.com/en/products/filter/cable-supports-and-fasteners/490',
        'https://www.digikey.com/en/products/filter/cable-ties-holders-and-mountings/488',
        'https://www.digikey.com/en/products/filter/cable-ties-and-cable-lacing/482',
        'https://www.digikey.com/en/products/filter/cable-and-cord-grips/492',
        'https://www.digikey.com/en/products/filter/cold-shrink-tape-tubing/485',
        'https://www.digikey.com/en/products/filter/fiber-optic-cables/481',
        'https://www.digikey.com/en/products/filter/grounding-braid-straps/494',
        'https://www.digikey.com/en/products/filter/heat-shrink-boots-caps/499',
        'https://www.digikey.com/en/products/filter/heat-shrink-fabric/489',
        'https://www.digikey.com/en/products/filter/heat-shrink-tubing/483',
        'https://www.digikey.com/en/products/filter/heat-shrink-wrap/497',
        'https://www.digikey.com/en/products/filter/labels-labeling/484',
        'https://www.digikey.com/en/products/filter/markers/493',
        'https://www.digikey.com/en/products/filter/protective-hoses-solid-tubing-sleeving/480',
        'https://www.digikey.com/en/products/filter/pulling-support-grips/498',
        'https://www.digikey.com/en/products/filter/solder-sleeve/478',
        'https://www.digikey.com/en/products/filter/spiral-wrap-expandable-sleeving/495',
        'https://www.digikey.com/en/products/filter/splice-enclosures-protection/496',
        'https://www.digikey.com/en/products/filter/wire-ducts-raceways-accessories-covers/957',
        'https://www.digikey.com/en/products/filter/wire-ducts-raceways-accessories/487',
        'https://www.digikey.com/en/products/filter/wire-ducts-raceways/486',
        'https://www.digikey.com/en/products/filter/coaxial-cables-rf/475',
        'https://www.digikey.com/en/products/filter/fiber-optic-cables/471',
        'https://www.digikey.com/en/products/filter/flat-flex-cables-ffc-fpc/476',
        'https://www.digikey.com/en/products/filter/flat-ribbon-cables/472',
        'https://www.digikey.com/en/products/filter/modular-flat-cable/477',
        'https://www.digikey.com/en/products/filter/multiple-conductor-cables/473',
        'https://www.digikey.com/en/products/filter/single-conductor-cables-hook-up-wire/474',
        'https://www.digikey.com/en/products/filter/wire-wrap/470',
        'https://www.digikey.com/en/products/filter/accessories/63',
        'https://www.digikey.com/en/products/filter/aluminum-polymer-capacitors/69',
        'https://www.digikey.com/en/products/filter/aluminum-electrolytic-capacitors/58',
        'https://www.digikey.com/en/products/filter/capacitor-networks-arrays/57',
        'https://www.digikey.com/en/products/filter/ceramic-capacitors/60',
        'https://www.digikey.com/en/products/filter/electric-double-layer-capacitors-edlc-supercapacitors/61',
        'https://www.digikey.com/en/products/filter/film-capacitors/62',
        'https://www.digikey.com/en/products/filter/mica-and-ptfe-capacitors/64',
        'https://www.digikey.com/en/products/filter/niobium-oxide-capacitors/67',
        'https://www.digikey.com/en/products/filter/silicon-capacitors/68',
        'https://www.digikey.com/en/products/filter/tantalum-polymer-capacitors/70',
        'https://www.digikey.com/en/products/filter/tantalum-capacitors/59',
        'https://www.digikey.com/en/products/filter/thin-film-capacitors/66',
        'https://www.digikey.com/en/products/filter/trimmers-variable-capacitors/65',
        'https://www.digikey.com/en/products/filter/accessories/145',
        'https://www.digikey.com/en/products/filter/circuit-breakers/143',
        'https://www.digikey.com/en/products/filter/electrical-specialty-fuses/155',
        'https://www.digikey.com/en/products/filter/fuseholders/140',
        'https://www.digikey.com/en/products/filter/fuses/139',
        'https://www.digikey.com/en/products/filter/gas-discharge-tube-arresters-gdt/142',
        'https://www.digikey.com/en/products/filter/ground-fault-circuit-interrupter-gfci/148',
        'https://www.digikey.com/en/products/filter/inrush-current-limiters-icl/151',
        'https://www.digikey.com/en/products/filter/lighting-protection/154',
        'https://www.digikey.com/en/products/filter/ptc-resettable-fuses/150',
        'https://www.digikey.com/en/products/filter/surge-suppression-ics/152',
        'https://www.digikey.com/en/products/filter/tvs-diodes/144',
        'https://www.digikey.com/en/products/filter/tvs-mixed-technology/149',
        'https://www.digikey.com/en/products/filter/tvs-surge-protection-devices-spds/992',
        'https://www.digikey.com/en/products/filter/tvs-thyristors/147',
        'https://www.digikey.com/en/products/filter/tvs-varistors-movs/141',
        'https://www.digikey.com/en/products/filter/thermal-cutoffs-thermal-fuses/146',
        'https://www.digikey.com/en/products/filter/accessories/881',
        'https://www.digikey.com/en/products/filter/adapter-cards/888',
        'https://www.digikey.com/en/products/filter/adapters-converters/882',
        'https://www.digikey.com/en/products/filter/brackets/889',
        'https://www.digikey.com/en/products/filter/cameras-projectors/898',
        'https://www.digikey.com/en/products/filter/computer-mouse-trackballs/893',
        'https://www.digikey.com/en/products/filter/desktop-joysticks-simulation-products/899',
        'https://www.digikey.com/en/products/filter/kvm-switches-keyboard-video-mouse-cables/896',
        'https://www.digikey.com/en/products/filter/kvm-switches-keyboard-video-mouse/890',
        'https://www.digikey.com/en/products/filter/keyboards/885',
        'https://www.digikey.com/en/products/filter/magnetic-strip-smart-card-readers/891',
        'https://www.digikey.com/en/products/filter/memory-card-readers/895',
        'https://www.digikey.com/en/products/filter/modems/897',
        'https://www.digikey.com/en/products/filter/monitors/900',
        'https://www.digikey.com/en/products/filter/printers-label-makers/887',
        'https://www.digikey.com/en/products/filter/privacy-filters-screen-protectors/883',
        'https://www.digikey.com/en/products/filter/server-acceleration-cards/986',
        'https://www.digikey.com/en/products/filter/usb-hubs/1015',
        'https://www.digikey.com/en/products/filter/backplane-connectors-arinc-inserts/430',
        'https://www.digikey.com/en/products/filter/backplane-connectors-arinc/386',
        'https://www.digikey.com/en/products/filter/backplane-connectors-accessories/343',
        'https://www.digikey.com/en/products/filter/backplane-connectors-contacts/335',
        'https://www.digikey.com/en/products/filter/backplane-connectors-din-41612/307',
        'https://www.digikey.com/en/products/filter/backplane-connectors-hard-metric-standard/406',
        'https://www.digikey.com/en/products/filter/backplane-connectors-housings/372',
        'https://www.digikey.com/en/products/filter/backplane-connectors-specialized/407',
        'https://www.digikey.com/en/products/filter/banana-and-tip-connectors-accessories/351',
        'https://www.digikey.com/en/products/filter/banana-and-tip-connectors-adapters/381',
        'https://www.digikey.com/en/products/filter/banana-and-tip-connectors-binding-posts/310',
        'https://www.digikey.com/en/products/filter/banana-and-tip-connectors-jacks-plugs/302',
        'https://www.digikey.com/en/products/filter/barrel-accessories/348',
        'https://www.digikey.com/en/products/filter/barrel-adapters/376',
        'https://www.digikey.com/en/products/filter/barrel-audio-connectors/434',
        'https://www.digikey.com/en/products/filter/barrel-power-connectors/435',
        'https://www.digikey.com/en/products/filter/between-series-adapters/373',
        'https://www.digikey.com/en/products/filter/blade-type-power-connectors-accessories/360',
        'https://www.digikey.com/en/products/filter/blade-type-power-connectors-contacts/420',
        'https://www.digikey.com/en/products/filter/blade-type-power-connectors-housings/419',
        'https://www.digikey.com/en/products/filter/blade-type-power-connectors/357',
        'https://www.digikey.com/en/products/filter/card-edge-connectors-accessories/349',
        'https://www.digikey.com/en/products/filter/card-edge-connectors-adapters/429',
        'https://www.digikey.com/en/products/filter/card-edge-connectors-contacts/345',
        'https://www.digikey.com/en/products/filter/card-edge-connectors-edgeboard-connectors/303',
        'https://www.digikey.com/en/products/filter/card-edge-connectors-housings/354',
        'https://www.digikey.com/en/products/filter/circular-connectors-accessories/329',
        'https://www.digikey.com/en/products/filter/circular-connectors-adapters/378',
        'https://www.digikey.com/en/products/filter/circular-connectors-backshells-and-cable-clamps/313',
        'https://www.digikey.com/en/products/filter/circular-connectors-contacts/330',
        'https://www.digikey.com/en/products/filter/circular-connectors-housings/320',
        'https://www.digikey.com/en/products/filter/circular-connectors/436',
        'https://www.digikey.com/en/products/filter/coaxial-connectors-rf-accessories/342',
        'https://www.digikey.com/en/products/filter/coaxial-connectors-rf-adapters/374',
        'https://www.digikey.com/en/products/filter/coaxial-connectors-rf-contacts/388',
        'https://www.digikey.com/en/products/filter/coaxial-connectors-rf-terminators/382',
        'https://www.digikey.com/en/products/filter/coaxial-connectors-rf/437',
        'https://www.digikey.com/en/products/filter/contacts-leadframe/416',
        'https://www.digikey.com/en/products/filter/contacts-multi-purpose/336',
        'https://www.digikey.com/en/products/filter/contacts-spring-loaded-and-pressure/311',
        'https://www.digikey.com/en/products/filter/d-shaped-connectors-centronics/438',
        'https://www.digikey.com/en/products/filter/d-sub-connectors/439',
        'https://www.digikey.com/en/products/filter/d-sub-d-shaped-connectors-accessories-jackscrews/447',
        'https://www.digikey.com/en/products/filter/d-sub-d-shaped-connectors-accessories/339',
        'https://www.digikey.com/en/products/filter/d-sub-d-shaped-connectors-adapters/375',
        'https://www.digikey.com/en/products/filter/d-sub-d-shaped-connectors-backshells-hoods/355',
        'https://www.digikey.com/en/products/filter/d-sub-d-shaped-connectors-contacts/332',
        'https://www.digikey.com/en/products/filter/d-sub-d-shaped-connectors-housings/321',
        'https://www.digikey.com/en/products/filter/d-sub-d-shaped-connectors-terminators/383',
        'https://www.digikey.com/en/products/filter/ffc-fpc-flat-flexible-connectors-accessories/350',
        'https://www.digikey.com/en/products/filter/ffc-fpc-flat-flexible-connectors-contacts/344',
        'https://www.digikey.com/en/products/filter/ffc-fpc-flat-flexible-connectors-housings/390',
        'https://www.digikey.com/en/products/filter/ffc-fpc-flat-flexible-connectors/399',
        'https://www.digikey.com/en/products/filter/fiber-optic-connectors-accessories/389',
        'https://www.digikey.com/en/products/filter/fiber-optic-connectors-adapters/387',
        'https://www.digikey.com/en/products/filter/fiber-optic-connectors-housings/445',
        'https://www.digikey.com/en/products/filter/fiber-optic-connectors/440',
        'https://www.digikey.com/en/products/filter/heavy-duty-connectors-accessories/358',
        'https://www.digikey.com/en/products/filter/heavy-duty-connectors-assemblies/327',
        'https://www.digikey.com/en/products/filter/heavy-duty-connectors-contacts/337',
        'https://www.digikey.com/en/products/filter/heavy-duty-connectors-frames/362',
        'https://www.digikey.com/en/products/filter/heavy-duty-connectors-housings-hoods-bases/363',
        'https://www.digikey.com/en/products/filter/heavy-duty-connectors-inserts-modules/361',
        'https://www.digikey.com/en/products/filter/keystone-accessories/426',
        'https://www.digikey.com/en/products/filter/keystone-faceplates-frames/427',
        'https://www.digikey.com/en/products/filter/keystone-inserts/428',
        'https://www.digikey.com/en/products/filter/lgh-connectors/441',
        'https://www.digikey.com/en/products/filter/memory-connectors-accessories/352',
        'https://www.digikey.com/en/products/filter/memory-connectors-inline-module-sockets/413',
        'https://www.digikey.com/en/products/filter/memory-connectors-pc-card-sockets/414',
        'https://www.digikey.com/en/products/filter/memory-connectors-pc-cards-adapters/421',
        'https://www.digikey.com/en/products/filter/modular-connectors-accessories/442',
        'https://www.digikey.com/en/products/filter/modular-connectors-adapters/379',
        'https://www.digikey.com/en/products/filter/modular-connectors-jacks-with-magnetics/365',
        'https://www.digikey.com/en/products/filter/modular-connectors-jacks/366',
        'https://www.digikey.com/en/products/filter/modular-connectors-plug-housings/403',
        'https://www.digikey.com/en/products/filter/modular-connectors-plugs/367',
        'https://www.digikey.com/en/products/filter/modular-connectors-wiring-blocks-accessories/417',
        'https://www.digikey.com/en/products/filter/modular-connectors-wiring-blocks/418',
        'https://www.digikey.com/en/products/filter/photovoltaic-solar-panel-connectors-accessories/424',
        'https://www.digikey.com/en/products/filter/photovoltaic-solar-panel-connectors-contacts/423',
        'https://www.digikey.com/en/products/filter/photovoltaic-solar-panel-connectors/326',
        'https://www.digikey.com/en/products/filter/pluggable-connectors-accessories/346',
        'https://www.digikey.com/en/products/filter/pluggable-connectors/443',
        'https://www.digikey.com/en/products/filter/power-entry-connectors-accessories/341',
        'https://www.digikey.com/en/products/filter/power-entry-connectors-inlets-outlets-modules/301',
        'https://www.digikey.com/en/products/filter/rectangular-connectors-accessories/340',
        'https://www.digikey.com/en/products/filter/rectangular-connectors-adapters/380',
        'https://www.digikey.com/en/products/filter/rectangular-connectors-arrays-edge-type-mezzanine-board-to-board/308',
        'https://www.digikey.com/en/products/filter/rectangular-connectors-board-in-direct-wire-to-board/317',
        'https://www.digikey.com/en/products/filter/rectangular-connectors-board-spacers-stackers-board-to-board/400',
        'https://www.digikey.com/en/products/filter/rectangular-connectors-contacts/331',
        'https://www.digikey.com/en/products/filter/rectangular-connectors-free-hanging-panel-mount/316',
        'https://www.digikey.com/en/products/filter/rectangular-connectors-headers-male-pins/314',
        'https://www.digikey.com/en/products/filter/rectangular-connectors-headers-receptacles-female-sockets/315',
        'https://www.digikey.com/en/products/filter/rectangular-connectors-headers-specialty-pin/318',
        'https://www.digikey.com/en/products/filter/rectangular-connectors-housings/319',
        'https://www.digikey.com/en/products/filter/rectangular-connectors-spring-loaded/408',
        'https://www.digikey.com/en/products/filter/shunts-jumpers/304',
        'https://www.digikey.com/en/products/filter/sockets-for-ics-transistors-accessories/410',
        'https://www.digikey.com/en/products/filter/sockets-for-ics-transistors-adapters/411',
        'https://www.digikey.com/en/products/filter/sockets-for-ics-transistors/409',
        'https://www.digikey.com/en/products/filter/solid-state-lighting-connectors-accessories/432',
        'https://www.digikey.com/en/products/filter/solid-state-lighting-connectors-contacts/446',
        'https://www.digikey.com/en/products/filter/solid-state-lighting-connectors/444',
        'https://www.digikey.com/en/products/filter/terminal-blocks-accessories-jumpers/385',
        'https://www.digikey.com/en/products/filter/terminal-blocks-accessories-marker-strips/384',
        'https://www.digikey.com/en/products/filter/terminal-blocks-accessories-wire-ferrules/364',
        'https://www.digikey.com/en/products/filter/terminal-blocks-accessories/309',
        'https://www.digikey.com/en/products/filter/terminal-blocks-adapters/322',
        'https://www.digikey.com/en/products/filter/terminal-blocks-barrier-blocks/368',
        'https://www.digikey.com/en/products/filter/terminal-blocks-contacts/338',
        'https://www.digikey.com/en/products/filter/terminal-blocks-din-rail-channel/369',
        'https://www.digikey.com/en/products/filter/terminal-blocks-headers-plugs-and-sockets/370',
        'https://www.digikey.com/en/products/filter/terminal-blocks-interface-modules/431',
        'https://www.digikey.com/en/products/filter/terminal-blocks-panel-mount/425',
        'https://www.digikey.com/en/products/filter/terminal-blocks-power-distribution/412',
        'https://www.digikey.com/en/products/filter/terminal-blocks-specialized/433',
        'https://www.digikey.com/en/products/filter/terminal-blocks-wire-to-board/371',
        'https://www.digikey.com/en/products/filter/terminal-junction-systems/422',
        'https://www.digikey.com/en/products/filter/terminal-strips-and-turret-boards/306',
        'https://www.digikey.com/en/products/filter/terminals-accessories/415',
        'https://www.digikey.com/en/products/filter/terminals-adapters/405',
        'https://www.digikey.com/en/products/filter/terminals-barrel-bullet-connectors/393',
        'https://www.digikey.com/en/products/filter/terminals-foil-connectors/402',
        'https://www.digikey.com/en/products/filter/terminals-housings-boots/325',
        'https://www.digikey.com/en/products/filter/terminals-knife-connectors/404',
        'https://www.digikey.com/en/products/filter/terminals-magnetic-wire-connectors/353',
        'https://www.digikey.com/en/products/filter/terminals-pc-pin-receptacles-socket-connectors/324',
        'https://www.digikey.com/en/products/filter/terminals-pc-pin-single-post-connectors/323',
        'https://www.digikey.com/en/products/filter/terminals-quick-connects-quick-disconnect-connectors/392',
        'https://www.digikey.com/en/products/filter/terminals-rectangular-connectors/395',
        'https://www.digikey.com/en/products/filter/terminals-ring-connectors/394',
        'https://www.digikey.com/en/products/filter/terminals-screw-connectors/396',
        'https://www.digikey.com/en/products/filter/terminals-solder-lug-connectors/401',
        'https://www.digikey.com/en/products/filter/terminals-spade-connectors/391',
        'https://www.digikey.com/en/products/filter/terminals-specialized-connectors/356',
        'https://www.digikey.com/en/products/filter/terminals-turret-connectors/328',
        'https://www.digikey.com/en/products/filter/terminals-wire-pin-connectors/397',
        'https://www.digikey.com/en/products/filter/terminals-wire-splice-connectors/305',
        'https://www.digikey.com/en/products/filter/terminals-wire-to-board-connectors/398',
        'https://www.digikey.com/en/products/filter/usb-dvi-hdmi-connectors-accessories/347',
        'https://www.digikey.com/en/products/filter/usb-dvi-hdmi-connectors-adapters/377',
        'https://www.digikey.com/en/products/filter/usb-dvi-hdmi-connectors/312',
    ]

    short_urls = ['https://www.digikey.com/en/products/filter/barrel-power-cables/464',
                  'https://www.digikey.com/en/products/filter/accessories/87']

    rand_urls = random.sample(all_urls, 6)
    run_crawlers(rand_urls, driver_path, download_dir, n_workers=2)


if __name__ == '__main__':
    main()
