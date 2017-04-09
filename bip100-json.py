#!/usr/bin/python3
import sys
sys.path.append("./lib/bitcoinrpc")
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

BLOCKS_IN_PERIOD = 2016

def read_cfg(param):
    cfglines = open("../.bitcoin/bitcoin.conf").readlines()
    for c in cfglines:
        if c.startswith(param):
            return c[len(param) + 1:-1]
    return None

rpcuser = read_cfg("rpcuser")
rpcpassword = read_cfg("rpcpassword")

testnet = False
if testnet:
    bip100_activation = 798336
    port = 18332
else:
    bip100_activation = 449568
    port = 8332

url = "http://%s:%s@127.0.0.1:%s" % (rpcuser, rpcpassword, port)
c = AuthServiceProxy(url)

def get_coinbase_str(block):
    txid = block["tx"][0]
    try:
        tx = c.decoderawtransaction(c.getrawtransaction(txid))
    except JSONRPCException as e:
        # This triggers if -txindex is not set in bitcoin.conf
        return "UNAVAILABLE"
    coinbase = tx["vin"][0]["coinbase"];
    return bytes.fromhex(coinbase).decode("utf-8", "ignore")

def get_block_info(block):
    return {
        "height" : block["height"],
        "sizelimit" : block["sizelimit"],
        "sizelimitvote" : block["sizelimitvote"],
        "coinbase_str" : get_coinbase_str(block)
    }

def export_period_info(tip, export_func):
    last_height = c.getblockheader(tip)["height"]
    curr = tip
    period = [ ]
    while last_height >= bip100_activation:
        block = c.getblock(curr)
        if block["height"] % 500 == 0:
            print(block["height"], end = ".", flush = True)
        else:
            print(".", end = ".", flush = True)

        last_height = block["height"]

        if block["height"] % BLOCKS_IN_PERIOD == 0:
            # start of period
            print("Finished period %s - %s"
                    % (block["height"], block["height"] + BLOCKS_IN_PERIOD))
            period = list(reversed(period))
            if export_func(period):
                print("Stopping early. Enough data exported.")
                return

            period = [ ]
        period.append(get_block_info(block))
        curr = block["previousblockhash"]

def json_export(period):
    import json
    import os
    period_start = period[0]["height"]
    export_dir = "web/period"
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    filename = os.path.join(export_dir, str(period_start) + ".json")
    print("writing %s" % filename)
    with open(filename, "w") as fh:
        import json
        fh.write(json.dumps(period))

    # update list of all periods
    from glob import glob
    import re
    periods = glob(export_dir + "/[0-9]*.json")
    periods = [re.findall(r'\d+', p)[0] for p in periods]
    periods.sort()
    filename = os.path.join(export_dir, "list.json")
    with open(os.path.join(export_dir, "list.json"), "w") as fh:
        fh.write(json.dumps(periods))

    # We assume that the Bitcoin network won't re-org 24 hours
    # worth of blocks. If we have data for earlier periods already, we can stop.
    return len(period) >= 144 \
            and str(period_start - BLOCKS_IN_PERIOD) in periods

def main_loop():
    last_tip = None
    while True:
        import time
        try:
            tip = c.getbestblockhash()
            if tip == last_tip:
                time.sleep(1)
                continue
            last_tip = tip
            export_period_info(tip, json_export)
            print("Done. Waiting of next block...")
        except Exception as e:
            print("Critical: %s. Retry in 30 seconds." % e)
            time.sleep(30)

main_loop()
