import cbor2
import time
from pycardano import (
    BlockFrostChainContext,
    ChainContext,
    Network,
    Address,
    PaymentVerificationKey,
    PaymentSigningKey,
    TransactionOutput,
    TransactionBuilder,
    Redeemer,
    RedeemerTag,
    MultiAsset,
    AssetName,
    ExecutionUnits,
    PlutusV2Script,
    PointerAddress,
    plutus_script_hash,
    HDWallet,
    VerificationKeyHash,
)

from lib.datums import *
from lib.redeemers import *
from lib.chain_query import ChainQuery

# import swap

from swap import SwapContract, Swap

from wallet import *

# the script address is the hash of the validator (wrapped in a scriptCredential)
oracle_owner_string = "addr_test1qqd92r2l2ujcfcdd6yjm2uf0wzdv8wvz3tvxtqdywkgz9wst8wu42mt05a6cy4g05semeh9qs93r3ar8wn9n0u49mx8sc5ctp6"
oracle_addr_string = "addr_test1wz58xs5ygmjf9a3p6y3qzmwxp7cyj09zk90rweazvj8vwds4d703u"
# swap_addr_string = "addr_test1wpvqg0lgah2wung0shfqh3u0q0xcjedhszvxrvr8gm6crfq4mwzd3"
swap_addr_string = "addr_test1wzymkkmv7tg2n2e2vffw9nluh3lvmhg2pnhvc7qxdtl82nggxgd8l"
#
# payment pub key hash // spending shared hash
# oracle_owner_ppkh = Address.from_primitive(oracle_owner_string).payment_part
# print(f"{oracle_owner_ppkh}")
oracle_payment_pub_key_hash = Address.from_primitive(oracle_addr_string).payment_part
# print  ( f"{type(oracle_payment_pub_key_hash)}")
# print (oracle_payment_pub_key_hash)
#
# Haskell address
# Address {addressCredential = ScriptCredential
# b0b82e3846ab80653843d417021e86a4e2ebcf700cf2d869d4cdc521,
# addressStakingCredential = Nothing}
#
BLOCKFROST_PROJECT_ID = "preprod0kc9ZbgLbwq7XcMtPKM4olGnedkOp2Vn"
BLOCKFROST_BASE_URL = "https://cardano-preprod.blockfrost.io/api"
NETWORK_MODE = Network.TESTNET
SCRIPT_PATH_ORACLE = "./utils/scripts/oracle.plutus"
SCRIPT_PATH_SWAP = "./utils/scripts/swap.plutus"
MEDIATOR_POLICY = ""

# Address
oracle_address = Address.from_primitive(oracle_addr_string)
swap_address = Address.from_primitive(swap_addr_string)

# print ( f"the type of oracle_address is  {type(oracle_address)}")
# print ( f"the type of oracle_addr is  {type(oracle_addr)}")


def initialise_cardano():
    chain_context = BlockFrostChainContext(
        project_id=BLOCKFROST_PROJECT_ID,
        base_url=BLOCKFROST_BASE_URL,
        network=NETWORK_MODE,
    )
    return chain_context


# context = initialise_cardano()
context = ChainQuery(
    BLOCKFROST_PROJECT_ID,
    NETWORK_MODE,
    base_url="https://cardano-preprod.blockfrost.io/api",
)

# with open("./utils/scripts/swap.plutus", "r") as f:
#     script_hex = f.read()
#     swap_script_u = cbor2.loads(bytes.fromhex(script_hex))

# script_hash_from_file = plutus_script_hash(swap_script_u)
# print(script_hash_from_file)

swap_scrip_hash_from_address = swap_address.payment_part
swap_script_address = context._get_script(str(swap_scrip_hash_from_address))
new_swap_script = PlutusV2Script(cbor2.dumps(swap_script_address))
# print(swap_script_address)

# test = plutus_script_hash(new)
# print(test)

# print(script_hash_from_file)
# if swap_script_address == script_hash_from_file:
#     print("same")
# else:
#     print("mistmatch")
# swap_script_address = PlutusV2Script(cbor2.dumps(swap_script_address))
# if swap_script_address == script_hash_from_file:
#     print("same")
# else:
#     print("mistmatch")
# node_signing_key = PaymentSigningKey.generate()
# node_signing_key.save("node.skey")
# node_verification_key = PaymentVerificationKey.from_signing_key(node_signing_key)
# node_verification_key.save("node.vkey")
extendend_payment_skey = PaymentSigningKey.load("./credentials/node.skey")
extendend_payment_vkey = PaymentVerificationKey.load("./credentials/node.vkey")
# node_pub_key_hash = node_verification_key.hash()
# print(type(extendend_payment_skey))
user_address = Address(payment_part=extendend_payment_vkey.hash(), network=NETWORK_MODE)
oracle_nft = MultiAsset.from_primitive(
    {
        "8fe2ef24b3cc8882f01d9246479ef6c6fc24a6950b222c206907a8be": {
            b"InlineOracleFeed": 1
        }
    }
)

aggState_nft = MultiAsset.from_primitive(
    {"8fe2ef24b3cc8882f01d9246479ef6c6fc24a6950b222c206907a8be": {b"AggState": 1}}
)

node_token = MultiAsset.from_primitive(
    {"8fe2ef24b3cc8882f01d9246479ef6c6fc24a6950b222c206907a8be": {b"NodeFeed": 1}}
)
fee_token = MultiAsset.from_primitive(
    {"436941ead56c61dbf9b92b5f566f7d5b9cac08f8c957f28f0bd60d4b": {b"PAYMENTTOKEN": 1}}
)

# Swap input configuration
# swap_nft = MultiAsset.from_primitive(
#     {"ba2cced519c47b27f0467cf91e6fb60ce224e04bbe07ea70fbad10e0": {b"": 1}}
# )
swap_nft = MultiAsset.from_primitive(
    {"5442f0aab0b8c67e65ea112c55ac16626de5f5ed3bcebc028af5ae89": {b"": 1}}
)
usdt = MultiAsset.from_primitive(
    {"c6f192a236596e2bbaac5900d67e9700dec7c77d9da626c98e0ab2ac": {b"USDT": 1}}
)
ada = AssetName.from_primitive("")

# test = Asset.from_primitive(
#     {"c6f192a236596e2bbaac5900d67e9700dec7c77d9da626c98e0ab2ac": {b"USDT": 1}}
# )
swap = Swap(swap_nft, usdt, ada)
swapInstance = SwapContract(context, oracle_address, oracle_nft, swap_address, swap)
# user_address = user_address()
print(f"Addres of the current user that wants to trade: {user_address}")
initial_value = 3
print(f"Trading quanity: {initial_value} B")
swapInstance.swap_B(
    initial_value, user_address, swap_address, new_swap_script, extendend_payment_skey
)
