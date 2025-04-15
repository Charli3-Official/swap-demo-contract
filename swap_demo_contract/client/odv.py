import asyncio
import logging

import aiohttp
from pycardano import ScriptHash, Transaction, TransactionWitnessSet
from pydantic import BaseModel, model_serializer

from swap_demo_contract.client.message import SignedOracleNodeMessage
from swap_demo_contract.lib.chain_query import ValidityWindow
from swap_demo_contract.lib.datums_odv import AggregateMessage, PosixTime
from swap_demo_contract.utils.load_configuration import NodeNetworkId

logger = logging.getLogger(__name__)


class OdvTxSignatureRequest(BaseModel):
    """Request signature from oracle node"""

    node_messages: dict[str, SignedOracleNodeMessage]
    tx_cbor: str

    @model_serializer
    def serialize(self) -> dict[str, dict]:
        return {
            "node_messages": {k: v.model_dump() for k, v in self.node_messages.items()},
            "tx_cbor": self.tx_cbor,
        }


class ODVClient:
    """Client for ODV node interactions."""

    async def collect_feed_updates(
        self,
        nodes: list[NodeNetworkId],
        policy_id: ScriptHash,
        validity_window: ValidityWindow,
    ) -> dict[str, SignedOracleNodeMessage]:
        """
        Collect feed updates from nodes.

        :param nodes: List of nodes to interact with.
        :param feed_request: The feed request to send to the nodes.
        :return: A dictionary mapping node public keys to their responses.
        """

        async def fetch_from_node(
            session: aiohttp.ClientSession, node: NodeNetworkId
        ) -> tuple[str, SignedOracleNodeMessage | None]:
            try:
                endpoint = f"{node.root_url.rstrip('/')}/odv/feed"
                request_data = {
                    "oracle_nft_policy_id": str(policy_id),
                    "tx_validity_interval": {
                        "start": validity_window.validity_start,
                        "end": validity_window.validity_end,
                    },
                }
                async with session.post(endpoint, json=request_data) as response:
                    if response.status != 200:
                        logger.error(f"Error from {node.root_url}: {response.status}")
                        return node.pub_key, None

                    data = await response.json()
                    signed_message = SignedOracleNodeMessage.model_validate(data)
                    return node.pub_key, signed_message

            except Exception as e:
                logger.error(f"Failed to fetch from {node.root_url}: {e!s}")
                return node.pub_key, None

        async with aiohttp.ClientSession() as session:
            tasks = [fetch_from_node(session, node) for node in nodes]
            responses = await asyncio.gather(*tasks)

            return {pkh: msg for pkh, msg in responses if msg is not None}

    async def collect_tx_signatures(
        self,
        nodes: list[NodeNetworkId],
        tx_request: OdvTxSignatureRequest,
    ) -> dict[str, str]:
        """
        Collect transaction signatures from nodes.

        :param nodes: List of nodes to interact with.
        :param tx_request: The transaction signature request to send to the nodes.
        :return: A dictionary mapping node public keys to their signatures.
        """

        async def fetch_signature(
            session: aiohttp.ClientSession, node: NodeNetworkId
        ) -> tuple[str, str | None]:
            try:
                endpoint = f"{node.root_url.rstrip('/')}/odv/sign"
                payload = tx_request.model_dump()
                async with session.post(endpoint, json=payload) as response:
                    if response.status != 200:
                        logger.error(f"Error from {node.root_url}: {response.status}")
                        return node.pub_key, None

                    data = await response.json()
                    logger.debug(f"Received response from {node.root_url}: {data}")
                    return node.pub_key, data["signed_tx_cbor"]

            except aiohttp.ClientError as e:
                logger.error(f"Connection error to {node.root_url}: {e!s}")
                return node.pub_key, None
            except Exception as e:
                logger.error(f"Error processing {node.root_url}: {e!s}")
                return node.pub_key, None

        async with aiohttp.ClientSession() as session:
            tasks = [fetch_signature(session, node) for node in nodes]
            responses = await asyncio.gather(*tasks)

            return {pkh: sig for pkh, sig in responses if sig is not None}

    def attach_tx_signatures(
        self,
        transaction: Transaction,
        signed_txs: dict[str, str],
    ) -> Transaction:
        """
        Attach collected signatures to the transaction.

        :param transaction: The transaction to attach signatures to.
        :param signed_txs: A dictionary of node public keys to their signatures.
        :return: The transaction with attached signatures.
        """
        if transaction.transaction_witness_set is None:
            transaction.transaction_witness_set = TransactionWitnessSet()

        for signed_tx_response in signed_txs.values():
            signed_tx = Transaction.from_cbor(signed_tx_response)
            if (
                signed_tx.transaction_witness_set
                and signed_tx.transaction_witness_set.vkey_witnesses
            ):
                transaction.transaction_witness_set.vkey_witnesses.extend(
                    signed_tx.transaction_witness_set.vkey_witnesses
                )

        return transaction


def build_aggregate_message(
    nodes_messages: list[SignedOracleNodeMessage],
    timestamp: PosixTime,
) -> AggregateMessage:
    """Build aggregate message from node messages and timestamp.

    Args:
        nodes_messages: List of signed oracle messages from nodes
        timestamp: POSIX timestamp in milliseconds

    Returns:
        AggregateMessage with sorted feeds and provided timestamp

    Raises:
        ValueError: If no messages provided or signature validation fails
    """
    if not nodes_messages:
        raise ValueError("No node messages provided")

    for msg in nodes_messages:
        try:
            msg.validate_signature()
        except ValueError as e:
            raise ValueError(f"Invalid message signature: {e}") from e

    feeds = {msg.verification_key.hash(): msg.message.feed for msg in nodes_messages}

    sorted_feeds = dict(sorted(feeds.items(), key=lambda x: x[1]))

    return AggregateMessage(
        node_feeds_sorted_by_feed=sorted_feeds,
        node_feeds_count=len(sorted_feeds),
        timestamp=timestamp,
    )
