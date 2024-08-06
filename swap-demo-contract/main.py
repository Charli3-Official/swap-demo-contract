import argparse
import cbor2
import os
import wallet as w

from datetime import datetime
from lib.chain_query import ChainQuery
from mint import Mint
from swap import SwapContract, Swap

from pycardano import (
    Address,
    MultiAsset,
    Network,
    PlutusV2Script,
    plutus_script_hash,
)

# Environment's settings
BLOCKFROST_PROJECT_ID = os.environ.get("BLOCKFROST_PROJECT_ID")
BLOCKFROST_BASE_URL = os.environ.get("BLOCFROST_BASE_URL")

NETWORK_MODE = Network.TESTNET

# Charli3's oracle contract address
oracle_address = Address.from_primitive(
    "addr_test1wz58xs5ygmjf9a3p6y3qzmwxp7cyj09zk90rweazvj8vwds4d703u"
)

# Custom contract address (swap contract)
swap_address = Address.from_primitive(
    "addr_test1wrcraeyfdkurcz286jaq02hdj5krntc47074vky5j8suhpqew37jy"
)

# Blockfrost's settings
context = ChainQuery(BLOCKFROST_PROJECT_ID, NETWORK_MODE, base_url=BLOCKFROST_BASE_URL)

# Get the script from the Network
swap_script_hash = swap_address.payment_part
swap_script = context._get_script(str(swap_script_hash))

if plutus_script_hash(swap_script) != swap_script_hash:
    swap_script = PlutusV2Script(cbor2.dumps(swap_script))

# Reading minting script
with open("./utils/scripts/mint_script.plutus", "r") as f:
    script_hex = f.read()
    plutus_script_v2 = PlutusV2Script(cbor2.loads(bytes.fromhex(script_hex)))

# User payment key generation
# node_signing_key = PaymentSigningKey.generate()
# node_signing_key.save("node.skey")
# node_verification_key = PaymentVerificationKey.from_signing_key(node_signing_key)
# node_verification_key.save("node.vkey")

# Load user payment key
# extended_payment_skey = PaymentSigningKey.load("./credentials/node.skey")
# extended_payment_vkey = PaymentVerificationKey.load("./credentials/node.vkey")
#
# Load user payment key grom wallet file
extended_payment_skey = w.user_esk()

# User address wallet
user_address = w.user_address()

# Oracle feed NFT identity
oracle_nft = MultiAsset.from_primitive(
    {
        "8fe2ef24b3cc8882f01d9246479ef6c6fc24a6950b222c206907a8be": {
            b"InlineOracleFeed": 1
        }
    }
)

# Swap NFT identity
swap_nft = MultiAsset.from_primitive(
    {"38f143722e0a340027510587d81e49b90904c10fb8271eca13913cd6": {b"SWAP": 1}}
)

# tUSDT asset information
tUSDT = MultiAsset.from_primitive(
    {"c6f192a236596e2bbaac5900d67e9700dec7c77d9da626c98e0ab2ac": {b"USDT": 1}}
)

# swap instance
swap = Swap(swap_nft, tUSDT)

# ---------------------      -- #
#         Parser Section        #
# -----------------------       #

parser = argparse.ArgumentParser(
    prog="python main.py",
    description="The swap python script is a demonstrative smart contract "
    "(Plutus v2) featuring the interaction with a Charli3's oracle. This "
    "script uses the inline oracle feed as reference input simulating the "
    "exchange rate between tADA and tUSDT to sell or buy assets from a swap "
    "contract in the test environment of preproduction. ",
    epilog="Copyrigth: (c) 2020 - 2023 Charli3",
)

# Create a subparser for each main choice
subparsers = parser.add_subparsers(dest="subparser_main_name")

# Create a parser for the "trade" choice
trade_parser = subparsers.add_parser(
    "trade",
    help="Call the trade transaction to exchange a user asset with another "
    "asset at the swap contract. Supported assets tADA and tUSDT.",
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
    help="Obtain information about the wallet of the user who participate in "
    "the trade transaction.",
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

swap_parser.add_argument(
    "--add-liquidity",
    nargs=2,
    action="store",
    dest="addliquidity",
    metavar=("tUSDT", "tADA"),
    type=int,
    help="Add asset liquidity at swap UTXO.",
)

swap_parser.add_argument(
    "--start-swap",
    dest="soracle",
    action="store_true",
    help="Generate a UTXO and mint an NFT at the specified swap contract address.",
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
        extended_payment_skey,
    )

elif args.subparser_main_name == "trade" and args.subparser_trade_name == "tUSDT":
    swapInstance = SwapContract(context, oracle_nft, oracle_address, swap_address, swap)
    swapInstance.swap_A(
        args.amount,
        user_address,
        swap_address,
        swap_script,
        extended_payment_skey,
    )

elif args.subparser_main_name == "user" and args.liquidity:
    swapInstance = SwapContract(context, oracle_nft, oracle_address, swap_address, swap)
    tlovelace = swapInstance.available_user_tlovelace(user_address)
    tUSDT = swapInstance.available_user_tusdt(user_address)
    print(
        f"""User wallet's liquidity:
    * {tlovelace // 1000000} tADA ({tlovelace} tlovelace).
    * {tUSDT} tUSDT."""
    )
elif args.subparser_main_name == "user" and args.address:
    print(f"User's wallet address (Mnemonic): {w.user_address()}")
elif args.subparser_main_name == "swap-contract" and args.liquidity:
    swapInstance = SwapContract(context, oracle_nft, oracle_address, swap_address, swap)
    tlovelace = swapInstance.get_swap_utxo().output.amount.coin
    tUSDT = swapInstance.add_asset_swap_amount(0)
    print(
        f"""Swap contract liquidity:
    * {tlovelace // 1000000} tADA ({tlovelace} tlovelace).
    * {tUSDT} tUSDT."""
    )
elif args.subparser_main_name == "swap-contract" and args.address:
    print(f"Swap contract's address: {swap_address}")
elif args.subparser_main_name == "swap-contract" and args.addliquidity:
    swapInstance = SwapContract(context, oracle_nft, oracle_address, swap_address, swap)
    swapInstance.add_liquidity(
        args.addliquidity[0],
        args.addliquidity[1],
        user_address,
        swap_address,
        swap_script,
        extended_payment_skey,
    )
elif args.subparser_main_name == "swap-contract" and args.soracle:
    swap_utxo_nft = Mint(
        context, extended_payment_skey, user_address, swap_address, plutus_script_v2
    )
    swap_utxo_nft.mint_nft_with_script()

elif args.subparser_main_name == "oracle-contract" and args.feed:
    swapInstance = SwapContract(context, oracle_nft, oracle_address, swap_address, swap)
    exchange = swapInstance.get_oracle_exchange_rate()
    generated_time = datetime.utcfromtimestamp(
        swapInstance.get_oracle_timestamp()
    ).strftime("%Y-%m-%d %H:%M:%S")
    expiration_time = datetime.utcfromtimestamp(
        swapInstance.get_oracle_expiration()
    ).strftime("%Y-%m-%d %H:%M:%S")
    print(
        f"Oracle feed:\n* Exchange rate tADA/tUSDt {exchange/1000000}\n* "
        "Generated data at: {generated_time}\n* Expiration data "
        "at: {expiration_time}"
    )
elif args.subparser_main_name == "oracle-contract" and args.address:
    print(f"Oracle contract's address: {oracle_address}")
