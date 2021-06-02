#### Intro

`ruler.py` allows everyone to borrow paired token by paying a sum of collateral token. 

In `ruler.py`, the administrator of ruler.py is expected to call `addPair` at first to allow other users to call `deposit` and `repay` to borrow paired tokens and pay back. 

`ruler` does not directly give paired token to the borrower, but only an equivalent amount of Ruler Capital Token (rcTokens) and another equivalent amount of Ruler Repayment Tokens (rrTokens). 

rcTokens are **expected to be sold on the market** for paired token, and represent the right to claim paired token after the loan expires (by calling `collect` in `ruler.py` after expiry). Usually the price of an rcToken sold on the market is lower than 1 paired token, because rcToken holders can only collect the paired token after a period of time (after expiry). The interest rate of the loan is simply determined by this market-driven price of rcToken.

rrToken is a representation of debt, indicating that the holder must pay back paired token before expiry. rc and rr tokens are created and managed by deploying multiple `rToken.py` contracts dynamically by `ruler.py`. 

The following figure shows the 4 steps of a loan operated by ruler and the market. 

![4 steps of ruler protocol operations](intro.png)

- **Defaulted loans**
  - part of collaterals are paid to rcToken holders when part of paired tokens go defaulted
  - Ruler protocol offers **FUNGIBLE** loan
    - A `Pair` is utilized by many borrowers. The pool of defaulted paired token is considered as a whole.
    - Any loan expired with any defaulted paired token caused by any borrower leads to all the rcToken holders receiving some collaterals. 

#### Objects / Concepts

- collateral token: 被抵押的币
- paired token: 被偿还的币
- expiry: a date before which the paired tokens are expected to be paid back
- **mint ratio**: 1 collateral token for how many rTokens (related to collateral ratio)
- **rcToken**: a representation of creditor's right; right to claim paired token . Users do not directly get paired token, but only rTokens from the ruler. rTokens are **publicly sold** on the market for paired token. Market-driven interest. 
- **rrToken**: a representation of debt liability; obligation to pay back paired token
- (I give the ruler 1 paired token; the ruler returns me *mint_ratio* rcTokens and *mint_ratio* rrTokens)
- Pair
  - collateral token
  - paired token
  - expiry
  - **mint ratio**
  - Representation: symbol of rTokens:
    - ticker symbol: `RC_{Collateral}_{Mint Ratio}_{Paired Token}_{Expiry}`
    - e.g. `RC_wBTC_10000_Dai_12_31_2021`

#### Management

- Pairs:
  - All the `Pair` objects and attributes of `Pair` are managed by administrator.
  - Borrowers should specify all the attributes of an existing `Pair` to borrow from that pair contract. 

#### Major APIs of solidity implementation

[RulerCore.sol](https://github.com/Ruler-Protocol/ruler-core-public/blob/1156cd52147efffb8cbd68508875010ef31acc38/contracts/RulerCore.sol#L242)

##### Functional APIs

| /// deposit collateral to a Ruler Pair, sender receives rcTokens and rrTokens |
| ------------------------------------------------------------ |
| function deposit                                             |
| address _col,<br/>address _paired,<br/>uint48 _expiry,<br/>uint256 _mintRatio,<br/>uint256 _colAmt |

| /// repay with rrTokens and paired token amount, sender receives collateral, no fees charged on collateral |
| ------------------------------------------------------------ |
| function repay                                               |

| /// sender collect paired tokens by returning same amount of rcTokens to Ruler |
| ------------------------------------------------------------ |
| function collect                                             |

| /// redeem with rrTokens and rcTokens <u>before expiry only</u>, sender receives collateral, <u>fees charged on collateral</u> |
| ------------------------------------------------------------ |
| function redeem                                              |

| /// market make deposit, deposit paired Token to received rcTokens, considered as an immediately repaid loan |
| ------------------------------------------------------------ |
| function mmDeposit                                           |

| /// Directly receive paired token (instead of rcTokens to be sold) with a fee |
| ------------------------------------------------------------ |
| function flashLoan                                           |

function viewCollectible  // How much I am eligible to collect

function getCollaterals  // Which types of collaterals are available to be paid to borrow paired tokens

function getPairList(address _col)  // detailed pair information using this type of collateral

##### Management APIs

| function addPair                                             |
| ------------------------------------------------------------ |
| address _col,<br/>address _paired,<br/>uint48 _expiry,<br/>string calldata _expiryStr,<br/>uint256 _mintRatio,<br/>string calldata _mintRatioStr,<br/>uint256 _feeRate |

**function _createRToken**  // deploy new contracts of rcToken and rrToken

function setFlashLoanRate

function updateCollateral

function setPairActive

function setFeeReceiver

function setPaused  // pause new deposits

function setOracle

function maxFlashLoan

function flashFee

#### Tests

- Test of token contract `rToken.py`: almost OK
- `Pair` CR(U?)(D?); `collaterals` CR(U?)(D?)
- `deposit` unit test
- `repay` unit test
- `collect` unit test

#### Known Problems

- Different rulers may deploy rToken contracts of the same `Pair(collateral, paired, expiry, mint_ratio)`. The ruler who deploys the rToken later would run into error: `Contract Already Exists: {contract_hash}`. A potential idea to resolve the conflict, is to add ruler's executing_script_hash into the name of rToken manifest. However, this method results in `'0x05' is invalid within a JSON string. The string should be correctly escaped. `, because executing_script_hash is not valid string.
- Precision of computation: repaying a little bit of GAS leads to 0 NEO returned. Possible solution: increase number of decimals, and require the returned number of tokens as integer. Also, What if we want the mint ratio as a float?
- Large integers may lead to unexpected results, but this might have been fixed in the latest version of `neo-vm`.
- It's VERY DIFFICULT to interpret the raw results returned from the contract. There has to be an SDK for users. 

#### Issues to be discussed

- Fees can be levied on lender. Shall fees be levied? Who receives the fee?
- Permission of management APIs ?
- Is it necessary to store representation strings (e.g. `expiry_str` and `mint_ratio_str`) in the contract?

#### Potential new features

- High precision: let there be no error in the amount of returned token, by automatically reducing the amount of paid token. **This would be very difficult if fees are levied.**
- flashLoan: borrower get actual paired tokens instead of rTokens. Fees charged.
- mmDeposit: market make deposit: deposit paired token into ruler to receive rcToken immediately. Fees?
- redeem: give rrTokens and rcTokens to the ruler before expiry to receive collateral. Fees charged.
- RULER token and liquidity mining
- xRULER token

#### Difficulties

no float support; no arithmetic division `/` support for now

no contract inheritance in Python

no support for returning multiple values

Cannot use wallet with Python SDK

#### Testing tactics

- VM-based
  - Use `ruler_test.py` to run scripts on `neo3vm`, utilizing `neo-mamba`.
  - Pros:
    - easily set the environment on the chain
    - faster execution
  - Cons:
    - No wallet support for now
    - Cannot utilize the latest `neo-vm`
    - Difficult to know the reason of exceptions raised from inside the `vm`
- private-chain-based
  - run a private chain with a consensus node and an outer node. The outer node accepts RPC requests from Python, and is run in a visual studio C# debugger with source codes of NEO.
  - Assisted by [DumpNef](https://github.com/devhawk/DumpNef), you can relate the InstructionPointer of the vm to the bytecodes in `.nef` files and the original Python codes of contract.
  - Pros:
    - Easy to watch the internal procedures in the blockchain. Easy to detect errors.
    - Almost the same as production environment
  - Cons
    - Harder to setup and reset the environment
    - Slower execution; unknown time for the transaction to be relayed on the blockchain.

#### Tutorial: How to test your smart contract on the vm using `neo-mamba`

Intuitively, you may want to deploy your smart contract onto your private blockchain, and test it via `neo-cli` commands manually, or via `RpcServer` plugin of `neo-cli` automatically. In fact, you do not always have to run a "real" blockchain to test your contract. The NEO virtual machine, as the backend of the blockchain's node, can execute the smart contract for you. Just follow these steps:

1. Build a "virtual" blockchain snapshot as the environment for the vm, simply with 2 lines of codes.

   ```python
   from neo3 import blockchain
   blockchain.Blockchain.__it__ = None  # This ensures your blockchain as a singleton object. Refer to:
   # https://github.com/CityOfZion/neo-mamba/blob/873932c8cb25497b90a39b3e327572746764e699/neo3/network/convenience/singleton.py#L12
   snapshot = blockchain.Blockchain(store_genesis_block=True).currentSnapshot
   # blockchain is singleton
   ```

   This snapshot contains blocks (only the genesis block in our case), contracts deployed on the chain, the history of transactions, and the storage status of all the contracts. This snapshot of blockchain does not update itself automatically. Instead, we use a vm to execute contracts and interact with the chain.

2. Build your vm, using your blockchain as the environment

   ```python
   from neo3 import vm, contracts
   from neo3.network import payloads
   tx = payloads.Transaction._serializable_init()
   engine = ApplicationEngine(contracts.TriggerType.APPLICATION, tx, snapshot, 0, test_mode=True)
   ```

   Now you have an `engine` to run custom smart contracts. `tx` is an empty `container` for your execution of contract.

3. Load your contract as a `Contract` object

   Your compiler `neo3-boa` generates a `.nef` file and a `.manifest.json` file. Load them into your Python environment with:

   ```python
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
   ```

   With the `nef` object and `manifest` object returned by function `build_nef_and_manifest_from_raw`, you can build you contract object:

   ```python
   contract = contracts.ContractState(0, nef, manifest, 0, types.UInt160.deserialize_from_bytes(raw_nef))
   ```

   The first `0` is the designated id of the contract in the block chain (assure no two contracts of the same id in the blockchain), and the second `0` is the counter of how many times the contract has been updated (usually just leave this as `0`). The `types.UInt160.deserialize_from_bytes(raw_nef)` is a placeholder for the hash of this contract. Note that the expression does not really generate the correct hash of the contract!

4. Deploy your contract

   ```python
   engine.snapshot.contracts.put(contract)
   ```

   A single line is enough for deploying.

5. Build a script to call a method in your contract

   First, you need a `ScriptBuilder`:

   ```python
   sb = vm.ScriptBuilder()
   ```

   Now you can build a script to call a method with arguments:

   ```python
   sb.emit_dynamic_call_with_args(contract.hash, method, params)
   ```

   or without arguments:

   ```python
   sb.emit_dynamic_call(contract.hash, method)
   ```

   Here, `method: str` is the name of the method in the contract you want to call, and `params: List[int, str, bytes, UInt160, ...]` is the arguments for the method. If an argument in your method is of type `UInt160`, you should always give `UInt160` type in `params`. `int`, `bytes` and `str` are not allowed. 

   Note that you are just building script in the `sb` object. You should then let the engine load your script built in `sb`. 

6. Load your script

   ```python
   engine.load_script(vm.Script(sb.to_array()))
   ```

7. Add signers

   Signers are wallets who witness the transaction. This is a safety concern to prevent issues like your transferring another person's tokens into your wallet. Usually you can specify yourself as a signer like this:

   ```python
   from neo3.core import types
   from neo3.core.types import UInt160
   signers = [payloads.Signer(types.UInt160.from_string('your_wallet_scripthash'), payloads.WitnessScope.CalledByEntry)]
   ```

   And

   ```python
   engine.script_container.signers = signers
   ```

8. Execute your contract!

   ```python
   engine.execute()
   ```

9. Commit the execution to the snapshot

   The execution of your contract should make effect on the blockchain, and in most cases you should persist this effect on the blockchain. So do not forget to commit the changes!

   ```python
   engine.snapshot.commit()
   ```

10. Watch the returned values of your method

    ```
    print(engine.state, str(engine.result_stack))
    ```

    A correct execution should result in `engine.state == VMState.HALT`. If you get `VMState.FAULT`, your engine probably have run into troubles.

11. Continuously execute another method

    Your blockchain has been changed because of the previous execution, and you should inherit the state of the blockchain from the previous engine. 

    ```python
    tx = payloads.Transaction._serializable_init()
    new_engine = ApplicationEngine(contracts.TriggerType.APPLICATION, tx, engine.snapshot, 0, test_mode=True)
    ```

    Now your `new_engine` has obtained the state of the blockchain after the previous execution. Happy testing with your `new_engine`!

12. The vm testing suite in this repository

    Consider using this re-encapsulated engine to run your tests!

    https://github.com/Hecate2/neo-ruler/blob/master/neo_test_with_vm/test_engine.py