import asyncio
import os
import sys
from pathlib import Path

import cbor2
import click
from pycardano import PlutusV2Script

from swap_demo_contract.client.format import (
    print_aggregate_summary,
    print_collection_stats,
    print_header,
    print_information,
    print_node_messages,
    print_progress,
    print_send_summary,
    print_signature_status,
    print_status,
)
from swap_demo_contract.client.odv import (
    ODVClient,
    OdvTxSignatureRequest,
    build_aggregate_message,
)
from swap_demo_contract.lib.builder import build_odv_tx
from swap_demo_contract.lib.common import get_oracle_exchange_rate
from swap_demo_contract.lib.exceptions import TransactionError
from swap_demo_contract.lib.transaction import TransactionManager
from swap_demo_contract.utils.load_configuration import (
    EnvironmentConfig,
    OdvClientConfig,
    SwapConfig,
    WalletConfig,
)
from swap_demo_contract.utils.parser import create_parser

from .mint import Mint
from .swap import SwapContract


# Parser command-line arguments
async def display(args):
    path = Path("config.yaml")
    odv = OdvClientConfig.from_yaml(path)
    environment = EnvironmentConfig.from_yaml(path, args)
    wallet = WalletConfig.from_yaml(path, args)
    swap = SwapConfig.from_yaml(path)

    swap_contract = SwapContract(environment.chain_query, odv, wallet, swap)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    swap_script_path = os.path.join(current_dir, "utils", "scripts", "swap.plutus")
    with open(swap_script_path, "r") as f:
        script_hex = f.read()
        swap_script = PlutusV2Script(cbor2.loads(bytes.fromhex(script_hex)))

    if args.subparser == "trade" and args.subparser_trade_subparser == "tADA":
        await swap_contract.swap_B(
            args.amount,
            wallet.address,
            swap.address,
            swap_script,
            wallet.esigning_key,
        )

    elif args.subparser == "trade" and args.subparser_trade_subparser == "BTC":
        await swap_contract.swap_A(
            args.amount,
            wallet.address,
            swap.address,
            swap_script,
            wallet.esigning_key,
        )

    elif args.subparser == "user" and args.liquidity:
        tlovelace = await swap_contract.available_user_tlovelace(wallet.address)
        tBTC = await swap_contract.available_user_tbtc(wallet.address)
        print_header("User wallet's liquidity:")

        print_status("Token A (BTC)", f"{tBTC}")
        print_status(
            "Token B (tADA)",
            f"{tlovelace // 1000000} tADA ({tlovelace} tlovelace)",
        )

    elif args.subparser == "user" and args.address:
        print_header("Wallet address")
        print_status("Derived from mnemonic-24", str(wallet.address))

    elif args.subparser == "swap-contract" and args.liquidity:
        swap_utxo = await swap_contract.get_swap_utxo()
        tlovelace = swap_utxo.output.amount.coin
        tBTC = await swap_contract.add_asset_swap_amount(0)
        print_header("Swap contract liquidity:")

        print_status("Token A (BTC)", f" {tBTC}")
        print_status(
            "Token B (tADA)", f"{tlovelace // 1000000} ({tlovelace} tlovelace)"
        )

    elif args.subparser == "swap-contract" and args.address:
        print_header("Swap")
        print_status("Contract Address", str(swap.address))

    elif args.subparser == "swap-contract" and args.addliquidity:
        await swap_contract.add_liquidity(
            args.addliquidity[0],
            args.addliquidity[1],
            wallet.address,
            swap.address,
            swap_script,
            wallet.esigning_key,
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
            environment.chain_query,
            wallet.esigning_key,
            wallet.address,
            swap.address,
            plutus_script_v2,
        )
        await swap_utxo_nft.mint_nft_with_script()

    elif args.subparser == "oracle-contract" and args.feed:
        try:
            feed_utxos = environment.chain_query.get_utxos_with_asset_from_kupo(
                odv.policy_id, odv.nft_aggstate
            )
            _, exchange = await get_oracle_exchange_rate(feed_utxos)

            print_header("Oracle Feed")
            print_status("Price BTC/USD", str(exchange))

        except Exception as e:
            return f"An error occurred while fetching the oracle feed: {e}"

    elif args.subparser == "oracle-contract" and args.address:
        print_header("On-Demand-Validation (ODV)")
        print_status("Contract Address", str(odv.address))

    elif args.subparser == "send-odv-request":

        try:
            print_header("ODV Send Request")
            print_progress("Loading configuration and initializing network connection")
            odv_client = ODVClient()

            validity_window = environment.chain_query.calculate_validity_window(
                odv.odv_validity_length
            )

            print_progress("Initiating node feed collection process")
            node_messages = await odv_client.collect_feed_updates(
                nodes=odv.nodes,
                policy_id=odv.policy_id,
                validity_window=validity_window,
            )
            if not node_messages:
                print_status(
                    "Node Collection", "No valid responses received", success=False
                )
                raise click.ClickException("No valid node responses received")

            print_collection_stats(
                received=len(node_messages),
                total=len(odv.nodes),
                collection_type="feed responses",
            )
            print_node_messages(node_messages)

            print_progress("Constructing ODV aggregate transaction")

            aggregate_message = build_aggregate_message(
                list(node_messages.values()), validity_window.current_time
            )
            print_aggregate_summary(aggregate_message, validity_window)

            result = await build_odv_tx(
                message=aggregate_message,
                signing_key=wallet.esigning_key,
                change_address=wallet.address,
                validity_window=validity_window,
                policy_id=odv.policy_id,
                chain_query=environment.chain_query,
                address=odv.address,
                reward_token_hash=odv.payment_token_policy_id,
                reward_token_name=odv.payment_token_asset_name,
            )

            print_information("Transaction Construction Complete")

            print_progress("Initiating signature collection from oracle nodes")
            tx_request = OdvTxSignatureRequest(
                node_messages=node_messages,
                tx_cbor=result.transaction.to_cbor_hex(),
            )

            signed_txs = await odv_client.collect_tx_signatures(
                nodes=odv.nodes, tx_request=tx_request
            )

            print_collection_stats(
                received=len(signed_txs),
                total=len(odv.nodes),
                collection_type="signatures",
            )
            print_signature_status(signed_txs)

            if not signed_txs:
                print_status(
                    "Signature Collection",
                    "No valid signatures received",
                    success=False,
                )
                raise click.ClickException("No valid signatures received")

            print_progress("Finalizing transaction with collected signatures")

            odv_client.attach_tx_signatures(
                transaction=result.transaction,
                signed_txs=signed_txs,
            )

            print_progress("Initiating ODV transaction submission")
            tx_manager = TransactionManager(environment.chain_query)
            tx_status, _ = await tx_manager.sign_and_submit(
                result.transaction, [wallet.esigning_key]
            )

            if tx_status == "confirmed":
                print_send_summary(result)
            else:
                print_status(
                    "Transaction Submission",
                    f"Failed with status: {tx_status}",
                    success=False,
                )
                raise click.ClickException(
                    f"Transaction failed with status: {tx_status}"
                )

        except TransactionError as e:
            print_status("Transaction Processing", str(e), success=False)
            raise click.ClickException(str(e)) from e
        except Exception as e:
            print_status("ODV Process", str(e), success=False)
            raise click.ClickException(str(e)) from e


def main():
    """main execution program"""
    parser = create_parser()
    args = parser.parse_args(None if sys.argv[1:] else ["-h"])
    asyncio.run(display(args))


if __name__ == "__main__":
    main()
