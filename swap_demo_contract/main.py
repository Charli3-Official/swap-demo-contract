import argparse
import asyncio
import os
import sys

import cbor2
import ogmios
import yaml
from charli3_offchain_core.backend.kupo import KupoContext
from charli3_offchain_core.chain_query import ChainQuery
from pycardano import (
    Address,
    Asset,
    AssetName,
    BlockFrostChainContext,
    ExtendedSigningKey,
    HDWallet,
    MultiAsset,
    Network,
    PaymentSigningKey,
    PaymentVerificationKey,
    PlutusV2Script,
    ScriptHash,
    TransactionId,
    TransactionInput,
)

from .lib.oracle_user import OracleUser
from .mint import Mint
from .swap import Swap, SwapContract


def load_contracts_addresses(configyaml):
    """Loads the contracts addresses"""
    c3_oracle_rate_nft_hash = ScriptHash.from_primitive(
        configyaml.get(["dynamic_payment_oracle_minting_policy"], None)
    )
    c3_oracle_rate_nft_name = configyaml(["dynamic_payment_oracle_asset_name"])

    return (
        Address.from_primitive(configyaml.get("oracle_contract_address")),
        Address.from_primitive(configyaml.get("swap_contract_address")),
        Address.from_primitive(configyaml.get("dynamic_payment_oracle_addr", None)),
        create_c3_oracle_rate_nft(c3_oracle_rate_nft_hash, c3_oracle_rate_nft_name),
    )


def create_c3_oracle_rate_nft(token_name, minting_policy) -> MultiAsset | None:
    """Create C3 oracle rate NFT."""
    if token_name and minting_policy:
        return MultiAsset.from_primitive(
            {minting_policy.payload: {bytes(token_name, "utf-8"): 1}}
        )
    else:
        return None


def load_swap_config_tokens(configyaml):

    swap_minting_policy = ScriptHash.from_primitive(
        configyaml.get("swap_minting_policy")
    )
    swap_asset_name = AssetName(configyaml.get("swap_asset_name").encode())
    swap_nft = MultiAsset({swap_minting_policy: Asset({swap_asset_name: 1})})

    token_a_minting_policy = ScriptHash.from_primitive(
        configyaml.get("token_a_minting_policy")
    )
    token_a_asset_name = AssetName(configyaml.get("token_a_asset_name").encode())
    token_a = MultiAsset({token_a_minting_policy: Asset({token_a_asset_name: 1})})
    return (swap_nft, token_a)


def load_odv_oracle_config_tokens(configyaml):
    aggstate_minting_policy = ScriptHash.from_primitive(
        configyaml.get("aggstate_minting_policy")
    )
    aggstate_asset_name = AssetName(configyaml.get("aggstate_asset_name").encode())
    aggstate_nft = MultiAsset(
        {aggstate_minting_policy: Asset({aggstate_asset_name: 1})}
    )

    oracle_nft_minting_policy = ScriptHash.from_primitive(
        configyaml.get("oracle_nft_minting_policy")
    )
    oracle_nft_asset_name = AssetName(configyaml.get("oracle_nft_asset_name").encode())
    oracle_nft = MultiAsset(
        {oracle_nft_minting_policy: Asset({oracle_nft_asset_name: 1})}
    )

    c3_token_hash = ScriptHash.from_primitive(configyaml.get("c3_token_hash"))

    c3_token_name = AssetName(configyaml.get("c3_token_name").encode())

    return (aggstate_nft, oracle_nft, c3_token_hash, c3_token_name)


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


def user_wallet_extended_signing_key(configyaml) -> PaymentSigningKey:
    mnemonic_24 = configyaml.get("MNEMONIC_24")
    hdwallet = HDWallet.from_mnemonic(mnemonic_24)
    hdwallet_spend = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

    extended_signing_key = ExtendedSigningKey.from_hdwallet(hdwallet_spend)
    return extended_signing_key


def user_wallet_credentials(configyaml) -> Address:
    mnemonic_24 = configyaml.get("MNEMONIC_24")
    hdwallet = HDWallet.from_mnemonic(mnemonic_24)
    hdwallet_spend = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
    spend_public_key = hdwallet_spend.public_key
    spend_vk = PaymentVerificationKey.from_primitive(spend_public_key)

    hdwallet_stake = hdwallet.derive_from_path("m/1852'/1815'/0'/2/0")
    stake_public_key = hdwallet_stake.public_key
    stake_vk = PaymentVerificationKey.from_primitive(stake_public_key)

    return spend_vk, stake_vk


def user_wallet_address(configyaml, args):

    if args.environment == "mainnet":
        network = Network.MAINNET
    elif args.environment == "preprod":
        network = Network.TESTNET
    else:
        network = None

    mnemonic_24 = configyaml.get("MNEMONIC_24")
    hdwallet = HDWallet.from_mnemonic(mnemonic_24)
    hdwallet_spend = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
    spend_public_key = hdwallet_spend.public_key
    spend_vk = PaymentVerificationKey.from_primitive(spend_public_key)

    hdwallet_stake = hdwallet.derive_from_path("m/1852'/1815'/0'/2/0")
    stake_public_key = hdwallet_stake.public_key
    stake_vk = PaymentVerificationKey.from_primitive(stake_public_key)

    str_address = Address(spend_vk.hash(), stake_vk.hash(), network=network).encode()
    return Address.from_primitive(str_address)


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

    # Odv request
    send_odv_request_parser = subparser.add_parser(
        "send-odv-request",
        help="Send a validation request on demand to ODV-Charli3 Oracle.",
        description="Generate a request for information by prepaying the Charli3 oracles.",
    )

    send_odv_request_parser.add_argument(
        "--funds-to-send",
        type=int,
        default=None,
        dest="fundstosend",
        help="Minimum C3 payment amount for the generation of an oracle-feed.",
    )
    return parser


# Parser command-line arguments
async def display(args, context):
    configyaml = load_config()

    # NFT configuration
    (
        oracle_address,
        swap_address,
        dynamic_payment_oracle_addr,
        dynamic_payment_oracle_nft,
    ) = load_contracts_addresses(configyaml)
    swap_nft, token_a = load_swap_config_tokens(configyaml)
    aggstate_nft, oracle_nft, c3_token_hash, c3_token_name = (
        load_odv_oracle_config_tokens(configyaml)
    )

    # Load user payment key from wallet file
    extended_payment_skey = user_wallet_extended_signing_key(configyaml)
    spend_vk, stake_vk = user_wallet_credentials(configyaml)

    # User address wallet
    user_address = user_wallet_address(configyaml, args)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    swap_script_path = os.path.join(current_dir, "utils", "scripts", "swap.plutus")
    with open(swap_script_path, "r") as f:
        script_hex = f.read()
        swap_script = PlutusV2Script(cbor2.loads(bytes.fromhex(script_hex)))

    swap = Swap(swap_nft, token_a)
    swapInstance = SwapContract(context, oracle_nft, oracle_address, swap_address, swap)

    if args.subparser == "trade" and args.subparser_trade_subparser == "tADA":
        await swapInstance.swap_B(
            args.amount,
            user_address,
            swap_address,
            swap_script,
            extended_payment_skey,
        )

    elif args.subparser == "trade" and args.subparser_trade_subparser == "tUSDT":
        await swapInstance.swap_A(
            args.amount,
            user_address,
            swap_address,
            swap_script,
            extended_payment_skey,
        )

    elif args.subparser == "user" and args.liquidity:
        tlovelace = await swapInstance.available_user_tlovelace(user_address)
        tUSDT = await swapInstance.available_user_tusdt(user_address)
        print("User wallet's liquidity:")
        print(f"- {tlovelace // 1000000} tADA ({tlovelace} tlovelace)")
        print(f"- {tUSDT} tUSDT")
    elif args.subparser == "user" and args.address:
        print(f"User's wallet address (Mnemonic): {user_address}")

    elif args.subparser == "swap-contract" and args.liquidity:
        swap_utxo = await swapInstance.get_swap_utxo()
        tlovelace = swap_utxo.output.amount.coin
        tUSDT = await swapInstance.add_asset_swap_amount(0)
        print("Swap contract liquidity:")
        print(f"- {tlovelace // 1000000} tADA ({tlovelace} tlovelace)")
        print(f"- {tUSDT} tUSDT")

    elif args.subparser == "swap-contract" and args.address:

        print(f"Swap contract's address: {swap_address}")

    elif args.subparser == "swap-contract" and args.addliquidity:
        await swapInstance.add_liquidity(
            args.addliquidity[0],
            args.addliquidity[1],
            user_address,
            swap_address,
            swap_script,
            extended_payment_skey,
        )
    elif args.subparser == "swap-contract" and args.soracle:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        mint_script_path = os.path.join(
            current_dir, "utils", "scripts", "mint_script.plutus"
        )
        with open(mint_script_path, "r") as f:
            script_hex = f.read()
            plutus_script_v2 = PlutusV2Script(cbor2.loads(bytes.fromhex(script_hex)))

        swap_utxo_nft = Mint(
            context, extended_payment_skey, user_address, swap_address, plutus_script_v2
        )
        await swap_utxo_nft.mint_nft_with_script()

    elif args.subparser == "oracle-contract" and args.feed:
        try:
            exchange = await swapInstance.get_oracle_exchange_rate()

            print("Charli3 - Oracle Feed")
            print(f"Last Price: {exchange / 1000000:.6f} tADA/tUSDt")

        except Exception as e:
            return f"An error occurred while fetching the oracle feed: {e}"

    elif args.subparser == "oracle-contract" and args.address:
        print(f"Oracle contract's address: {oracle_address}")

    elif args.subparser == "send-odv-request":
        load_script_input = configyaml.get("script_input_oracle")
        tx_id_hex, index = load_script_input.split("#")
        tx_id = TransactionId(bytes.fromhex(tx_id_hex))
        index = int(index)
        reference_script_input = TransactionInput(tx_id, index)

        if args.environment == "mainnet":
            network = Network.MAINNET
        elif args.environment == "preprod":
            network = Network.TESTNET
        else:
            network = None

        oracle_user = OracleUser(
            network,
            context,
            extended_payment_skey,
            spend_vk,
            stake_vk,
            str(oracle_address),
            aggstate_nft,
            reference_script_input,
            c3_token_hash,
            c3_token_name,
            dynamic_payment_oracle_addr,
            dynamic_payment_oracle_nft,
        )
        if args.fundstosend:
            await oracle_user.send_odv_request(args.fundstosend)
        else:
            funds_to_add = await oracle_user.calc_recommended_funds_amount()
            print(f"Minimum quantity required {funds_to_add}")
            await oracle_user.send_odv_request(funds_to_add)


def main():
    """main execution program"""
    parser = create_parser()
    args = parser.parse_args(None if sys.argv[1:] else ["-h"])
    ctx = context(args)
    asyncio.run(display(args, ctx))


if __name__ == "__main__":
    main()
