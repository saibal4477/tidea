
import time
import datetime
import numpy as np
import quandl
import pandas as pd
from pandas.tseries.offsets import BDay
import talib
import urllib
from bs4 import BeautifulSoup


#####
##  Stock class 
#####
class Stock :


    # Get the hourly data
    def get_hourly_data(ticker_name, period, window):
        url_root1 = 'https://www.google.com/finance/getprices?i=' + str(period) + '&p=' + str(window) + 'd&q=' + ticker_name
        response = urllib.request.urlopen(url_root1)
        csv = response.read().decode('utf-8').split('\n')

        ll = [[] for i in range(6)]
        for bar in range(7,len(csv)):
            if csv[bar].count(',')!=5: continue
            each_entry = csv[bar].split(',')
            offset=each_entry[0]
            # offset
            if offset[0]=='a':
                day = float(offset[1:])
                offset = 0
            else:
                offset = float(offset)
            each_entry[0]=datetime.datetime.fromtimestamp(day+(period*offset))  
            for i in range(1,5):
                each_entry[i]=float(each_entry[i])
            for i in range(6):
                ll[i].append(each_entry[i])

        df=pd.DataFrame({'date': pd.Series(ll[0]),
                         'open':pd.Series(ll[4]),
                         'high':pd.Series(ll[3]),
                         'low':pd.Series(ll[2]),
                         'close':pd.Series(ll[1]),
                         'volume':pd.Series(ll[5])}  )
                        
        return df

    
    # Get the stock price 
    def get_daily_price(ticker_name, duration, refresh_now=False):
        if (refresh_now):
            quandl.ApiConfig.api_key = 'onPJFXR13SZYuYp3UZsK'
            df=quandl.get_table('WIKI/PRICES', ticker=ticker_name, date={'gte': pd.datetime.today() - duration*BDay() })
            df.to_csv('{}.csv'.format(ticker_name))
        else:
            df=pd.read_csv('{}.csv'.format(ticker_name))
        df['date'] = pd.to_datetime(df['date'])
        return df

    # routine to get all S&P ticker names
    def get_sp_ticker_name():
        SITE = "http://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        hdr = {'User-Agent': 'Mozilla/5.0'}
        #req = urllib.Request(SITE, headers=hdr)
        page = urllib.request.urlopen(SITE)
        soup = BeautifulSoup(page)

        table = soup.find('table', {'class': 'wikitable sortable'})
        sector_tickers = dict()
        for row in table.findAll('tr'):
            col = row.findAll('td')
            if len(col) > 0:
                sector = str(col[3].string.strip()).lower().replace(' ', '_')
                ticker = str(col[0].string.strip())
                if sector not in sector_tickers:
                    sector_tickers[sector] = list()
                sector_tickers[sector].append(ticker)
        print (sector_tickers)
        return sector_tickers


    # get ticker name
    def get_all_ticker_name():
        df_nasdaq=pd.read_csv('nasdaq-companylist.csv')
        df_nyse=pd.read_csv('AMEX-companylist.csv')
        df_amex=pd.read_csv('NYSE-companylist.csv')
        
        for i in [df_nasdaq,df_nyse,df_amex]:
            i.drop(['ADR TSO','Summary Quote','IPOyear'],axis=1,inplace=True)
            i=i[df_nasdaq['LastSale']!='n/a']
            i['LastSale']=i['LastSale'].astype(float)
            i=i[i['LastSale']>10]
            i['quote_info']=i['Symbol'].apply(Stock.get_stock_quote)
            i.write_csv('st{}.csv'.format(i))        

    #def get_quote(ticker_symbol):
    def get_stock_quote(ticker_symbol):   
        url = 'http://finance.google.com/finance/info?q=%s' % ticker_symbol
        lines =[]
        try:
            lines = urllib.request.urlopen(url).read().decode('utf-8').splitlines()
            print (lines)
        except urllib.error.HTTPError:
            pass
        return lines
        #return json.loads(''.join([x for x in lines if x not in ('// [', ']')]))
        


