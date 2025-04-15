import argparse


def create_parser():
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="The swap python script is a demonstrative smart contract "
        "(Plutus v2) featuring the interaction with a Charli3's oracle. This "
        "script uses the inline oracle feed as reference input simulating the "
        "exchange rate between tADA and BTC to sell or buy assets from a swap "
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
        "asset at the swap contract. Supported assets tADA and BTC.",
        description="Trade transaction to sell and buy BTC or tADA.",
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

    tbtc_subparser_trade_subparser = subparser_trade_subparser.add_parser(
        "BTC", help="Toy BTC asset."
    )
    tbtc_subparser_trade_subparser.add_argument(
        "--amount",
        type=int,
        default=0,
        metavar="BTC",
        help="Amount of BTC to trade.",
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
        metavar=("BTC", "tADA"),
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
        help="Print the oracle feed (exchange rate) BTC/tADA.",
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
