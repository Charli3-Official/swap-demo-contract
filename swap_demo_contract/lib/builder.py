from copy import deepcopy
from dataclasses import dataclass

from pycardano import (
    Address,
    AssetName,
    ExtendedSigningKey,
    PaymentSigningKey,
    Redeemer,
    ScriptHash,
    Transaction,
    TransactionOutput,
)

from swap_demo_contract.lib.chain_query import ChainQuery, ValidityWindow
from swap_demo_contract.lib.common import (
    create_agg_state_output,
    create_transport_output,
    find_transport_pair,
    get_fee_rate_reference_utxo,
    get_reference_script_utxo,
    get_settings_datum,
)
from swap_demo_contract.lib.datums_odv import AggregateMessage, AggState, NoDatum
from swap_demo_contract.lib.math import (
    calculate_min_fee_amount,
    median,
    scale_rewards_by_rate,
)
from swap_demo_contract.lib.redeemers import OdvAggregate
from swap_demo_contract.lib.transaction import TransactionManager


@dataclass
class OdvResult:
    """Result of ODV transaction."""

    transaction: Transaction
    transport_output: TransactionOutput
    agg_state_output: TransactionOutput


async def build_odv_tx(
    message: AggregateMessage,
    signing_key: PaymentSigningKey | ExtendedSigningKey,
    policy_id: ScriptHash,
    address: Address,
    change_address: Address | None = None,
    validity_window: ValidityWindow | None = None,
    chain_query: ChainQuery | None = None,
    reward_token_hash: ScriptHash | None = None,
    reward_token_name: AssetName | None = None,
) -> OdvResult:
    """Build ODV aggregation transaction with comprehensive validation.

    Args:
        message: Aggregate message to validate
        signing_key: Signing key for transaction
        change_address: Optional change address

    Returns:
        OdvResult containing transaction and outputs

    Raises:
        ValidationError: If validation fails
        TransactionError: If transaction building fails
    """
    # Get UTxOs and settings first
    asset_name = AssetName(b"C3CS")
    [utxo] = chain_query.get_utxos_with_asset_from_kupo(policy_id, asset_name)

    settings_datum, settings_utxo = get_settings_datum(utxo)
    reference_inputs = {settings_utxo}

    utxos = chain_query and await chain_query.get_utxos(address)
    script_utxo = utxos and get_reference_script_utxo(utxos)

    # Calculate the transaction time window and current time ONCE
    if validity_window is None:
        validity_window = chain_query and chain_query.calculate_validity_window(
            settings_datum.time_uncertainty_aggregation
        )
    else:
        window_length = validity_window.validity_end - validity_window.validity_start
        if window_length > settings_datum.time_uncertainty_aggregation:
            raise ValueError(
                f"Incorrect validity window length: {window_length} > {settings_datum.time_uncertainty_aggregation}"
            )
        if window_length <= 0:
            raise ValueError(f"Incorrect validity window length: {window_length}")

    validity_start, validity_end, current_time = [
        validity_window.validity_start,
        validity_window.validity_end,
        validity_window.current_time,
    ]

    validity_start_slot, validity_end_slot = chain_query._validity_window_to_slot(
        validity_start, validity_end
    )

    transport, agg_state = find_transport_pair(utxos, policy_id, current_time)

    # Create a new message with the current timestamp
    current_message = AggregateMessage(
        node_feeds_sorted_by_feed=message.node_feeds_sorted_by_feed,
        node_feeds_count=message.node_feeds_count,
        timestamp=current_time,
    )

    # Calculate median using the current message
    feeds = list(current_message.node_feeds_sorted_by_feed.values())
    node_count = current_message.node_feeds_count
    median_value = median(
        feeds,
        node_count,
    )

    # Update fees according to the rate feed
    reward_prices = deepcopy(settings_datum.fee_info.reward_prices)
    if settings_datum.fee_info.rate_nft != NoDatum():
        rate_nft = settings_datum.fee_info.rate_nft
        rate_policy_id = ScriptHash.from_primitive(rate_nft.asset.policy_id)
        rate_name = AssetName.from_primitive(rate_nft.asset.name)
        feed_utxos = chain_query.get_utxos_with_asset_from_kupo(
            rate_policy_id, rate_name
        )

        oracle_fee_rate_utxo = get_fee_rate_reference_utxo(feed_utxos)

        if oracle_fee_rate_utxo.output.datum is None:
            raise ValueError(
                "Oracle fee rate datum is None. "
                "A valid fee rate datum is required to scale rewards."
            )

        standard_datum: AggState = oracle_fee_rate_utxo.output.datum
        reference_inputs.add(oracle_fee_rate_utxo)
        scale_rewards_by_rate(
            reward_prices,
            standard_datum,
        )

    # Calculate minimum fee
    minimum_fee = calculate_min_fee_amount(
        reward_prices, len(current_message.node_feeds_sorted_by_feed)
    )
    # Create outputs using helper methods
    transport_output = create_transport_output(
        transport=transport,
        current_message=current_message,
        median_value=median_value,
        node_reward_price=reward_prices.node_fee,
        minimum_fee=minimum_fee,
        reward_token_hash=reward_token_hash,
        reward_token_name=reward_token_name,
        address=address,
    )

    agg_state_output = create_agg_state_output(
        agg_state=agg_state,
        median_value=median_value,
        current_time=current_time,
        liveness_period=settings_datum.aggregation_liveness_period,
        address=address,
    )

    # Build and return transaction
    tx_manager = TransactionManager(chain_query)
    tx = await tx_manager.build_script_tx(
        script_inputs=[
            (transport, Redeemer(OdvAggregate()), script_utxo),
            (agg_state, Redeemer(OdvAggregate()), script_utxo),
        ],
        script_outputs=[transport_output, agg_state_output],
        reference_inputs=reference_inputs,
        required_signers=list(current_message.node_feeds_sorted_by_feed.keys()),
        change_address=change_address,
        signing_key=signing_key,
        validity_start=validity_start_slot,
        validity_end=validity_end_slot,
    )

    return OdvResult(tx, transport_output, agg_state_output)
