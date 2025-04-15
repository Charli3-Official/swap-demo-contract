import time
from copy import deepcopy
from typing import Sequence

from pycardano import (
    Address,
    Asset,
    AssetName,
    MultiAsset,
    ScriptHash,
    TransactionOutput,
    UTxO,
)

from swap_demo_contract.lib.datums_odv import (
    AggregateMessage,
    Aggregation,
    AggState,
    NoRewards,
    OracleSettingsDatum,
    OracleSettingsVariant,
    PriceData,
    RewardConsensusPending,
    RewardTransportVariant,
)
from swap_demo_contract.lib.exceptions import StateValidationError, ValidationError


def convert_cbor_to_agg_states(
    agg_state_utxos: Sequence[UTxO],
) -> list[UTxO]:
    """
    Convert CBOR encoded NodeDatum objects to their corresponding Python objects.

    Parameters:
    - agg_state_utxos (List[UTxO]): A list of UTxO objects that contain AggStateDatum objects
      in CBOR encoding.

    Returns:
    - A list of UTxO objects that contain  AggState Datum objects in their
      original Python format.
    """
    result: list[UTxO] = []
    for utxo in agg_state_utxos:
        if utxo.output.datum and not isinstance(utxo.output.datum, AggState):
            if utxo.output.datum.cbor:
                utxo.output.datum = AggState.from_cbor(utxo.output.datum.cbor)
                result.append(utxo)
        elif utxo.output.datum and isinstance(utxo.output.datum, AggState):
            result.append(utxo)
    return result


def get_settings_datum(settings_utxo: UTxO) -> tuple[OracleSettingsDatum, UTxO]:
    settings_datum = settings_utxo.output.datum
    if settings_datum and not isinstance(
        settings_utxo.output.datum, OracleSettingsVariant
    ):
        settings_utxo.output.datum = OracleSettingsVariant.from_cbor(
            settings_utxo.output.datum.cbor
        )
        settings_datum = settings_utxo.output.datum
    return settings_datum.datum, settings_utxo


def filter_valid_agg_states(utxos: Sequence[UTxO], current_time: int) -> list[UTxO]:
    """Filter UTxOs for empty or expired aggregation states.

    Args:
        utxos: List of UTxOs to filter
        current_time: Current time for checking expiry

    Returns:
        List of UTxOs with empty or expired aggregation states
    """
    utxos_with_datum = convert_cbor_to_agg_states(utxos)

    return [
        utxo
        for utxo in utxos_with_datum
        if utxo.output.datum
        and isinstance(utxo.output.datum, AggState)
        and (
            utxo.output.datum.price_data.is_empty  # Empty state
            or (utxo.output.datum.price_data.is_expired(current_time))  # Expired state
        )
    ]


def filter_utxos_by_token_name(
    utxos: Sequence[UTxO], policy_id: ScriptHash, token_name: str
) -> list[UTxO]:
    """Filter UTxOs containing a specific token.

    Args:
        utxos: List of UTxOs to filter
        policy_id: Policy ID of the token
        token_name: Name of the token

    Returns:
        List of UTxOs containing the token

    Raises:
        ValidationError: If policy_id or token_name is invalid
    """
    if not policy_id or not token_name:
        raise ValidationError("Invalid policy_id or token_name: cannot be empty")

    encoded_name = AssetName(
        token_name.encode() if isinstance(token_name, str) else token_name
    )

    return [
        utxo
        for utxo in utxos
        if (
            utxo.output.amount.multi_asset  # Has multi_asset
            and policy_id in utxo.output.amount.multi_asset  # Has correct policy
            and encoded_name in utxo.output.amount.multi_asset[policy_id]  # Has token
            and utxo.output.amount.multi_asset[policy_id][encoded_name] >= 1
        )  # Amount is >= 1
    ]


def convert_cbor_to_transports(transport_utxos: Sequence[UTxO]) -> list[UTxO]:
    """
    Convert CBOR encoded NodeDatum objects to their corresponding Python objects.

    Parameters:
    - transport_utxos (List[UTxO]): A list of UTxO objects that contain RewardTransportDatum objects
      in CBOR encoding.

    Returns:
    - A list of UTxO objects that contain  RewardTransport Datum objects in their
      original Python format.
    """
    result: list[UTxO] = []
    for utxo in transport_utxos:
        if utxo.output.datum and not isinstance(
            utxo.output.datum, RewardTransportVariant
        ):
            if utxo.output.datum.cbor:
                utxo.output.datum = RewardTransportVariant.from_cbor(
                    utxo.output.datum.cbor
                )
                result.append(utxo)
        elif utxo.output.datum and isinstance(
            utxo.output.datum, RewardTransportVariant
        ):
            result.append(utxo)
    return result


def filter_empty_transports(utxos: Sequence[UTxO]) -> list[UTxO]:
    """Filter UTxOs for empty reward transport states.

    Args:
        utxos: List of UTxOs to filter

    Returns:
        List of UTxOs with empty reward transport states
    """

    utxos_with_datum = convert_cbor_to_transports(utxos)

    return [
        utxo
        for utxo in utxos_with_datum
        if utxo.output.datum
        and isinstance(utxo.output.datum, RewardTransportVariant)
        and isinstance(utxo.output.datum.datum, NoRewards)
    ]


def get_reference_script_utxo(utxos: list[UTxO]) -> UTxO:
    """Find reference script UTxO.

    Args:
        utxos: List of UTxOs to search

    Returns:
        UTxO: Reference script UTxO

    Raises:
        StateValidationError: If no reference script UTxO is found
    """
    for utxo in utxos:
        if utxo.output.script:
            return utxo

    raise ValueError("No reference script UTxO found")


def find_transport_pair(
    utxos: Sequence[UTxO], policy_id: ScriptHash, current_time: int
) -> tuple[UTxO, UTxO]:
    """Find empty transport and agg state pair (empty or expired).

    Args:
        utxos: List of UTxOs to search
        policy_id: Policy ID for filtering tokens
        current_time: Current time for checking expiry

    Returns:
        Tuple of (transport UTxO, agg state UTxO)

    Raises:
        StateValidationError: If no valid pair is found
    """
    try:
        # Find empty transports
        transports = filter_empty_transports(
            filter_utxos_by_token_name(utxos, policy_id, "C3RT")
        )
        if not transports:
            raise StateValidationError("No empty transport UTxO found")

        # Find empty or expired agg states
        agg_states = filter_valid_agg_states(
            filter_utxos_by_token_name(utxos, policy_id, "C3AS"),
            current_time,
        )
        if not agg_states:
            raise StateValidationError("No valid agg state UTxO found")

        # Return first pair found
        return transports[0], agg_states[0]

    except Exception as e:
        raise StateValidationError(f"Failed to find UTxO pair: {e}") from e


async def get_oracle_exchange_rate(feed_utxos) -> tuple[UTxO, int]:
    """Get oracle's feed exchange rate with the most recent creation time."""
    newest_utxo = None
    newest_time = 0
    price = 0

    feed_utxos_with_datum = convert_cbor_to_agg_states(feed_utxos)

    for utxo in feed_utxos_with_datum:
        # Skip empty price maps
        if utxo.output.datum.price_data.is_empty:
            continue

        creation_time = utxo.output.datum.price_data.get_creation_time

        if creation_time > newest_time:
            newest_time = creation_time
            newest_utxo = utxo

    if newest_utxo:
        price = newest_utxo.output.datum.price_data.get_price
        return (newest_utxo, price)
    else:
        return (newest_utxo, price)


def get_fee_rate_reference_utxo(utxos: list[UTxO]) -> UTxO:
    for utxo in utxos:
        if utxo.output.datum and utxo.output.datum.cbor:
            utxo.output.datum = AggState.from_cbor(utxo.output.datum.cbor)

    current_time = int(time.time_ns() * 1e-6)
    non_expired_agg_states = [
        utxo
        for utxo in utxos
        if utxo.output.datum
        and isinstance(utxo.output.datum, AggState)
        and utxo.output.datum.price_data.is_valid
        and utxo.output.datum.price_data.is_active(current_time)
    ]
    if not non_expired_agg_states:
        raise ValidationError("No Aggregation State Rate datum with fresh timestamp")

    non_expired_agg_states.sort(
        key=lambda utxo: utxo.output.datum.price_data.get_expiration_time
    )
    return non_expired_agg_states.pop()


def create_agg_state_output(
    agg_state: UTxO,
    median_value: int,
    current_time: int,
    liveness_period: int,
    address: Address,
) -> TransactionOutput:
    """Helper method to create agg state output with consistent timestamp."""
    return TransactionOutput(
        address=address,
        amount=agg_state.output.amount,
        datum=AggState(
            price_data=PriceData.set_price_map(
                median_value, current_time, current_time + liveness_period
            )
        ),
    )


def create_transport_output(
    transport: UTxO,
    current_message: AggregateMessage,
    median_value: int,
    node_reward_price: int,
    minimum_fee: int,
    reward_token_hash: ScriptHash | None,
    reward_token_name: AssetName | None,
    address: Address,
) -> TransactionOutput:
    """Helper method to create transport output with consistent data."""
    transport_output = deepcopy(transport.output)

    _add_reward_to_output(
        transport_output, minimum_fee, reward_token_hash, reward_token_name
    )

    return _create_final_output(
        transport_output,
        current_message,
        median_value,
        node_reward_price,
        minimum_fee,
        address,
    )


def _add_reward_to_output(
    transport_output: TransactionOutput,
    minimum_fee: int,
    reward_token_hash: ScriptHash | None,
    reward_token_name: AssetName | None,
) -> None:
    """
    Add fees to the transport output based on reward token configuration.

    Args:
        transport_output: The output to add fees to
        minimum_fee: The fee amount to add
    """
    if not (reward_token_hash or reward_token_name):
        transport_output.amount.coin += minimum_fee
        return

    _add_token_fees(transport_output, minimum_fee, reward_token_hash, reward_token_name)


def _add_token_fees(
    transport_output: TransactionOutput,
    minimum_fee: int,
    token_hash: ScriptHash | None,
    token_name: AssetName | None,
) -> None:
    """
    Add token-based fees to the output.

    Args:
        transport_output: The output to add token fees to
        minimum_fee: The fee amount to add
    """

    if (
        token_hash in transport_output.amount.multi_asset
        and token_name in transport_output.amount.multi_asset[token_hash]
    ):
        transport_output.amount.multi_asset[token_hash][token_name] += minimum_fee
    else:
        fee_asset = MultiAsset({token_hash: Asset({token_name: minimum_fee})})
        transport_output.amount.multi_asset += fee_asset


def _create_final_output(
    transport_output: TransactionOutput,
    current_message: AggregateMessage,
    median_value: int,
    node_reward_price: int,
    minimum_fee: int,
    address: Address,
) -> TransactionOutput:
    """
    Create the final transaction output with all necessary data.

    Args:
        transport_output: The processed transport output
        current_message: Current aggregate message
        median_value: The calculated median value
        node_reward_price: Price for node reward
        minimum_fee: Minimum fee added

    Returns:
        TransactionOutput: The final transaction output
    """
    return TransactionOutput(
        address=address,
        amount=transport_output.amount,
        datum=RewardTransportVariant(
            datum=RewardConsensusPending(
                aggregation=Aggregation(
                    oracle_feed=median_value,
                    message=current_message,
                    node_reward_price=node_reward_price,
                    rewards_amount_paid=minimum_fee,
                )
            )
        ),
    )
