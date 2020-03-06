#!/usr/bin/python3
import sys
from bitcoincash.electrum import Electrum
from bitcoincash.core import CBlockHeader, x, CTransaction
from bitcoincash.electrum.svr_info import ServerInfo

import pickle
import asyncio
import html

BLOCKS_IN_PERIOD = 2016

# Voting started in the past at MTP >= 1573819200
START_HASH = "0000000000000000026f7ec9e79be2f5bb839f29ebcf734066d4bb9a13f6ea83"
START_HEIGHT = 609135

VOTE_GENERAL = 0
VOTE_ABC = 1
VOTE_BCHD = 2
VOTE_EC = 3

def isKthBitSet(n, k):
    return n & (1 << k)

def parse_votes(version):
    whitelist = []

    if isKthBitSet(version, VOTE_GENERAL):
        whitelist.append("General fund")
    if isKthBitSet(version, VOTE_ABC):
        whitelist.append("Bitcoin ABC")
    if isKthBitSet(version, VOTE_BCHD):
        whitelist.append("BCHD")
    if isKthBitSet(version, VOTE_EC):
        whitelist.append("Electron Cash")

    if len(whitelist) == 0:
        return None
    return ", ".join(whitelist)

def get_block_info(header, coinbase, height):
    version = format(header.nVersion, '#034b')
    scriptsig = coinbase.vin[0].scriptSig
    return {
        "height" : height,
        "version": version,
        "votes" : parse_votes(int(version, 2)),
        "scriptSig": html.escape(scriptsig.decode('utf-8', 'ignore')),
    }

def export_period_info(tip_height, headers, coinbases, export_func):
    curr_height = tip_height
    period = [ ]
    while curr_height >= START_HEIGHT:
        header = headers[curr_height]
        coinbase = coinbases[curr_height]

        if curr_height % BLOCKS_IN_PERIOD == 0:
            # start of period
            print("Finished period %s - %s"
                    % (curr_height, curr_height + BLOCKS_IN_PERIOD))
            period = list(reversed(period))
            export_func(period)
            period = [ ]

        period.append(get_block_info(header, coinbase, curr_height))
        curr_height -= 1

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

async def sync_headers(cli, headers, tip_height):

    for h in range(START_HEIGHT, tip_height + 1):

        # TODO: Discover reorgs
        if h in headers:
            continue

        header_hex = await cli.RPC('blockchain.block.header', h)
        headers[h] = CBlockHeader.deserialize(x(header_hex))
        print("Fetched header {}".format(h))

async def sync_coinbases(cli, coinbases, tip_height):

    for h in range(START_HEIGHT, tip_height + 1):

        # TODO: Discover reorgs
        if h in coinbases:
            continue

        coinbase_txid = await cli.RPC('blockchain.transaction.id_from_pos', h, 0)
        tx_raw = await cli.RPC('blockchain.transaction.get', coinbase_txid)
        print(f"Fetched coinbase {h} {coinbase_txid}")
        coinbases[h] = CTransaction.deserialize(x(tx_raw))


async def main_loop(headers, coinbases):
    cli = Electrum()
    server = ServerInfo("bestserver", "bitcoincash.network", "s50002")
    await cli.connect()
    tip, new_tips = cli.subscribe('blockchain.headers.subscribe')
    tip = await tip
    print("TIP: {}".format(tip))

    try:
        while True:
            await asyncio.gather(*[
                sync_headers(cli, headers, tip['height']),
                sync_coinbases(cli, coinbases, tip['height'])])
            export_period_info(tip['height'], headers, coinbases, json_export)
            print("Done. Waiting for next block...")
            # tip = await new_tips.get()
            raise Exception("workaround die")

    finally:
        await cli.close()

try:
    with open("headers.pickle", "rb") as fh:
        headers = pickle.load(fh)
        for k in headers.keys():
            headers[k] = CBlockHeader.deserialize(headers[k])
except FileNotFoundError as _:
    headers = { }

try:
    with open("coinbases.pickle", "rb") as fh:
        coinbases = pickle.load(fh)
        for k in coinbases.keys():
            coinbases[k] = CTransaction.deserialize(coinbases[k])
except FileNotFoundError as _:
    coinbases = { }

try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main_loop(headers, coinbases))
    loop.close()
finally:
    with open("headers.pickle", "wb") as fh:
        for k in headers.keys():
            headers[k] = headers[k].serialize()
        pickle.dump(headers, fh)

    with open("coinbases.pickle", "wb") as fh:
        for k in coinbases.keys():
            coinbases[k] = coinbases[k].serialize()
        pickle.dump(coinbases, fh)
