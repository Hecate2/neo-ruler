"""
A replication of ruler protocol from ETH ecology: https://rulerprotocol.com/

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
Amount of defaulted loan is counted by the remaining total supply of rrToken.
    Therefore, rrTokens should not be burned after expiry
The loan is FUNGIBLE. Anyone can collateralize tokens to borrow paired tokens. Any defaulted loan from the contract
    results to rcToken holder to get collateral tokens instead of paired tokens.

Potential fees of paired or collateral can be charged by the ruler on borrower or lender,
    but fees are not reliably supported for now.

pair["colTotal"] is used to count all the rrTokens that have been minted; usually does not need to be reduced.
"""

from typing import Any, cast
from boa3.builtin.interop.iterator import Iterator

from boa3.builtin import NeoMetadata, metadata, public
from boa3.builtin.interop.contract import call_contract, create_contract
from boa3.builtin.interop.runtime import get_time, executing_script_hash, calling_script_hash, check_witness
from boa3.builtin.interop.storage import get, put, find, StorageMap, get_context
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

ADMINISTRATOR_KEY = b'ADMIN'
FEE_RECEIVER_KEY = b'FEE_RECEIVER'
FLASH_LOAN_RATE_KEY = b'FLASH_LOAN_RATE'
DEPLOYED_KEY = b'DEPLOYED'

DECIMAL_BASE = 100_000_000
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

# feesMap: Dict[UInt160, int] = {}
feesMap = StorageMap(current_storage_context, 'feesMap')


@metadata
def manifest_metadata() -> NeoMetadata:
    meta = NeoMetadata()
    meta.author = "github.com/Hecate2"
    meta.description = "Ruler Protocol prototype"
    meta.email = "chenxinhao@ngd.neo.org"
    return meta


@public
def onNEP17Payment(_from_address: UInt160, _amount: int, _data: Any):
    pass  # do nothing for now
    # if _data != "Transfer from caller to Ruler" and _data != "Transfer from Ruler to caller":
    #     # just a mechanism to prevent accidental wrong payment
    #     abort()


@public
def deploy(administrator: UInt160) -> bool:
    """
    administrating access is mostly related to flashLoan
    """
    assert check_witness(administrator) or calling_script_hash == administrator
    if get(DEPLOYED_KEY) == b'':  # not deployed
        assert get(ADMINISTRATOR_KEY) == b''
        put(ADMINISTRATOR_KEY, administrator)
        put(FEE_RECEIVER_KEY, administrator)
        put(DEPLOYED_KEY, 1)
    else:
        original_administrator = get(ADMINISTRATOR_KEY)
        assert check_witness(original_administrator) or calling_script_hash == original_administrator
        put(ADMINISTRATOR_KEY, administrator)
    return True


@public
def setFlashLoanRate(_newRate: int) -> bool:
    administrator = get(ADMINISTRATOR_KEY)
    assert check_witness(administrator) or calling_script_hash == administrator
    put(FLASH_LOAN_RATE_KEY, _newRate)
    return True


@public
def getFlashLoanRate() -> int:
    return get(FLASH_LOAN_RATE_KEY).to_int()


@public
def setFeeReceiver(receiver: UInt160) -> bool:
    administrator = get(ADMINISTRATOR_KEY)
    assert check_witness(administrator) or calling_script_hash == administrator
    put(FEE_RECEIVER_KEY, receiver)
    return True


@public
def collectFee(token: UInt160) -> bool:
    # no need to check witness
    fee_receiver = get(FEE_RECEIVER_KEY)
    amount = feesMap.get(token).to_int()
    if amount > 0:
        feesMap.put(token, 0)
        assert call_contract(token, 'transfer', [executing_script_hash, fee_receiver, amount, bytearray(b'collect ') + token])
        return True
    return False


@public
def collectFees() -> bool:
    """
    No guaranteed iterator support in Python.
    """
    # no need to check witness
    iterator = find('feesMap')
    fee_receiver = get(FEE_RECEIVER_KEY)
    while iterator.next():
        token = cast(UInt160, iterator.value[0])
        fee_amount = cast(bytes, iterator.value[1]).to_int()
        if fee_amount > 0:
            assert call_contract(token, 'transfer', [executing_script_hash, fee_receiver, fee_amount, 'Collect Fees'])
    return True


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


@public
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
def mmDeposit(invoker: UInt160, _col: UInt160, _paired: UInt160, _expiry: int, _mintRatio: int, _rcTokenAmt: int) -> bool:
    """
    market make deposit
    deposit paired token into the contract to receive rcToken immediately
    caller must permit this contract to get token from caller's wallet
    I cannot infer the purpose of using this method. Trying to receive collateral instead of paired token?
    :param _col: address of the collateralized token
    :param _paired: address of the paired token
    :param _expiry: time of expiry
    :param _mintRatio:
    :param _rcTokenAmt:
    :return: None
    """
    pair_index = _get_pair_with_assertion(_col, _paired, _expiry, _mintRatio)
    _validateDepositInputs(pair_index)
    assert call_contract(_paired, "transfer", [invoker, executing_script_hash, _rcTokenAmt, "Transfer from caller to Ruler"]), "Failed to transfer paired token from caller to Ruler"
    
    rcToken_address = cast(UInt160, get_pair_attribute(pair_index, 'rcToken'))
    call_contract(rcToken_address, "mint", [invoker, _rcTokenAmt])

    feeRate = get_pair_attribute(pair_index, 'feeRate').to_int()
    feesMap.put(_paired, feesMap.get(_paired).to_int() + _rcTokenAmt * feeRate // DECIMAL_BASE)
    
    colAmount = _getColAmtFromRTokenAmt(_rcTokenAmt, _col, rcToken_address, _mintRatio)
    colTotal_key = gen_pair_key(pair_index, 'colTotal')
    colTotal = pair_map.get(colTotal_key).to_int()
    pair_map.put(colTotal_key, colTotal + colAmount)

    return True


@public
def deposit(invoker: UInt160, _col: UInt160, _paired: UInt160, _expiry: int, _mintRatio: int, _colAmt: int) -> bool:
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
    assert call_contract(_col, "transfer", [invoker, executing_script_hash, _colAmt, "Transfer from caller to Ruler"]), "Failed to transfer collateral from caller to ruler."
    colTotal_key = gen_pair_key(pair, "colTotal")
    pair_map.put(colTotal_key, pair_map.get(colTotal_key).to_int() + _colAmt)
    mintAmount = _getRTokenAmtFromColAmt(_colAmt, _col, _paired, _mintRatio)
    rcToken_address = cast(UInt160, get_pair_attribute(pair, "rcToken"))
    call_contract(rcToken_address, "mint", [invoker, mintAmount])
    rrToken_address = cast(UInt160, get_pair_attribute(pair, "rrToken"))
    call_contract(rrToken_address, "mint", [invoker, mintAmount])
    # The following codes lead to 2 DROP instructions after System.Contract.Call, and there would be exception
    # call_contract(cast(UInt160, get_pair_attribute(pair, "rcToken")), "mint", [invoker, mintAmount])
    # call_contract(cast(UInt160, get_pair_attribute(pair, "rrToken")), "mint", [invoker, mintAmount])
    return True


def _getRTokenAmtFromColAmt(_colAmt: int, _col: UInt160, _paired: UInt160, _mintRatio: int) -> int:
    parity_token_decimals = call_contract(_paired, "decimals")
    collateral_token_decimals = call_contract(_col, "decimals")
    delta_decimals = cast(int, parity_token_decimals) - cast(int, collateral_token_decimals)
    if delta_decimals >= 0:
        return _colAmt * _mintRatio * (10 ** delta_decimals)
    else:
        delta_decimals = -delta_decimals
        return _colAmt * _mintRatio // (10 ** delta_decimals)
        # is // a good choice?
        # TODO: consider / instead of //


def _getColAmtFromRTokenAmt(_rTokenAmt: int, _col: UInt160, _rToken: UInt160, _mintRatio: int) -> int:
    r_token_decimals = call_contract(_rToken, "decimals")
    collateral_token_decimals = call_contract(_col, "decimals")
    delta_decimals = cast(int, collateral_token_decimals) - cast(int, r_token_decimals)
    if delta_decimals >= 0:
        return _rTokenAmt * (10 ** delta_decimals) // _mintRatio
    else:
        delta_decimals = -delta_decimals
        return _rTokenAmt // (_mintRatio * 10 ** delta_decimals)
        # is // a good choice?
        # TODO: consider / instead of //


def _validateDepositInputs(_pair: int):
    assert get_pair_attribute(_pair, "active"), "Ruler: pair inactive"
    assert get_pair_attribute(_pair, "expiry").to_int() > get_time, "Ruler: pair expired"
    # TODO: Oracle


@public
def redeem(invoker: UInt160, _col: UInt160, _paired: UInt160, _expiry: int, _mintRatio: int, _rTokenAmt: int) -> bool:
    """
    give rrTokens and rcTokens before expiry to receive collateral. Fees charged on collateral
    """
    pair = _get_pair_with_assertion(_col, _paired, _expiry, _mintRatio)
    assert get_time < get_pair_attribute(pair, 'expiry').to_int(), 'Ruler: pair expired'
    
    rcToken_address = cast(UInt160, get_pair_attribute(pair, 'rcToken'))
    call_contract(rcToken_address, 'burnByRuler', [invoker, _rTokenAmt])
    rrToken_address = cast(UInt160, get_pair_attribute(pair, 'rrToken'))
    call_contract(rrToken_address, 'burnByRuler', [invoker, _rTokenAmt])
    
    colAmountToPay = _getColAmtFromRTokenAmt(_rTokenAmt, _col, rcToken_address, _mintRatio)
    colTotal_key = gen_pair_key(pair, 'colTotal')
    colTotal = pair_map.get(colTotal_key).to_int()
    pair_map.put(colTotal_key, colTotal - colAmountToPay)
    
    feeRate = get_pair_attribute(pair, 'feeRate').to_int()
    _sendAmtPostFeesOptionalAccrue(invoker, _col, colAmountToPay, feeRate, True)

    return True


@public
def repay(invoker: UInt160, _col: UInt160, _paired: UInt160, _expiry: int, _mintRatio: int, _rrTokenAmt: int):
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
    assert get_pair_attribute(pair, "expiry").to_int() > get_time, "Ruler: pair expired"

    assert call_contract(_paired, "transfer", [invoker, executing_script_hash, _rrTokenAmt, "Transfer from caller to Ruler"])
    rrToken_address = cast(UInt160, get_pair_attribute(pair, "rrToken"))
    call_contract(rrToken_address, "burnByRuler", [invoker, _rrTokenAmt])
    
    feesMap.put(_paired, feesMap.get(_paired).to_int() + _rrTokenAmt * get_pair_attribute(pair, 'feeRate').to_int() // 10_000_000)

    colAmountToPay = _getColAmtFromRTokenAmt(_rrTokenAmt, _col, cast(UInt160, get_pair_attribute(pair, "rcToken")), get_pair_attribute(pair, "mintRatio").to_int())
    assert call_contract(_col, "transfer", [executing_script_hash, invoker, colAmountToPay, "Transfer from Ruler to caller"])


@public
def collect(invoker: UInt160, _col: UInt160, _paired: UInt160, _expiry: int, _mintRatio: int, _rcTokenAmt: int):
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
    assert get_time > get_pair_attribute(pair, "expiry").to_int(), "Ruler: loan not expired"
    rcToken_address = cast(UInt160, get_pair_attribute(pair, "rcToken"))
    call_contract(rcToken_address, "burnByRuler", [invoker, _rcTokenAmt])
    
    rrToken_address = cast(UInt160, get_pair_attribute(pair, "rrToken"))
    defaultedLoanAmt = cast(int, call_contract(rrToken_address, "totalSupply", []))
    
    pairedToken_address = cast(UInt160, get_pair_attribute(pair, "pairedToken"))
    if defaultedLoanAmt == 0:
        _sendAmtPostFeesOptionalAccrue(invoker, pairedToken_address, _rcTokenAmt, get_pair_attribute(pair, "feeRate").to_int(), False)
    else:
        mintRatio = get_pair_attribute(pair, "mintRatio").to_int()
        feeRate = get_pair_attribute(pair, "feeRate").to_int()
        rcTokensEligibleAtExpiry = _getRTokenAmtFromColAmt(get_pair_attribute(pair, "colTotal").to_int(), _col, _paired, mintRatio)
        
        pairedTokenAmtToCollect = _rcTokenAmt * (rcTokensEligibleAtExpiry - defaultedLoanAmt) // rcTokensEligibleAtExpiry
        _sendAmtPostFeesOptionalAccrue(invoker, pairedToken_address, pairedTokenAmtToCollect, feeRate, False)

        colAmount = _getColAmtFromRTokenAmt(_rcTokenAmt, _col, rcToken_address, mintRatio)
        colAmountToCollect = colAmount * defaultedLoanAmt // rcTokensEligibleAtExpiry
        _sendAmtPostFeesOptionalAccrue(invoker, _col, colAmountToCollect, feeRate, True)


def _sendAmtPostFeesOptionalAccrue(invoker: UInt160, _token: UInt160, _amount: int, _feeRate: int, _accrue: bool):
    fees = _amount * _feeRate // DECIMAL_BASE
    assert call_contract(_token, "transfer", [executing_script_hash, invoker, _amount - fees, "collect paired token from ruler with rcTokens"])
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
    return rTokenTemplateManifestPrefix + _symbol + rTokenTemplateManifestSuffix


def _createRToken(_col: UInt160, _paired: UInt160, _expiry: int, _expiryStr: str, _mintRatioStr: str, _prefix: bytes, _paired_token_decimals: int) -> UInt160:
    col_symbol = cast(bytes, call_contract(_col, "symbol", []))
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
    add a new Ruler Pair. It is not bad for all the users to utilize this method.
        Not necessary to limit the permission to the administrator of ruler.
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
    assert _feeRate < DECIMAL_BASE, "Ruler: fee rate must be < 100%"  # TODO: fee rate
    assert _expiry > get_time, "Ruler: expiry time earlier than current block timestamp"
    # minColRatioMap is related to fees
    # assert minColRatioMap.get(_col).to_int() > 0, "Ruler: collateral not listed"
    # minColRatioMap.put(_paired, DECIMAL_BASE)
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
    collaterals.put(_col, True)
    return pair
    

@public
def flashLoan(_receiver: UInt160, _token: UInt160, _amount: int, _data: Any) -> bool:
    """
    invoker receives an amount of token immediately, utilize the amount of paired token immediately with onFlashLoan,
        and repay all the borrowed paired token and an amount of fee immediately
    :param _receiver:
    :param _token:
    :param amount:
    :param _data:
    :return:
    """
    assert call_contract(_token, "transfer", [executing_script_hash, _receiver, _amount, _data]), "Failed to transfer from Ruler to flashLoan receiver"
    fee = get(FLASH_LOAN_RATE_KEY).to_int() * _amount // DECIMAL_BASE
    assert call_contract(_receiver, 'onFlashLoan', [calling_script_hash, _token, _amount, fee, _data]), "Failed to execute method 'onFlashLoan' of flashLoan receiver"
    feesMap.put(_token, feesMap.get(_token).to_int() + fee)
    assert call_contract(_token, "transfer", [_receiver, executing_script_hash, _amount + fee, _data]), "Failed to transfer from flashLoan receiver to Ruler"
    return True


@public
def getCollaterals() -> Iterator:
    return find(b'collaterals', current_storage_context)

@public
def getPairsMap(_col: UInt160) -> Iterator:
    return find(bytearray(b'pairs') + _col, current_storage_context)

@public
def getPairAttributes(_pair: int) -> Iterator:
    return find(bytearray(b'pair_') + bytearray(_pair.to_bytes()) + SEPARATOR)

@public
def getFeesMap() -> Iterator:
    assert check_witness(get(ADMINISTRATOR_KEY)) or check_witness(get(FEE_RECEIVER_KEY))
    return find(b'feesMap')