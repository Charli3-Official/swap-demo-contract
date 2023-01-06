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
    plutus_script_hash,
)
from datetime import datetime
import argparse

# Environment's settings
BLOCKFROST_PROJECT_ID = "preprod0kc9ZbgLbwq7XcMtPKM4olGnedkOp2Vn"
BLOCKFROST_BASE_URL = "https://cardano-preprod.blockfrost.io/api"
NETWORK_MODE = Network.TESTNET

# Charli3's oracle contract address
oracle_address = Address.from_primitive(
    "addr_test1wz58xs5ygmjf9a3p6y3qzmwxp7cyj09zk90rweazvj8vwds4d703u"
)

# Custom contract address (swap contract)
swap_address = Address.from_primitive(
    "addr_test1wqhsrhfqs6xv9g39mraau2jwnaqd7utt9x50d5sfmlz972spwd66j"
)

# Blockfrost's settings
context = ChainQuery(
    BLOCKFROST_PROJECT_ID,
    NETWORK_MODE,
    base_url="https://cardano-preprod.blockfrost.io/api",
)

swap_script_hash = swap_address.payment_part
swap_script = context._get_script(str(swap_script_hash))

if plutus_script_hash(swap_script) != swap_script_hash:
    swap_script = PlutusV2Script(cbor2.dumps(swap_script))

# User payment key generation
# node_signing_key = PaymentSigningKey.generate()
# node_signing_key.save("node.skey")
# node_verification_key = PaymentVerificationKey.from_signing_key(node_signing_key)
# node_verification_key.save("node.vkey")

# Load user payment key
extendend_payment_skey = PaymentSigningKey.load("./credentials/node.skey")
extendend_payment_vkey = PaymentVerificationKey.load("./credentials/node.vkey")

user_address = Address(payment_part=extendend_payment_vkey.hash(), network=NETWORK_MODE)

# Oracle feed nft identity
oracle_nft = MultiAsset.from_primitive(
    {
        "8fe2ef24b3cc8882f01d9246479ef6c6fc24a6950b222c206907a8be": {
            b"InlineOracleFeed": 1
        }
    }
)

# Swap nft identity
swap_nft = MultiAsset.from_primitive(
    {"ce9d1f8f464e1e930f19ae89ccab3de93d11ee5518eed15d641f6693": {b"SWAP": 1}}
)

# Swap asset information
tUSDT = MultiAsset.from_primitive(
    {"c6f192a236596e2bbaac5900d67e9700dec7c77d9da626c98e0ab2ac": {b"USDT": 1}}
)

swap = Swap(swap_nft, tUSDT)

# Parser
parser = argparse.ArgumentParser(
    prog="python main.py",
    description="The swap python script is a demonstrative smart contract (Plutus v2) featuring the interaction with a charli3's oracle. This script uses the inline oracle feed as reference input simulating the exchange rate between tADA and tUSDT to sell or buy assets from a swap contract in the test environment of preproduction. ",
    epilog="Copyrigth: (c) 2020 - 2023 Charli3",
)

# Create a subparser for each main choice
subparsers = parser.add_subparsers(dest="subparser_main_name")

# Create a parser for the "trade" choice
trade_parser = subparsers.add_parser(
    "trade",
    help="Call the trade transaction to exchange a user asset with another asset at the swap contract. Supported assets tADA and tUSDT.",
    description="Trade transaction to sell and buy tUSDT or tADA.",
)

# Create a subparser for each trade option
sub_sub = trade_parser.add_subparsers(dest="subparser_trade_name")

sub_trade_parser = sub_sub.add_parser("tADA", help="Toy ADA asset.")
sub_trade_parser.add_argument(
    "--amount",
    type=int,
    default=0,
    metavar="tLOVELACE",
    help="Amount of lovelace to trade.",
)

sub_trade_parser = sub_sub.add_parser("tUSDT", help="Toy USDT asset.")
sub_trade_parser.add_argument(
    "--amount",
    type=int,
    default=0,
    metavar="tUSDT",
    help="Amount of tUSDT to trade.",
)

# Create a parser for the "user" choice
user_parser = subparsers.add_parser(
    "user",
    help="Obtain information about the wallet of the user who participate in the trade transaction.",
    description="User wallet information.",
)
user_parser.add_argument(
    "--liquidity",
    action="store_true",
    help="Print the amount of availables assets.",
)

user_parser.add_argument(
    "--address",
    action="store_true",
    help="Print the wallet address.",
)
# Create a parser for the "swap-contract" choice
swap_parser = subparsers.add_parser(
    "swap-contract",
    help="Obtain information about the SWAP smart contract.",
    description="SWAP smart contract information.",
)
swap_parser.add_argument(
    "--liquidity",
    action="store_true",
    help="Print the amount of availables assets.",
)

swap_parser.add_argument(
    "--address",
    action="store_true",
    help="Print the swap contract address.",
)
# Create a parser for the "oracle-contract" choice
oracle_parser = subparsers.add_parser(
    "oracle-contract",
    help="Obtain information about the ORACLE smart contract.",
    description="ORACLE smart contract information.",
)
oracle_parser.add_argument(
    "--feed",
    action="store_true",
    help="Print the oracle feed (exchange rate) tUSDT/tADA.",
)

oracle_parser.add_argument(
    "--address",
    action="store_true",
    help="Print the oracle contract address.",
)

# Parser command-line arguments
args = parser.parse_args()

if args.subparser_main_name == "trade" and args.subparser_trade_name == "tADA":
    swapInstance = SwapContract(context, oracle_nft, oracle_address, swap_address, swap)
    swapInstance.swap_B(
        args.amount,
        user_address,
        swap_address,
        swap_script,
        extendend_payment_skey,
    )

elif args.subparser_main_name == "trade" and args.subparser_trade_name == "tUSDT":
    swapInstance = SwapContract(context, oracle_nft, oracle_address, swap_address, swap)
    swapInstance.swap_A(
        args.amount,
        user_address,
        swap_address,
        swap_script,
        extendend_payment_skey,
    )

elif args.subparser_main_name == "user" and args.liquidity:
    swapInstance = SwapContract(context, oracle_nft, oracle_address, swap_address, swap)
    tlovelace = swapInstance.available_user_tlovelace(user_address)
    tUSDT = swapInstance.available_user_tusdt(user_address)
    print(
        f"""User wallet's liquidity:
    * {tlovelace} tlovelace.
    * {tUSDT} tUSDT."""
    )
elif args.subparser_main_name == "user" and args.address:
    print(f"User's wallet address: {user_address}")
elif args.subparser_main_name == "swap-contract" and args.liquidity:
    swapInstance = SwapContract(context, oracle_nft, oracle_address, swap_address, swap)
    tlovelace = swapInstance.get_swap_utxo().output.amount.coin
    tUSDT = swapInstance.add_asset_swap_amount(0)
    print(
        f"""Swap contract liquidity:
    * {tlovelace} tlovelace.
    * {tUSDT} tUSDT."""
    )
elif args.subparser_main_name == "swap-contract" and args.address:
    print(f"Swap contract's address: {swap_address}")
elif args.subparser_main_name == "oracle-contract" and args.feed:
    swapInstance = SwapContract(context, oracle_nft, oracle_address, swap_address, swap)
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print(
        f"Oracle feed: Exchange rate tADA/tUSDt {swapInstance.get_oracle_exchange_rate()} at {current_time}"
    )
elif args.subparser_main_name == "oracle-contract" and args.address:
    print(f"Oracle contract's address: {oracle_address}")
