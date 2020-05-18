
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
if 'KEY' in os.environ:
    ftxKEY = os.environ['ftxkey']

    ftxSECRET = os.environ['ftxsecret']
maxmargin = float(obj['maxusedmargin'])
percentbalancefororders = float(obj['percentbalancefororders']) # 0.1% of balance / maxlev will be used in each order
percentbalancefororders = percentbalancefororders / 100
testing = obj['testing']
class FTXTaker( object ):
    
    def __init__( self, test=testing ):
        self.ftx = None
        self.test = test
        self.futures            = []
        self.bal = None
        self.positions = {}
        self.margin = None
    def create_client( self ):
        self.ftx     = ccxt.ftx({
            'enableRateLimit': True,
            'apiKey': ftxKEY,   
            'secret': ftxSECRET,
        })
    def check_balance(self):
        bal2 = self.ftx.fetchBalance()
        self.bal = bal2[ 'USDT' ] [ 'total' ]
        marginftx = 0.1
        marginbinance = 0.1
        
        if self.ftx.privateGetAccount()['result']['marginFraction'] is not None:
            self.margin = (1 / self.ftx.privateGetAccount()['result']['marginFraction']) 
            #print(marginftx)

    def get_bbo( self, contract ): # Get best b/o excluding own orders
        try:
            if 'ftx' in contract:
                contract = contract.split('-')[0] +  '-PERP'
            if '-' in contract:
                ob      = self.ftx.fetchOrderBook( contract )
            else:
                if '-' in contract:
                    ob      = self.ftx.fetchOrderBook( contract )
                else:
                    ob      = self.ftx.fetchOrderBook( contract + '-PERP')
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
            abc=123
    def post_info( self ):
        positionsToPost = {}
        for pos in self.positions:
            if self.positions[pos]['size'] != 0:
                positionsToPost[pos] = self.positions[pos]
        data = {'start_time': start_time, 'balance': self.bal, 'positions': positionsToPost, 'IP': host_ip}
        print(data)
        posted = requests.post("http://someurl:someport/info_updatte", data=data, verify=False, timeout=5)
        print(posted)
        r = Timer(60, self.post_info, ())
        r.start() 
    def run_first(self):
        r = Timer(1, self.post_info, ())
        r.start() 
        self.create_client()
        self.get_futures()
    def run (self):
        self.run_first()
        while True:
            self.check_balance()
            self.update_positions()
            self.checkTrades()
            sleep(1 * 60)
    def update_positions( self ):
        try:
            ##print('update_positions')
            for pair in self.futures:
                if '-' in pair:
                    self.positions[pair] = {
                    'size':         0,
                    'sizeBtc':      0,
                    'averagePrice': None,
                    'floatingPl': 0}    
                
    
                ex='ftx'
                try:
                    positions       = self.ftx.privateGetPositions()['result']
                    ###print(self.futures)
                    for pos in positions:
                        ###print('ftx pos')
                        
                        pos['floatingPl'] = pos['unrealizedPnl']
                        if pos['entryPrice'] is not None:
                            pos['size'] = float(pos['netSize']) * (pos['entryPrice'])
                        else:
                            pos['size'] = 0
                        #if pos['size'] == 0:
                        #    pos['size'] = 2
                        if pos['size'] != 0:
                            self.positions[ pos[ 'future' ]] = pos


                except:
                    PrintException()
        except:
            abc=123   
    def checkTrades(self):
        if self.test == True:

            fut = 'EOS-PERP'
            lorm = "market"
            direction = 'buy'
            gogo = True
            prc = self.get_bbo(fut)['bid']

            qty = self.bal * maxmargin * percentbalancefororders 
            qty = qty / prc
            if self.positions[fut]['size'] is not None and self.margin is not None:
                if direction == 'buy' and self.positions[fut]['size'] > 0 and self.margin > maxmargin:
                    gogo = False
                if  direction == 'sell' and self.positions[fut]['size'] < 0 and self.margin > maxmargin:
                    gogo = False
            if gogo == True:
                self.ftx.createOrder(  fut, lorm, direction, qty)
                 
        else:
        
            r = requests.get("someurl:port/endpoint").json()
            for signal in r:
                fut = signal['fut']
                lorm = 'market'
                direction = signal['direction']
                gogo = True
                prc = self.get_bbo(fut)

                qty = self.bal * maxmargin * percentbalancefororders 
                qty = qty / prc
                if self.positions[fut]['size'] is not None and self.margin is not None:
                    if direction == 'buy' and self.positions[fut]['size'] > 0 and self.margin > maxmargin:
                        gogo = False
                    if  direction == 'sell' and self.positions[fut]['size'] < 0 and self.margin > maxmargin:
                        gogo = False
                if gogo == True:
                    self.ftx.createOrder(  fut, lorm, direction, qty)
        self.ftx.createOrder(  fut, lorm, direction, qty)
                 
    def get_futures(self):
        ftxmarkets = requests.get("https://ftx.com/api/futures").json()['result']
        expis = []
        allfuts = []
        for market in ftxmarkets:
            self.futures.append(market['name'])
    def restart( self ):        
        try:
            strMsg = 'RESTARTING'
            print( strMsg )
            
            for fut in self.futures:
                self.cancelall(fut, 'ftx')
            #for fut in self.futures:
            #    self.cancelall(fut, 'binance')
            
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
        for fut in ftxbot.futures:
            ftxbot.cancelall(fut, 'ftx')
            #mmbot.cancelall(fut, 'binance')
        
        sys.exit()
    except:
        print ( traceback.format_exc())
        sys.exit()
        mmbot.restart()
        

