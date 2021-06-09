"""
This test would never always succeed because we cannot know whether the transactions have been relayed on the chain
"""

from typing import Dict
import time

from tests.utils import Hash160Str, Signer, WitnessScope, \
    gen_expiry_timestamp_and_str_in_seconds,\
    ClientResultInterpreter, sleep_until
from neo_test_with_rpc import TestClient
from neo3.contracts import NeoToken, GasToken
neo, gas = NeoToken(), GasToken()

target_url = 'http://127.0.0.1:23332'

# make sure you deploy ruler.nef manually
# contract_hash = Hash160Str('0xaf9abd7ba5bfb7dd17d70267ed09ec9d0876c814')
from tests.config import contract_hash

consensus_wallet_address = 'NhSRQSzNv8BwjKwQn2Spk7tY194uxXiESv'
consensus_wallet_hash = Hash160Str('0x113f10ed24f2b70115d37c103130a236b7011dec')
consensus_signer = Signer(consensus_wallet_hash, WitnessScope.CalledByEntry)

dev_wallet_address = 'NTzUx1Jm4oe7QPU2ankRtDwBzEGuiMfJim'
dev_wallet_hash = Hash160Str('0xa44dcf7f3a95ae60c6c2e97cf904979fd4839b58')
dev_signer = Signer(dev_wallet_hash, WitnessScope.CalledByEntry)

administrating_client = TestClient(target_url, contract_hash, consensus_wallet_hash, consensus_wallet_address, 'consensus.json', '1')
administrating_client.openwallet()
# expiry_timestamp, expiry_str = gen_expiry_timestamp_and_str(33)  # this works for deposit and repay
expiry_timestamp, expiry_str = gen_expiry_timestamp_and_str_in_seconds(60)  # this does not work for deposit
print(expiry_timestamp - time.time() * 1000)

DECIMAL_BASE = 100_000_000
mint_ratio = 7 * DECIMAL_BASE
fee_rate = 0 * DECIMAL_BASE
try:
    administrating_client.invokefunction('addPair', [neo.hash, gas.hash, expiry_timestamp, expiry_str, mint_ratio, str(mint_ratio), fee_rate])
except ValueError as e:
    if 'ASSERT is executed with false result.' in e.args[0]:
        print(e, end=' '); print('Maybe you have already added the Pair')
    else:
        raise e
print()
dev_client = TestClient(target_url, contract_hash, dev_wallet_hash, dev_wallet_address, 'dev.json', '1')
dev_client.openwallet()
time.sleep(15)
neo_balance, gas_balance = dev_client.get_neo_balance(), dev_client.get_gas_balance()
if neo_balance < 10 or gas_balance < 100e8:
    input(f'Warning: only f{neo_balance} NEOs and {gas_balance/1e8} left. \npress ENTER to continue')
dev_client.invokefunction("getCollaterals", result_interpreted_as_iterator=True)
collaterals = ClientResultInterpreter.interpret_getCollaterals(dev_client.previous_result)
print('collaterals:', collaterals)
try:
    assert Hash160Str.from_UInt160(neo.hash) in collaterals
except AssertionError as e:
    print('getCollaterals failed. Maybe you need to wait 15 seconds before running this test again')
    raise e
dev_client.invokefunction("getPairsMap", params=[collaterals[0]], result_interpreted_as_iterator=True)
pairs:Dict[int, Hash160Str] = ClientResultInterpreter.interpret_getPairsMap(dev_client.previous_result)
print('pairs:', pairs)
selected_pair = list(pairs.keys())[0]
dev_client.invokefunction("getPairAttributes", params=[selected_pair], result_interpreted_as_iterator=True)
attributes = ClientResultInterpreter.interpret_getPairAttribtutes(dev_client.previous_result)
print('attributes:', attributes)
print()
print('check rcToken and rrToken balance before deposit:')
rcToken_before_deposit = dev_client.get_rToken_balance(attributes['rcToken'])
print('rcToken balance:', rcToken_before_deposit)
rrToken_before_deposit = dev_client.get_rToken_balance(attributes['rrToken'])
print('rrToken balance:', rrToken_before_deposit)

dev_client.invokefunction("deposit",
    params=[dev_wallet_hash, attributes['collateralToken'], attributes['pairedToken'], attributes['expiry'], attributes['mintRatio'], 1],
    signers=[Signer(dev_wallet_hash, WitnessScope.Global)])  # CalledByEntry does not take effect
dev_client.print_previous_result()

dev_client.invokefunction("deposit",
    params=[dev_wallet_hash, attributes['collateralToken'], attributes['pairedToken'], attributes['expiry'], attributes['mintRatio'], 100],
    signers=[Signer(dev_wallet_hash, WitnessScope.Global)])
dev_client.print_previous_result()

time.sleep(15)

print()
print('check rcToken and rrToken balance after deposit:')
rcToken_before_deposit = dev_client.get_rToken_balance(attributes['rcToken'])
print('rcToken balance:', rcToken_before_deposit)
rrToken_before_deposit = dev_client.get_rToken_balance(attributes['rrToken'])
print('rrToken balance:', rrToken_before_deposit)

dev_client.invokefunction("repay",
    params=[dev_wallet_hash, attributes['collateralToken'], attributes['pairedToken'], attributes['expiry'], attributes['mintRatio'], 700000000],
    signers=[Signer(dev_wallet_hash, WitnessScope.Global)])
dev_client.print_previous_result()

dev_client.invokefunction("repay",
    params=[dev_wallet_hash, attributes['collateralToken'], attributes['pairedToken'], attributes['expiry'], attributes['mintRatio'], 1400000000],
    signers=[Signer(dev_wallet_hash, WitnessScope.Global)])
dev_client.print_previous_result()

sleep_until(expiry_timestamp)
time.sleep(15)

dev_client.invokefunction("collect",
    params=[dev_wallet_hash, attributes['collateralToken'], attributes['pairedToken'], attributes['expiry'], attributes['mintRatio'], 700000000],
    signers=[Signer(dev_wallet_hash, WitnessScope.Global)])
dev_client.print_previous_result()

dev_client.invokefunction("collect",
    params=[dev_wallet_hash, attributes['collateralToken'], attributes['pairedToken'], attributes['expiry'], attributes['mintRatio'], 2800000000],
    signers=[Signer(dev_wallet_hash, WitnessScope.Global)])
dev_client.print_previous_result()
