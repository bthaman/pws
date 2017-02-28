"""
author: bill thaman
"""
from tkinter import *
from tkinter import ttk
import pandas as pd
import os
from pws_list_v2 import *
import sqlite3


class App(ttk.LabelFrame):
    def __init__(self, buyers=True, purchases=True):
        # create the gui
        self.root = Tk()
        self.root.title('PWS Data Retrieval')
        ttk.LabelFrame.__init__(self, self.root, text=None)
        self.padding = '6, 6, 12, 12'
        self.grid(column=0, row=0, sticky=(N, W, E, S))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.entered_county = StringVar()
        self.entered_county.trace('w', self.handle_event)

        cmb_cnty = ttk.Combobox(self, textvariable=self.entered_county)
        cmb_cnty.grid(column=2, row=1, sticky=E)
        # get the counties as a list
        cmb_cnty['values'] = self.get_county()
        # following line sets a default value
        # cmb_cnty.current(0)

        ttk.Label(self, text="County").grid(column=1, row=1, sticky=W)
        self.btn_ok = ttk.Button(self, text='OK', width=7, command=self.okclick)
        self.btn_ok.grid(column=3, row=1, sticky='E')
        self.btn_ok.configure(state='disabled')
        for child in self.winfo_children():
            child.grid_configure(padx=5, pady=5)
        cmb_cnty.focus()
        # binding causes the button event to run when window is closed
        # root.bind('<Return>', okclick())

        self.buyers = buyers
        self.purchases = purchases
        self.county = None
        self.df = pd.DataFrame()
        self.df_buyer = pd.DataFrame()
        self.df_source = pd.DataFrame()
        self.df_purchase = pd.DataFrame()
        self.pwsDict = {}
        self.buyerDict = {}
        self.sourceDict = {}
        self.purchaseDict = {}

    def handle_event(self, *args):
        if self.entered_county.get():
            self.btn_ok.configure(state='normal')
        else:
            self.btn_ok.configure(state='disabled')

    def okclick(self):
        self.county = self.entered_county.get()
        print(self.county)

        # reset dataframes and dictionaries
        self.df = pd.DataFrame()
        self.df_buyer = pd.DataFrame()
        self.df_source = pd.DataFrame()
        self.df_purchase = pd.DataFrame()
        self.pwsDict = {}
        self.buyerDict = {}
        self.sourceDict = {}
        self.purchaseDict = {}

        # create a Pandas Excel writer using XlsxWriter as the engine.
        xlsfile = os.path.join(os.getcwd(), 'output', self.county + '.xlsx')
        writer = pd.ExcelWriter(xlsfile, engine='xlsxwriter')

        # get the list of counties and the pws detail for each
        #     get a county pws object
        county_pws = CountyPWS()
        #     get the urls for the selected county
        #     can be sliced --> county_pws.get_url(self.county.upper())[0:3]
        pws_list = county_pws.get_urls(self.county.upper())
        max_to_process = len(pws_list)
        for i, url in enumerate(pws_list[:max_to_process]):
            print(str(int(round((i + 1) / max_to_process * 100, 0))) + '% : ' + url)
            self.pws_detail(url)

        # convert the dataframe to an XlsxWriter Excel object.
        self.df.to_excel(writer, sheet_name='Detail')
        self.df_source.to_excel(writer, sheet_name='Sources')

        if self.buyers:
            self.df_buyer.to_excel(writer, sheet_name='Buyers')
        if self.purchases:
            self.df_purchase.to_excel(writer, sheet_name='Purchases')

        # close the Pandas Excel writer and output the Excel file.
        writer.save()
        # open the file
        file = xlsfile
        os.startfile(file)

        # don't quit so that another county can be selected
        # self.root.quit()

    def pws_detail(self, url):
        buyertable = None
        purchasetable = None
        flowratetable = None
        sourcetable = None
        measurestable = None

        # initialize the dictionaries
        self.pwsDict = {'Sys Num': '', 'Sys Name': '', 'Sys Type': '', 'Primary Source Type': '', 'Population': '',
                        'Contact': '', 'Business Phone': '', 'Mobile Phone': '', 'Max Daily Demand': '',
                        'Provided Prod. Capacity': '', 'Provided Service Pump Capacity': '', 'Avg. Daily Usage': '',
                        'Total Storage Cap.': '', 'Total Pressure Tank Cap.': '', 'Elevated Storage Cap.': ''}
        self.buyerDict = {'Sys Name': '', 'Sys Num': '', 'Buyer': '', 'Buyer Pop': '', 'Buyer Status': ''}
        self.purchaseDict = {'Sys Name': '', 'Sys Num': '', 'Purchase Info': ''}
        self.sourceDict = {'Sys Name': '', 'Sys Num': '', 'Source Name': '', 'Type': '',
                           'Activity': '', 'Availability': ''}

        parsed = parse(request.urlopen(url))
        doc = parsed.getroot()
        tables = doc.findall('.//table')

        # sys. no., name, pop in 4th table
        systable = tables[3]
        rows = systable.findall('.//tr')
        sysinfo = self._unpack(rows[1])
        sysinfo = ["".join(x.split()) for x in sysinfo]
        self.pwsDict['Sys Num'] = sysinfo[1].strip()
        self.pwsDict['Sys Type'] = sysinfo[3].strip()

        # name is in the 3rd tr
        sysinfo = self._unpack(rows[2])
        sysinfo = [re.sub(r'(\s+|&nbsp)', ' ', val) for val in sysinfo]
        self.pwsDict['Sys Name'] = sysinfo[1].strip()
        self.pwsDict['Primary Source Type'] = sysinfo[3].strip()

        # pop is in the 6th tr
        sysinfo = self._unpack(rows[5])
        sysinfo = ["".join(x.split()) for x in sysinfo]
        self.pwsDict['Population'] = sysinfo[1].strip()

        # contact in the 5th table
        systable = tables[4]
        rows = systable.findall('.//tr')
        if len(rows) >= 3:
            sysinfo = self._unpack(rows[2])
            sysinfo = [re.sub(r'(\s+|&nbsp)', ' ', val) for val in sysinfo]
            self.pwsDict['Contact'] = sysinfo[1].strip()
            if len(sysinfo) >= 5:
                self.pwsDict['Business Phone'] = sysinfo[4].strip()
            if len(sysinfo) >= 7:
                self.pwsDict['Mobile Phone'] = sysinfo[6].strip()

        # the number of buyers and sellers dictate how many tables there are, so certain tables cannot always be
        #     found in the same location. have to look at the th values to find them.
        for table in tables:
            rows = table.findall('.//tr')
            # if rows has list elements, its boolean is True; if an empty list, False
            if rows:
                header = self._unpack(rows[0], kind='th')
                if header is not None:
                    if header[0] == 'Buyers of Water':
                        buyertable = table
                    elif header[0] == 'Water Purchases':
                        purchasetable = table
                    elif header[0] == 'Sources of Water':
                        sourcetable = table
                    elif header[0] == 'WS Flow Rates':
                        flowratetable = table
                    elif header[0] == 'WS Measures':
                        measurestable = table

        # WS Flow Rates table
        if flowratetable is not None:
            rows = flowratetable.findall('.//tr')
            if len(rows) >= 3:
                flowinfo = self._unpack(rows[2])
                flowinfo = [re.sub(r'(\s+|&nbsp)', ' ', val) for val in flowinfo]
                self.pwsDict['Max Daily Demand'] = flowinfo[1].strip() + ' (' + flowinfo[2].strip() + ')'

            if len(rows) >= 4:
                flowinfo = self._unpack(rows[3])
                flowinfo = [re.sub(r'(\s+|&nbsp)', ' ', val) for val in flowinfo]
                self.pwsDict['Provided Prod. Capacity'] = flowinfo[1].strip() + ' (' + flowinfo[2].strip() + ')'

            if len(rows) >= 5:
                flowinfo = self._unpack(rows[4])
                flowinfo = [re.sub(r'(\s+|&nbsp)', ' ', val) for val in flowinfo]
                self.pwsDict['Provided Service Pump Capacity'] = flowinfo[1].strip() + ' (' + flowinfo[2].strip() + ')'

            if len(rows) >= 6:
                flowinfo = self._unpack(rows[5])
                flowinfo = [re.sub(r'(\s+|&nbsp)', ' ', val) for val in flowinfo]
                self.pwsDict['Avg. Daily Usage'] = flowinfo[1].strip() + ' (' + flowinfo[2].strip() + ')'

        # WS Measures table
        if measurestable is not None:
            rows = measurestable.findall('.//tr')
            if len(rows) >= 3:
                flowinfo = self._unpack(rows[2])
                flowinfo = [re.sub(r'(\s+|&nbsp)', ' ', val) for val in flowinfo]
                self.pwsDict['Total Storage Cap.'] = flowinfo[1].strip() + ' (' + flowinfo[2].strip() + ')'

            if len(rows) >= 4:
                flowinfo = self._unpack(rows[3])
                flowinfo = [re.sub(r'(\s+|&nbsp)', ' ', val) for val in flowinfo]
                self.pwsDict['Total Pressure Tank Cap.'] = flowinfo[1].strip() + ' (' + flowinfo[2].strip() + ')'

            if len(rows) >= 5:
                flowinfo = self._unpack(rows[4])
                flowinfo = [re.sub(r'(\s+|&nbsp)', ' ', val) for val in flowinfo]
                self.pwsDict['Elevated Storage Cap.'] = flowinfo[1].strip() + ' (' + flowinfo[2].strip() + ')'

        # add dictionary to dataframe
        self.df = self.df.append(self.pwsDict, ignore_index=True)

        # put columns in correct order
        self.df = self.df[['Sys Num', 'Sys Name', 'Sys Type', 'Primary Source Type', 'Population',
                           'Contact', 'Business Phone', 'Mobile Phone', 'Max Daily Demand', 'Provided Prod. Capacity',
                           'Provided Service Pump Capacity', 'Avg. Daily Usage', 'Total Storage Cap.',
                           'Total Pressure Tank Cap.', 'Elevated Storage Cap.']]

        ###################
        # get the sources #
        ###################
        self.sourceDict['Sys Name'] = self.pwsDict['Sys Name']
        self.sourceDict['Sys Num'] = self.pwsDict['Sys Num']
        if sourcetable is not None:
            rows = sourcetable.findall('.//tr')
            # get sources as a list of lists
            if len(rows) >= 3:
                sources = [self._unpack(row) for row in rows[2:]]
                for xlr, row in enumerate(sources):
                    for xlc, val in enumerate(row):
                        if xlc == 0:
                            self.sourceDict['Source Name'] = val.strip()
                        if xlc == 1:
                            self.sourceDict['Type'] = val.strip()
                        if xlc == 2:
                            self.sourceDict['Activity'] = val.strip()
                        if xlc == 3:
                            self.sourceDict['Availability'] = val.strip()
                    self.df_source = self.df_source.append(self.sourceDict, ignore_index=True)
            else:
                # there are no sources
                self.sourceDict['Source Name'] = 'NO SOURCES LISTED'
                self.df_source = self.df_source.append(self.sourceDict, ignore_index=True)
        else:
            self.sourceDict['Source Name'] = 'SOURCE TABLE NOT FOUND'
            self.df_source = self.df_source.append(self.sourceDict, ignore_index=True)
        self.df_source = self.df_source[['Sys Name', 'Sys Num', 'Source Name', 'Type', 'Activity', 'Availability']]

        ###################
        # get the buyers  #
        ###################
        try:
            self.buyerDict['Sys Name'] = self.pwsDict['Sys Name']
            self.buyerDict['Sys Num'] = self.pwsDict['Sys Num']
            if buyertable is not None and self.buyers:
                rows = buyertable.findall('.//tr')
                if len(rows) >= 3:
                    buyers = [self._unpack(row) for row in rows[2:]]
                    # buyers contains who is buying, their population, and their status...separated by '/'
                    #     remove the whitespace
                    buyers = [re.sub(r'(\s+|&nbsp)', ' ', val) for vals in buyers for val in vals]
                    # split in '/', creating a list of lists
                    buyers_split = [x.split('/') for x in buyers]
                    for xlr, row in enumerate(buyers_split):
                        for xlc, val in enumerate(row):
                            if xlc == 0:
                                self.buyerDict['Buyer'] = val.strip()
                            if xlc == 1:
                                self.buyerDict['Buyer Pop'] = val.strip()
                            if xlc == 2:
                                self.buyerDict['Buyer Status'] = val.strip()
                        self.df_buyer = self.df_buyer.append(self.buyerDict, ignore_index=True)
                        if xlr > 750:
                            self.buyerDict['Buyer'] = 'BUYER DATA TRUNCATED DUE TO LENGTH. SEE TCEQ FOR MORE INFO.'
                            self.buyerDict['Buyer Pop'] = ''
                            self.buyerDict['Buyer Status'] = ''
                            self.df_buyer = self.df_buyer.append(self.buyerDict, ignore_index=True)
                            break
            else:
                self.buyerDict['Buyer'] = 'BUYER TABLE NOT FOUND'
                self.df_buyer = self.df_buyer.append(self.buyerDict, ignore_index=True)
        except Exception:
            self.buyerDict['Buyer'] = 'PROBLEM READING BUYER TABLE IN HTML'
            self.df_buyer = self.df_buyer.append(self.buyerDict, ignore_index=True)

        self.df_buyer = self.df_buyer[['Sys Name', 'Sys Num', 'Buyer', 'Buyer Pop', 'Buyer Status']]

        ######################
        # get the purchases  #
        ######################
        try:
            self.purchaseDict['Sys Name'] = self.pwsDict['Sys Name']
            self.purchaseDict['Sys Num'] = self.pwsDict['Sys Num']
            if purchasetable is not None and self.purchases:
                rows = purchasetable.findall('.//tr')
                if len(rows) >= 3:
                    purchases = [self._unpack(row) for row in rows[2:]]
                    # remove the whitespace
                    purchases = [re.sub(r'(\s+|&nbsp)', ' ', val) for vals in purchases for val in vals]
                    for xlr, row in enumerate(purchases):
                        self.purchaseDict['Purchase Info'] = row.strip()
                        self.df_purchase = self.df_purchase.append(self.purchaseDict, ignore_index=True)
                        if xlr > 750:
                            self.purchaseDict[
                                'Purchase Info'] = 'PURCHASE DATA TRUNCATED DUE TO LENGTH: SEE TCEQ FOR MORE INFO'
                            self.df_purchase = self.df_purchase.append(self.purchaseDict, ignore_index=True)
                            break
            else:
                self.purchaseDict['Purchase Info'] = 'PURCHASE TABLE NOT FOUND'
                self.df_purchase = self.df_purchase.append(self.purchaseDict, ignore_index=True)
        except Exception:
            self.purchaseDict['Purchase Info'] = 'PURCHASE TABLE NOT FOUND'
            self.df_purchase = self.df_purchase.append(self.purchaseDict, ignore_index=True)

        self.df_purchase = self.df_purchase[['Sys Name', 'Sys Num', 'Purchase Info']]

    @staticmethod
    def _unpack(row, kind='td'):
        elts = row.findall('.//%s' % kind)
        # if the tag was found, the list has members and its boolean is True
        if elts:
            return [val.text_content() for val in elts]
        else:
            return None

    @staticmethod
    def get_county():
        db = os.getcwd() + os.sep + 'pws.db'
        conn = sqlite3.connect(db)
        conn.text_factory = conn.text_factory = lambda x: str(x, 'latin1')
        sql = "select cnty_name from county order by cnty_name"
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        # rows is a list of tuples, and tkinter combobox values need a list of strings
        # use list comprehension to convert to a list of strings
        cnty_list = [str(row[0]) for row in rows]
        conn.close()
        return cnty_list

    def show(self):
        self.root.mainloop()


# app = App(buyers=True, purchases=True)
# app.show()
########################################################################################################################
# main code
########################################################################################################################
if __name__ == "__main__":
    app = App(buyers=True, purchases=True)
    app.show()
