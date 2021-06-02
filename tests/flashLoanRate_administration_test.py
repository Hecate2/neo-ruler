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

flashLoanRate = 10_000_000
engine.invoke_method_with_print('setFlashLoanRate', [flashLoanRate])  # FAULT
engine.invoke_method_with_print('setFeeReceiver', [contract_owner_hash])  # FAULT
engine.invoke_method_with_print('deploy', [contract_owner_hash])
engine.invoke_method_with_print('setFlashLoanRate', [flashLoanRate])
engine.invoke_method_with_print('setFeeReceiver', [contract_owner_hash])
engine.invoke_method_with_print('getFlashLoanRate')
engine.invoke_method_with_print('deploy', [random_hash], signers=[random_hash, contract_owner_hash])
engine.invoke_method_with_print('setFlashLoanRate', [flashLoanRate//2], signers=[random_hash])
engine.invoke_method_with_print('setFeeReceiver', [random_hash], signers=[random_hash])
engine.invoke_method_with_print('getFlashLoanRate')
