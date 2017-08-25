# -*- coding: utf-8 -*-
"""
Created on Tue Aug 15 15:03:47 2017

@author: sghosh
"""

import talib
import numpy as np
import pandas
from enum import Enum
#import logging




class EventType(Enum):
    NEW_BAR=1
    NEW_TRADE_IDEA=2
    ORDER_CREATED=3
    ORDER_EXECUTED=4
    ORDER_EXPIRED=5
    ORDER_CANCELLED=6
    END_TEST=7

class Event:
    def __init__(self,t,d):
        self.event_type_=t
        self.event_data_=d

class EventManager:
    
    def __init__(self):
        self.listeners_=[]
        self.event_list_=[]
    
    def enq(self,event):
        self.event_list_.append(event)        
                
    def add_listener(self,event_type,handler):
        self.listeners_.append((event_type,handler))
    
    def handle_all_events(self):
        to_be_removed=[]
        
        list_snap=[]
        for l in self.event_list_:
            list_snap.append(l)

        for event in list_snap:
            for listener in self.listeners_:
                if (listener[0]==event.event_type_):
                    listener[1](event)
            to_be_removed.append(event)
            
        for event in to_be_removed:
            if (event in self.event_list_):
                self.event_list_.remove(event)                
        return len(self.event_list_)
        
class StrategyType (Enum):
    SMA=1

class OrderType(Enum):
    LIMIT=1    
    OCA=2
    
class OrderDirection(Enum):
    BUY=1
    SELL=2

class OrderStatus(Enum):
    CREATED=1
    SUBMITTED=2
    EXECUTED=3
    CANCELLED=4
    
# 
class Order:
    count_=0
    def __init__(self,ticker_name,o_type,direction,price,price2,size,bar_stamp,leg):
        
        self.ticker_name_=ticker_name
        self.type_=o_type
        self.direction_=direction
        self.price_=price
        self.price2_=price2
        self.size_=size
        self.status_=OrderStatus.CREATED
        self.executed_price_=0
        self.created_at_=bar_stamp
        self.executed_at_=0
        self.commssion_=0
        self.leg_=leg
        
        Order.count_=Order.count_+1
        #print ('total order created ', Order.count_)
        
    def __str__(self):
        return 'type={}, direction={}, price={:.2f}, price2={:.2f}, executed_price={:.2f}, created_at={}, executed_at={}, leg={}'.format(
                self.type_,self.direction_,self.price_,self.price2_,self.executed_price_, 
                self.created_at_, self.executed_at_, self.leg_)
    

class TradeIdeaType (Enum):
    LONG=1 
    SHORT=2


class TradeIdea:
    ''' This class represents one trade idea 
    '''
    
    def __init__(self,idea_type,ticker_name,strategy_type,entry,
                 stop_loss,exit_price, bar_stamp):
        self.idea_type_=idea_type
        self.ticker_name_=ticker_name
        self.strategy_type_=strategy_type
        self.entry_=entry
        self.stop_loss_=stop_loss
        self.exit_=exit_price
        self.bar_stamp_=bar_stamp
        


class Trade:
    def __init__(self,idea,start_order,second_leg_order):
        self.ticker_name_=idea.ticker_name_
        self.trade_type_=idea.idea_type_
        self.expected_entry_=start_order.price_
        
        self.expected_stop_loss_=second_leg_order.price_
        self.expected_exit_=second_leg_order.price2_
        self.entry_=start_order.executed_price_
        self.started_=start_order.executed_at_
        
        self.exit_=second_leg_order.executed_price_
        self.ended_=second_leg_order.executed_at_
        self.size_=start_order.size_


    def __str__(self):
        return '{} : entry = {:.2f} ({:2d}) exit= {:.2f} ({:2d}) size={:.2f} =>  p/l {:.2f} '.format(
            self.ticker_name_,self.entry_, self.started_, self.exit_, self.ended_,self.size_, self.pnl() )
        
    def pnl(self):
        return  (self.exit_-self.entry_)*self.size_
        
    def trade_time(self):
        return (self.ended_-self.started_)
    
    
class TradeManager:
    '''
    This class handles the trading of the idea
    Sends the order etc.
    '''
    
    def __init__(self):
        self.completed_trades_=[]
        self.inprogress_trades_=[]
        self.count_=0;

    def initialize(self):
        trading_system().event_mgr().add_listener(EventType.NEW_TRADE_IDEA,self.new_idea_handler)
        trading_system().event_mgr().add_listener(EventType.ORDER_EXECUTED,self.order_executed_handler)

            
    def new_idea_handler(self,new_idea_event):
        idea=new_idea_event.event_data_
        sz=trading_system().portfolio().get_order_size(idea)
        if (sz>0):            
            
            if (idea.idea_type_==TradeIdeaType.LONG):
                first_leg_order_dir=OrderDirection.BUY
                second_leg_order_dir=OrderDirection.SELL
            else:
                first_leg_order_dir=OrderDirection.SELL
                second_leg_order_dir=OrderDirection.BUY
                    
            first_leg_order = Order(idea.ticker_name_,OrderType.LIMIT,first_leg_order_dir,idea.entry_,0,sz,idea.bar_stamp_,1)
            second_leg_order = Order(idea.ticker_name_,OrderType.OCA,second_leg_order_dir,idea.stop_loss_,idea.exit_,sz,0,2)
            trading_system().event_mgr().enq(Event(EventType.ORDER_CREATED,first_leg_order))
            self.inprogress_trades_.append({'idea':idea,'first_leg':first_leg_order,'second_leg':second_leg_order})
                        
        return True
        
    def order_executed_handler(self,order_executed_event):
        order=order_executed_event.event_data_
        completed_trade=None   
        found=False
        self.count_=self.count_+1
        for t in self.inprogress_trades_:
            if (order==t['first_leg']):                
                second_leg_order=t['second_leg']
                second_leg_order.created_at_=order.executed_at_
                trading_system().event_mgr().enq(Event(EventType.ORDER_CREATED,second_leg_order))
                found=True
                break
            elif (order==t['second_leg']):
                completed_trade=t
                found=True
                break
            
        
        if (not found):
            print ('unmatched order ' , order.order_direction_,order.order_type_)
        if (completed_trade):
            self.completed_trades_.append(
                    Trade(completed_trade['idea'],completed_trade['first_leg'],
                          completed_trade['second_leg']))
            self.inprogress_trades_.remove(completed_trade)
            
        return True
    
    def trade_log(self):
        pnl=0
        hit=0
        trade_time=[]
        for t in (self.completed_trades_):
            print (t)
            l=t.pnl()
            if (l>0):
                hit=hit+1
            pnl=pnl+l
            trade_time.append(t.trade_time())
            
        print ('Statistics :')
        total=len(self.completed_trades_)
        com=trading_system().broker().commission() 
        print ('total # of trades: {:2d}, winning trade: {:2d},  hit ratio: {:.2f}'.
               format(total, hit, hit/total ) )        
        print ('total commission paid: {:.2f}'.format(total*2*com))
        print ('P/L:       {:.2f}'.format(pnl- (total*2*com)))
        #wait_time=np.mean(trade_time)
        
        
class Broker:
    
    def __init__(self):
        self.commision_=5.0
        self.pending_order_list_=[]
        self.bar_count_=0
        self.count_=0
        
    def initialize(self):
        trading_system().event_mgr().add_listener(EventType.ORDER_CREATED,self.order_created_handler)
        trading_system().event_mgr().add_listener(EventType.NEW_BAR,self.new_bar_handler)
        trading_system().event_mgr().add_listener(EventType.END_TEST,self.end_test_handler)

    
    def order_created_handler(self,new_order_event):
        order = new_order_event.event_data_
        self.pending_order_list_.append(order)


    def new_bar_handler(self,new_bar_event):        
        self.bar_count_=self.bar_count_+1
        ticker_name=new_bar_event.event_data_[0]
        new_bar=new_bar_event.event_data_[1]
        to_be_removed_list=[]
        for order in self.pending_order_list_:
            if (order.ticker_name_==ticker_name): 
                if (self.bar_count_ > order.created_at_+10):
                    if (order.leg_==2):
                        #print ('time out case [',str(order), '], [',str(new_bar),'] --- ', new_bar[0])
                        self.execute(order,new_bar[0])
                        to_be_removed_list.append(order)
                else:
                    execute_price=self.can_execute(order,new_bar)
                    if (execute_price>0.0):
                        #print ('limit case [',str(order), '], [',str(new_bar),']  --- ' , execute_price )
                        self.execute(order,execute_price)
                        to_be_removed_list.append(order)

        for o in to_be_removed_list:
            self.pending_order_list_.remove(o)

    def can_execute(self,order,latest_bar):        
        execute_price=0.0
        if (order.leg_==1):            
            if (order.type_==OrderType.LIMIT):
                if (order.price_ < latest_bar[1] and order.price_ > latest_bar[2]):                
                    execute_price=order.price_
        else:
            if (order.type_==OrderType.OCA):
                if (order.direction_==OrderDirection.SELL):
                    if (order.price_ > latest_bar[0]):
                        execute_price=latest_bar[0]
                else:
                    if (order.price_ < latest_bar[0]):
                        execute_price=latest_bar[0]
                
                if (order.price2_ < latest_bar[1] and order.price2_ > latest_bar[2]):                
                    execute_price=order.price2_
                
        return execute_price
    
    def execute(self,order,execute_price):
        order.executed_price_=execute_price
        order.status_=OrderStatus.EXECUTED
        order.commission_=self.commision_
        order.executed_at_=self.bar_count_
        trading_system().event_mgr().enq(Event(EventType.ORDER_EXECUTED,order))
        self.count_=self.count_+1

    def end_test_handler(self,end_test_event):
        last_bar=end_test_event.event_data_[1]
        ticker_name=end_test_event.event_data_[0]
        to_be_removed_list=[]
        #print ('total number of pending orders ', len(self.pending_order_list_) )
        for order in self.pending_order_list_:
            #print('end_test_handler  ', order.direction_, order.status_, order.type_)
            if (order.ticker_name_==ticker_name):                 
                if (order.leg_==2):
                    #print ('last bar [',str(order), '], [',str(last_bar),'] --- ', last_bar[0])
                    self.execute(order,last_bar[0])
                    to_be_removed_list.append(order)

        for o in to_be_removed_list:
            self.pending_order_list_.remove(o)

        
    def set_commision(self,com):
        self.commision_=com

    def commission(self):
        return self.commision_
    
class DataStore:
    def __init__(self):
        self.stock_data_={}

    def initialize(self):
        trading_system().event_mgr().add_listener(EventType.NEW_BAR,self.new_bar_handler)
    
    def new_bar_handler(self,new_bar_event):
        new_bar_data=new_bar_event.event_data_
        ticker=new_bar_data[0]
        df=new_bar_data[1]
        if (ticker not in self.stock_data_):
            self.stock_data_[ticker]={ 'open':[], 'high':[],
                                        'low':[], 'close':[], 'volume':[] }
        self.stock_data_[ticker]['open'].append(df[0])
        self.stock_data_[ticker]['high'].append(df[1])
        self.stock_data_[ticker]['low'].append(df[2])
        self.stock_data_[ticker]['close'].append(df[3])
        self.stock_data_[ticker]['volume'].append(df[4])


    def ohlc(self,ticker_name):        
        return self.stock_data_[ticker_name]
            

class Strategy:
    pass

class SMAStrategy(Strategy):    
    def __init__(self):
        self.strategy_type_=StrategyType.SMA
        self.bar_count_=0

    def initialize(self):
        trading_system().event_mgr().add_listener(EventType.NEW_BAR,self.new_bar_handler)

        
    def new_bar_handler(self,new_bar_event):
        self.bar_count_=self.bar_count_+1
        ticker_name=new_bar_event.event_data_[0]
        df=new_bar_event.event_data_[1]
        last_close=df[3]
        close_array=np.array(trading_system().data_store().ohlc(ticker_name)['close'])        
        sma=talib.SMA(close_array,timeperiod=50)
        
        if (last_close> sma[-1]):
            new_tidea=TradeIdea(TradeIdeaType.LONG,ticker_name=ticker_name,
                                    strategy_type=self.strategy_type_,
                                    entry=sma[-1],
                                    stop_loss=sma[-1]*0.98,
                                    exit_price=sma[-1]*1.15,
                                    bar_stamp=self.bar_count_)
            trading_system().event_mgr().enq(Event(EventType.NEW_TRADE_IDEA,new_tidea))         

#
# Portfolio holds the cash and the stock positions
#
class PortFolio:

    def __init__(self):
        self.holdings_={}
        self.cash_=0
        self.count_=0

    def initialize(self):
        trading_system().event_mgr().add_listener(EventType.ORDER_EXECUTED,self.order_executed_handler)
        
    def order_executed_handler(self,order_event):
        order=order_event.event_data_
        if (order.direction_==OrderDirection.BUY):
            f=+1
        else:
            f=-1

                
        if order.ticker_name_ in self.holdings_:
            self.holdings_[order.ticker_name_]=self.holdings_[order.ticker_name_]+(f*order.size_)            
        else:
            self.holdings_[order.ticker_name_]=(f*order.size_)
        
        self.cash_=self.cash_-(f*order.size_*order.executed_price_)-order.commission_

        

        
    def get_valuation(self):
        total=self.cash_
        for h in self.holdings_.items():
            ticker_name=h[0]
            sz=h[1]
            cmp=trading_system().data_store().ohlc(ticker_name)['close'][-1]
            print (self.cash_,cmp,sz,cmp*sz,self.cash_+(sz*cmp))
            
            total=total+(sz*cmp)
        return total
    
    def set_cash(self,cash_amt):
        self.cash_=cash_amt
    
    
    def get_order_size(self,idea):
        
        if (idea.ticker_name_ in self.holdings_):
            if (idea.idea_type_ ==TradeIdeaType.LONG):
               if (self.holdings_[idea.ticker_name_]<0):
                    return 0    
                
            else:
                if (self.holdings_[idea.ticker_name_]>0):
                    return 0
            
            if (abs(self.holdings_[idea.ticker_name_])*idea.entry_>0.5*self.cash_):
                return 0
        
        
        return int(self.cash_*.2/idea.entry_)

# 
class FeedSystem:

    def __init__(self):
        self.st_data_={}
        pass
    
    def add_ticker(self,ticker_name):
        df=pandas.read_csv('C:/Users/sghosh/Desktop/tidea/daily/{}.csv'.format(ticker_name))
        self.st_data_[ticker_name]=[df,0]
        #self.df['date'] = pandas.to_datetime(self.df['date'])
    
    def next_bar(self,ticker_name):
        current_ind=self.st_data_[ticker_name][1]
        if (current_ind==len(self.st_data_[ticker_name][0])):
            return []
        else:
            ar=self.bar_at_index(ticker_name,current_ind)
            self.st_data_[ticker_name][1]=current_ind+1
            return ar                
    
    def last_bar(self,ticker_name):
        
        current_ind=self.st_data_[ticker_name][1]
        if (current_ind==len(self.st_data_[ticker_name][0])):
            return []        
        return self.bar_at_index(ticker_name,current_ind)
    
    def bar_at_index(self,ticker_name,current_ind):
        ar=[self.st_data_[ticker_name][0]['Open'][current_ind], self.st_data_[ticker_name][0]['High'][current_ind], 
            self.st_data_[ticker_name][0]['Low'][current_ind], self.st_data_[ticker_name][0]['Close'][current_ind], 
            self.st_data_[ticker_name][0]['Volume'][current_ind]]
        return ar                
        
# The main platform
class Platform:
    
    def __init__(self):
        self.stock_data_={}
        
    def run(self):        
        done=False
        last_df=[]
        while (not done):            
            
            # check queue if any event is to be addressed
            trading_system().event_mgr().handle_all_events()  
            
            # Get feed and 
            for ticker in (trading_system().ticker_list()):
                df=trading_system().feed().next_bar(ticker)
                if (len(df)==0):
                    trading_system().event_mgr().enq(Event(EventType.END_TEST,[ticker,last_df]))
                    done=True
                    break
                else:
                    trading_system().event_mgr().enq(Event(EventType.NEW_BAR,[ticker,df]))
                    last_df=df

        # check queue if any event is to be addressed
        while (trading_system().event_mgr().handle_all_events()):
            pass

    
    def get_cmp(self,ticker_name):
        return self.stock_data[ticker_name]['close'][-1]

'''
This class binds everything together 
'''
class TradingSystem:
    
    def __init__(self):
        self.plat_=Platform()
        self.port_=PortFolio()
        self.trade_mgr_=TradeManager()
        self.event_mgr_=EventManager()
        self.feed_=FeedSystem()
        self.broker_=Broker()
        self.strategies_=[]
        self.ticker_list_=[]
        self.data_store_=DataStore()

    def initialize(self):
        self.trade_mgr_.initialize()
        self.broker_.initialize()
        self.data_store_.initialize()
        self.port_.initialize()

    
    def platform(self):
        return self.plat_

    def trade_mgr(self):
        return self.trade_mgr_
    
    def event_mgr(self):
        return self.event_mgr_
    
    def portfolio(self):
        return self.port_

    def feed(self):
        return self.feed_
    
    def strategies(self):
        return self.strategies_
    
    def add_ticker_feed(self,feed):
        self.feeds_.append(feed)
    
    def add_market_feed(self,feed):
        self.market_feed_.append(feed)

    def add_strategy(self,st):
        self.strategies_.append(st)        
        st.initialize()

        
    def broker(self):
        return self.broker_
    
    def add_ticker_list(self,ticker_list):
        for ticker in ticker_list:
            self.feed_.add_ticker(ticker)
            self.ticker_list_.append(ticker)

    def ticker_list(self):
        return self.ticker_list_
    
    def data_store(self):
        return self.data_store_
    
def back_test(ticker_list) : #,start_date,end_date,strategy_type):
    print ('Backtesting ', ticker_list, ' :')
    trading_system().add_ticker_list(ticker_list)
    sma_strategy=SMAStrategy()
    trading_system().add_strategy(sma_strategy)
    trading_system().portfolio().set_cash(100000)
    
    before=trading_system().portfolio().get_valuation()
    print ("Portfolio value before test {:.2f}".format(before))
    trading_system().platform().run()
    trading_system().trade_mgr().trade_log()
    after=trading_system().portfolio().get_valuation()
    print ("Portfolio value after test {:.2f} === PNL: {:.2f} ({:.2f}%)".format(after,after-before, (100*(after-before))/before ))


trade_system=TradingSystem ()
def trading_system():
    return trade_system
 
trade_system.initialize()



back_test(['XOM'])