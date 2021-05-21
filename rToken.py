'''
can be compiled by neo3-boa==0.8.1
rTokens are NEP17 tokens, but its token symbol and administrator can be dynamically changed when deployed
'''
# TODO: Discussion is needed for safety and permission issues

from typing import Any, Union

from boa3.builtin import NeoMetadata, metadata, public
from boa3.builtin.contract import Nep17TransferEvent, abort
from boa3.builtin.interop.blockchain import get_contract
from boa3.builtin.interop.contract import GAS, NEO, call_contract
from boa3.builtin.interop.runtime import calling_script_hash, check_witness
from boa3.builtin.interop.storage import delete, get, put
from boa3.builtin.type import UInt160


# -------------------------------------------
# METADATA
# -------------------------------------------

@metadata
def manifest_metadata() -> NeoMetadata:
    meta = NeoMetadata()
    meta.author = "github.com/Hecate2"
    meta.description = "Ruler token prototype; inherited from NEP-17"
    meta.email = "chenxinhao@ngd.neo.org"
    return meta


# -------------------------------------------
# TOKEN SETTINGS
# -------------------------------------------

NOT_DEPLOYED_KEY = 'NOT_DEPLOYED'

# Script hash of the contract owner
RULER_KEY = 'RULER'  # get(RULER_KEY) for the address of the ruler contract
SUPPLY_KEY = 'totalSupply'

# Symbol of the Token
TOKEN_SYMBOL_KEY = 'TOKEN_SYMBOL'

# Number of decimal places
TOKEN_DECIMALS_KEY = 'TOKEN_DECIMALS'


# -------------------------------------------
# Events
# -------------------------------------------


on_transfer = Nep17TransferEvent


# -------------------------------------------
# Methods
# -------------------------------------------


@public
def main() -> str:
    return "rToken standard inherited from NEP-17"


@public  # NEP-17 standard. DO NOT MODIFY
def symbol() -> str:
    """
    Gets the symbols of the token.

    This string must be valid ASCII, must not contain whitespace or control characters, should be limited to uppercase
    Latin alphabet (i.e. the 26 letters used in English) and should be short (3-8 characters is recommended).
    This method must always return the same value every time it is invoked.

    :return: a short string representing symbol of the token managed in this contract.
    """
    return get(TOKEN_SYMBOL_KEY).to_str()


@public  # NEP-17 standard. DO NOT MODIFY
def decimals() -> int:
    """
    Gets the amount of decimals used by the token.

    E.g. 8, means to divide the token amount by 100,000,000 (10 ^ 8) to get its user representation.
    This method must always return the same value every time it is invoked.

    :return: the number of decimals used by the token.
    """
    return get(TOKEN_DECIMALS_KEY).to_int()


@public  # NEP-17 standard. DO NOT MODIFY
def totalSupply() -> int:
    """
    Gets the total token supply deployed in the system.

    This number must not be in its user representation. E.g. if the total supply is 10,000,000 tokens, this method
    must return 10,000,000 * 10 ^ decimals.

    :return: the total token supply deployed in the system.
    """
    return get(SUPPLY_KEY).to_int()


@public  # NEP-17 standard. DO NOT MODIFY
def balanceOf(account: UInt160) -> int:
    """
    Get the current balance of an address

    The parameter account must be a 20-byte address represented by a UInt160.

    :param account: the account address to retrieve the balance for
    :type account: UInt160
    """
    assert len(account) == 20
    return get(account).to_int()


@public  # NEP-17 standard. DO NOT MODIFY
def transfer(from_address: UInt160, to_address: UInt160, amount: int, data: Any) -> bool:
    """
    Transfers an amount of NEP17 tokens from one account to another

    If the method succeeds, it must fire the `Transfer` event and must return true, even if the amount is 0,
    or from and to are the same address.

    :param from_address: the address to transfer from
    :type from_address: UInt160
    :param to_address: the address to transfer to
    :type to_address: UInt160
    :param amount: the amount of NEP17 tokens to transfer
    :type amount: int
    :param data: whatever data is pertinent to the onPayment method
    :type data: Any

    :return: whether the transfer was successful
    :raise AssertionError: raised if `from_address` or `to_address` length is not 20 or if `amount` is less than zero.
    """
    # the parameters from and to should be 20-byte addresses. If not, this method should throw an exception.
    assert len(from_address) == 20 and len(to_address) == 20
    # the parameter amount must be greater than or equal to 0. If not, this method should throw an exception.
    assert amount >= 0

    # The function MUST return false if the from account balance does not have enough tokens to spend.
    from_balance = get(from_address).to_int()
    if from_balance < amount:
        return False

    # The function should check whether the from address equals the caller contract hash.
    # If so, the transfer should be processed;
    # If not, the function should use the check_witness to verify the transfer.
    if from_address != calling_script_hash:
        if not check_witness(from_address):
            return False

    # skip balance changes if transferring to yourself or transferring 0 cryptocurrency
    if from_address != to_address and amount != 0:
        if from_balance == amount:
            delete(from_address)
        else:
            put(from_address, from_balance - amount)

        to_balance = get(to_address).to_int()
        put(to_address, to_balance + amount)

    # if the method succeeds, it must fire the transfer event
    on_transfer(from_address, to_address, amount)
    # if the to_address is a smart contract, it must call the contracts onPayment
    post_transfer(from_address, to_address, amount, data)
    # and then it must return true
    return True


def post_transfer(from_address: Union[UInt160, None], to_address: Union[UInt160, None], amount: int, data: Any):
    """
    Checks if the one receiving NEP17 tokens is a smart contract and if it's one the onPayment method will be called

    :param from_address: the address of the sender
    :type from_address: UInt160
    :param to_address: the address of the receiver
    :type to_address: UInt160
    :param amount: the amount of cryptocurrency that is being sent
    :type amount: int
    :param data: any pertinent data that might validate the transaction
    :type data: Any
    """
    if not isinstance(to_address, None):    # TODO: change to 'is not None' when `is` semantic is implemented
        contract = get_contract(to_address)
        if not isinstance(contract, None):      # TODO: change to 'is not None' when `is` semantic is implemented
            call_contract(to_address, 'onNEP17Payment', [from_address, amount, data])


@public
def mint(account: UInt160, amount: int):
    """
    Mints new tokens. This is not a NEP-17 standard method.

    :param account: the address of the account that is sending cryptocurrency to this contract
    :type account: UInt160
    :param amount: the amount of gas to be refunded
    :type amount: int
    :raise AssertionError: raised if amount is less than than 0
    """
    ruler = get(RULER_KEY)
    assert calling_script_hash == ruler or check_witness(ruler), "No permission to mint rToken"
    assert amount > 0, "mint amount <= 0"
    current_total_supply = totalSupply()
    account_balance = balanceOf(account)

    put(SUPPLY_KEY, current_total_supply + amount)
    put(account, account_balance + amount)

    on_transfer(None, account, amount)
    post_transfer(None, account, amount, None)


@public  # rToken standard
def burnByRuler(account: UInt160, amount: int):
    assert amount > 0
    ruler = get(RULER_KEY)
    assert calling_script_hash == ruler or check_witness(ruler)
    
    remaining_balance = balanceOf(account)
    assert remaining_balance >= amount, "No enough Token to burn. Maybe you requested an overly large amount."
    put(account, remaining_balance - amount)
    
    total_supply = totalSupply()
    put(SUPPLY_KEY, total_supply - amount)
    
    on_transfer(account, None, amount)  # somehow meaningless
    post_transfer(account, None, amount, "Burn rToken by Ruler")  # somehow meaningless


@public
def verify() -> bool:
    """
    When this contract address is included in the transaction signature,
    this method will be triggered as a VerificationTrigger to verify that the signature is correct.
    For example, this method needs to be called when withdrawing token from the contract.

    :return: whether the transaction signature is correct
    """
    return check_witness(get(RULER_KEY))


@public
def deploy(ruler: UInt160, symbol: str, decimals: int) -> bool:
    """
    Initializes the params when the smart contract is deployed. This method must be executed immediately when deployed
    :param ruler: the address of ruler contract
    :param symbol: the symbol of rToken, f'{RC or RR}_{COLLATERAL_RATE}_{MINT_RATIO}_{PARITY_TOKEN}_{EXPIRY_TIMESTAMP}'
    :return: whether the deploy was successful. This method must return True only during the smart contract's deploy.
    """
    # do not check whether calling_script_hash == ruler, because this contract is deployed just now
    assert get(NOT_DEPLOYED_KEY) == b'' \
           and get(RULER_KEY) == b'' \
           and totalSupply() == 0, \
        'Ruler Core: the token has been deployed'
    put(NOT_DEPLOYED_KEY, 1)
    put(RULER_KEY, ruler)
    put(TOKEN_SYMBOL_KEY, symbol)
    put(TOKEN_DECIMALS_KEY, decimals)
    return True


@public
def onNEP17Payment(from_address: UInt160, amount: int, data: Any):
    if data != "Transfer from caller to Ruler" and data != "Transfer from Ruler to caller":
        # just a mechanism to prevent accidental wrong payment
        abort()

