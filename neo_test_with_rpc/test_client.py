from typing import List, Union, Dict
from enum import Enum
import json
import requests
from neo_test_with_rpc.retry import retry, RetryExhausted

from neo3.core.types import UInt160
from neo3.core.serialization import BinaryReader
from neo3.contracts import NeoToken, GasToken
neo, gas = NeoToken(), GasToken()

RequestExceptions=(
    requests.RequestException,
    requests.ConnectionError,
    requests.HTTPError,
    requests.Timeout,
    )
request_timeout = 10


class WitnessScope(Enum):
    NONE = 'None'
    CalledByEntry = 'CalledByEntry'
    CustomContracts = 'CustomContracts'
    CustomGroups = 'CustomGroups'
    Global = 'Global'


class HashStr(str):
    def __init__(self, string:str):
        super(HashStr, self).__init__()
        # check length of string here
        # assert string.startswith('0x')
        self.string = string

    def to_str(self):
        return self.string
    def __str__(self):
        return self.string
    def __repr__(self):
        return self.string
    
    

class Hash256Str(HashStr):
    """
    0x59916d8c2fc5feb06b77aec289ac34b49ae3bccb1f88fe64ea5172c79fc1af05
    """

    def __init__(self, string: str):
        # assert string.startswith('0x')
        if len(string) == 64:
            string = '0x' + string
        assert len(string) == 66
        super().__init__(string)


class Hash160Str(HashStr):
    """
    0xf61eebf573ea36593fd43aa150c055ad7906ab83
    """
    def __init__(self, string:str):
        # assert string.startswith('0x')
        if len(string) == 40:
            string = '0x' + string
        assert len(string) == 42
        super().__init__(string)
    
    @classmethod
    def from_UInt160(cls, u:UInt160):
        u_bytearray = bytearray(u._data)
        u_bytearray.reverse()
        hash160str = u_bytearray.hex()
        return cls(hash160str)
    
    def to_UInt160(self):
        return UInt160.from_string(self.string)
    
    def to_str(self):
        return self.string
        
    def __str__(self):
        return self.string
    def __repr__(self):
        return self.string


class Signer:
    def __init__(self, account:Hash160Str, scopes:WitnessScope, allowedcontracts:List[Hash160Str]=None, allowedgroups:List[str]=None):
        self.account:Hash160Str = account
        self.scopes:WitnessScope = scopes
        if allowedcontracts == None:
            allowedcontracts = []
        self.allowedcontracts = [str(allowedcontract) for allowedcontract in allowedcontracts]
        if allowedgroups == None:
            allowedgroups = []
        self.allowedgroups = allowedgroups
        
    def to_dict(self):
        return {
            'account': str(self.account),
            'scopes': self.scopes.value,
            'allowedcontracts': self.allowedcontracts,
            'allowedgroups': self.allowedgroups,
        }


class TestClient:
    def __init__(self, target_url: str, wallet_scripthash:Hash160Str, wallet_address:str, wallet_path: str, wallet_password: str, session=requests.Session()):
        """
        
        :param target_url: url to the rpc server affliated to neo-cli
        :param wallet_scripthash: scripthash of your wallet
        :param wallet_address: address of your wallet (starting with 'N'); "NVbGwMfRQVudTjWAUJwj4K68yyfXjmgbPp"
        :param wallet_path: 'wallets/dev.json'
        :param wallet_password: '12345678'
        :param session: requests.Session
        """
        self.target_url = target_url
        self.session = session
        self.wallet_scripthash = wallet_scripthash
        self.wallet_address = wallet_address
        self.wallet_path = wallet_path
        self.wallet_password = wallet_password
        self.previous_post_data = None
        
    @staticmethod
    def request_body_builder(method, parameters: List):
       return json.dumps({
           "jsonrpc": "2.0",
           "method": method,
           "params": parameters,
           "id": 1,
       }, separators=(',', ':'))
    
    @retry(RequestExceptions, tries=2, logger=None)
    def meta_rpc_method(self, method:str, parameters:List, relay:bool=True) -> dict:
        post_data = self.request_body_builder(method, parameters)
        self.previous_post_data = post_data
        result = json.loads(self.session.post(self.target_url, post_data, timeout=request_timeout).text)
        if 'error' in result:
            raise ValueError(result['error']['message'])
        if type(result['result']) is dict:
            if result['result']['state'] != 'HALT':
                print(result)
                raise ValueError(result['result']['exception'])
            if relay and 'tx' in result['result']:
                tx = result['result']['tx']
                self.sendrawtransaction(tx)
        self.previous_result = result
        return result
    
    def print_previous_result(self):
        print(self.previous_result)
    
    def sendrawtransaction(self, transaction:str):
        """
        :param transaction: result['tx']. e.g. "ALmNfAb4lqIAAA...="
        """
        return self.meta_rpc_method("sendrawtransaction", [transaction], relay=False)
    
    def openwallet(self, path: str=None, password: str=None) -> dict:
        """
        WARNING: usually you should use this method along with __init__.
        Use another TestClient object to open another wallet
        """
        if not path:
            path = self.wallet_path
        if not password:
            password = self.wallet_password
        open_wallet_raw_result = self.meta_rpc_method("openwallet", [path, password])
        if open_wallet_raw_result['result'] != True:
            raise ValueError(f'Failed to open wallet {path} with given password.')
        return open_wallet_raw_result
    
    def invokefunction(self, scripthash:Hash160Str, operation:str,
                       params:List[Union[str, int, Hash160Str, UInt160]], signers:List[Signer]=None) -> dict:
        def parse_params(param: Union[str, int, Hash160Str, UInt160]) -> Dict[str, str]:
            type_param = type(param)
            if type_param is UInt160:
                return {
                    'type': 'Hash160',
                    'value': str(Hash160Str.from_UInt160(param)),
                }
            if type_param is Hash160Str:
                return {
                    'type':'Hash160',
                    'value':str(param),
                }
            elif type_param is int:
                return {
                    'type': 'Integer',
                    'value': str(param),
                }
            elif type_param is str:
                return {
                    'type': 'String',
                    'value': param,
                }
            else:
                raise ValueError(f'Unable to handle param {param} with type {type_param}')
        if not params:
            params = []
        if not signers:
            signers = []
        parameters = [
            str(scripthash),
            operation,
            list(map(lambda param: parse_params(param), params)),
            list(map(lambda signer: signer.to_dict(), signers)),
        ]
        return self.meta_rpc_method('invokefunction', parameters)
    
    def sendfrom(self, asset_id:Hash160Str, from_address:str, to_address:str, value:int, signers:List[Signer]=None):
        """
        
        :param asset_id: NEO: '0xef4073a0f2b305a38ec4050e4d3d28bc40ea63f5';
            GAS: '0xd2a4cff31913016155e38e474a2c06d08be276cf'
        :param from_address: "NgaiKFjurmNmiRzDRQGs44yzByXuSkdGPF"
        :param to_address: "NikhQp1aAD1YFCiwknhM5LQQebj4464bCJ"
        :param value: 100000000, including decimals
        :param signers:
        :return:
        """
        if not signers:
            signers = []
        return self.meta_rpc_method('sendfrom', [
            asset_id.to_str(),
            from_address, to_address, value,
            signers
        ])
    
    def sendtoaddress(self, asset_id:Hash160Str, address, value:int):
        return self.meta_rpc_method('sendtoaddress', [
            asset_id.string, address, value,
        ])
    
    def send_neo_to_address(self, to_address: Hash160Str, value:int):
        return self.sendtoaddress(Hash160Str.from_UInt160(NeoToken().hash), to_address, value)
    
    def send_gas_to_address(self, to_address: Hash160Str, value:int):
        return self.sendtoaddress(Hash160Str.from_UInt160(GasToken().hash), to_address, value)

    def getwalletbalance(self, asset_id: Hash160Str) -> int:
        return int(self.meta_rpc_method('getwalletbalance', [asset_id.to_str()])['result']['balance'])
    
    def get_neo_balance(self) -> int:
        return self.getwalletbalance(Hash160Str.from_UInt160(NeoToken().hash))
    
    def get_gas_balance(self) -> int:
        return self.getwalletbalance(Hash160Str.from_UInt160(GasToken().hash))