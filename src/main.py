import cbor2
from lib.chain_query import ChainQuery
from swap import SwapContract, Swap
from pycardano import (
    Network,
    Address,
    PaymentVerificationKey,
    PaymentSigningKey,
    MultiAsset,
    PlutusV2Script,
)

oracle_addr_string = "addr_test1wz58xs5ygmjf9a3p6y3qzmwxp7cyj09zk90rweazvj8vwds4d703u"
swap_addr_string = "addr_test1wqhsrhfqs6xv9g39mraau2jwnaqd7utt9x50d5sfmlz972spwd66j"

BLOCKFROST_PROJECT_ID = "preprod0kc9ZbgLbwq7XcMtPKM4olGnedkOp2Vn"
BLOCKFROST_BASE_URL = "https://cardano-preprod.blockfrost.io/api"
NETWORK_MODE = Network.TESTNET
SCRIPT_PATH_ORACLE = "./utils/scripts/oracle.plutus"
SCRIPT_PATH_SWAP = "./utils/scripts/swap.plutus"

oracle_address = Address.from_primitive(oracle_addr_string)
swap_address = Address.from_primitive(swap_addr_string)

context = ChainQuery(
    BLOCKFROST_PROJECT_ID,
    NETWORK_MODE,
    base_url="https://cardano-preprod.blockfrost.io/api",
)

# with open("./utils/scripts/swap.plutus", "r") as f:
#     script_hex = f.read()
#     swap_script_u = cbor2.loads(bytes.fromhex(script_hex))

swap_scrip_hash_from_address = swap_address.payment_part
swap_script_address = context._get_script(str(swap_scrip_hash_from_address))
new_swap_script = PlutusV2Script(cbor2.dumps(swap_script_address))

# node_signing_key = PaymentSigningKey.generate()
# node_signing_key.save("node.skey")
# node_verification_key = PaymentVerificationKey.from_signing_key(node_signing_key)
# node_verification_key.save("node.vkey")

extendend_payment_skey = PaymentSigningKey.load("./credentials/node.skey")
extendend_payment_vkey = PaymentVerificationKey.load("./credentials/node.vkey")

user_address = Address(payment_part=extendend_payment_vkey.hash(), network=NETWORK_MODE)

oracle_nft = MultiAsset.from_primitive(
    {
        "8fe2ef24b3cc8882f01d9246479ef6c6fc24a6950b222c206907a8be": {
            b"InlineOracleFeed": 1
        }
    }
)

swap_nft = MultiAsset.from_primitive(
    {"ce9d1f8f464e1e930f19ae89ccab3de93d11ee5518eed15d641f6693": {b"SWAP": 1}}
)

tUSDT = MultiAsset.from_primitive(
    {"c6f192a236596e2bbaac5900d67e9700dec7c77d9da626c98e0ab2ac": {b"USDT": 1}}
)

swap = Swap(swap_nft, tUSDT)
swapInstance = SwapContract(context, oracle_nft, oracle_address, swap_address, swap)

print(f"Addres of the current user that wants to trade: {user_address}")
initial_value = 5000000
print(f"Trading quanity: {initial_value} B")


# Swap tlovelace with tUSDT
swapInstance.swap_B(
    initial_value, user_address, swap_address, new_swap_script, extendend_payment_skey
)

# Swap tUSDT with lovelace
swapInstance.swap_A(
    initial_value, user_address, swap_address, new_swap_script, extendend_payment_skey
)
