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
# settings.default_settings['network']['standby_committee'] = [contract_owner_pubkey]
engine = TestEngine('ruler.nef', signers=[contract_owner_hash])

# _30_days_later_ending_milisecond, _30_days_later_date_str = gen_expiry_timestamp_and_str(30)
_30_days_later_ending_milisecond, _30_days_later_date_str = gen_expiry_timestamp_and_str_in_seconds(30)
DECIMAL_BASE = 100_000_000
mint_ratio = 7 * DECIMAL_BASE
fee_rate = 0 * DECIMAL_BASE

engine.invoke_method_with_print('deploy', [contract_owner_hash])

engine.invoke_method_with_print("addPair", params=[neo.hash, gas.hash, _30_days_later_ending_milisecond, _30_days_later_date_str, mint_ratio, str(mint_ratio), fee_rate])
assert engine.state == VMState.HALT and engine.result_stack.peek() == IntegerStackItem(1)
engine.invoke_method_with_print("getCollaterals", result_interpreted_as_iterator=True, further_interpreter=EngineResultInterpreter.interpret_getCollaterals)
a_collateral = list(engine.previous_processed_result.keys())[0]
engine.invoke_method_with_print("getPairsMap", params=[a_collateral], result_interpreted_as_iterator=True, further_interpreter=EngineResultInterpreter.interpret_getPairsMap)
a_pair_index = list(engine.previous_processed_result.keys())[0]
engine.invoke_method_with_print('getPairAttributes', params=[a_pair_index], result_interpreted_as_iterator=True, further_interpreter=EngineResultInterpreter.interpret_getPairAttribtutes)
pair_attributes = engine.previous_processed_result
assert a_collateral == pair_attributes['collateralToken']
rcToken_address = pair_attributes['rcToken']
rrToken_address = pair_attributes['rrToken']

engine.set_NEP17_token_balance(neo, contract_owner_hash)
engine.set_NEP17_token_balance(gas, contract_owner_hash)
engine.invoke_method_of_arbitrary_contract(neo.hash, 'balanceOf', [contract_owner_hash])
print('invoke method balanceOf my NEO:', end=' '); engine.print_results()
engine.invoke_method_of_arbitrary_contract(gas.hash, 'balanceOf', [contract_owner_hash])
print('invoke method balanceOf my GAS:', end=' '); engine.print_results()

engine.invoke_method_with_print('mmDeposit', [contract_owner_hash, pair_attributes['collateralToken'], pair_attributes['pairedToken'], pair_attributes['expiry'], pair_attributes['mintRatio'], 700000000])
engine.invoke_method_of_arbitrary_contract(gas.hash, 'balanceOf', [contract_owner_hash])
print('GAS balance after mmDeposit:'); engine.print_results()
engine.invoke_method_of_arbitrary_contract(pair_attributes['rcToken'], 'balanceOf', [contract_owner_hash])
print('rcToken amount after mmDeposit:'); engine.print_results()
