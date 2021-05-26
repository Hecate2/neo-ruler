from neo_test_with_rpc import TestClient, Hash160Str, Hash256Str, Signer, WitnessScope
from utils import gen_expiry_timestamp_and_str
from neo3.contracts import NeoToken, GasToken
neo, gas = NeoToken(), GasToken()
neo_hash160str = Hash160Str.from_UInt160(neo.hash)
gas_hash160str = Hash160Str.from_UInt160(gas.hash)

target_url = 'http://127.0.0.1:23332'

# make sure you deploy ruler.nef manually
contract_hash = Hash256Str('0x59916d8c2fc5feb06b77aec289ac34b49ae3bccb1f88fe64ea5172c79fc1af05')

consensus_wallet_hash = Hash160Str('0x41a762a20b49b1250cccbc68b5fbdb0557c6e608')
consensus_wallet_address = 'NLj33oVWYzXQNBJDfznhJ2JQ1Sx3P1FtC6'
administrating_client = TestClient(target_url, consensus_wallet_hash, consensus_wallet_address, 'consensus.json', '1')
administrating_client.openwallet()
expiry_timestamp, expiry_str = gen_expiry_timestamp_and_str(30)
mint_ratio = 7
print(administrating_client.invokefunction(contract_hash, 'addPair', [neo_hash160str, gas_hash160str, expiry_timestamp, expiry_str, mint_ratio, str(mint_ratio), 0]))

dev_wallet_hash = Hash160Str('0x6d629e44cceaf8722c99a41d5fb98cf3472c286a')
dev_wallet_address = 'NVbGwMfRQVudTjWAUJwj4K68yyfXjmgbPp'
dev_signer = Signer(dev_wallet_hash, WitnessScope.CalledByEntry)

dev_client = TestClient(target_url, dev_wallet_hash, dev_wallet_address, 'dev.json', '1')
dev_client.openwallet()
neo_balance, gas_balance = dev_client.get_neo_balance(), dev_client.get_gas_balance()
if neo_balance < 10 or gas_balance < 100e8:
    input(f'Warning: only f{neo_balance} NEOs and {gas_balance/1e8} left. \npress ENTER to continue')
dev_client.invokefunction()