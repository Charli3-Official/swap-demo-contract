from copy import deepcopy
from typing import Tuple

from charli3_offchain_core.chain_query import ChainQuery
from charli3_offchain_core.oracle_checks import c3_get_rate, filter_utxos_by_asset
from pycardano import Address, MultiAsset, Network, UTxO

from .datums import AggDatum, PriceRewards

# CONSTANT
COIN_PRECISION = 1000000


def mk_scale_reward(c3_oracle_rate_feed: float):
    def scale_reward(val: int) -> int:
        return (val * c3_oracle_rate_feed) // COIN_PRECISION

    return scale_reward


def scale_reward_prices(c3_oracle_rate_feed: float, reward_prices: PriceRewards):
    scale_reward = mk_scale_reward(c3_oracle_rate_feed)
    reward_prices.aggregate_fee = scale_reward(reward_prices.aggregate_fee)
    reward_prices.platform_fee = scale_reward(reward_prices.platform_fee)
    reward_prices.node_fee = scale_reward(reward_prices.node_fee)


class DynamicRewardsMixin:
    """
    Class used for calculation of oracle nodes and platform rewards
    """

    def __init__(
        self,
        network: Network,
        chain_query: ChainQuery,
        oracle_addr: str,
        aggstate_nft: MultiAsset,
        oracle_rate_addr: None | Address,
        oracle_rate_nft: None | MultiAsset,
    ):
        self.network = network
        self.chain_query = chain_query

        self.oracle_addr = Address.from_primitive(oracle_addr)
        self.aggstate_nft = aggstate_nft
        self.oracle_rate_addr = oracle_rate_addr
        self.oracle_rate_nft = oracle_rate_nft

        c3_oracle_rate_feed = None
        c3_oracle_rate_utxo = None
        c3_oracle_rate_utxos = (
            self.chain_query.context.utxos(self.oracle_rate_addr)
            if self.oracle_rate_addr
            else None
        )
        if c3_oracle_rate_utxos is not None:
            (c3_oracle_rate_feed, c3_oracle_rate_utxo) = c3_get_rate(
                c3_oracle_rate_utxos, self.oracle_rate_nft
            )
        self.c3_oracle_rate_feed = c3_oracle_rate_feed
        self.c3_oracle_rate_utxo = c3_oracle_rate_utxo

    async def calc_recommended_funds_amount(
        self, oracle_settings: None | AggDatum = None
    ) -> int:
        """
        calculate recommended price for sending ODV request
        using dynamic rewards method (if applicable)
        """

        if oracle_settings is None:
            _, oracle_settings = await self._get_aggstate_utxo_and_datum()

        nodes_count = len(oracle_settings.aggstate.ag_settings.os_node_list)

        reward_prices = deepcopy(oracle_settings.aggstate.ag_settings.os_node_fee_price)
        if self.c3_oracle_rate_feed is not None:
            scale_reward_prices(self.c3_oracle_rate_feed, reward_prices)

        return (
            reward_prices.aggregate_fee
            + reward_prices.platform_fee
            + nodes_count * reward_prices.node_fee
        )

    async def _get_aggstate_utxo_and_datum(self) -> Tuple[UTxO, AggDatum]:
        """Get aggstate utxo and datum."""
        oracle_utxos = await self.chain_query.get_utxos(self.oracle_addr)
        aggstate_utxo: UTxO = filter_utxos_by_asset(oracle_utxos, self.aggstate_nft)[0]

        if aggstate_utxo.output.datum and not isinstance(
            aggstate_utxo.output.datum, AggDatum
        ):
            if aggstate_utxo.output.datum.cbor:
                aggstate_datum: AggDatum = AggDatum.from_cbor(
                    aggstate_utxo.output.datum.cbor
                )
                return aggstate_utxo, aggstate_datum

        return aggstate_utxo, aggstate_utxo.output.datum
