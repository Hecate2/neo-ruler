from neo_test_with_vm import TestEngine

from neo3.core.types import UInt160
from neo3 import settings
from neo3.vm import IntegerStackItem, VMState
import datetime, time
from neo3.contracts import NeoToken, GasToken
neo, gas = NeoToken(), GasToken()

nef_path = 'rToken.nef'
contract_owner_hash = "6d629e44cceaf8722c99a41d5fb98cf3472c286a"
random_hash = '0' * 40
engine = TestEngine('ruler.nef', signer=contract_owner_hash)

today = datetime.date.today()
_30_days_later = today + datetime.timedelta(days=30)
_30_days_later_ending_milisecond = (int(time.mktime(time.strptime(str(_30_days_later), '%Y-%m-%d'))) * 1000 - 1)
_30_days_later_date_str = _30_days_later.strftime('%m_%d_%Y')
mint_ratio = 7
fee_rate = 0

engine.invoke_method_with_print("addPair", params=[neo.hash, gas.hash, _30_days_later_ending_milisecond, _30_days_later_date_str, mint_ratio, str(mint_ratio), fee_rate])
assert engine.previous_engine.state == VMState.HALT \
    and engine.previous_engine.result_stack.peek() == IntegerStackItem(1)
# The following codes require wallet support from neo-mamba
engine.invoke_method_of_arbitrary_contract(neo.hash, 'transfer', [neo.hash, contract_owner_hash, 100, b'data'], signer=neo.hash)
engine.print_results()
engine.invoke_method_with_print("deposit", params=[neo.hash, gas.hash, _30_days_later_ending_milisecond, mint_ratio, 1])
print()