#### Objects / Concepts

- collateral token: 被抵押的币
- paired token: 被偿还的币
- expiry: a date before which the paired tokens are expected to be paid back
- **mint ratio**: 1 collateral token for how many paired tokens
- **rcToken**: a representation of creditor's right; right to claim paired token . Users do not directly get paired token, but only rTokens from the ruler. rTokens are **publicly sold** on the market for paired token. Market-driven interest. 
- **rrToken**: a representation of debt liability; obligation to pay back paired token
- (I give the ruler 1 paired token; the ruler returns me *mint_ratio* rcTokens and *mint_ratio* rrTokens)
- Pair
  - collateral token
  - paired token
  - expiry
  - **mint ratio**
  - Representation: ticker symbol: `RC_{Collateral}_{Mint Ratio}_{Paired Token}_{Expiry}`
    - e.g. `RC_wBTC_10000_Dai_12_31_2021`

#### Management

- Pairs:
  - All the `Pair` objects and attributes of `Pair` are managed by administrator.
  - Borrowers should specify all the attributes of an existing `Pair` to borrow from that pair contract. 
- Defaulted loans
  - part of collaterals are paid to rcToken holders
  - Ruler protocol offers **FUNGIBLE** loan
    - A `Pair` is utilized by many borrowers. The pool of defaulted paired token is considered as a whole.
    - Any loan expired with any defaulted paired token caused by any user leads to rcToken holders receive some collaterals. 

#### Major APIs of solidity implementation

[RulerCore.sol](https://github.com/Ruler-Protocol/ruler-core-public/blob/1156cd52147efffb8cbd68508875010ef31acc38/contracts/RulerCore.sol#L242)

##### Functional APIs

| /// deposit collateral to a Ruler Pair, sender receives rcTokens and rrTokens |
| ------------------------------------------------------------ |
| function deposit                                             |
| address _col,<br/>    address _paired,<br/>    uint48 _expiry,<br/>    uint256 _mintRatio,<br/>    uint256 _colAmt |

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

function getCollaterals

function getPairList(address _col)

##### Management APIs

| function addPair                                             |
| ------------------------------------------------------------ |
| address _col,<br/>    address _paired,<br/>    uint48 _expiry,<br/>    string calldata _expiryStr,<br/>    uint256 _mintRatio,<br/>    string calldata _mintRatioStr,<br/>    uint256 _feeRate |

**function _createRToken**  // deploy new contracts of rcToken and rrToken

function setFlashLoanRate

function updateCollateral

function setPairActive

function setFeeReceiver

function setPaused

function setOracle

function maxFlashLoan

function flashFee

#### Tests

- Test of token contract `rToken.py`
- `Pair` CR(U?)(D?); `collaterals` CR(U?)(D?)
- `deposit` unit test
- `repay` unit test
- `collect` unit test

The Python SDK does not support wallet for testing. RPC-based tests on private chains are being implemented

#### Difficulties

no float support; no arithmetic division `/` support for now

no contract inheritance in Python

no support for returning multiple values

Automated tests: difficult be implemented in Python

- Cannot use wallet with Python SDK
- Cannot relay transaction to blockchain with RPC'
- Trying to utilize test engines provided by compiler