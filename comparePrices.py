import cbpro
from forex_python.converter import CurrencyRates
import pdb
import numpy as np
from itertools import combinations 
import time
import krakenex

def compare_exchange_rate_coinbase(public_client, crypto, fiat1, fiat2, verbose=False):
    # Get the order book at the default level.
    cr_fiat_1 = public_client.get_product_order_book(crypto + '-' + fiat1)
    # bid_price_cr_fiat_1  = float(cr_fiat_1["bids"][0][0])
    # bid_size_cr_fiat_1   = float(cr_fiat_1["bids"][0][1])
    # bid_orders_cr_fiat_1 = float(cr_fiat_1["bids"][0][2])
    # ask_price_cr_fiat_1  = float(cr_fiat_1["asks"][0][0])
    # ask_size_cr_fiat_1   = float(cr_fiat_1["asks"][0][1])
    # ask_orders_cr_fiat_1 = float(cr_fiat_1["asks"][0][2])

    cr_fiat_2 = public_client.get_product_order_book(crypto + '-' + fiat2)
    # bid_price_cr_fiat_2  = float(cr_fiat_2["bids"][0][0])
    # bid_size_cr_fiat_2   = float(cr_fiat_2["bids"][0][1])
    # bid_orders_cr_fiat_2 = float(cr_fiat_2["bids"][0][2])
    # ask_price_cr_fiat_2  = float(cr_fiat_2["asks"][0][0])
    # ask_size_cr_fiat_2   = float(cr_fiat_2["asks"][0][1])
    # ask_orders_cr_fiat_2 = float(cr_fiat_2["asks"][0][2])

    avg_bid_ask_cr_fiat_1 = (bid_price_cr_fiat_1 + ask_price_cr_fiat_1)/2
    avg_bid_ask_cr_fiat_2 = (bid_price_cr_fiat_2 + ask_price_cr_fiat_2)/2
    # pdb.set_trace()
    try:
        last_price_fiat_1 = float(public_client.get_product_ticker(product_id=(crypto + '-' + fiat1))["price"])
        last_price_fiat_2 = float(public_client.get_product_ticker(product_id=(crypto + '-' + fiat2))["price"])
    except Exception as e:
        print("Failed:", e)
        failed.append(e)
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

    products = k.query_public('AssetPairs')
    exchanges = []
    tex = []
    for product_name in products["result"]:
        for q in quote:
            try:
                product = products["result"][product_name]
                altname = product["altname"]
                wsname  = product["wsname"]
                # print(altname, " ", wsname)
            except:
                continue
            if q in altname:
                # last_trade = k.query_public('Ticker', {'pair': altname})["result"][altname]["c"]
                exchanges.append(wsname)
                # print(altname, " ", wsname)
    print(exchanges)
    quote_lst = [[] for i in range(0,len(quote))]
    for ex in exchanges:
        for i, q in enumerate(quote):
            if q in ex:
                curr = ex.split("/")[0] if ex.split("/")[0] != q else ex.split("/")[1]
                quote_lst[i].append(curr)
    matches = set(quote_lst[0]) & set(quote_lst[1])
    tex = []
    tpairs = [[],[]]
    for m in matches:
        for ex in exchanges:
            for i, q in enumerate(quote):
                if str(q + "/" + m) == ex or str(m + "/" + q) == ex:
                    tpairs[i].append(ex)
    q = list(quote)
    for m in matches:
        tex.append((q[0], m, q[1]))
    return tex, tpairs

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
            failed.append(e)
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
        print(ex)
        diff = 100
        count = 0
        while diff != None and abs(diff) > 1.1 and count < 10:
            if exchange_provider == "coinbase":
                diff = compare_exchange_rate_coinbase(client, ex[1], ex[0], ex[2])
            if exchange_provider == "kraken":
                diff = compare_exchange_rate_kraken(client, ex, [pairs_kr[0][i], pairs_kr[1][i]])
            print("% exchange rate difference " +  str(diff))
            time.sleep(0.5)
            count = count + 1

quote = {'EUR', 'GBP'}

k = krakenex.API()
k.load_key('kraken.key')

failed  = []

public_client = cbpro.PublicClient()
products = public_client.get_products()

# tex_cb = get_tradable_exchanges_coinbase(public_client, quote, verbose=False)
# get_all_ex_rate_diffs(public_client, tex_cb, "coinbase")

tex_kr, pairs_kr = get_tradable_exchanges_kraken(k, quote)
get_all_ex_rate_diffs(k, tex_kr, pairs_kr, "kraken")

print(failed)


# print(k.query_private('Depth', {'pair': 'BTCUSD', 'count': '10'}))


