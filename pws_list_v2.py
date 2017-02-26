from lxml.html import parse
from urllib import request
import re
import pandas as pd
import os


class CountyPWS:
    def __init__(self):
        self.county = None
        self.urls = []
        self.pws_names = []

    def get_county(self):
        return self.county

    def get_urls(self, county):
        self.county = re.sub(r'\s', r'%20', county)
        base_url = 'http://dww2.tceq.texas.gov/DWW/JSP/'
        url = 'http://dww2.tceq.texas.gov/DWW/JSP/SearchDispatch?number=&name=&ActivityStatusCD=All&county=' \
              + self.county + '&WaterSystemType=All&SourceWaterType=All&SampleType=null&begin_date=10%2F4%2F2014' \
              '&end_date=10%2F4%2F2016&action=Search+For+Water+Systems'
        print(url)
        parsed = parse(request.urlopen(url))
        doc = parsed.getroot()
        tables = doc.findall('.//table')
        # links are in the 3rd table
        pws_table = tables[2]
        # each pws's info is in a separate tr
        rows = pws_table.findall('.//tr')
        # get all the 'a' tags in each row: each pws has three "a" tags
        pws_a_tags = [row.findall('.//a') for row in rows[1:]]

        # use a list comprehension to get all the url's
        #     the water sys detail link is in the first tag within each pws
        self.urls = [base_url + re.sub(r'\s', '', pws[0].get('href')) for pws in pws_a_tags]
        return self.urls

    def get_pws_names(self, county):
        cnty_urls = self.get_urls(county)
        pws_names = []

        for cnty_url in cnty_urls:
            parsed = parse(request.urlopen(cnty_url))
            doc = parsed.getroot()
            tables = doc.findall('.//table')
            # sys. no., name in 4th table
            systable = tables[3]
            rows = systable.findall('.//tr')

            # name is in the 3rd tr
            sysinfo = self._unpack(rows[2])
            sysinfo = [re.sub(r'(\s+|&nbsp)', ' ', val) for val in sysinfo]
            pws_names.append(sysinfo[1].strip())
        return pws_names

    @staticmethod
    def _unpack(row, kind='td'):
        elts = row.findall('.//%s' % kind)
        # if the tag was found, the list has members and its boolean is True
        if elts:
            return [val.text_content() for val in elts]
        else:
            return None


# main code
if __name__ == "__main__":
    county_pws = CountyPWS()
    the_list = county_pws.get_pws_names('BAILEY')
    # create a dataframe from the list
    df = pd.DataFrame(the_list, columns=['PWS_NUM', 'PWS_NAME', 'URL'])

    # create a Pandas Excel writer using XlsxWriter as the engine.
    xlsfile = county_pws.get_county() + '.PWS.List' + '.xlsx'
    writer = pd.ExcelWriter(xlsfile, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='PWS.List')

    # close the Pandas Excel writer and output the Excel file.
    writer.save()
    # open the file
    file = os.getcwd() + os.sep + xlsfile
    os.startfile(file)
