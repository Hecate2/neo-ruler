from neo_test_with_vm import TestEngine

from neo3.core.types import UInt160
from neo3 import settings
from neo3.vm import IntegerStackItem, VMState
import datetime, time
from neo3.contracts import NeoToken, GasToken
neo, gas = NeoToken(), GasToken()

nef_path = 'rToken.nef'
contract_owner_pubkey = '0355688d0a1dc59a51766b3736eee7617404f2e0af1eb36e57f11e647297ad8b34'
contract_owner_hash = "6d629e44cceaf8722c99a41d5fb98cf3472c286a"
random_hash = '0' * 40
# settings.default_settings['network']['standby_committee'] = [contract_owner_pubkey]
engine = TestEngine('ruler.nef', signers=[contract_owner_hash])

today = datetime.date.today()
_30_days_later = today + datetime.timedelta(days=30)
_30_days_later_ending_milisecond = (int(time.mktime(time.strptime(str(_30_days_later), '%Y-%m-%d'))) * 1000 - 1)
_30_days_later_date_str = _30_days_later.strftime('%m_%d_%Y')
mint_ratio = 7
fee_rate = 0

engine.invoke_method_with_print("addPair", params=[neo.hash, gas.hash, _30_days_later_ending_milisecond, _30_days_later_date_str, mint_ratio, str(mint_ratio), fee_rate])
assert engine.state == VMState.HALT and engine.result_stack.peek() == IntegerStackItem(1)
engine.invoke_method_with_print("getCollaterals", result_interpreted_as_iterator=True)
a_collateral = list(engine.previous_processed_result.keys())[0][len('collaterals'):]
engine.invoke_method_with_print("getPairsMap", params=[UInt160.deserialize_from_bytes(a_collateral)], result_interpreted_as_iterator=True)
assert b'pairs' + a_collateral in list(engine.previous_processed_result.keys())[0]
# The following codes require wallet support from neo-mamba
engine.invoke_method_of_arbitrary_contract(neo.hash, 'balanceOf', [contract_owner_hash])
print('invoke method balanceOf me:'); engine.print_results()
engine.invoke_method_of_arbitrary_contract(neo.hash, 'balanceOf', [neo.hash])
print('invoke method balanceOf neo:'); engine.print_results()
engine.invoke_method_of_arbitrary_contract(neo.hash, 'transfer', [neo.hash, contract_owner_hash, 100, b'data'], signers=[neo.hash])
print('invoke method transfer:')
engine.print_results()
engine.invoke_method_with_print("deposit", params=[neo.hash, gas.hash, _30_days_later_ending_milisecond, mint_ratio, 1], signers=[engine.contract.hash])
print()