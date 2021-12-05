#! python
import asyncio
import os

import pandas as pd
from pyppeteer import launch

from utils import *


class ICTCFScrapper():
    BASE_URL = "http://ictcf.biocuckoo.cn/"
    HREF_FUNCTION = '(nodes => nodes.map(n => n.href))'
    INNERTEXT_FUNCTION = '(nodes => nodes.map(n => n.innerText.trim()))'

    SUBMIT_SELECTOR = 'input[name="Submit"]'
    TABLE_SELECTOR = 'table[id="Results"]'
    PATIENT_OVERVIEW_SELECTOR = '#Overview > #Info > table td.content'
    NEXT_XPATH = '//a[contains(., "Next")]'

    # Extra Person Info
    # Order is important, these are respectively number 3 and 4 in the overview page
    PATIENT_HEADERS = ['Body temperature', 'Underlying diseases']

    def __init__(self, export_path="export"):
        self.resource_url = build_url(ICTCFScrapper.BASE_URL, 'Resource.php')
        self.export_path = export_path
        self.covid_ds = {}
        self.patient_pages = []

    async def screenshot(self):
        title = await self.page.title()
        filename = f"{title}.png"
        ss_options = {'path': os.path.join(
            self.export_path, filename), 'fullPage': True}
        await self.page.screenshot(ss_options)

    async def goto_page(self):
        await self.page.goto(self.resource_url)
        await self.page.click(ICTCFScrapper.SUBMIT_SELECTOR)

    async def get_patient_info(self):
        patient_overview = []
        nb_patients = len(self.patient_pages)
        print(f"[Info] Found {nb_patients} patient pages")
        for idx, patient_page in enumerate(self.patient_pages):
            # Example of patient page: http://ictcf.biocuckoo.cn/view.php?id=Patient%201
            self.patient_page = await self.browser.newPage()
            print(
                f"\r[Scrapping] Patient page {idx+1}/{nb_patients}", end='')
            await self.patient_page.goto(patient_page)
            patient_info = await self.patient_page.querySelectorAllEval(ICTCFScrapper.PATIENT_OVERVIEW_SELECTOR, ICTCFScrapper.INNERTEXT_FUNCTION)
            await self.patient_page.close()

            # Only get body temp and diseases from patient info
            extra_patient_headers = ICTCFScrapper.PATIENT_HEADERS
            body_temp = extra_patient_headers[0]
            diseases = extra_patient_headers[1]
            self.covid_ds[body_temp].append(patient_info[3])
            self.covid_ds[diseases].append(patient_info[4])

        print("\n[Info] Scrapping patient pages done!")

    async def table_parser(self, table):
        # Find all rows in table
        rows = await table.querySelectorAll('tr')

        # Find header names and add them to
        header_names = await rows[0].querySelectorAllEval('th', ICTCFScrapper.INNERTEXT_FUNCTION)
        # Add extra headers
        header_names.extend(ICTCFScrapper.PATIENT_HEADERS)

        # Initialize dictionary with headers as keys
        if not self.covid_ds:
            for header_name in header_names:
                self.covid_ds[header_name] = []

        # Find all values of data cells
        data_rows = rows[1:-1]
        for row in data_rows:
            data_row = await row.querySelectorAllEval('td', ICTCFScrapper.INNERTEXT_FUNCTION)
            patient_pages = await row.querySelectorAllEval('td > a', ICTCFScrapper.HREF_FUNCTION)
            self.patient_pages.extend(patient_pages)

            for header, data in zip(header_names, data_row):
                self.covid_ds[header].append(data)

        pagination = rows[-1]
        next_page = await pagination.xpath(ICTCFScrapper.NEXT_XPATH)

        if len(next_page) > 0:
            return next_page[0]

    def export_csv(self):
        df = pd.DataFrame(self.covid_ds)
        csv_path = os.path.join(self.export_path, 'iCTCF.xlsx')
        df.to_excel(csv_path, index=False)
        return csv_path

    async def run(self):
        page_num = 1
        self.browser = await launch()
        self.page = await self.browser.newPage()
        await self.goto_page()

        print(f"\r[Scrapping] iCTCF page {page_num}", end="")
        table = await self.page.querySelector(ICTCFScrapper.TABLE_SELECTOR)
        next_page = await self.table_parser(table)

        while next_page:
            await next_page.click()
            page_num += 1
            print(f"\r[Scrapping] iCTCF page {page_num}", end="")
            table = await self.page.querySelector(ICTCFScrapper.TABLE_SELECTOR)
            next_page = await self.table_parser(table)

        print("\n[Info] Scrapping iCTCF pages done!")
        print(f"[Info] {page_num} pages scrapped")

        # Fetch patient info
        await self.get_patient_info()
        csv_path = self.export_csv()
        print(f"[Export] File exported to {csv_path}")

        await self.browser.close()


if __name__ == '__main__':
    os.makedirs('export', exist_ok=True)
    ictcf_parser = ICTCFScrapper()
    asyncio.get_event_loop().run_until_complete(ictcf_parser.run())
