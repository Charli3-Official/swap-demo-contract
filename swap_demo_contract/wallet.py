import os
from pycardano import (
    HDWallet,
    Address,
    Network,
    ExtendedSigningKey,
    PaymentVerificationKey,
    PaymentSigningKey,
)

MNEMONIC_24 = "issue patient merge audit idea swamp session afford nose spider boss wreck stairs evoke invest usage casino street muscle fury myth island host rude"


def user_address() -> Address:
    hdwallet = HDWallet.from_mnemonic(MNEMONIC_24)
    hdwallet_spend = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
    spend_public_key = hdwallet_spend.public_key
    spend_vk = PaymentVerificationKey.from_primitive(spend_public_key)

    hdwallet_stake = hdwallet.derive_from_path("m/1852'/1815'/0'/2/0")
    stake_public_key = hdwallet_stake.public_key
    stake_vk = PaymentVerificationKey.from_primitive(stake_public_key)

    str_address = Address(
        spend_vk.hash(), stake_vk.hash(), network=Network.TESTNET
    ).encode()
    return Address.from_primitive(str_address)


def user_esk() -> PaymentSigningKey:
    hdwallet = HDWallet.from_mnemonic(MNEMONIC_24)
    hdwallet_spend = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

    extended_signing_key = ExtendedSigningKey.from_hdwallet(hdwallet_spend)
    return extended_signing_key


user_address()
user_esk()
