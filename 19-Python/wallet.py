import subprocess
import json
import os
from constants import *
from bit import PrivateKeyTestnet
from bit.network import NetworkAPI
from web3 import Web3, middleware, Account
from web3.gas_strategies.time_based import medium_gas_price_strategy
from dotenv import load_dotenv


# set environment variables
load_dotenv()
mnemonic=os.getenv("MNEMONIC")
 
 
# Derive_wallet function - 
def derive_wallets(mnemonic, num, coin):
    command = f'php ./derive -g --mnemonic="{mnemonic}" --numderive="{num}" --coin="{coin}" --format=json'
    p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    output, err = p.communicate()
    p_status = p.wait()
    keys = json.loads(output)
    return keys

# wallet dict - 
coins = {'eth', 'btc', 'btc-test'}
numderive = 3

keys = {}
for coin in coins:
    keys[coin]=derive_wallets(mnemonic, coin, numderive)

# priv_key_to_account function
def priv_key_to_account(coin, priv_key):
    if coin == ETH:
        return Account.privateKeyToAccount(priv_key)
    elif coin == BTCTEST:
        return PrivateKeyTestNet(priv_key)

# create_tx function
def create_tx(coin, account, recipient, amount):
    if coin == ETH:
        gasEstimate = w3.eth.estimateGas(
        {"from":eth_acc.address, "to":recipient, "Value":amount}
        )
        return {
            "from": eth_acc.address,
            "to": recipient,
            "value": amount,
            "gasPrice":w3.eth.gasPrice,
            "gas": gasEstimate,
            "nonce":we.eth.getTransaactionCount(eth_acc.address)
        }
    elif coin == BTCTEST:
        return PrivateKeyTestnet.prepare_transaction(account.address,[(recipient, amount, BTC)])

# send_tx function to call the create_tx
def send_tx(coin, account, recipient, amount):
    txn = create_tx(coin, account, recipient, amount)
    if coin == ETH:
        signed_txn = eth_acc.sign_transaction(txn)
        result = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
        print(result.hex())
        return result.hex()
    elif coin == BTCTEST:
        tx_btctest = create_tx(coin, account, recipient, amount)
        signed_txn = account.sign_transaction(txn)
        print(signed_txn)
        return NetworkAPI.broadcast_tx_testnet(signed_txn)
