import json
from typing import Tuple, List, Union
from boa3.builtin.interop.iterator import Iterator

from neo3 import vm, contracts, storage
from neo3.network import payloads
from neo3.core import to_script_hash, types, cryptography
from neo3.contracts import ApplicationEngine, NeoToken, GasToken
from tests.contracts.interop.utils import test_engine, test_tx
from boa3.builtin.interop.contract import NEO, GAS
from copy import deepcopy

def read_raw_nef_and_raw_manifest(nef_path: str, manifest_path: str) -> Tuple[bytes, dict]:
    with open(nef_path, 'rb') as f:
        raw_nef = f.read()
    with open(manifest_path, 'r') as f:
        raw_manifest = json.loads(f.read())
    return raw_nef, raw_manifest


def build_nef_and_manifest_from_raw(raw_nef: bytes, raw_manifest: dict) -> Tuple[
    contracts.NEF, contracts.manifest.ContractManifest]:
    nef = contracts.NEF.deserialize_from_bytes(raw_nef)
    manifest = contracts.manifest.ContractManifest.from_json(raw_manifest)
    return nef, manifest


def invoke_main(nef: contracts.NEF) -> ApplicationEngine:
    engine = test_engine(has_container=True, has_snapshot=True)
    engine.load_script(vm.Script(nef.script))
    engine.execute()
    if engine.state == engine.state.FAULT:
        print(f'engine fault from method "main":')
        print(engine.exception_message)
    return engine


def invoke_method(raw_nef: bytes, method: str, params: List=None, signer: str='',
                  scope: payloads.WitnessScope = payloads.WitnessScope.CALLED_BY_ENTRY,
                  engine:ApplicationEngine=None) -> ApplicationEngine:
    '''
    TODO: multiple signers
    Args:
        signer: ScriptHash of wallet address, "6d629e44cceaf8722c99a41d5fb98cf3472c286a"
    '''
    if params is None:
        params = []
    print(f'method {method}:')
    if not engine:
        engine = test_engine(has_container=True, has_snapshot=True, default_script=False)
    contract = contracts.ContractState(0, nef, manifest, 0, types.UInt160.deserialize_from_bytes(raw_nef))
    try:
        engine.snapshot.contracts.put(contract)
    except ValueError:  # the contract has already been deployed to the blockchain
        pass
    engine.load_script(vm.Script(contract.script))
    if signer:
        engine.script_container.signers = [payloads.Signer(
            types.UInt160.from_string(signer),
            scope
        )]
    array = vm.ArrayStackItem(engine.reference_counter)
    if params:
        array.append(params)  # parameters for method
    engine.push(array)
    engine.push(vm.IntegerStackItem(15))  # CallFlag
    engine.push(vm.ByteStringStackItem(method))
    engine.push(vm.ByteStringStackItem(contract.hash.to_array()))
    engine.invoke_syscall_by_name("System.Contract.Call")
    engine.execute()
    if engine.state == engine.state.FAULT:
        print(f'engine fault from method "{method}":')
        print(engine.exception_message)
    return engine


def print_results(engine:ApplicationEngine, first_item_interpreted_as_hex=False, first_item_interpreted_as_iterator=False):
    results: List = [item for item in engine.result_stack._items]
    if results and first_item_interpreted_as_hex:
        results = [item.__str__() for item in results]
        results[0] = bytes.fromhex(results[0]).decode()
    elif results and first_item_interpreted_as_iterator:
        results: List[vm.MapStackItem, str]
        keys = results[0].keys()
        values = results[0].values()
        results[0]:dict = {}
        for k,v in zip(keys, values):
            results[0][bytes.fromhex(str(k))] = int.from_bytes(bytes.fromhex(str(v)), 'little')
        results[1] = str(results[1])
    else:
        results = [item.__str__() for item in results]
    print(engine.state, results)


def engine_factory(previous_engine: ApplicationEngine) -> ApplicationEngine:
    return ApplicationEngine(contracts.TriggerType.APPLICATION, payloads.Transaction._serializable_init(),
                             previous_engine.snapshot, 0, test_mode=True)


raw_nef, raw_manifest = read_raw_nef_and_raw_manifest('rToken.nef', 'rToken.manifest.json')
nef, manifest = build_nef_and_manifest_from_raw(raw_nef, raw_manifest)
contract_owner_hash = "6d629e44cceaf8722c99a41d5fb98cf3472c286a"
contract_owner_hash_bytes = types.UInt160.from_string(contract_owner_hash).to_array()
contract = contracts.ContractState(0, nef, manifest, 0, types.UInt160.deserialize_from_bytes(raw_nef))
contract_hash = contract.hash

print_results(invoke_main(nef))
deployed_engine = invoke_method(raw_nef, "decimals")
print_results(deployed_engine)
deployed_engine = invoke_method(raw_nef, "deploy", params=[vm.ByteStringStackItem(contract_owner_hash_bytes), vm.ByteStringStackItem(b'R_TOKEN_TEST')], signer=contract_owner_hash, engine=engine_factory(deployed_engine))
print_results(deployed_engine)
deployed_engine = invoke_method(raw_nef, "deploy", params=[vm.ByteStringStackItem(contract_owner_hash_bytes), vm.ByteStringStackItem(b'R_TOKEN_TEST')], signer=contract_owner_hash, engine=engine_factory(deployed_engine))
print_results(deployed_engine)
# deployed_engine.call_from_native(NEO, contract_hash, "onNEP17Payment", [contract_owner_hash, vm.IntegerStackItem(100), vm.IntegerStackItem(100)])
deployed_engine = invoke_method(raw_nef, 'onNEP17Payment',
                            params=[vm.ByteStringStackItem(),
                                    vm.IntegerStackItem(100), vm.ByteStringStackItem(b"Transfer from caller to Ruler")], signer=NEO, engine=engine_factory(deployed_engine))
print_results(deployed_engine)

deployed_engine = invoke_method(raw_nef, 'mint',
                            params=[vm.ByteStringStackItem(contract_owner_hash_bytes),
                                    vm.IntegerStackItem(100)], signer=contract_owner_hash, engine=ApplicationEngine(contracts.TriggerType.APPLICATION, payloads.Transaction._serializable_init(),
                             deployed_engine.snapshot, 0, test_mode=True))
print_results(deployed_engine)
deployed_engine = invoke_method(raw_nef, 'balanceOf',
                            params=[vm.ByteStringStackItem(contract_owner_hash_bytes)], signer=contract_owner_hash, engine=ApplicationEngine(contracts.TriggerType.APPLICATION, payloads.Transaction._serializable_init(),
                             deployed_engine.snapshot, 0, test_mode=True))
print_results(deployed_engine)
deployed_engine = invoke_method(raw_nef, 'burnByRuler',
                            params=[vm.ByteStringStackItem(contract_owner_hash_bytes), vm.IntegerStackItem(10)], signer=contract_owner_hash, engine=ApplicationEngine(contracts.TriggerType.APPLICATION, payloads.Transaction._serializable_init(),
                             deployed_engine.snapshot, 0, test_mode=True))
print_results(deployed_engine)
deployed_engine = invoke_method(raw_nef, 'balanceOf',
                            params=[vm.ByteStringStackItem(contract_owner_hash_bytes)], signer=contract_owner_hash, engine=ApplicationEngine(contracts.TriggerType.APPLICATION, payloads.Transaction._serializable_init(),
                             deployed_engine.snapshot, 0, test_mode=True))
print_results(deployed_engine)
deployed_engine = invoke_method(raw_nef, 'totalSupply',
                             signer=contract_owner_hash, engine=ApplicationEngine(contracts.TriggerType.APPLICATION, payloads.Transaction._serializable_init(),
                             deployed_engine.snapshot, 0, test_mode=True))
print_results(deployed_engine)
deployed_engine = invoke_method(raw_nef, 'burnByRuler',
                            params=[vm.ByteStringStackItem(contract_owner_hash_bytes), vm.IntegerStackItem(90)], signer=contract_owner_hash, engine=ApplicationEngine(contracts.TriggerType.APPLICATION, payloads.Transaction._serializable_init(),
                             deployed_engine.snapshot, 0, test_mode=True))
print_results(deployed_engine)
deployed_engine = invoke_method(raw_nef, 'balanceOf',
                            params=[vm.ByteStringStackItem(contract_owner_hash_bytes)], signer=contract_owner_hash, engine=ApplicationEngine(contracts.TriggerType.APPLICATION, payloads.Transaction._serializable_init(),
                             deployed_engine.snapshot, 0, test_mode=True))
print_results(deployed_engine)
deployed_engine = invoke_method(raw_nef, 'totalSupply',
                             signer=contract_owner_hash, engine=ApplicationEngine(contracts.TriggerType.APPLICATION, payloads.Transaction._serializable_init(),
                             deployed_engine.snapshot, 0, test_mode=True))
print_results(deployed_engine)

