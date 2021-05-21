import json
import os
from functools import partial
from typing import List, Union, Tuple, Any, cast

from neo3 import vm, contracts, blockchain
from neo3.contracts import ApplicationEngine
from neo3.core import types
from neo3.core.types import UInt160
from neo3.network import payloads


class TestEngine:
    NO_SIGNER = 'NO_SIGNER'
    
    @staticmethod
    def new_engine(previous_engine: ApplicationEngine = None) -> ApplicationEngine:
        tx = payloads.Transaction._serializable_init()
        if not previous_engine:
            blockchain.Blockchain.__it__ = None
            snapshot = blockchain.Blockchain(store_genesis_block=True).currentSnapshot  # blockchain is singleton
            return ApplicationEngine(contracts.TriggerType.APPLICATION, tx, snapshot, 0, test_mode=True)
        else:
            return ApplicationEngine(contracts.TriggerType.APPLICATION, tx, previous_engine.snapshot, 0, test_mode=True)
    
    @staticmethod
    def read_raw_nef_and_raw_manifest(nef_path: str, manifest_path: str = '') -> Tuple[bytes, dict]:
        with open(nef_path, 'rb') as f:
            raw_nef = f.read()
        if not manifest_path:
            file_path, fullname = os.path.split(nef_path)
            nef_name, _ = os.path.splitext(fullname)
            manifest_path = os.path.join(file_path, nef_name + '.manifest.json')
        with open(manifest_path, 'r') as f:
            raw_manifest = json.loads(f.read())
        return raw_nef, raw_manifest
    
    @staticmethod
    def build_nef_and_manifest_from_raw(raw_nef: bytes, raw_manifest: dict) \
            -> Tuple[contracts.NEF, contracts.manifest.ContractManifest]:
        nef = contracts.NEF.deserialize_from_bytes(raw_nef)
        manifest = contracts.manifest.ContractManifest.from_json(raw_manifest)
        return nef, manifest
    
    def __init__(self, nef_path: str, manifest_path: str = '', signer: Union[str, UInt160] = ''):
        """
        Only the contract specified in __init__ can be tested. You can deploy more contracts to be called by the tested
        contract.
        """
        self.raw_nef, self.raw_manifest = self.read_raw_nef_and_raw_manifest(nef_path, manifest_path)
        self.nef, self.manifest = self.build_nef_and_manifest_from_raw(self.raw_nef, self.raw_manifest)
        self.previous_engine: ApplicationEngine = self.new_engine()
        self.contract = contracts.ContractState(0, self.nef, self.manifest, 0,
                                                types.UInt160.deserialize_from_bytes(self.raw_nef))
        self.next_contract_id = 1  # if you deploy more contracts in a same engine, the contracts must have different id
        self.previous_engine.snapshot.contracts.put(self.contract)
        self.deployed_contracts = [self.contract]
        if signer:
            if type(signer) is str:
                signer = types.UInt160.from_string(signer)
            self.signer = signer
        else:
            self.signer = UInt160()

        # add methods to this class for users to call contract methods
        for method in self.manifest.abi.methods:
            method_name = method.name
            method_name_with_print = method_name + '_with_print'
            if hasattr(self, method_name) or hasattr(self, method_name_with_print):
                print(f'Warning: method {method_name} or {method_name_with_print} already exists in {self}')
            partial_function = partial(self.invoke_method, method_name)
            setattr(self, method_name, partial_function)
            partial_function_with_print = partial(self.invoke_method_with_print, method_name)
            setattr(self, method_name_with_print, partial_function_with_print)
    
    def deploy_more_contracts(self, nef_path: str, manifest_path: str = ''):
        """
        these extra contracts can be called but cannot be tested
        """
        raw_nef, raw_manifest = self.read_raw_nef_and_raw_manifest(nef_path, manifest_path)
        nef, manifest = self.build_nef_and_manifest_from_raw(raw_nef, raw_manifest)
        contract = contracts.ContractState(self.next_contract_id, nef, manifest, 0,
                                           types.UInt160.deserialize_from_bytes(raw_nef))
        self.previous_engine.snapshot.contracts.put(contract)
        self.deployed_contracts.append(contract)
        self.next_contract_id += 1
    
    @staticmethod
    def param_auto_checker(param: Any) -> Any:
        if type(param) is str and len(param) == 40:
            return types.UInt160.from_string(param).to_array()
        if type(param) is UInt160:
            return param.to_array()
        else:
            return param
    
    def invoke_method(self, method: str, params: List = None, signer: Union[str, UInt160] = '',
                      scope: payloads.WitnessScope = payloads.WitnessScope.CALLED_BY_ENTRY,
                      engine: ApplicationEngine = None, with_print=False) -> ApplicationEngine:
        if with_print:
            return self.invoke_method_with_print(method, params, signer, scope, engine)
        return self.invoke_method_of_arbitrary_contract(self.contract.hash, method, params, signer, scope, engine)

    def invoke_method_with_print(self, method: str, params: List = None, signer: Union[str, UInt160] = '',
                                 scope: payloads.WitnessScope = payloads.WitnessScope.CALLED_BY_ENTRY,
                                 engine: ApplicationEngine = None, result_interpreted_as_hex=False,
                                 result_interpreted_as_iterator=False) -> ApplicationEngine:
        print(f'invoke method {method}:')
        executed_engine = self.invoke_method(method, params, signer, scope, engine)
        if executed_engine.state == executed_engine.state.FAULT:
            print(f'engine fault from method "{method}":')
            print(executed_engine.exception_message)
        self.print_results(executed_engine, result_interpreted_as_hex, result_interpreted_as_iterator)
        return executed_engine

    def invoke_method_of_arbitrary_contract(self, contract_hash: UInt160, method: str, params: List = None, signer: Union[str, UInt160] = '',
                      scope: payloads.WitnessScope = payloads.WitnessScope.CALLED_BY_ENTRY,
                      engine: ApplicationEngine = None, with_print=False):
        if params is None:
            params = []
        params = list(map(lambda param: self.param_auto_checker(param), params))
        if not engine:
            engine = self.new_engine(self.previous_engine)
    
        contract = self.contract
        # engine.load_script(vm.Script(contract.script))
        sb = vm.ScriptBuilder()
        if params:
            sb.emit_dynamic_call_with_args(contract_hash, method, params)
        else:
            sb.emit_dynamic_call(contract.hash, method)
        engine.load_script(vm.Script(sb.to_array()))
    
        if signer:
            if type(signer) is str and signer != self.NO_SIGNER:
                signer = types.UInt160.from_string(signer)
            engine.script_container.signers = [payloads.Signer(signer, scope)]
        elif self.signer:
            engine.script_container.signers = [payloads.Signer(self.signer, scope)]
    
        engine.execute()
        self.previous_engine = engine
        return engine

    def analyze_results(self, engine: ApplicationEngine = None, result_interpreted_as_hex=False,
                        result_interpreted_as_iterator=False) -> Tuple[vm.VMState, Any]:
        if not engine:
            engine = self.previous_engine
        if not engine.result_stack:
            return engine.state, engine.result_stack
        result = engine.result_stack.peek()
        if result and result_interpreted_as_hex:
            processed_result = bytes.fromhex(str(result))
        elif result and result_interpreted_as_iterator:
            cast(vm.MapStackItem, result)
            keys = result.keys()
            values = result.values()
            processed_result = {}
            for k, v in zip(keys, values):
                processed_result[bytes.fromhex(str(k))] = int.from_bytes(bytes.fromhex(str(v)), 'little')
        else:
            processed_result = str(result)
        self.previous_engine_state = engine.state
        self.previous_processed_result = processed_result
        return engine.state, processed_result
    
    def print_results(self, engine: ApplicationEngine = None, result_interpreted_as_hex=False,
                      result_interpreted_as_iterator=False) -> None:
        state, result = self.analyze_results(engine, result_interpreted_as_hex, result_interpreted_as_iterator)
        print(state, result)
    
    def reset_environment(self):
        '''
        reset the blockchain environment, and re-deploy all the contracts that have been deployed.
        '''
        self.engine = self.new_engine()
        for contract in self.deployed_contracts:
            self.engine.snapshot.contracts.put(contract)
    
    def __repr__(self):
        return f'class TestEngine: {self.previous_engine_state} {self.previous_processed_result}'
