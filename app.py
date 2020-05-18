
import datetime
from datetime import timedelta
import sys
import linecache
import os
import traceback
from threading import Timer
import ccxt
import requests
import json
import math
from time import sleep
d         = datetime.datetime.now()  
epoch = datetime.datetime(1970,1,1)
start_time = int((d - epoch).total_seconds())

  
# Function to display hostname and 
# IP address 
host_ip = None

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    string = 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)
    print(string)
def pprint(string):
    log = 'log.txt'
    with open(log, "a") as myfile:
        myfile.write(datetime.datetime.utcnow().strftime( '%Y-%m-%d %H:%M:%S' ) + ', line: ' + str(inspect.currentframe().f_back.f_lineno)  + ': ' + str(string) + '\n')
try: 
    
    host_ip = requests.get("https://api.ipify.org?format=json").json()['ip']

    
except: 
    PrintException()

with open('conf.json', 'r') as conf:
    data=conf.read()

# parse file
obj = json.loads(data)
ftxKEY     = obj["apikey"]#"NqOlVRaqGM-XCX0cpf67UYxvT2tcB56SHlS-tlB-"#"VC4d7Pj1"
ftxSECRET  = obj["apisecret"]#gnBQZHa8-cT1E-p0YyNqHkx9Y_8bdk"#"IB4VEP26OzTNUt4JhNILOW9aDuzctbGs_K6izxQG2dI"
if 'ftxkey' in os.environ:
    ftxKEY = os.environ['ftxkey']

    ftxSECRET = os.environ['ftxsecret']
maxmargin = float(obj['maxusedmargin'])
percentbalancefororders = float(obj['percentbalancefororders']) # 0.1% of balance / maxlev will be used in each order
percentbalancefororders = percentbalancefororders / 100
testing = obj['testing']

SECONDS_IN_DAY    = 3600 * 24
SECONDS_IN_YEAR  = 365 * SECONDS_IN_DAY

class FTXTaker( object ):
    
    def __init__( self, test=testing ):
        self.ftx = None
        self.test = test
        self.lts            = []
        self.bal = None
        self.bal_init = None
        self.bal_btc = None
        self.bal_btc_init = None
        self.positions = {}
        self.margin = None
        self.skew_size = {}
        self.IM = 0
        self.LEV = 0
        self.mean_looptimes    = []
        self.mean_looptime = 1
        self.start_time      = datetime.datetime.utcnow()
    def create_client( self ):
        self.ftx     = ccxt.ftx({
            'enableRateLimit': True,
            'apiKey': ftxKEY,   
            'secret': ftxSECRET,
        })
    def check_balance(self):
        bal2 = self.ftx.fetchBalance()
        newbal = 0
        for coin in bal2['info']['result']:
            newbal = newbal + coin['usdValue']
        self.bal = newbal

        self.bal_btc = self.bal / self.get_spot()
        if self.bal_init == None:
            self.bal_init = self.bal
            self.bal_btc_init = self.bal_btc
        marginftx = 0.1
        marginbinance = 0.1
        
        if self.ftx.privateGetAccount()['result']['marginFraction'] is not None:
            self.margin = (1 / self.ftx.privateGetAccount()['result']['marginFraction']) 
            #print(marginftx)

    def get_bbo( self, contract ): # Get best b/o excluding own orders
        try:
            
            ob      = self.ftx.fetchOrderBook( contract)
            bids    = ob[ 'bids' ]
            asks    = ob[ 'asks' ]
       
            #best_bid = self.get_spot(contract)
            #best_ask = best_bid
            try:
                best_bid    = bids[0][0]
                best_ask    = asks[0][0]
            except:
                PrintException()
            
            print({'bid': best_bid, 'ask': best_ask})
            return { 'bid': best_bid, 'ask': best_ask }
        except: 
            PrintException()
    def post_info( self ):
        positionsToPost = {}
        for pos in self.positions:
            if self.positions[pos]['usdValue'] != 0:
                positionsToPost[pos] = self.positions[pos]
        data = {'start_time': start_time, 'balance': self.bal, 'positions': positionsToPost, 'IP': host_ip}
        print(data)
        """
        lt = 'ETHBEAR/USDT'
        lorm = "market"
        direction = 'buy'
        gogo = True
        prc = self.get_bbo(lt)['bid']

        qty = self.bal * maxmargin * percentbalancefororders 
        qty = qty / prc
        if lt in self.positions:
            if self.positions[lt]['usdValue'] is not None and self.margin is not None:
                if direction == 'buy' and self.positions[lt]['usdValue'] > 0 and self.margin > maxmargin:
                    gogo = False
                if  direction == 'sell' and self.positions[lt]['usdValue'] < 0 and self.margin > maxmargin:
                    gogo = False
        print(gogo)
        if gogo == True:
            r = self.ftx.createOrder(  lt, lorm, direction, qty)   
            print(r)
        """
        if self.test == False:

            posted = requests.post("http://someurl:someport/info_updatte", data=data, verify=False, timeout=5)
            print(posted)
            r = Timer(60, self.post_info, ())
            r.start() 
    def get_spot( self ):
        return self.get_bbo('BTC-PERP')['bid']
    def output_status( self ):
        

        
        now  = datetime.datetime.utcnow()
        days    = ( now - self.start_time ).total_seconds() / SECONDS_IN_DAY
        print    (   '********************************************************************' )
        print    (   'Start Time:       %s' % self.start_time.strftime( '%Y-%m-%d %H:%M:%S' ))
        print    (   'Current Time:   %s' % now.strftime( '%Y-%m-%d %H:%M:%S' ))
        print    (   'Days:           %s' % round( days, 1 ))
        print    (   'Hours:             %s' % round( days * 24, 1 ))
        print    (   'Spot Price:       %s' % self.get_spot())
        
        
        pnl_usd = self.bal - self.bal_init
        pnl_btc = self.bal_btc - self.bal_btc_init
        
        print    (   'Equity ($):       %7.2f'   % self.bal)
        print    (   'P&L ($)           %7.2f'   % pnl_usd)
        print    (   'Equity (BTC):   %7.4f'   % self.bal_btc)
        print    (   'P&L (BTC)       %7.4f'   % pnl_btc)
        
        #print_dict_of_dicts( {
        #   k: {
        #       '$USD': self.positions[ k ][ 'usdValue' ]
        #   } for k in self.positions.keys()
        #   }, 
        #   title = 'Positions' )
        ###print(self.positions)
        t = 0
        a = 0
        for k in self.positions:
            self.skew_size[k[0:3]] = 0

        for k in self.positions:
            self.skew_size[k[0:3]] = self.skew_size[k[0:3]] + self.positions[k]['usdValue']
        #print(' ')
        #print('Skew')

        for pos in self.skew_size:
        
            if self.skew_size[pos] != 0:
                print    (   pos + ': $' + str( self.skew_size[pos]))

        #print(' ')
        #print('Positions')
        for pos in self.positions:
        
            a = a + math.fabs(self.positions[pos]['usdValue'])
            t = t + self.positions[pos]['usdValue']
            if self.positions[pos]['usdValue'] > 0 or self.positions[pos]['usdValue'] < 0 :
                print    (   pos + ': $' + str( self.positions[pos]['usdValue']))

        print    (   '\nNet delta (exposure) USD: $' + str(t))
        print    (   'Total absolute delta (IM exposure) USD: $' + str(a))
        
        acc2 = self.ftx.privateGetAccount()
        self.LEV = acc2['result']['totalPositionSize'] / acc2['result']['totalAccountValue']
        self.IM = self.LEV * 2
        print    (   '(Roughly) initial margin across lts: ' + str(self.IM) + '% and (actual) leverage is ' + str(round(self.LEV * 1000)/1000) + 'x')

        print    (   '\nMean Loop Time: %s' % round( self.mean_looptime, 2 ))
            
        ###print( '' )

    def run_first(self):
        
        self.create_client()
        self.get_futures()
        for pair in self.lts:
            self.positions[pair] = {
            'usdValue':         0,
            'sizeBtc':      0,
            'averagePrice': None,
            'floatingPl': 0}   
        r = Timer(3, self.post_info, ())
        r.start() 
    def run (self):
        self.run_first()
        t_loop = datetime.datetime.utcnow()
        while True:
            self.check_balance()
            self.update_positions()
            self.output_status()
            self.checkTrades()
            print('sleeping...')
            sleep(1 * 60)
            t_now      = datetime.datetime.utcnow()
            looptime    = ( t_now - t_loop ).total_seconds()
            
            
            self.mean_looptimes.append(looptime)
            if len(self.mean_looptimes) > 100:
                self.mean_looptimes.pop(0)
            self.mean_looptime = sum(self.mean_looptimes) / len(self.mean_looptimes)
            
            t_loop    = t_now
    def update_positions( self ):
        try:
            print('update_positions')
             
            

            ex='ftx'
            try:
                positions       = self.ftx.privateGetLtBalances()['result']
                ###print(self.lts)
                for pos in positions:
                    #print(pos)
                    ###print('ftx pos')
                    

                    self.positions[ pos[ 'coin' ]] = pos


            except:
                PrintException()
        except:
            abc=123   
    def checkTrades(self):
        if self.test == True:

            lt = 'ETHBEAR/USDT'
            lorm = "market"
            direction = 'buy'
            gogo = True
            prc = self.get_bbo(lt)['bid']

            qty = self.bal * maxmargin * percentbalancefororders 
            qty = qty / prc
            if self.positions[lt]['usdValue'] is not None and self.margin is not None:
                if direction == 'buy' and self.positions[lt]['usdValue'] > 0 and self.margin > maxmargin:
                    gogo = False
                if  direction == 'sell' and self.positions[lt]['usdValue'] < 0 and self.margin > maxmargin:
                    gogo = False
            #if gogo == True:
                #self.ftx.createOrder(  lt, lorm, direction, qty)
                 
        else:
        
            r = requests.get("someurl:port/endpoint").json()
            for signal in r:
                lt = signal['fut']
                lorm = 'market'
                direction = signal['direction']
                gogo = True
                prc = self.get_bbo(lt)

                qty = self.bal * maxmargin * percentbalancefororders 
                qty = qty / prc
                if self.positions[lt]['usdValue'] is not None and self.margin is not None:
                    if direction == 'buy' and self.positions[lt]['usdValue'] > 0 and self.margin > maxmargin:
                        gogo = False
                    if  direction == 'sell' and self.positions[lt]['usdValue'] < 0 and self.margin > maxmargin:
                        gogo = False
                if gogo == True:
                    self.ftx.createOrder(  lt, lorm, direction, qty)
                 
    def get_futures(self):
        ftxmarkets = self.ftx.fetchMarkets()
        expis = []
        alllts = []
        for market in ftxmarkets:
            if '/' in market['symbol']:
                self.lts.append(market['symbol'])
    def restart( self ):        
        try:
            strMsg = 'RESTARTING'
            print( strMsg )
            
            for lt in self.lts:
                self.cancelall(lt, 'ftx')
            #for lt in self.lts:
            #    self.cancelall(lt, 'binance')
            
            strMsg += ' '
            for i in range( 0, 5 ):
                strMsg += '.'
                print( strMsg )
                sleep( 1 )
            #mmbot = MarketMaker( monitor = args.monitor, output = args.output )
            #mmbot.run()
        except:
            PrintException()
            pass
        finally:
            os.execv( sys.executable, [ sys.executable ] + sys.argv )        
            
    def cancelall(self, pair, ex ):

        print(pair)
        w = None
        for ex in self.totrade:
            if ex != 'ftx':
                w = ex
        ords        = self.ftx.fetchOpenOrders( pair + '-PERP')
        ords1        = self.ftx.fetchOpenOrders( pair + '-' + w)
        for order in ords:
            ###print(order)
            oid = order ['info'] ['id']
           # ##print(order)
            try:
                
                self.ftx.cancelOrder( oid , pair + '-PERP')
            except Exception as e:
                print(e)
        for order in ords1:
            ###print(order)
            oid = order ['info'] ['id']
           # ##print(order)
            try:
                
                self.ftx.cancelOrder( oid , pair + '-' + w )
            except Exception as e:
                pprint(e)
if __name__ == '__main__':
    
    ##print('hello world')
    try:
        try:
            os.rename('log.txt', 'log-' + str(start_time) + '.txt')
        except Exception as e:
            abc123 = 1
        ftxbot = FTXTaker(  )
        ftxbot.run()
    except( KeyboardInterrupt, SystemExit ):
        
        ###print( "Cancelling open orders" )
        for lt in ftxbot.futures:
            ftxbot.cancelall(lt, 'ftx')
            #mmbot.cancelall(lt, 'binance')
        
        sys.exit()
    except:
        print ( traceback.format_exc())
        sys.exit()
        mmbot.restart()
        

