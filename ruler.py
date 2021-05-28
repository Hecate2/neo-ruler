"""
requires neo3-boa==0.8.1
A replication of RULER protocol from ETH
https://rulerprotocol.com/
It is likely that the protocol cannot fully comply with NEP-17
because the name of tokens are always varying

The invoker of this contract borrows parity token by paying collateral token.
The contract gives the invoker not the parity token, but instead rcToken and rrToken.
rcToken (ruler capital token) is intended to be sold on market for parity token, which is finally needed by the invoker.
rrToken (ruler repayment token) represents the obligation to pay back parity token
Before the expiry date to return the parity token, the invoker should pay the amount of parity token back.
Otherwise, the collateral token would be forfeited by the contract.
When the parity token is paid back by the borrower, the owners of rcToken are given the parity token,
    and the borrower is given the collateral token.
If the parity token is only partially (or never) paid back after expiry,
    part of the borrower's collateral token can be claimed by rcToken holders,
    and the remaining part of the collateral can be claimed by the borrower.
(This contract attempts to support only NEO as the collateral token, and GAS as the parity token?)
The loan is FUNGIBLE. Anyone can collateralize tokens to borrow paired tokens. Any defaulted loan from the contract
    results to rcToken holder to get collateral tokens instead of paired tokens.

pair["colTotal"] is used to count all the rrTokens that have been minted; usually does not need to be reduced.
"""

from typing import Any, List, Tuple, Union, Dict, Sequence, cast
from boa3.builtin.interop.iterator import Iterator

from boa3.builtin import NeoMetadata, metadata, public
from boa3.builtin.contract import Nep17TransferEvent, abort
from boa3.builtin.interop.blockchain import get_contract
from boa3.builtin.interop.contract import NEO, GAS, call_contract, create_contract
from boa3.builtin.interop.runtime import calling_script_hash, check_witness, get_time, executing_script_hash
from boa3.builtin.interop.storage import delete, get, put, find, StorageMap, get_context
# from boa3.builtin.interop.crypto import sha256
from boa3.builtin.type import UInt160

"""
RC_TOKEN_NAME_PATTERN = f'RC_{COLLATERAL_TOKEN}_{MINT_RATIO}_{PARITY_TOKEN}_{EXPIRY_TIMESTAMP}'
RR_TOKEN_NAME_PATTERN = f'RR_{COLLATERAL_TOKEN}_{MINT_RATIO}_{PARITY_TOKEN}_{EXPIRY_TIMESTAMP}'
"""

'''
FILL this with compiled rToken contract nef and manifest.json!
'''
# rTokenTemplateNef: bytes = open('rToken.nef', 'rb').read()
# rTokenTemplateManifest: str = open('rToken.manifest.json', 'r').read()
rTokenTemplateNef: bytes = b'NEF3neo3-boa by COZ-0.8.1.0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xfdF\x04\x0c%rToken standard inherited from NEP-17@[A\x9b\xf6g\xceA\x92]\xe81J\xd8&\x07E\x0c\x00\xdb(\xdb(@\\A\x9b\xf6g\xceA\x92]\xe81J\xd8&\x07E\x0c\x00\xdb(\xdb!@ZA\x9b\xf6g\xceA\x92]\xe81J\xd8&\x07E\x0c\x00\xdb(\xdb!@W\x00\x01x\xca\x0c\x01\x14\xdb!\xb39xA\x9b\xf6g\xceA\x92]\xe81J\xd8&\x07E\x0c\x00\xdb(\xdb!@W\x02\x04x\xca\x0c\x01\x14\xdb!\xb3y\xca\x0c\x01\x14\xdb!\xb3\xab9z\x10\xb89xA\x9b\xf6g\xceA\x92]\xe81J\xd8&\x07E\x0c\x00\xdb(\xdb!phz\xb5&\x04\x10@xA9Sn<\x98&\rxA\xf8\'\xec\x8c\xaa&\x04\x10@xy\x98z\x10\xb4\xab&Ghz\xb3&\x0fxA\x9b\xf6g\xceA/X\xc5\xed"\x10hz\x9fxA\x9b\xf6g\xceA\xe6?\x18\x84yA\x9b\xf6g\xceA\x92]\xe81J\xd8&\x07E\x0c\x00\xdb(\xdb!qiz\x9eyA\x9b\xf6g\xceA\xe6?\x18\x84zyx\x13\xc0\x0c\x08TransferA\x95\x01oa{zyx4\x04\x11@W\x01\x04y\xd8\xaa&Sy\x11\xc0\x0c\x01\x0f\x0c\x0bgetContract\x0c\x14\xfd\xa3\xfaCF\xeaS*%\x8f\xc4\x97\xdd\xad\xdbd7\xc9\xfd\xffAb}[Rph\xd8\xaa&\x1f{zx\x13\xc0\x1f\x0c\x0eonNEP17PaymentyAb}[RE@W\x03\x02YA\x9b\xf6g\xceA\x92]\xe81J\xd8&\x07E\x0c\x00\xdb(pA9Sn<h\x97hA\xf8\'\xec\x8c\xac9y\x10\xb795\x8c\xfe\xff\xffqx5\x9c\xfe\xff\xffriy\x9eZA\x9b\xf6g\xceA\xe6?\x18\x84jy\x9exA\x9b\xf6g\xceA\xe6?\x18\x84yx\x0b\x13\xc0\x0c\x08TransferA\x95\x01oa\x0byx\x0b5:\xff\xff\xff@W\x03\x02y\x10\xb79YA\x9b\xf6g\xceA\x92]\xe81J\xd8&\x07E\x0c\x00\xdb(pA9Sn<h\x97hA\xf8\'\xec\x8c\xac9x50\xfe\xff\xffqiy\xb89iy\x9fxA\x9b\xf6g\xceA\xe6?\x18\x845\x01\xfe\xff\xffrjy\x9fZA\x9b\xf6g\xceA\xe6?\x18\x84y\x0bx\x13\xc0\x0c\x08TransferA\x95\x01oa\x0c\x14Burn rToken by Rulery\x0bx5\xaf\xfe\xff\xff@YA\x9b\xf6g\xceA\x92]\xe81J\xd8&\x07E\x0c\x00\xdb(A\xf8\'\xec\x8c@W\x00\x03XA\x9b\xf6g\xceA\x92]\xe81J\xd8&\x07E\x0c\x00\xdb(\x0c\x00\x97YA\x9b\xf6g\xceA\x92]\xe81J\xd8&\x07E\x0c\x00\xdb(\x0c\x00\x97\xab5n\xfd\xff\xff\x10\xb3\xab9\x11XA\x9b\xf6g\xceA\xe6?\x18\x84xYA\x9b\xf6g\xceA\xe6?\x18\x84y[A\x9b\xf6g\xceA\xe6?\x18\x84z\\A\x9b\xf6g\xceA\xe6?\x18\x84\x11@W\x00\x03z\x0c\x1dTransfer from caller to Ruler\x98z\x0c\x1dTransfer from Ruler to caller\x98\xab&\x038@V\x05\x0c\x8e\ncan be compiled by neo3-boa==0.8.1\nrTokens are NEP17 tokens, but its token symbol and administrator can be dynamically changed when deployed\nE\x0c\x0cNOT_DEPLOYED`\x0c\x05RULERa\x0c\x0btotalSupplyb\x0c\x0cTOKEN_SYMBOLc\x0c\x0eTOKEN_DECIMALSd@\xcc\xa3\n\xde'
rTokenTemplateManifestPrefix: bytes = b'''{"name":"'''
# rTokenTemplateManifestPrefix + token_symbol + rTokenTemplateManifestSuffix == rTokenManifest
rTokenTemplateManifestSuffix: bytes = b''' ","groups":[],"abi":{"methods":[{"name":"main","offset":0,"parameters":[],"returntype":"String","safe":false},{"name":"symbol","offset":40,"parameters":[],"returntype":"String","safe":false},{"name":"decimals","offset":63,"parameters":[],"returntype":"Integer","safe":false},{"name":"totalSupply","offset":86,"parameters":[],"returntype":"Integer","safe":false},{"name":"balanceOf","offset":109,"parameters":[{"name":"account","type":"Hash160"}],"returntype":"Integer","safe":false},{"name":"transfer","offset":144,"parameters":[{"name":"from_address","type":"Hash160"},{"name":"to_address","type":"Hash160"},{"name":"amount","type":"Integer"},{"name":"data","type":"Any"}],"returntype":"Boolean","safe":false},{"name":"mint","offset":415,"parameters":[{"name":"account","type":"Hash160"},{"name":"amount","type":"Integer"}],"returntype":"Void","safe":false},{"name":"burnByRuler","offset":529,"parameters":[{"name":"account","type":"Hash160"},{"name":"amount","type":"Integer"}],"returntype":"Void","safe":false},{"name":"verify","offset":668,"parameters":[],"returntype":"Boolean","safe":false},{"name":"deploy","offset":694,"parameters":[{"name":"ruler","type":"Hash160"},{"name":"symbol","type":"String"},{"name":"decimals","type":"Integer"}],"returntype":"Boolean","safe":false},{"name":"onNEP17Payment","offset":803,"parameters":[{"name":"from_address","type":"Hash160"},{"name":"amount","type":"Integer"},{"name":"data","type":"Any"}],"returntype":"Void","safe":false},{"name":"_initialize","offset":877,"parameters":[],"returntype":"Void","safe":false}],"events":[{"name":"Transfer","parameters":[{"name":"from_addr","type":"Any"},{"name":"to_addr","type":"Any"},{"name":"amount","type":"Integer"}]}]},"permissions":[{"contract":"*","methods":"*"}],"trusts":[],"features":[],"supportedstandards":[],"extra":{"Author":"github.com/Hecate2","Email":"chenxinhao@ngd.neo.org","Description":"Ruler token prototype; inherited from NEP-17"}}'''
# TODO: run a public contract for users to access standard rToken nef and manifest?

current_storage_context = get_context()

# collaterals: List[UInt160] = []
collaterals = StorageMap(current_storage_context, b'collaterals')
# collateral => minimum collateralizing ratio, paired token default to 1e8

# minColRatioMap: Dict[UInt160, int] = {}
minColRatioMap = StorageMap(current_storage_context, 'minColRatioMap')

# pairs: collateral => pairedToken => expiry => mintRatio => Pair
# pairs: Dict[UInt160, Dict[UInt160, Dict[int, Dict[int, Dict[str, Any]]]]] = {}
pairs_map = StorageMap(current_storage_context, b'pairs')
# get(f'{collateral}{pairedToken}{expiry}{mintRatio}') for the index of a pair
pair_max_index_key = b'pair_max_index'
put(pair_max_index_key, 1)
# pair: Dict[gen_pair_key, Any]; class Pair => attributes
pair_map = StorageMap(current_storage_context, b'pair_')  # store attributes of pairs

SEPARATOR = bytearray(b'_')


def gen_pair_key(index: int, attribute: str) -> bytearray:
    return bytearray(index.to_bytes()) + SEPARATOR + bytearray(attribute.to_bytes())


'''
pair: stores class Pair; key pattern: {index}{attribute}
class Pair:
    bool active;
    int expiry;
    UInt160 pairedToken;  # pairedToken address
    UInt160 rcToken;  # ruler capitol token address
    UInt160 rrToken;  # ruler repayment token address
    int mintRatio;  # 1e8 by default, price of collateral / collateralization ratio
    int feeRate;  # 1e8 by default
    int colTotal;  # used to count all the rrTokens that have been minted; usually does not need to be reduced.
'''

# pairList: List[Dict[str, Any]] = []  # List[Pair]
# pairList = StorageMap(current_storage_context, 'pairList')
# feesMap: Dict[UInt160, int] = {}
feesMap = StorageMap(current_storage_context, 'feesMap')

flashLoanRate: int = 0  # TODO: to be determined


@metadata
def manifest_metadata() -> NeoMetadata:
    meta = NeoMetadata()
    meta.author = "github.com/Hecate2"
    meta.description = "Ruler Protocol prototype"
    meta.email = "chenxinhao@ngd.neo.org"
    return meta


@public
def onNEP17Payment(_from_address: UInt160, _amount: int, _data: Any):
    if _data != "Transfer from caller to Ruler" and _data != "Transfer from Ruler to caller":
        # just a mechanism to prevent accidental wrong payment
        abort()


'''
@public
def mmDeposit(_col: UInt160, _paired: UInt160, _expiry: int, _mintRatio: int, _rcTokenAmt: int) -> None:
    """
    market make deposit
    deposit paired token into the contract to receive rcToken immediately
    caller must permit this contract to get token from caller's wallet
    I cannot infer the purpose of using this method. Will not be implemented with priority
    :param _col: address of the collateralized token
    :param _paired: address of the paired token
    :param _expiry: time of expiry
    :param _mintRatio:
    :param _rcTokenAmt:
    :return: None
    """
    # emit MarketMakeDeposit event
    return
'''


def _get_pair(_col: UInt160, _paired: UInt160, _expiry: int, _mintRatio: int) -> bytes:
    """
    assert result != b''
    :type _mintRatio: object
    """
    # pair = pairs[_col][_paired][_expiry][_mintRatio]
    key = _col + SEPARATOR + _paired + SEPARATOR + bytearray(_expiry.to_bytes())\
          + SEPARATOR + bytearray(_mintRatio.to_bytes())
    pair = pairs_map.get(key)
    return pair  # int or b''


def _get_pair_with_assertion(_col: UInt160, _paired: UInt160, _expiry: int, _mintRatio: int) -> int:
    """
    does not assert whether result is b'' or not
    :type _mintRatio: object
    """
    pair = _get_pair(_col, _paired, _expiry, _mintRatio)
    assert pair != b''
    return pair.to_int()  # int


def get_pair_attribute(pair_index: int, attribute: str) -> bytes:
    return pair_map.get(gen_pair_key(pair_index, attribute))


def _insert_pair(active: bool, feeRate: int, mintRatio: int, expiry: int,
                 collateralToken: UInt160, pairedToken: UInt160,
                 rcToken: UInt160, rrToken: UInt160, colTotal: int) -> int:
    """
    pairs[_col][_paired][_expiry][_mintRatio] = pair. This method does not consider whether the pair exists
    """
    max_index = get(pair_max_index_key).to_int()
    pair_map.put(gen_pair_key(max_index, "active"), active)
    pair_map.put(gen_pair_key(max_index, "feeRate"), feeRate)
    pair_map.put(gen_pair_key(max_index, "mintRatio"), mintRatio)
    pair_map.put(gen_pair_key(max_index, "expiry"), expiry)
    pair_map.put(gen_pair_key(max_index, "pairedToken"), pairedToken)
    pair_map.put(gen_pair_key(max_index, "collateralToken"), collateralToken)
    pair_map.put(gen_pair_key(max_index, "rcToken"), rcToken)
    pair_map.put(gen_pair_key(max_index, "rrToken"), rrToken)
    pair_map.put(gen_pair_key(max_index, "colTotal"), colTotal)
    put(pair_max_index_key, max_index + 1)
    return max_index


@public
def deposit(_col: UInt160, _paired: UInt160, _expiry: int, _mintRatio: int, _colAmt: int) -> bool:
    """
    deposit collateral to a Ruler Pair, and the sender receives rcTokens and rrTokens
    :param _col:
    :param _paired:
    :param _expiry:
    :param _mintRatio:
    :param _colAmt:
    :return: None
    """
    pair = _get_pair_with_assertion(_col, _paired, _expiry, _mintRatio)
    _validateDepositInputs(pair)
    # Before taking collateral from message sender,
    # get the balance of collateral of this contract
    assert call_contract(_col, "transfer", [calling_script_hash, executing_script_hash, _colAmt, "Transfer from caller to Ruler"]), "Failed to transfer collateral from caller to ruler."
    colTotal_key = gen_pair_key(pair, "colTotal")
    pair_map.put(colTotal_key, pair_map.get(colTotal_key).to_int() + _colAmt)
    mintAmount = _getRTokenAmtFromColAmt(_colAmt, _col, _paired, _mintRatio)
    call_contract(cast(UInt160, get_pair_attribute(pair, "rcToken")), "mint", [calling_script_hash, mintAmount])
    call_contract(cast(UInt160, get_pair_attribute(pair, "rrToken")), "mint", [calling_script_hash, mintAmount])
    return True


def _getRTokenAmtFromColAmt(_colAmt: int, _col: UInt160, _paired: UInt160, _mintRatio: int) -> int:
    parity_token_decimals = call_contract(_paired, "decimals")
    collateral_token_decimals = call_contract(_col, "decimals")
    delta_decimals = cast(int, parity_token_decimals) - cast(int, collateral_token_decimals)
    if delta_decimals >= 0:
        return _colAmt * (10 ** delta_decimals)
    else:
        delta_decimals = -delta_decimals
        return _colAmt // (10 ** delta_decimals)
        # is // a good choice?
        # TODO: consider / insetead of //


def _getColAmtFromRTokenAmt(_rTokenAmt: int, _col: UInt160, _rToken: UInt160, _mintRatio: int) -> int:
    r_token_decimals = call_contract(_rToken, "decimals")
    collateral_token_decimals = call_contract(_col, "decimals")
    delta_decimals = cast(int, collateral_token_decimals) - cast(int, r_token_decimals)
    if delta_decimals >= 0:
        return _rTokenAmt * (10 ** delta_decimals)
    else:
        delta_decimals = -delta_decimals
        return _rTokenAmt // (10 ** delta_decimals)
        # is // a good choice?
        # TODO: consider / insetead of //


def _validateDepositInputs(_pair: int):
    # assert cast(int, _pair["mintRatio"]) != 0, "Ruler: pair does not exist"
    assert get_pair_attribute(_pair, "active"), "Ruler: pair inactive"
    assert get_pair_attribute(_pair, "expiry").to_int() > get_time, "Ruler: pair expired"
    # TODO: Oracle


'''
@public
def redeem(_col: UInt160, _paired: UInt160, _expiry: int, _mintRatio: int, _colAmt: int):
    """
    give rrTokens and rcTokens before expiry to receive collateral. Fees charged on collateral
    No priority
    :param _col:
    :param _paired:
    :param _expiry:
    :param _mintRatio:
    :param _colAmt:
    :return:
    """
    return
'''


@public
def repay(_col: UInt160, _paired: UInt160, _expiry: int, _mintRatio: int, _rrTokenAmt: int):
    """
    repay the contract with rrTokens and paired token amount, and sender receives collateral.
    NO fees charged on collateral
    :param _col:
    :param _paired:
    :param _expiry:
    :param _mintRatio:
    :param _rrTokenAmt:
    :return:
    """
    pair = _get_pair_with_assertion(_col, _paired, _expiry, _mintRatio)
    _validateDepositInputs(pair)

    call_contract(_paired, "transfer", [calling_script_hash, executing_script_hash, _rrTokenAmt, "Transfer from caller to Ruler"])
    call_contract(cast(UInt160, get_pair_attribute(pair, "rrToken")), "burnByRuler", [calling_script_hash, _rrTokenAmt])

    colAmountToPay = _getColAmtFromRTokenAmt(_rrTokenAmt, _col, cast(UInt160, get_pair_attribute(pair, "rcToken")), get_pair_attribute(pair, "mintRatio").to_int())
    call_contract(_col, "transfer", [executing_script_hash, calling_script_hash, colAmountToPay, "Transfer from Ruler to caller"])


@public
def burn_rrToken_after_expiry(_col: UInt160, _paired: UInt160, _expiry: int, _mintRatio: int, _rrTokenAmt: int):
    pair = _get_pair_with_assertion(_col, _paired, _expiry, _mintRatio)
    assert get_time > _expiry, "You can only burn your rrToken after the loan expires"
    call_contract(cast(UInt160, get_pair_attribute(pair, "rrToken")), "burnByRuler", [calling_script_hash, _rrTokenAmt])


@public
def collect(_col: UInt160, _paired: UInt160, _expiry: int, _mintRatio: int, _rcTokenAmt: int):
    """
    sender collect paired tokens by returning same amount of rcTokens to Ruler
    :param _col:
    :param _paired:
    :param _expiry:
    :param _mintRatio:
    :param _rcTokenAmt:
    :return:
    """
    pair = _get_pair_with_assertion(_col, _paired, _expiry, _mintRatio)
    # assert cast(int, pair["mintRatio"]) != 0, "Ruler: pair does not exist"
    assert get_time > get_pair_attribute(pair, "expiry").to_int(), "Ruler: loan not expired"
    call_contract(cast(UInt160, get_pair_attribute(pair, "rcToken")), "burnByRuler", [calling_script_hash, _rcTokenAmt])
    
    defaultedLoanAmt = cast(int, call_contract(cast(UInt160, get_pair_attribute(pair, "rrToken")), "totalSupply", []))
    if defaultedLoanAmt == 0:
        _sendAmtPostFeesOptionalAccrue(cast(UInt160, get_pair_attribute(pair, "pairedToken")), _rcTokenAmt, get_pair_attribute(pair, "feeRate").to_int(), False)
    else:
        mintRatio = get_pair_attribute(pair, "mintRatio").to_int()
        feeRate = get_pair_attribute(pair, "feeRate").to_int()
        rcTokensEligibleAtExpiry = _getRTokenAmtFromColAmt(get_pair_attribute(pair, "colTotal").to_int(), _col, _paired, mintRatio)
        
        pairedTokenAmtToCollect = _rcTokenAmt * (rcTokensEligibleAtExpiry - defaultedLoanAmt) // rcTokensEligibleAtExpiry
        _sendAmtPostFeesOptionalAccrue(cast(UInt160, get_pair_attribute(pair, "pairedToken")), pairedTokenAmtToCollect, feeRate, False)
        
        colAmount = _getColAmtFromRTokenAmt(_rcTokenAmt, _col, cast(UInt160, get_pair_attribute(pair, "rcToken")), mintRatio)
        colAmountToCollect = colAmount * defaultedLoanAmt // rcTokensEligibleAtExpiry
        _sendAmtPostFeesOptionalAccrue(_col, colAmountToCollect, feeRate, True)


def _sendAmtPostFeesOptionalAccrue(_token: UInt160, _amount: int, _feeRate: int, _accrue: bool):
    fees = _amount * _feeRate // 100_000_000
    call_contract(_token, "transfer", [executing_script_hash, calling_script_hash, _amount - fees])
    if _accrue:
        original_fee = feesMap.get(_token).to_int()
        feesMap.put(_token, original_fee + fees)


"""
class Pair:
    active: bool
    feeRate: int
    mintRatio: int
    expiry: int
    pairedToken: UInt160
    rcToken: NEP17 token contract address
    rrToken: NEP17 token contract address
    colTotal: int
"""


def _modifyManifestName(_symbol: bytes) -> bytes:
    '''
    modify the manifest: add the token symbol field into the manifest.json file
    :param _template_manifest:
    :param _symbol:
    :return:
    '''
    # make sure _template_manifest[:-1] removes the last '}' in the manifest
    return rTokenTemplateManifestPrefix + _symbol + rTokenTemplateManifestSuffix


def _createRToken(_col: UInt160, _paired: UInt160, _expiry: int, _expiryStr: str, _mintRatioStr: str, _prefix: bytes, _paired_token_decimals: int) -> UInt160:
    # assert _paired_token_decimals >= 0, "RulerCore: paired decimals < 0"
    col_symbol = cast(bytes, call_contract(_col, "symbol", []))
    # col_decimals = cast(int, call_contract(_col, "decimals", []))
    paired_symbol = cast(bytes, call_contract(_paired, "symbol", []))
    symbol = bytearray(_prefix) + \
             bytearray(col_symbol) + \
             SEPARATOR + \
             bytearray(_mintRatioStr.to_bytes()) + \
             SEPARATOR + \
             bytearray(paired_symbol) + \
             SEPARATOR + \
             bytearray(_expiryStr.to_bytes())
    modified_manifest = _modifyManifestName(symbol)
    contract = create_contract(rTokenTemplateNef, modified_manifest)
    paired_decimals = cast(int, call_contract(_paired, "decimals", []))
    call_contract(contract.hash, 'deploy', [executing_script_hash, symbol, paired_decimals])
    return contract.hash


@public
def addPair(_col: UInt160, _paired: UInt160, _expiry: int, _expiryStr: str, _mintRatio: int, _mintRatioStr: str, _feeRate: int) -> int:
    """
    add a new Ruler Pair
    :param _col: collateral token address
    :param _paired: paired token address
    :param _expiry: expiry timestamp
    :param _expiryStr: readable date string. 'MM/DD/YYYY'. e.g. '05/20/2021'
    :param _mintRatio: mint ratio of this loan. How many paired token is worth 1 collateral token
    :param _mintRatioStr:
    :param _feeRate: A fee is charged for extraordinary operations. TODO: feeRate to be determined
    :return: None
    """
    pair = _get_pair(_col, _paired, _expiry, _mintRatio)
    assert pair == b'', 'Ruler: pair exists'
    assert _mintRatio > 0, "Ruler: _mintRatio <= 0"
    assert _feeRate < 100_000_000, "Ruler: fee rate must be < 100%"  # TODO: fee rate
    assert _expiry > get_time, "Ruler: expiry time earlier than current block timestamp"
    # minColRatioMap is related to fees
    # assert minColRatioMap.get(_col).to_int() > 0, "Ruler: collateral not listed"
    # minColRatioMap.put(_paired, 100_000_000)
    paired_token_decimals = cast(int, call_contract(_paired, "decimals", []))
    # pair: Dict[str, Any] = {
    #     'active': True,
    #     'feeRate': _feeRate,
    #     'mintRatio': _mintRatio,
    #     'expiry': _expiry,
    #     'pairedToken': _paired,
    #     'collateralToken': _col,
    #     'rcToken': _createRToken(_col, _paired, _expiry, _expiryStr, _mintRatioStr, "RC_", paired_token_decimals),
    #     'rrToken': _createRToken(_col, _paired, _expiry, _expiryStr, _mintRatioStr, "RR_", paired_token_decimals),
    #     'colTotal': 0,
    # }
    pair = _insert_pair(True, _feeRate, _mintRatio, _expiry, _col, _paired,
                 _createRToken(_col, _paired, _expiry, _expiryStr, _mintRatioStr, bytearray(b"RC") + SEPARATOR, paired_token_decimals),
                 _createRToken(_col, _paired, _expiry, _expiryStr, _mintRatioStr, bytearray(b"RR") + SEPARATOR, paired_token_decimals),
                 0)
    pairs_map.put(_col + SEPARATOR + _paired + SEPARATOR + bytearray(_expiry.to_bytes()) +
                  SEPARATOR + bytearray(_mintRatio.to_bytes()), pair)
    # pairList.append(pair)
    # pairList.put(_col + SEPARATOR + _paired, True)
    collaterals.put(_col, True)
    return pair
    
    
# @public
# def flashLoan(_receiver: UInt160, _token: UInt160, _amount: int, _data: Any) -> bool:
#     """
#     I cannot really understand the purpose of this feature provided by ETH ruler.
#     :param _receiver:
#     :param _token:
#     :param amount:
#     :param _data:
#     :return:
#     """
#     global minColRatioMap
#     assert minColRatioMap[_token] > 0, "Ruler: token not allowed"
#     call_contract(_token, "transfer", [executing_script_hash, calling_script_hash, _amount])
#     unfinished
#     requires method 'onFlashLoan' to be implemented by the user as a standard
#     return False


def flashFee(_token: UInt160, _amount: int) -> int:
    global minColRatioMap
    assert minColRatioMap.get(_token).to_int() > 0, 'RulerCore: token not supported'
    return _amount * flashLoanRate // 100_000_000


"""
@public
def setFlashLoanRate(_newRate: int) -> bool:
    return False

"""
@public
def getCollaterals() -> Iterator:
    return find(b'collaterals', current_storage_context)

# @public
# def getPairList(_col: UInt160) -> Iterator:
#     return find(bytearray(b'pairList') + _col, current_storage_context)
#     # return pairList.find(_col)

@public
def getPairsMap(_col: UInt160) -> Iterator:
    return find(bytearray(b'pairs') + _col, current_storage_context)

@public
def getPairAttributes(_pair: int) -> Iterator:
    return find(bytearray(b'pair_') + bytearray(_pair.to_bytes()) + SEPARATOR)