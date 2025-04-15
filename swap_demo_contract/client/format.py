from datetime import datetime
from enum import Enum
from typing import Any

import click

from swap_demo_contract.client.message import SignedOracleNodeMessage
from swap_demo_contract.lib.builder import OdvResult
from swap_demo_contract.lib.datums_odv import (
    AggregateMessage,
    PriceData,
    RewardConsensusPending,
)


class CliColor(str, Enum):
    """CLI color scheme"""

    SUCCESS = "green"
    ERROR = "red"
    WARNING = "yellow"
    INFO = "blue"
    HEADER = "cyan"
    ADDRESS = "bright_blue"
    HASH = "bright_black"
    PROGRESS = "yellow"
    TITLE = "bright_cyan"
    NEUTRAL = "white"

    DETAIL = "bright_white"
    PROCESSING = "magenta"
    HIGHLIGHT = "bright_yellow"
    VALUE = "bright_magenta"
    SECONDARY = "white"
    EMPHASIS = "bright_red"


def print_collection_stats(received: int, total: int, collection_type: str) -> None:
    """Print collection statistics with visual progress indicator."""
    click.secho("\n┌ Collection Status", fg=CliColor.INFO)
    click.secho("├─ Received: ", fg=CliColor.SECONDARY, nl=False)
    click.secho(f"{received}", fg=CliColor.VALUE, nl=False)
    click.secho(" of ", fg=CliColor.SECONDARY, nl=False)
    click.secho(f"{total}", fg=CliColor.VALUE)

    percentage = (received / total) * 100
    status_color = CliColor.SUCCESS if received == total else CliColor.WARNING
    click.secho("└─ Status: ", fg=CliColor.SECONDARY, nl=False)
    click.secho(f"{percentage:.1f}% {collection_type} collected", fg=status_color)


def print_node_messages(node_responses: dict[str, SignedOracleNodeMessage]) -> None:
    """Print formatted node feed responses."""
    print_header("Node Feed Responses")

    total_nodes = len(node_responses)
    click.secho("\nReceived responses from ", fg=CliColor.INFO, nl=False)
    click.secho(f"{total_nodes} ", fg=CliColor.VALUE, nl=False)
    click.secho("nodes\n", fg=CliColor.INFO)

    for node_id, response in node_responses.items():
        feed_value = int(response.message.feed) / 1_000_000
        timestamp = datetime.fromtimestamp(response.message.timestamp / 1000)

        click.secho("┌ Node: ", fg=CliColor.HEADER, nl=False)
        click.secho(f"{node_id}", fg=CliColor.ADDRESS)

        click.secho("├─ Feed Value: ", fg=CliColor.SECONDARY, nl=False)
        click.secho(f"{feed_value:.6f}", fg=CliColor.VALUE)

        click.secho("└─ Timestamp: ", fg=CliColor.SECONDARY, nl=False)
        click.secho(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n", fg=CliColor.DETAIL)


def print_progress(message: str) -> None:
    """Print progress message."""
    click.secho(f"⟳ {message}...", fg=CliColor.PROGRESS)


def print_information(text: str) -> None:
    """Print styled information text."""
    click.secho(f"=== {text} ===", fg=CliColor.INFO, bold=True)


def print_header(text: str) -> None:
    """Print styled header text."""
    click.echo()
    click.secho(f"=== {text} ===", fg=CliColor.HEADER, bold=True)
    click.echo()


def print_status(status: str, message: str, success: bool = True) -> None:
    """Print status message with appropriate styling."""
    icon = "✓" if success else "✗"
    color = CliColor.SUCCESS if success else CliColor.ERROR
    click.secho(f"{icon} {status}: {message}", fg=color)


def print_aggregate_summary(
    aggregate_message: AggregateMessage, validity_window: Any
) -> None:
    """Print summary of aggregation details."""
    print_header("Aggregation Details")

    # Print Validity Window
    window_start = datetime.fromtimestamp(validity_window.validity_start / 1000)
    window_end = datetime.fromtimestamp(validity_window.validity_end / 1000)

    click.secho("\n┌ Validity Window", fg=CliColor.INFO)
    click.secho("├─ Start: ", fg=CliColor.SECONDARY, nl=False)
    click.secho(f"{window_start.strftime('%Y-%m-%d %H:%M:%S')}", fg=CliColor.DETAIL)
    click.secho("└─ End:   ", fg=CliColor.SECONDARY, nl=False)
    click.secho(f"{window_end.strftime('%Y-%m-%d %H:%M:%S')}", fg=CliColor.DETAIL)

    # Print Aggregate Message Details
    msg_time = datetime.fromtimestamp(aggregate_message.timestamp / 1000)

    click.secho("\n┌ Aggregate Message", fg=CliColor.INFO)
    click.secho("├─ Timestamp: ", fg=CliColor.SECONDARY, nl=False)
    click.secho(f"{msg_time.strftime('%Y-%m-%d %H:%M:%S')}", fg=CliColor.DETAIL)
    click.secho("├─ Node Count: ", fg=CliColor.SECONDARY, nl=False)
    click.secho(f"{aggregate_message.node_feeds_count}", fg=CliColor.DETAIL)

    # Print Node Feeds
    click.secho("└─ Node Feeds", fg=CliColor.SECONDARY)

    for idx, (vkh, feed) in enumerate(
        aggregate_message.node_feeds_sorted_by_feed.items(), 1
    ):
        is_last = idx == len(aggregate_message.node_feeds_sorted_by_feed)
        prefix = "    └─" if is_last else "    ├─"

        feed_value = feed / 1_000_000 if isinstance(feed, (int | float)) else feed

        click.secho(f"{prefix} Node {idx}: ", fg=CliColor.SECONDARY, nl=False)
        click.secho(f"VKH: {vkh.to_primitive().hex()} ", fg=CliColor.DETAIL, nl=False)
        click.secho(f"Feed: {feed_value:.6f}", fg=CliColor.VALUE)


def print_signature_status(signed_txs: dict[str, str]) -> None:
    """Print status of collected signatures."""
    total_sigs = len(signed_txs)
    if total_sigs > 0:
        click.secho("\nCollected ", fg=CliColor.INFO, nl=False)
        click.secho(f"{total_sigs} ", fg=CliColor.VALUE, nl=False)
        click.secho("valid signature(s)", fg=CliColor.INFO)

        for node_id in signed_txs.keys():
            click.secho("  ✓ ", fg=CliColor.SUCCESS, nl=False)
            click.secho("Node ", fg=CliColor.SECONDARY, nl=False)
            click.secho(f"{node_id}", fg=CliColor.ADDRESS)
    else:
        click.secho("\n⚠ No signatures collected", fg=CliColor.ERROR)


def print_separator() -> None:
    """Print a separator line in the table."""
    click.secho(f"├{'─' * 50}┤", fg=CliColor.SECONDARY)


def print_footer() -> None:
    """Print the footer of the table."""
    click.secho(f"└{'─' * 50}┘", fg=CliColor.SECONDARY)


def print_row(label: str, value: str, color: Any = CliColor.VALUE) -> None:
    """Print a row in the table with a label and value."""
    click.secho("│ ", fg=CliColor.SECONDARY, nl=False)
    click.secho(label.ljust(25), fg=CliColor.SECONDARY, nl=False)
    click.secho(value.ljust(23), fg=color, nl=False)
    click.secho(" │", fg=CliColor.SECONDARY)


def print_table_header(title: str) -> None:
    """Print a header with the given title."""
    click.secho(f"\n┌{'─' * 50}┐", fg=CliColor.SECONDARY)
    click.secho("│ ", fg=CliColor.SECONDARY, nl=False)
    click.secho(title.ljust(48), fg=CliColor.INFO, nl=False)
    click.secho(" │", fg=CliColor.SECONDARY)
    click.secho(f"├{'─' * 50}┤", fg=CliColor.SECONDARY)


def print_send_summary(result: OdvResult) -> None:
    """Print comprehensive summary of ODV transaction in table format."""
    print_table_header("ODV Transaction Summary")

    transport_datum: RewardConsensusPending = result.transport_output.datum.datum
    agg_datum: PriceData = result.agg_state_output.datum.price_data

    # Oracle Feed Section
    print_table_header("Oracle Feed Details")
    print_row(
        "Current Feed:", f"{transport_datum.aggregation.oracle_feed / 1_000_000:.6f}"
    )
    print_row(
        "Node Participation:",
        f"{len(transport_datum.aggregation.message.node_feeds_sorted_by_feed)} nodes",
    )

    # Reward Section
    print_separator()
    print_table_header("Reward Distribution")
    node_count = len(transport_datum.aggregation.message.node_feeds_sorted_by_feed)
    node_reward = transport_datum.aggregation.node_reward_price
    total_fee = transport_datum.aggregation.rewards_amount_paid
    platform_fee = total_fee - (node_count * node_reward)

    print_row("Per Node Reward:", f"{node_reward / 1_000_000:.6f} ₳")
    print_row("Platform Fee:", f"{platform_fee / 1_000_000:.6f} ₳")
    print_row("Total Amount:", f"{total_fee / 1_000_000:.6f} ₳")

    # Timing Section
    print_separator()
    print_table_header("Timing Details")
    created_time = datetime.fromtimestamp(agg_datum.get_creation_time / 1000)
    expiry_time = datetime.fromtimestamp(agg_datum.get_expiration_time / 1000)

    print_row("Created:", created_time.strftime("%Y-%m-%d %H:%M:%S"), CliColor.DETAIL)
    print_row("Expires:", expiry_time.strftime("%Y-%m-%d %H:%M:%S"), CliColor.DETAIL)

    # Transaction Section
    print_separator()
    print_table_header("Transaction Details")
    print_row(
        "Network Fee:", f"{result.transaction.transaction_body.fee / 1_000_000:.6f} ₳"
    )
    print_status(
        "ODV aggregation completed successfully",
        f"tx id {result.transaction.id}",
        success=True,
    )

    print_footer()
