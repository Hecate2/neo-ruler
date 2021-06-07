from neo_test_with_vm import TestEngine

from neo3.core.types import UInt160
# from neo3 import settings
from neo3.network.payloads import Signer, WitnessScope
from neo3.vm import IntegerStackItem, VMState
from neo3.contracts import NeoToken, GasToken
neo, gas = NeoToken(), GasToken()
from tests.utils import gen_expiry_timestamp_and_str_in_seconds, EngineResultInterpreter

contract_owner_pubkey = '0355688d0a1dc59a51766b3736eee7617404f2e0af1eb36e57f11e647297ad8b34'
contract_owner_hash = "6d629e44cceaf8722c99a41d5fb98cf3472c286a"
random_hash = '0' * 40
# settings.default_settings['network']['standby_committee'] = [contract_owner_pubkey]
engine = TestEngine('ruler.nef', signers=[contract_owner_hash])

# _30_days_later_ending_milisecond, _30_days_later_date_str = gen_expiry_timestamp_and_str(30)
_30_days_later_ending_milisecond, _30_days_later_date_str = gen_expiry_timestamp_and_str_in_seconds(30)
DECIMAL_BASE = 100_000_000
mint_ratio = 7 * DECIMAL_BASE
fee_rate = 0 * DECIMAL_BASE

engine.invoke_method_with_print('deploy', [contract_owner_hash])

engine.invoke_method_with_print("addPair", params=[neo.hash, gas.hash, _30_days_later_ending_milisecond, _30_days_later_date_str, mint_ratio, str(mint_ratio), fee_rate], signers=[random_hash])
assert engine.state == VMState.HALT and engine.result_stack.peek() == IntegerStackItem(1)
engine.invoke_method_with_print("getCollaterals", result_interpreted_as_iterator=True, further_interpreter=EngineResultInterpreter.interpret_getCollaterals)
a_collateral = list(engine.previous_processed_result.keys())[0]
engine.invoke_method_with_print("getPairsMap", params=[a_collateral], result_interpreted_as_iterator=True, further_interpreter=EngineResultInterpreter.interpret_getPairsMap)
a_pair_index = list(engine.previous_processed_result.keys())[0]
engine.invoke_method_with_print('getPairAttributes', params=[a_pair_index], result_interpreted_as_iterator=True, further_interpreter=EngineResultInterpreter.interpret_getPairAttribtutes)
pair_attributes = engine.previous_processed_result
assert a_collateral == pair_attributes['collateralToken']
assert pair_attributes['active'] == 0
rcToken_address = pair_attributes['rcToken']
rrToken_address = pair_attributes['rrToken']

engine.set_NEP17_token_balance(neo, contract_owner_hash)
engine.set_NEP17_token_balance(gas, contract_owner_hash)

engine.invoke_method_with_print('mmDeposit', [contract_owner_hash, pair_attributes['collateralToken'], pair_attributes['pairedToken'], pair_attributes['expiry'], pair_attributes['mintRatio'], 700000000])
assert engine.state == VMState.FAULT
engine.invoke_method_with_print("deposit", params=[contract_owner_hash, neo.hash, gas.hash, _30_days_later_ending_milisecond, mint_ratio, 1],
                                signers=[Signer(UInt160.from_string(contract_owner_hash), WitnessScope.GLOBAL)])
assert engine.state == VMState.FAULT

engine.invoke_method_with_print('setActive', params=[pair_attributes['collateralToken'], pair_attributes['pairedToken'], pair_attributes['expiry'], pair_attributes['mintRatio']], signers=[random_hash])
assert engine.state == VMState.FAULT

engine.invoke_method_with_print('setActive', params=[pair_attributes['collateralToken'], pair_attributes['pairedToken'], pair_attributes['expiry'], pair_attributes['mintRatio']])
engine.invoke_method_with_print('mmDeposit', [contract_owner_hash, pair_attributes['collateralToken'], pair_attributes['pairedToken'], pair_attributes['expiry'], pair_attributes['mintRatio'], 700000000])
assert engine.state == VMState.HALT
engine.invoke_method_with_print("deposit", params=[contract_owner_hash, neo.hash, gas.hash, _30_days_later_ending_milisecond, mint_ratio, 1],
                                signers=[Signer(UInt160.from_string(contract_owner_hash), WitnessScope.GLOBAL)])
assert engine.state == VMState.HALT

engine.invoke_method_with_print('setPaused', params=[pair_attributes['collateralToken'], pair_attributes['pairedToken'], pair_attributes['expiry'], pair_attributes['mintRatio']], signers=[random_hash])
assert engine.state == VMState.FAULT

engine.invoke_method_with_print('setPaused', params=[pair_attributes['collateralToken'], pair_attributes['pairedToken'], pair_attributes['expiry'], pair_attributes['mintRatio']])
engine.invoke_method_with_print('mmDeposit', [contract_owner_hash, pair_attributes['collateralToken'], pair_attributes['pairedToken'], pair_attributes['expiry'], pair_attributes['mintRatio'], 700000000])
assert engine.state == VMState.FAULT
engine.invoke_method_with_print("deposit", params=[contract_owner_hash, neo.hash, gas.hash, _30_days_later_ending_milisecond, mint_ratio, 1],
                                signers=[Signer(UInt160.from_string(contract_owner_hash), WitnessScope.GLOBAL)])
assert engine.state == VMState.FAULT
