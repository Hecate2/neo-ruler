from neo_test_with_vm import TestEngine
# from neo3.core.types import UInt160

nef_path = 'rToken.nef'
contract_owner_hash = "6d629e44cceaf8722c99a41d5fb98cf3472c286a"
random_hash = '0' * 40
engine = TestEngine(nef_path, signer=contract_owner_hash)
engine.invoke_method_with_print('decimals')
engine.decimals(with_print=True)
engine.invoke_method_with_print('deploy', params=[contract_owner_hash, b'R_TOKEN_TEST'])
engine.invoke_method_with_print('deploy', params=[contract_owner_hash, b'R_TOKEN_MULTIPLE_DEPLOY'])
assert engine.previous_engine.state == engine.previous_engine.state.FAULT
engine.invoke_method_with_print('deploy', params=[random_hash, b'R_TOKEN_RANDOM_USER'])
engine.invoke_method_with_print('symbol', result_interpreted_as_hex=True)
engine.onNEP17Payment_with_print(params=[None,100,b"Transfer from caller to Ruler"])
engine.invoke_method_with_print("mint", params=[contract_owner_hash, 100])
engine.invoke_method_with_print("balanceOf", params=[contract_owner_hash])
engine.invoke_method_with_print("burnByRuler", params=[contract_owner_hash, 10])
engine.invoke_method_with_print("balanceOf", params=[contract_owner_hash])
engine.invoke_method_with_print("totalSupply")
engine.invoke_method_with_print("burnByRuler", params=[contract_owner_hash, 90])
engine.invoke_method_with_print("balanceOf", params=[contract_owner_hash])
engine.invoke_method_with_print("totalSupply")
