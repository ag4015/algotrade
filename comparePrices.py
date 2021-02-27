import cbpro
from forex_python.converter import CurrencyRates
import pdb
import numpy as np
from itertools import combinations 
import time
import krakenex
from datetime import datetime

def compare_exchange_rate_coinbase(public_client, crypto, fiat1, fiat2, verbose=False):
    # Get the order book at the default level.
    cr_fiat_1 = public_client.get_product_order_book(crypto + '-' + fiat1)
    cr_fiat_2 = public_client.get_product_order_book(crypto + '-' + fiat2)

    avg_bid_ask_cr_fiat_1 = (bid_price_cr_fiat_1 + ask_price_cr_fiat_1)/2
    avg_bid_ask_cr_fiat_2 = (bid_price_cr_fiat_2 + ask_price_cr_fiat_2)/2
    try:
        last_price_fiat_1 = float(public_client.get_product_ticker(product_id=(crypto + '-' + fiat1))["price"])
        last_price_fiat_2 = float(public_client.get_product_ticker(product_id=(crypto + '-' + fiat2))["price"])
    except Exception as e:
        print("Failed:", e)
        return 0

    exchange_rate = last_price_fiat_1/last_price_fiat_2
    c = CurrencyRates()
    exchange_rate_diff_percent = (c.get_rate(fiat2, fiat1) - exchange_rate)*100

    if verbose:
        print(crypto + "-" + fiat1 + ": " + str(last_price_fiat_1))
        print(crypto + "-" + fiat2 + ": " + str(last_price_fiat_2))
        print("Crypto exchange rate " + str(exchange_rate))
        print("Fiat exchange rate " + str(c.get_rate(fiat2, fiat1)))
        print("% exchange rate difference " +  str(exchange_rate_diff_percent))
    return exchange_rate_diff_percent

def get_tradable_exchanges_coinbase(public_client, quote, verbose=False):

    base = set([product["base_currency"] for product in products])
    exchanges = []
    tex = []
    tc  = []
    for q in quote:
        for product in products:
            if q in product["id"] and q is not product["base_currency"]:
                exchanges.append((q,product["base_currency"]))
    exchanges = set(exchanges)
    for b in base:
        matches = []
        for ex in exchanges:
            if ex[0] == b or ex[1] == b:
                matches.append(ex)
        for m in range(0, len(matches) - 1):
            tex.append((matches[m][0], matches[m][1], matches[m+1][0]))
            tc.append(matches[m][1])
    tex = set(tex)
    if verbose:
        print("quote:\n", quote)
        print("base:\n", base)
        print("exchanges:\n", exchanges)
        print("Tradeable exchanges:\n", tex)
        print("Middle currency:\n", tc)
    return sorted(tex)

def get_tradable_exchanges_kraken(k, quote, verbose=False):

    quote = list(quote)
    products = k.query_public('AssetPairs')
    exchanges = []
    tex = []
    for product_name in products["result"]:
        for q in quote:
            try:
                product = products["result"][product_name]
                altname = product["altname"]
                wsname  = product["wsname"]
            except:
                continue
            if q in altname:
                exchanges.append(wsname)
                # print(altname, " ", wsname)
    print("exchanges")
    print(exchanges)
    quote_lst = [[] for i in range(0,len(quote))]
    for ex in exchanges:
        for i, q in enumerate(quote):
            if q in ex:
                curr = ex.split("/")[0] if ex.split("/")[0] != q else ex.split("/")[1]
                quote_lst[i].append(curr)
    print("quote_lst")
    print(quote_lst)
    quote_comb = list(combinations(quote, 2))
    quote_comb_idx = list(combinations([i for i in range(len(quote))],2))
    matches = [[] for i in range(len(quote_comb))]
    for i in range(0, len(matches)):
        matches[i] = set(quote_lst[quote_comb_idx[i][0]]) & set(quote_lst[quote_comb_idx[i][1]])
    print("matches")
    print(matches)
    tex = []
    tpairs = []
    # tpairs = [[] for i in range(0,len(matches))]
    for i in range(0, len(matches)):
        for m in matches[i]:
            if only_fiats_in_exchange([quote[quote_comb_idx[i][0]], m, quote[quote_comb_idx[i][1]]]):
               continue 
            tpairs.append([m + "/" + quote[quote_comb_idx[i][0]], m + "/" + quote[quote_comb_idx[i][1]]])
            tex.append((quote[quote_comb_idx[i][0]], m, quote[quote_comb_idx[i][1]]))
    print("tpairs")
    print(tpairs)
    print("tex")
    print(tex)
    return tex, tpairs, products["result"]

def ask_or_bid(pair, ex):
    init_fiat = ex[0]
    final_fiat = ex[2]
    # EUR BTC GBP
    if pair[:len(init_fiat)] == init_fiat: # EUR/BTC
        return "asks"
    if pair[-len(init_fiat):] == init_fiat: # BTC/EUR
        return "bids"
    if pair[:len(final_fiat)] == final_fiat: # GBP/BTC
        return "bids"
    if pair[-len(final_fiat):] == final_fiat: # BTC/GBP
        return "asks"
    return "error"
    

def compare_exchange_rate_kraken(k, ex, pairs, verbose=False):

    fiat1  = ex[0]
    crypto = ex[1]
    fiat2  = ex[2]
    last_price  = np.zeros((2,1))
    order_price = np.zeros((2,1))
    print(pairs)
    for i, pair in enumerate(pairs):
        try:
            pair = pair.replace("/", "")
            # last_price[i] = float(k.query_public('Ticker', {'pair': pair})["result"][pair]["c"][0])
            order = ask_or_bid(pair, ex)
            query = k.query_public('Depth', {'pair': pair, 'count': 1})
            result = list(query["result"].items())
            order_price[i] = float(query["result"][result[0][0]][order][0][0])
        except Exception as e:
            print("Failed: ", e)
            return

    # exchange_rate = last_price[0][0]/last_price[1][0]
    exchange_rate = order_price[0][0]/order_price[1][0]
    c = CurrencyRates()
    exchange_rate_diff_percent = (c.get_rate(fiat2, fiat1) - exchange_rate)*100

    if verbose:
        print(crypto + "-" + fiat1 + ": " + str(last_price[0]))
        print(crypto + "-" + fiat2 + ": " + str(last_price[1]))
        print("Crypto exchange rate " + str(exchange_rate))
        print("Fiat exchange rate " + str(c.get_rate(fiat2, fiat1)))
        print("% exchange rate difference " +  str(exchange_rate_diff_percent))
    return exchange_rate_diff_percent

def get_all_ex_rate_diffs(client, tex, pairs, exchange_provider):
    for i, ex in enumerate(tex):
        diff = 100
        count = 0
        while diff != None and abs(diff) > 1.1 and count < 10:
            if exchange_provider == "coinbase":
                diff = compare_exchange_rate_coinbase(client, ex[1], ex[0], ex[2])
            if exchange_provider == "kraken":
                diff = compare_exchange_rate_kraken(client, ex, [pairs_kr[0][i], pairs_kr[1][i]])
            print("% exchange rate difference " +  str(diff))
            time.sleep(0.2)
            count = count + 1

def only_fiats_in_exchange(ex):
    if len(set(fiat_list) & set(ex)) == 3:
        return True
    return False

def execute_transaction(pair, ex, amount, n):
    # Example for EUR - XBT - GBP
    if pair.split("/")[0] in fiat_list and n == 0: # EUR/XBT
        buy_or_sell = "sell"
    elif pair.split("/")[1] in fiat_list and n == 0: # XBT/EUR
        buy_or_sell = "buy"
    elif pair.split("/")[0] in fiat_list and n == 1: # GBP/XBT
        buy_or_sell = "buy"
    elif pair.split("/")[1] in fiat_list and n == 1: # XBT/GBP 
        buy_or_sell = "sell"
    pair = pair.replace("/", "")
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    logStr = current_time + "\n"
    logStr += "Executing transaction for pair: " + str(pair) + "\n"
    logStr += "For an exchange within: " + str(ex) + "\n"
    logStr += "This is a " + str(buy_or_sell) + " order\n"
    logStr += "For an amount of: " +  str(amount) + "\n"
    print(logStr)
    logfile.write(logStr)
    response = k.query_private('AddOrder',
	  			{'pair': pair,
	  			 'type': buy_or_sell,
	  			 'ordertype': 'market',
	  			 'volume': amount,
                                 'validate': 'True'})
    # response = k.query_private('AddOrder',
	#   			{'pair': pair,
	#   			 'type': buy_or_sell,
	#   			 'ordertype': 'market',
	#   			 'volume': amount})

def reverse_exchange(ex, pairs):
    rev_ex = [ex[2], ex[1], ex[0]]
    rev_pairs = [pairs[1], pairs[0]]
    return rev_ex, rev_pairs

def iterate_algorithm(client, tex, pairs_kr, exchange_provider, products):
    iteration = -1
    if exchange_provider != "kraken":
        return
    while True:
        iteration = iteration + 1
        print("Iteration: ", iteration)
        for i, ex in enumerate(tex):
            pairs = pairs_kr[i]
            print(ex)
            if only_fiats_in_exchange(ex):
                print("only fiats")
                continue
            if ex[0] != "EUR" and ex[0] != "GBP":
                print("Not EUR or GBP for starting currency")
                continue
            time.sleep(0.2)
            diff = compare_exchange_rate_kraken(client, ex, pairs)
            print(diff)
            if abs(diff) > 2:
                if diff < 0:
                   ex, pairs = reverse_exchange(ex, pairs) 
                if ex[0] == "USD":
                    continue
                logStr = "For a difference of " + str(diff) + "\n"
                logfile.write(logStr)
                for n, pair in enumerate(pairs): # n = 0: into crypto; n = 1, back to fiat
                    amount = products[pair.replace("/", "")]["ordermin"]
                    execute_transaction(pair, ex, amount, n)
                    response = k.query_private('OpenOrders')
                    while len(response["result"]["open"]) == 1:
                        print("Waiting for order to close")
                        response = k.query_private('OpenOrders')
                response = k.query_private('TradeBalance',
                                {'asset': "EUR"})
                logStr = "Equivalent balance in EUR: " + response["result"]["eb"] + "\n"
                print(logStr)
                logfile.write(logStr)
                time.sleep(5)
    

quote = {'EUR', 'GBP', 'USD', "CAD", "CHF"}

fiat_list = ["EUR", "USD", "GBP", "CAD", "CHF", "JPY", "AUD"]

k = krakenex.API()
k.load_key('kraken.key')

public_client = cbpro.PublicClient()
products_cb = public_client.get_products()

logfile = open("logFile.txt", "a")

# tex_cb = get_tradable_exchanges_coinbase(public_client, quote, verbose=False)
# get_all_ex_rate_diffs(public_client, tex_cb, "coinbase")

tex_kr, pairs_kr, products = get_tradable_exchanges_kraken(k, quote)

## TODO INVESTIGATE TRADABLE EXCHANGES
print(tex_kr)
# get_all_ex_rate_diffs(k, tex_kr, pairs_kr, "kraken")

iterate_algorithm(k, tex_kr, pairs_kr, "kraken", products)

pdb.set_trace()


