import argparse
import asyncio
import os
import sys
from datetime import datetime

import cbor2
import ogmios
import yaml
from charli3_offchain_core.backend.kupo import KupoContext
from charli3_offchain_core.chain_query import ChainQuery
from pycardano import (
    Address,
    BlockFrostChainContext,
    MultiAsset,
    Network,
    PlutusV2Script,
    plutus_script_hash,
)

from . import wallet as w
from .mint import Mint
from .swap import Swap, SwapContract


def load_contracts_addresses():
    """Loads the contracts addresses"""
    configyaml = load_config()
    return (
        Address.from_primitive(configyaml.get("oracle_contract_address")),
        Address.from_primitive(configyaml.get("swap_contract_address")),
    )


def load_config():
    """Loads the YAML configuration file."""
    try:
        with open("config.yaml", "r", encoding="UTF-8") as config_yaml:
            return yaml.load(config_yaml, Loader=yaml.FullLoader)
    except FileNotFoundError:
        print("Configuration file not found.")
        sys.exit(1)


def validate_config(config, connection, required_keys):
    """Validates that all required keys exist for a connection configuration."""
    if connection not in config or not all(
        key in config[connection] for key in required_keys
    ):
        raise ValueError(f"Context for {connection} not found or is incomplete.")


def context(args) -> ChainQuery:
    """Connection context"""
    blockfrost_context = None
    ogmios_context = None
    kupo_context = None

    configyaml = load_config()

    if args.environment == "mainnet":
        network = Network.MAINNET
    elif args.environment == "preprod":
        network = Network.TESTNET
    else:
        network = None

    if args.connection == "blockfrost":
        required_keys = ["project_id"]
        validate_config(configyaml, args.connection, required_keys)

        blockfrost_context = BlockFrostChainContext(
            project_id=configyaml[args.connection].get("project_id", ""),
            base_url=None,
        )
    elif args.connection == "ogmios":
        required_keys = ["kupo_url", "ws_url"]
        validate_config(configyaml, args.connection, required_keys)

        ogmios_ws_url = configyaml["ogmios"]["ws_url"]
        kupo_url = configyaml["ogmios"]["kupo_url"]

        _, ws_string = ogmios_ws_url.split("ws://")
        ws_url, port = ws_string.split(":")
        ogmios_context = ogmios.OgmiosChainContext(
            host=ws_url, port=int(port), network=network
        )

        kupo_context = KupoContext(kupo_url)

    return ChainQuery(
        blockfrost_context=blockfrost_context,
        ogmios_context=ogmios_context,
        kupo_context=kupo_context,
    )


# Reading minting script
current_dir = os.path.dirname(os.path.abspath(__file__))
mint_script_path = os.path.join(current_dir, "utils", "scripts", "mint_script.plutus")
with open(mint_script_path, "r") as f:
    script_hex = f.read()
    plutus_script_v2 = PlutusV2Script(cbor2.loads(bytes.fromhex(script_hex)))

# Load user payment key grom wallet file
extended_payment_skey = w.user_esk()

# User address wallet
user_address = w.user_address()

# Oracle feed NFT identity
oracle_nft = MultiAsset.from_primitive(
    {"a71cbfd2e54d057612ca21f8d9a3637fbb307bd74fa33d4f6174e82f": {b"OracleFeed": 1}}
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


def create_parser():
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="The swap python script is a demonstrative smart contract "
        "(Plutus v2) featuring the interaction with a Charli3's oracle. This "
        "script uses the inline oracle feed as reference input simulating the "
        "exchange rate between tADA and tUSDT to sell or buy assets from a swap "
        "contract in the test environment of preproduction. ",
        epilog="Copyrigth: (c) 2020 - 2024 Charli3",
    )

    # Service to connect to the blockchain
    parser.add_argument(
        "connection",
        choices=["blockfrost", "ogmios"],
        nargs="?",
        default="blockfrost",
        help="External service to read blockhain information",
    )

    # Service to connect to the blockchain
    parser.add_argument(
        "environment",
        choices=["preprod", "mainnet"],
        nargs="?",
        default="preprod",
        help="Blockchain environment",
    )

    # Create a subparser for each main choice
    subparser = parser.add_subparsers(dest="subparser")

    # Create a parser for the "trade" choice
    trade_subparser = subparser.add_parser(
        "trade",
        help="Call the trade transaction to exchange a user asset with another "
        "asset at the swap contract. Supported assets tADA and tUSDT.",
        description="Trade transaction to sell and buy tUSDT or tADA.",
    )

    # Create a subparser for each trade option
    subparser_trade_subparser = trade_subparser.add_subparsers(
        dest="subparser_trade_subparser"
    )

    tada_subparser_trade_subparser = subparser_trade_subparser.add_parser(
        "tADA", help="Toy ADA asset."
    )
    tada_subparser_trade_subparser.add_argument(
        "--amount",
        type=int,
        default=0,
        metavar="tLOVELACE",
        help="Amount of lovelace to trade.",
    )

    tusdt_subparser_trade_subparser = subparser_trade_subparser.add_parser(
        "tUSDT", help="Toy USDT asset."
    )
    tusdt_subparser_trade_subparser.add_argument(
        "--amount",
        type=int,
        default=0,
        metavar="tUSDT",
        help="Amount of tUSDT to trade.",
    )

    # Create a parser for the "user" choice
    user_parser = subparser.add_parser(
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
    swap_contract_parser = subparser.add_parser(
        "swap-contract",
        help="Obtain information about the SWAP smart contract.",
        description="SWAP smart contract information.",
    )
    swap_contract_parser.add_argument(
        "--liquidity",
        action="store_true",
        help="Print the amount of availables assets.",
    )

    swap_contract_parser.add_argument(
        "--address",
        action="store_true",
        help="Print the swap contract address.",
    )

    swap_contract_parser.add_argument(
        "--add-liquidity",
        nargs=2,
        action="store",
        dest="addliquidity",
        metavar=("tUSDT", "tADA"),
        type=int,
        help="Add asset liquidity at swap UTXO.",
    )

    swap_contract_parser.add_argument(
        "--start-swap",
        dest="soracle",
        action="store_true",
        help="Generate a UTXO and mint an NFT at the specified swap contract address.",
    )

    # Create a parser for the "oracle-contract" choice
    oracle_contract_parser = subparser.add_parser(
        "oracle-contract",
        help="Obtain information about the ORACLE smart contract.",
        description="ORACLE smart contract information.",
    )
    oracle_contract_parser.add_argument(
        "--feed",
        action="store_true",
        help="Print the oracle feed (exchange rate) tUSDT/tADA.",
    )

    oracle_contract_parser.add_argument(
        "--address",
        action="store_true",
        help="Print the oracle contract address.",
    )
    return parser


# Parser command-line arguments
async def display(args, context):
    oracle_address, swap_address = load_contracts_addresses()
    swap_script_hash = swap_address.payment_part
    swap_script = await context.get_plutus_script(swap_script_hash)

    if args.subparser == "trade" and args.subparser_trade_subparser == "tADA":
        swapInstance = SwapContract(
            context, oracle_nft, oracle_address, swap_address, swap
        )
        await swapInstance.swap_B(
            args.amount,
            user_address,
            swap_address,
            swap_script,
            extended_payment_skey,
        )

    elif args.subparser == "trade" and args.subparser_trade_subparser == "tUSDT":
        swapInstance = SwapContract(
            context, oracle_nft, oracle_address, swap_address, swap
        )
        await swapInstance.swap_A(
            args.amount,
            user_address,
            swap_address,
            swap_script,
            extended_payment_skey,
        )

    elif args.subparser == "user" and args.liquidity:
        swapInstance = SwapContract(
            context, oracle_nft, oracle_address, swap_address, swap
        )
        tlovelace = await swapInstance.available_user_tlovelace(user_address)
        tUSDT = await swapInstance.available_user_tusdt(user_address)
        print("User wallet's liquidity:")
        print(f"- {tlovelace // 1000000} tADA ({tlovelace} tlovelace)")
        print(f"- {tUSDT} tUSDT")
    elif args.subparser == "user" and args.address:
        print(f"User's wallet address (Mnemonic): {w.user_address()}")

    elif args.subparser == "swap-contract" and args.liquidity:
        swapInstance = SwapContract(
            context, oracle_nft, oracle_address, swap_address, swap
        )
        swap_utxo = await swapInstance.get_swap_utxo()
        tlovelace = swap_utxo.output.amount.coin
        tUSDT = await swapInstance.add_asset_swap_amount(0)
        print("Swap contract liquidity:")
        print(f"- {tlovelace // 1000000} tADA ({tlovelace} tlovelace)")
        print(f"- {tUSDT} tUSDT")

    elif args.subparser == "swap-contract" and args.address:

        print(f"Swap contract's address: {swap_address}")

    elif args.subparser == "swap-contract" and args.addliquidity:
        swapInstance = SwapContract(
            context, oracle_nft, oracle_address, swap_address, swap
        )
        await swapInstance.add_liquidity(
            args.addliquidity[0],
            args.addliquidity[1],
            user_address,
            swap_address,
            swap_script,
            extended_payment_skey,
        )
    elif args.subparser == "swap-contract" and args.soracle:
        swap_utxo_nft = Mint(
            context, extended_payment_skey, user_address, swap_address, plutus_script_v2
        )
        await swap_utxo_nft.mint_nft_with_script()

    elif args.subparser == "oracle-contract" and args.feed:
        try:
            swapInstance = SwapContract(
                context, oracle_nft, oracle_address, swap_address, swap
            )
            exchange = await swapInstance.get_oracle_exchange_rate()

            print("Charli3 - Oracle Feed")
            print(f"Last Price: {exchange / 1000000:.6f} tADA/tUSDt")

        except Exception as e:
            return f"An error occurred while fetching the oracle feed: {e}"

    elif args.subparser == "oracle-contract" and args.address:
        print(f"Oracle contract's address: {oracle_address}")


def main():
    """main execution program"""
    parser = create_parser()
    args = parser.parse_args(None if sys.argv[1:] else ["-h"])
    ctx = context(args)
    asyncio.run(display(args, ctx))


if __name__ == "__main__":
    main()
