from neo_test_with_rpc import TestClient, Hash160Str, Hash256Str, Signer, WitnessScope
from utils import gen_expiry_timestamp_and_str
from neo3.contracts import NeoToken, GasToken
neo, gas = NeoToken(), GasToken()

target_url = 'http://127.0.0.1:23332'

# make sure you deploy ruler.nef manually
contract_hash = Hash160Str('0x709dcde755e9152fa3b6b7f9e9d116f8eecdbc1b')

consensus_wallet_hash = Hash160Str('0xb1d5f6a149539e83afb53ce3af2d7fc4fe634880')
consensus_wallet_address = 'NXcGQ6d4162MyrryfN3gdWJGvzNEw8AtCQ'
consensus_signer = Signer(consensus_wallet_hash, WitnessScope.CalledByEntry)

dev_wallet_hash = Hash160Str('0x71929fb00416c7333e404f8a482cd9ccf9e4aadb')
dev_wallet_address = 'NfwTtijo9uqeJDiuryu8eqADn9ALnPgmQd'
dev_signer = Signer(dev_wallet_hash, WitnessScope.CalledByEntry)

administrating_client = TestClient(target_url, consensus_wallet_hash, consensus_wallet_address, 'consensus.json', '1')
administrating_client.openwallet()
expiry_timestamp, expiry_str = gen_expiry_timestamp_and_str(60)
mint_ratio = 7
fee_rate = 0
administrating_client.invokefunction(contract_hash, 'addPair', [neo.hash, gas.hash, expiry_timestamp, expiry_str, mint_ratio, str(mint_ratio), fee_rate])
administrating_client.print_previous_result()

dev_client = TestClient(target_url, dev_wallet_hash, dev_wallet_address, 'dev.json', '1')
dev_client.openwallet()
neo_balance, gas_balance = dev_client.get_neo_balance(), dev_client.get_gas_balance()
if neo_balance < 10 or gas_balance < 100e8:
    input(f'Warning: only f{neo_balance} NEOs and {gas_balance/1e8} left. \npress ENTER to continue')
dev_client.invokefunction()