"""Swap Contract"""

from datetime import datetime

import pycardano as pyc

from swap_demo_contract.client.format import print_information, print_status
from swap_demo_contract.lib.chain_query import ChainQuery
from swap_demo_contract.lib.common import get_oracle_exchange_rate
from swap_demo_contract.utils.load_configuration import (
    OdvClientConfig,
    SwapConfig,
    WalletConfig,
)

from .lib.redeemers import AddLiquidity, SwapA, SwapB


class SwapContract:
    """SwapContact to interact with the swap smart contract

    Attributes:
        context: Blockfrost class
        oracle_nft: The NFT identifier of the oracle feed utxo
        oracle_addr: Address of the oracle contract
        swap_addr: Address of the swap contract
    """

    def __init__(
        self,
        chain_query: ChainQuery,
        odv_config: OdvClientConfig,
        wallet_config: WalletConfig,
        swap: SwapConfig,
    ) -> None:
        self.chain_query = chain_query
        self.odv_config = odv_config
        self.coin_precision = 1000000
        self.swap = swap
        self.wallet = wallet_config

    async def add_liquidity(
        self,
        amountA: int,
        amountB: int,
        user_address: pyc.Address,
        swap_address: pyc.Address,
        script: bytes,
        sk: pyc.PaymentSigningKey,
    ):

        swap_utxo = await self.get_swap_utxo()
        available_user_tADA = (
            await self.available_user_tlovelace(user_address) // 1000000
        )
        available_user_tBTC = await self.available_user_tbtc(user_address)
        if available_user_tADA < amountB or available_user_tBTC < amountA:
            print(
                f"""Error! The user's wallet  doesn't have enough liquidity!
            Available: {available_user_tBTC} BTC, {available_user_tADA} tADA"""
            )
        else:
            updated_swap_multi_asset, updated_swap_total_amount = (
                await self.add_asset_swap(amountA)
            )

            updated_amountB_for_swap_utxo = (
                swap_utxo.output.amount.coin + amountB * 1000000
            )

            swap_redeemer = pyc.Redeemer(AddLiquidity())

            swap_value = pyc.transaction.Value(
                coin=updated_amountB_for_swap_utxo,
                multi_asset=updated_swap_multi_asset,
            )

            updated_swap_utxo = pyc.TransactionOutput(
                address=swap_address, amount=swap_value, datum=pyc.Unit()
            )

            builder = pyc.TransactionBuilder(self.chain_query.context)
            (
                builder.add_script_input(
                    utxo=swap_utxo,
                    script=script,
                    redeemer=swap_redeemer,
                )
                .add_input_address(user_address)
                .add_output(updated_swap_utxo)
            )

            await self.chain_query.submit_tx_builder(builder, sk, user_address)

            print("Updated swap contract liquidity:")
            print(
                f"- {updated_amountB_for_swap_utxo // 1000000} tADA ({updated_amountB_for_swap_utxo} tlovelaces)"
            )
            print(f"- {updated_swap_total_amount} BTC.")

    async def swap_A(
        self,
        amountA: int,
        user_address: pyc.Address,
        swap_address: pyc.Address,
        script: bytes,
        sk: pyc.PaymentSigningKey,
    ):
        """Exchange of asset A  with B"""
        oracle_feed_utxo = await self.get_oracle_utxo()
        swap_utxo = await self.get_swap_utxo()
        amountB = await self.swap_a_with_b(amountA)
        amountB_precision = amountB * self.coin_precision

        swap_amountB_tADA = swap_utxo.output.amount.coin // 1000000
        user_amountB_tBTC = await self.available_user_tbtc(user_address)

        if amountB < 1:
            print(
                f"The minimum sale quantity of tADA is 1. Current value {amountB} tADA."
            )

        elif amountB > swap_amountB_tADA:
            print("Error! The user's wallet doesn't have enough liquidity!")
            print(f"Available: {swap_amountB_tADA} BTC.")
        elif amountA > user_amountB_tBTC:
            print("Error! The user's wallet doesn't have enough liquidity!")
            print(f"Available: {user_amountB_tBTC} BTC.")
        else:
            swap_redeemer = pyc.Redeemer(SwapA(amountA))

            amount_for_the_user = pyc.transaction.Value(coin=amountB_precision)

            new_output_utxo_user = pyc.TransactionOutput(
                address=user_address, amount=amount_for_the_user
            )

            # swap utxo
            # TODO change units to ada instead of lovelace
            updated_amountB_for_swap_utxo = swap_utxo.output.amount.coin - amountB

            updated_swap_multi_asset, updated_swap_total_amount = (
                await self.add_asset_swap(amountA)
            )
            amount_swap = pyc.transaction.Value(
                coin=updated_amountB_for_swap_utxo,
                multi_asset=updated_swap_multi_asset,
            )

            new_output_swap = pyc.TransactionOutput(
                address=swap_address, amount=amount_swap, datum=pyc.Unit()
            )

            builder = pyc.TransactionBuilder(self.chain_query.context)
            (
                builder.add_script_input(
                    utxo=swap_utxo, script=script, redeemer=swap_redeemer
                )
                .add_input_address(user_address)
                .add_output(new_output_utxo_user)
                .add_output(new_output_swap)
                .reference_inputs.add(oracle_feed_utxo.input)
            )

            print(f"Exchanging {amountA} lovelace for {amountB} tADA.")
            await self.chain_query.submit_tx_builder(builder, sk, user_address)

            print("Updated swap contract liquidity:")
            print(f"- {updated_amountB_for_swap_utxo} tlovelaces.")
            print(f"- {updated_swap_total_amount} BTC.")

    async def swap_B(
        self,
        amountB: int,
        user_address: pyc.Address,
        swap_address: pyc.Address,
        script: bytes,
        sk: pyc.PaymentSigningKey,
    ):
        """Exchange of asset B  with A"""
        oracle_feed_utxo = await self.get_oracle_utxo()
        swap_utxo = await self.get_swap_utxo()
        amountA = await self.swap_b_with_a(amountB)
        available_user_tADA = (
            await self.available_user_tlovelace(user_address) // 1000000
        )

        available_swap_tbtc = await self.decrease_asset_swap_amount(0)
        if amountA < 1:
            print_information(
                f"The minimum sale quantity of BTC is 1. Current value {amountA} BTC."
            )
        elif amountB > available_user_tADA:
            print_information(
                f"""Error! The user's wallet doesn't have enough liquidity!
            Available: {available_user_tADA} tADA."""
            )
        elif amountA > available_swap_tbtc:
            print_information(
                f"""Error! The swap contract doesn't have enough liquidity!
            Available: {available_swap_tbtc} BTC."""
            )
        else:
            swap_redeemer = pyc.Redeemer(SwapB(amountB))

            multi_asset_for_the_user = await self.take_multi_asset_user(amountA)

            # Add the minimum lovelace amount to the user value
            amount_for_the_user = pyc.transaction.Value(
                coin=2000000, multi_asset=multi_asset_for_the_user
            )

            # Add the value to the user UTXO
            new_output_utxo_user = pyc.TransactionOutput(
                address=user_address, amount=amount_for_the_user
            )

            amountB_at_swap_utxo = swap_utxo.output.amount.coin
            updated_amountB_for_swap_utxo = amountB_at_swap_utxo + (amountB * 1000000)

            updated_masset_for_swap_utxo = await self.decrease_asset_swap(amountA)
            updated_masset_amount_for_swap_utxo = await self.decrease_asset_swap_amount(
                amountA
            )

            amount_swap = pyc.transaction.Value(
                coin=updated_amountB_for_swap_utxo,
                multi_asset=updated_masset_for_swap_utxo,
            )

            new_output_swap = pyc.TransactionOutput(
                address=swap_address, amount=amount_swap, datum=pyc.Unit()
            )

            builder = pyc.TransactionBuilder(self.chain_query.context)
            (
                builder.add_script_input(
                    utxo=swap_utxo,
                    script=script,
                    redeemer=swap_redeemer,
                )
                .add_input_address(user_address)
                .add_output(new_output_utxo_user)
                .add_output(new_output_swap)
                .reference_inputs.add(oracle_feed_utxo.input)
            )

            print(f"Exchanging {amountB} tADA for {amountA} BTC.")
            await self.chain_query.submit_tx_builder(builder, sk, user_address)
            # await self.submit_tx_builder(builder, sk, user_address)
            print("Updated swap contract liquidity:")
            print(
                f"- {updated_amountB_for_swap_utxo // 1000000 } tADA ({updated_amountB_for_swap_utxo} tlovelaces)."
            )
            print(f"- {updated_masset_amount_for_swap_utxo} BTC.")

    async def swap_b_with_a(self, amount_b: int) -> int:
        """Operation for swaping coin B with A"""

        feed_utxos = self.chain_query.get_utxos_with_asset_from_kupo(
            self.odv_config.policy_id, self.odv_config.nft_aggstate
        )
        _, exchange_rate_price = await get_oracle_exchange_rate(feed_utxos)
        print_status(
            "Oracle exchange rate",
            f"{exchange_rate_price / self.coin_precision} BTC/tADA (A/B)",
        )
        return (amount_b * self.coin_precision) // exchange_rate_price

    async def swap_a_with_b(self, amount_a: int) -> int:
        """Operation for swaping coin A with B"""
        feed_utxos = self.chain_query.get_utxos_with_asset_from_kupo(
            self.odv_config.policy_id, self.odv_config.nft_aggstate
        )
        _, exchange_rate_price = await get_oracle_exchange_rate(feed_utxos)

        print_status(
            "Oracle exchange rate",
            f"{exchange_rate_price / self.coin_precision} BTC/tADA (A/B)",
        )
        return (amount_a * exchange_rate_price) // self.coin_precision

    def format_timestamp(self, timestamp):
        """Convert epoch to humnan"""
        return datetime.utcfromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")

    async def get_oracle_timestamp(self) -> int:
        """Get the oracle's feed exchange rate"""
        oracle_feed_utxo = await self.get_oracle_utxo()
        oracle_inline_datum: GenericData = GenericData.from_cbor(
            oracle_feed_utxo.output.datum.cbor
        )
        return oracle_inline_datum.price_data.get_timestamp()

    async def get_oracle_expiration(self) -> int:
        """Get the oracle's feed exchange rate"""
        oracle_feed_utxo = await self.get_oracle_utxo()
        oracle_inline_datum: GenericData = GenericData.from_cbor(
            oracle_feed_utxo.output.datum.cbor
        )
        return oracle_inline_datum.price_data.get_expiry()

    async def get_oracle_utxo(self) -> pyc.UTxO:
        """Retrieve the oracle's feed UTXO using the NFT identifier."""

        feed_utxos = self.chain_query.get_utxos_with_asset_from_kupo(
            self.odv_config.policy_id, self.odv_config.nft_aggstate
        )
        utxo, _ = await get_oracle_exchange_rate(feed_utxos)

        return utxo

    async def get_swap_utxo(self) -> pyc.UTxO:
        """Retrieve the UTxO for the swap using the NFT identifier"""
        try:
            swap_utxos = self.chain_query.get_utxos_with_asset_from_kupo(
                self.swap.policy_id, self.swap.nft_swap
            )
            return swap_utxos[0]
        except StopIteration:
            raise ValueError("No matching UTxO found for the given NFT identifier")

    async def decrease_asset_swap(self, selling_amount: int) -> pyc.MultiAsset:
        """The updated swap asset to be decreased at the address"""
        policy_id = self.swap.token_a_policy_id
        asset_name = self.swap.token_a_asset_name

        swap_utxo = await self.get_swap_utxo()
        m_assets = swap_utxo.output.amount.multi_asset.to_shallow_primitive()

        new_multi_asset_dict = pyc.MultiAsset()
        multi_asset_assets_names = pyc.Asset()
        for swap_policy_id, assets in m_assets.items():
            if swap_policy_id == policy_id:
                for asset_name_in_utxo, amount in assets.items():
                    if asset_name_in_utxo == asset_name:
                        multi_asset_assets_names[asset_name_in_utxo] = (
                            amount - selling_amount
                        )
                    else:
                        multi_asset_assets_names[asset_name_in_utxo] = amount
            else:
                new_multi_asset_dict[swap_policy_id] = assets
        new_multi_asset_dict[policy_id] = multi_asset_assets_names
        return new_multi_asset_dict

    async def decrease_asset_swap_amount(self, selling_amount: int) -> int:
        """The updated swap asset amount to be decreased at the address"""
        policy_id = self.swap.token_a_policy_id
        asset_name = self.swap.token_a_asset_name

        swap_utxo = await self.get_swap_utxo()
        m_assets = swap_utxo.output.amount.multi_asset.to_shallow_primitive()

        amountA = 0
        for swap_policy_id, assets in m_assets.items():
            if swap_policy_id == policy_id:
                for asset_name_in_utxo, amount in assets.items():
                    if asset_name_in_utxo == asset_name:
                        amountA = amount - selling_amount
        return amountA

    async def add_asset_swap(self, buying_amount: int):
        """The updated swap asset to be added at the address"""
        swap_utxo = await self.get_swap_utxo()

        coin_a_policy_id = str(self.swap.token_a_policy_id)
        coin_a_asset_name = str(self.swap.token_a_asset_name)

        has_coin_a_policy = swap_utxo.output.amount.multi_asset.get(
            coin_a_policy_id, None
        )

        if has_coin_a_policy:
            has_coin_a_asset_name = swap_utxo.output.amount.multi_asset[
                coin_a_policy_id
            ].get(coin_a_asset_name, None)
            if has_coin_a_asset_name:
                swap_utxo.output.amount.multi_asset[coin_a_policy_id][
                    coin_a_asset_name
                ] += buying_amount

            else:
                swap_utxo.output.amount.multi_asset[coin_a_policy_id][
                    coin_a_asset_name
                ] = buying_amount

        else:
            new_asset = pyc.Asset({coin_a_asset_name: buying_amount})
            swap_utxo.output.amount.multi_asset[coin_a_policy_id] = new_asset

        total_amount = swap_utxo.output.amount.multi_asset[coin_a_policy_id][
            coin_a_asset_name
        ]
        return swap_utxo.output.amount.multi_asset, total_amount

    async def add_asset_swap_amount(self, buying_amount: int) -> int:
        """The updated swap asset amount to be added at the address"""
        policy_id = self.swap.token_a_policy_id
        asset_name = self.swap.token_a_asset_name

        swap_utxo = await self.get_swap_utxo()
        m_assets = swap_utxo.output.amount.multi_asset.to_shallow_primitive()

        amountA = 0
        for swap_policy_id, assets in m_assets.items():
            if swap_policy_id == policy_id:
                for asset_name_in_utxo, amount in assets.items():
                    if asset_name_in_utxo == asset_name:
                        amountA = amount + buying_amount

        return amountA

    async def take_multi_asset_user(self, buying_amount: int) -> pyc.MultiAsset:
        """The updated user asset to be added to it's wallet"""
        ((policy_id, assets),) = self.swap.coinA.to_shallow_primitive().items()
        ((asset, _),) = assets.to_shallow_primitive().items()

        swap_utxo = await self.get_swap_utxo()
        m_assets = swap_utxo.output.amount.multi_asset.to_shallow_primitive()

        new_multi_asset_dict = pyc.MultiAsset()
        multi_asset_assets_names = pyc.Asset()
        for swap_policy_id, assets in m_assets.items():
            if swap_policy_id == policy_id:
                for asset_name, _ in assets.items():
                    if asset_name == asset:
                        multi_asset_assets_names[asset_name] = buying_amount
        new_multi_asset_dict[policy_id] = multi_asset_assets_names
        return new_multi_asset_dict

    def available_user_pure_tlovelace(self, user_address: pyc.Address) -> int:
        """Get the available user's pure lovelace amount"""
        amount = 0
        for utxo in self.chain_query.utxos(str(user_address)):
            if not utxo.output.amount.multi_asset:
                amount += utxo.output.amount.coin
        return amount

    async def available_user_tlovelace(self, user_address: pyc.Address) -> int:
        """Get the available user's  lovelace amount"""
        amount = 0
        utxos = await self.chain_query.get_utxos(str(user_address))
        for utxo in utxos:
            amount += utxo.output.amount.coin
        return amount

    async def available_user_tbtc(self, user_address: pyc.Address) -> int:
        amount_asset = 0

        policy_id = self.swap.token_a_policy_id
        asset_name = self.swap.token_a_asset_name

        utxos = await self.chain_query.get_utxos(str(user_address))
        for utxo in utxos:
            m_assets = utxo.output.amount.multi_asset.to_shallow_primitive()
            for user_policy_id, assets in m_assets.items():
                if user_policy_id == policy_id:
                    for asset_name_in_utxo, amount in assets.items():
                        if asset_name_in_utxo == asset_name:
                            amount_asset += amount
        return amount_asset
