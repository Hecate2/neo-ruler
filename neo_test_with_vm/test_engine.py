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
    
    @property
    def state(self):
        return self.previous_engine.state
    
    @property
    def snapshot(self):
        return self.previous_engine.snapshot
    
    @property
    def result_stack(self):
        return self.previous_engine.result_stack
    
    def __init__(self, nef_path: str, manifest_path: str = '', signers: List[Union[str, UInt160]] = None,
                 scope: payloads.WitnessScope = payloads.WitnessScope.CALLED_BY_ENTRY):
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
        if signers:
            signers = list(map(lambda signer:
                               self.signer_auto_checker(signer, scope),
                               signers))
            self.signers = signers
        else:
            self.signers = [UInt160()]

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
    
    def deploy_another_contract(self, nef_path: str, manifest_path: str = ''):
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
        type_param = type(param)
        if type_param is str and len(param) == 40:
            return types.UInt160.from_string(param).to_array()
        if type_param is UInt160:
            return param.to_array()
        else:
            return param
    
    @staticmethod
    def signer_auto_checker(signer: Union[str, UInt160], scope: payloads.WitnessScope) -> payloads.Signer:
        type_signer = type(signer)
        if type_signer is str and len(signer) == 40:
            return payloads.Signer(types.UInt160.from_string(signer), scope)
        elif type_signer is UInt160:
            return payloads.Signer(signer, scope)
        else:
            raise ValueError(f'Unable to handle signer {signer} with type {type_signer}')
    
    def invoke_method(self, method: str, params: List = None, signers: List[Union[str, UInt160]] = None,
                      scope: payloads.WitnessScope = payloads.WitnessScope.CALLED_BY_ENTRY,
                      engine: ApplicationEngine = None, with_print=False) -> ApplicationEngine:
        if with_print:
            return self.invoke_method_with_print(method, params, signers, scope, engine)
        return self.invoke_method_of_arbitrary_contract(self.contract.hash, method, params, signers, scope, engine)

    def invoke_method_with_print(self, method: str, params: List = None, signers: List[Union[str, UInt160]] = None,
                                 scope: payloads.WitnessScope = payloads.WitnessScope.CALLED_BY_ENTRY,
                                 engine: ApplicationEngine = None, result_interpreted_as_hex=False,
                                 result_interpreted_as_iterator=False) -> ApplicationEngine:
        if not signers:
            signers = []
        print(f'invoke method {method}:')
        executed_engine = self.invoke_method(method, params, signers, scope, engine)
        if executed_engine.state == executed_engine.state.FAULT:
            print(f'engine fault from method "{method}":')
            print(executed_engine.exception_message)
        self.print_results(executed_engine, result_interpreted_as_hex, result_interpreted_as_iterator)
        return executed_engine

    def invoke_method_of_arbitrary_contract(self, contract_hash: UInt160, method: str, params: List = None,
                      signers: List[Union[str, UInt160]] = None,
                      scope: payloads.WitnessScope = payloads.WitnessScope.CALLED_BY_ENTRY,
                      engine: ApplicationEngine = None):
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
    
        if signers and signers != self.NO_SIGNER:
            signers = list(map(lambda signer:
                               self.signer_auto_checker(signer, scope),
                               signers))
            engine.script_container.signers = signers
        elif self.signers:  # use signers stored in self when no external signer specified
            engine.script_container.signers = self.signers
    
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
            processed_result = dict()
            iterator = list(result.get_object().it)
            for k,v in iterator:
                processed_result[k.key] = v.value
        else:
            processed_result = str(result)
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
        self.previous_engine = self.new_engine()
        for contract in self.deployed_contracts:
            self.previous_engine.snapshot.contracts.put(contract)
            
    def __repr__(self):
        return f'class TestEngine: {self.state} {self.previous_processed_result}'
