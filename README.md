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

#### Known Issues

- Different rulers may deploy rToken contracts of the same `Pair(collateral, paired, expiry, mint_ratio)`. The ruler who deploys the rToken later would run into error: `Contract Already Exists: {contract_hash}`. A potential idea to resolve the conflict, is to add ruler's executing_script_hash into the name of rToken manifest. However, this method results in `'0x05' is invalid within a JSON string. The string should be correctly escaped. `, because executing_script_hash is not valid string.

#### Difficulties

Currently the Python SDK `neo-mamba` does not support wallet for testing. Meanwhile, RPC-based tests on private chains do not support relaying transactions to the block chain, so any execution of contract does not take effect on the blockchain.

no float support; no arithmetic division `/` support for now

no contract inheritance in Python

no support for returning multiple values

Automated tests: difficult to be implemented in Python

- Cannot use wallet with Python SDK