import pycardano as pyc
from typing import Tuple
from lib.chain_query import ChainQuery

from lib.datums import GenericData
from lib.redeemers import SwapA, SwapB


class Swap:
    """Class Swap for interact with the assets in the swap operation
    and identify the spwa NFT

    Attribures:
        swap_nft: The NFT identifier of the swap utxo
        coinA: Asset
    """

    def __init__(
        self,
        swap_nft: pyc.MultiAsset,
        coinA: pyc.MultiAsset,
    ) -> None:
        self.swap_nft = swap_nft
        self.coinA = coinA


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
        context: ChainQuery,
        oracle_nft: pyc.MultiAsset,
        oracle_addr: pyc.Address,
        swap_addr: pyc.Address,
        swap: Swap,
    ) -> None:
        self.context = context
        self.oracle_addr = oracle_addr
        self.swap_addr = swap_addr
        self.coin_precision = 1000000
        self.swap = swap
        self.oracle_nft = oracle_nft

    def swap_A(
        self,
        amountA: int,
        user_address: pyc.Address,
        swap_address: pyc.Address,
        script: bytes,
        sk: pyc.PaymentSigningKey,
    ):
        """Exchange of asset A  with B"""
        oracle_feed_utxo = self.get_oracle_utxo()
        swap_utxo = self.get_swap_utxo()
        amountB = self.swap_a_with_b(amountA)
        swap_redeemer = pyc.Redeemer(pyc.RedeemerTag.SPEND, SwapA(amountA))
        print(amountB)

        amount_for_the_user = pyc.transaction.Value(coin=amountB * self.coin_precision)

        new_output_utxo_user = pyc.TransactionOutput(
            address=user_address, amount=amount_for_the_user
        )
        # swap utxo
        amountB_at_swap_utxo = swap_utxo.output.amount.coin
        updated_amountB_for_swap_utxo = amountB_at_swap_utxo - amountB

        updated_masset_for_swap_utxo = self.add_asset_swap(amountA)  # add usdt
        amount_swap = pyc.transaction.Value(
            coin=updated_amountB_for_swap_utxo, multi_asset=updated_masset_for_swap_utxo
        )

        new_output_swap = pyc.TransactionOutput(
            address=swap_address, amount=amount_swap, datum=pyc.PlutusData()
        )

        builder = pyc.TransactionBuilder(self.context)
        (
            builder.add_script_input(
                utxo=swap_utxo, script=script, redeemer=swap_redeemer
            )
            .add_input_address(user_address)
            .add_output(new_output_utxo_user)
            .add_output(new_output_swap)
            .reference_inputs.add(oracle_feed_utxo.input)
        )

        self.submit_tx_builder(builder, sk, user_address)

    def swap_B(
        self,
        amountB: int,
        user_address: pyc.Address,
        swap_address: pyc.Address,
        script: bytes,
        sk: pyc.PaymentSigningKey,
    ):
        """Exchange of asset B  with A"""
        oracle_feed_utxo = self.get_oracle_utxo()
        swap_utxo = self.get_swap_utxo()
        amountA = self.swap_b_with_a(amountB // self.coin_precision)
        swap_redeemer = pyc.Redeemer(
            pyc.RedeemerTag.SPEND, SwapB(amountB // self.coin_precision)
        )

        multi_asset_for_the_user = self.take_multi_asset_user(amountA)
        amount_for_the_user = pyc.transaction.Value(
            coin=2000000, multi_asset=multi_asset_for_the_user
        )
        new_output_utxo_user = pyc.TransactionOutput(
            address=user_address, amount=amount_for_the_user
        )

        amountB_at_swap_utxo = swap_utxo.output.amount.coin
        updated_amountB_for_swap_utxo = amountB_at_swap_utxo + (amountB)
        updated_masset_for_swap_utxo = self.decrease_asset_swap(amountA)

        amount_swap = pyc.transaction.Value(
            coin=updated_amountB_for_swap_utxo, multi_asset=updated_masset_for_swap_utxo
        )

        new_output_swap = pyc.TransactionOutput(
            address=swap_address, amount=amount_swap, datum=pyc.PlutusData()
        )

        builder = pyc.TransactionBuilder(self.context)
        (
            builder.add_script_input(
                utxo=swap_utxo, script=script, redeemer=swap_redeemer
            )
            .add_input_address(user_address)
            .add_output(new_output_utxo_user)
            .add_output(new_output_swap)
            .reference_inputs.add(oracle_feed_utxo.input)
        )

        self.submit_tx_builder(builder, sk, user_address)

        # print(f"Amount avaiblabe in swap to trade: {available_amountB_in_swap} A")
        # print(f"Traded: {amountB} B with {amountA} A.")

    def swap_b_with_a(self, amount_b: int) -> int:
        """operation for swaping coin B with A"""
        exchange_rate_price = self.get_oracle_exchange_rate()
        print(f"Oracle exchange rate: {exchange_rate_price} B/A")
        return (amount_b * self.coin_precision) // exchange_rate_price

    def swap_a_with_b(self, amount_a: int) -> int:
        """operation for swaping coin A with B"""
        exchange_rate_price = self.get_oracle_exchange_rate()
        print(f"Oracle exchange rate: {exchange_rate_price} B/A")
        return (amount_a * exchange_rate_price) // self.coin_precision

    def get_asset_amount_in_swap(self, asset: pyc.MultiAsset) -> Tuple[pyc.Asset, int]:
        """Determine a given asset amount at swap utxo"""
        swap_utxo = self.get_swap_utxo()
        [policy_id] = asset
        value = swap_utxo.output.amount.multi_asset
        token = ()
        for currency_symbol, k in value.items():
            if currency_symbol == policy_id:
                ((r, s),) = k.items()
                token = tuple((r, s))
        return token

    def get_oracle_exchange_rate(self) -> int:
        """Get the oracle feed exchange rate"""
        oracle_feed_utxo = self.get_oracle_utxo()
        oracle_inline_datum: GenericData = GenericData.from_cbor(
            oracle_feed_utxo.output.datum.cbor
        )
        return oracle_inline_datum.price_data.get_price()

    def get_oracle_utxo(self) -> pyc.UTxO:
        """Get the oracle feed utxo"""
        oracle_utxos = self.context.utxos(str(self.oracle_addr))
        [oracle_utxo_nft] = filter(
            lambda x: x.output.amount.multi_asset >= self.oracle_nft,
            oracle_utxos,
        )
        return oracle_utxo_nft

    def get_swap_utxo(self) -> pyc.UTxO:
        """Get the swap utxo using the nft identifier"""
        swap_utxos = self.context.utxos(str(self.swap_addr))
        [swap_utxo_nft] = filter(
            lambda x: x.output.amount.multi_asset >= self.swap.swap_nft,
            swap_utxos,
        )
        return swap_utxo_nft

    def decrease_asset_swap(self, selling_amount: int) -> pyc.MultiAsset:
        """The updated swap asset to be decreased at the address"""
        ((policy_id, assets),) = self.swap.coinA.to_shallow_primitive().items()
        ((asset, _),) = assets.to_shallow_primitive().items()

        swap_utxo = self.get_swap_utxo()
        m_assets = swap_utxo.output.amount.multi_asset.to_shallow_primitive()

        new_multi_asset_dict = pyc.MultiAsset()
        multi_asset_assets_names = pyc.Asset()
        for swap_policy_id, assets in m_assets.items():
            if swap_policy_id == policy_id:
                for asset_name, amount in assets.items():
                    if asset_name == asset:
                        multi_asset_assets_names[asset_name] = amount - selling_amount
                    else:
                        multi_asset_assets_names[asset_name] = amount
            else:
                new_multi_asset_dict[swap_policy_id] = assets
        new_multi_asset_dict[policy_id] = multi_asset_assets_names
        return new_multi_asset_dict

    def add_asset_swap(self, buying_amount: int) -> pyc.MultiAsset:
        """The updated swap asset to be added at the address"""
        ((policy_id, assets),) = self.swap.coinA.to_shallow_primitive().items()
        ((asset, _),) = assets.to_shallow_primitive().items()

        swap_utxo = self.get_swap_utxo()
        m_assets = swap_utxo.output.amount.multi_asset.to_shallow_primitive()

        new_multi_asset_dict = pyc.MultiAsset()
        multi_asset_assets_names = pyc.Asset()
        for swap_policy_id, assets in m_assets.items():
            if swap_policy_id == policy_id:
                for asset_name, amount in assets.items():
                    if asset_name == asset:
                        multi_asset_assets_names[asset_name] = amount + buying_amount
                    else:
                        multi_asset_assets_names[asset_name] = amount
            else:
                new_multi_asset_dict[swap_policy_id] = assets
        new_multi_asset_dict[policy_id] = multi_asset_assets_names
        return new_multi_asset_dict

    def take_multi_asset_user(self, buying_amount: int) -> pyc.MultiAsset:
        """The updated user asset to be added to it's wallet"""
        ((policy_id, assets),) = self.swap.coinA.to_shallow_primitive().items()
        ((asset, _),) = assets.to_shallow_primitive().items()

        swap_utxo = self.get_swap_utxo()
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

    def get_available_amount(self, asset: pyc.MultiAsset) -> int:
        """Get the available amount of an asset at swap UTXO"""
        ((policy_id, assets),) = asset.to_shallow_primitive().items()
        ((asset, _),) = assets.to_shallow_primitive().items()

        swap_utxo = self.get_swap_utxo()
        m_assets = swap_utxo.output.amount.multi_asset.to_shallow_primitive()

        available_amount = 0
        for swap_policy_id, assets in m_assets.items():
            if swap_policy_id == policy_id:
                for asset_name, amount in assets.items():
                    if asset_name == asset:
                        available_amount = amount
        return available_amount

    def submit_tx_builder(
        self,
        builder: pyc.TransactionBuilder,
        sk: pyc.PaymentSigningKey,
        address: pyc.Address,
    ):
        """Adds collateral and signers to tx , sign and submit tx."""
        non_nft_utxo = self.context.find_collateral(address)

        if non_nft_utxo is None:
            self.context.create_collateral(address, sk)
            non_nft_utxo = self.context.find_collateral(address)

        builder.collaterals.append(non_nft_utxo)
        print(builder)
        signed_tx = builder.build_and_sign([sk], change_address=address)
        # self.context.submit_tx_with_print(signed_tx)
