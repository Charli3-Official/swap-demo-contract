"""A class to read an oracle feed"""
import pycardano as pyc
from typing import List, Tuple
from lib.chain_query import ChainQuery
import cbor2

from lib.datums import GenericData, PriceData
from lib.redeemers import SwapA, SwapB
from lib.datums import *


class Swap:
    def __init__(
        self,
        swap_nft: pyc.MultiAsset,
        coinA: pyc.MultiAsset,
        coinB: pyc.AssetName,
    ) -> None:
        self.swap_nft = swap_nft
        self.coinA = coinA
        self.coinB = coinB


class SwapContract:
    """read oralce feed"""

    def __init__(
        self,
        context: ChainQuery,
        oracle_addr: pyc.Address,
        oracle_nft: pyc.MultiAsset,
        swap_addr: pyc.Address,
        swap: Swap,
    ) -> None:
        self.context = context
        self.oracle_addr = oracle_addr
        self.swap_addr = swap_addr
        self.coin_precision = 1000000
        self.swap = swap
        self.swap_script_hash = self.swap_addr.payment_part
        self.oracle_nft = oracle_nft

    def create_contract_instance(self):
        """Create an oracle contract using the oracle as input"""
        # the instance should use an referce script utxo at the swap address
        pass

    def add_liquidity(self, coinA: int, coinB: int):
        """Add liquidity of two predifined coins"""
        pass

    # operation for swaping coin A with B
    def swap_A(self):
        pass

    # operation for swaping coin B with A
    def swap_B(
        self,
        amountB: int,
        user_address: pyc.Address,
        swap_address: pyc.Address,
        script: bytes,
        sk: pyc.PaymentSigningKey,
    ):
        oracle_feed_utxo = self.get_oracle_feed_utxo()
        swap_utxo = self.context.utxos(str(swap_address))[0]

        swap_redeemer = pyc.Redeemer(
            pyc.RedeemerTag.SPEND, SwapB(amountB), pyc.ExecutionUnits(1000000, 80000000)
        )

        builder = pyc.TransactionBuilder(self.context)

        amountA = self.swap_b_with_a(amountB)
        traded_asset_for_the_user = self.new_multi_asset_user(amountA)
        new_value_user = pyc.transaction.Value(
            coin=2000000, multi_asset=traded_asset_for_the_user
        )

        output_user = pyc.TransactionOutput(
            address=user_address, amount=new_value_user, datum=Nothing()
        )

        available_amountB_in_swap = self.get_available_amount(self.swap.coinA)
        sending_amount = available_amountB_in_swap + (amountB * self.coin_precision)
        sending_m_asset = self.add_asset_swap(amountA)

        amount_swap = pyc.transaction.Value(
            coin=sending_amount, multi_asset=sending_m_asset
        )

        output_swap = pyc.TransactionOutput(
            address=swap_address, amount=amount_swap, datum=Nothing()
        )

        (
            builder.add_script_input(swap_utxo, script, PlutusData(), swap_redeemer)
            .add_input_address(user_address)
            .add_output(output_user)
            .add_output(output_swap)
            .reference_inputs.add(oracle_feed_utxo)
        )

        # print(f"Amount avaiblabe in swap to trade: {available_amountB_in_swap} A")

        # print(builder)
        non_nft_utxo = None
        for utxo in self.context.utxos(str(user_address)):
            # multi_asset should be empty for collateral utxo
            if not utxo.output.amount.multi_asset:
                non_nft_utxo = utxo
                break

        builder.collaterals.append(non_nft_utxo)

        signed_tx = builder.build_and_sign([sk], change_address=user_address)
        self.context.submit_tx(signed_tx.to_cbor())

        print(f"Traded: {amountB} ADA by {amountA} USDT.")

    # operation for swaping coin B with A
    def swap_b_with_a(self, amount_b: int) -> int:
        exchange_rate_price = self.get_oracle_exchange_rate()
        print(f"Oracle exchange rate: {exchange_rate_price} B/A")
        return (amount_b * self.coin_precision) // exchange_rate_price

    # operation for swaping coin A with B
    def swap_a_with_b(self, amount_a: int) -> int:
        exchange_rate_price = self.get_oracle_exchange_rate()
        print(f"Oracle exchange rate: {exchange_rate_price} B/A")
        return (amount_a * exchange_rate_price) // self.coin_precision
        # exchange_rate_price = self.get_oracle_exchange_rate()
        # print(f"Oracle exchange rate: {exchange_rate_price} ADA/USDT")
        # tokenName, amount_in_swap = self.get_asset_amount_in_swap(asset_to_use)
        # print(f"Amount of {tokenName} in liquidity: {amount_in_swap}")
        # change = 0
        # if self.swap.coinA == asset_to_use:
        #     change = self.exchange_A(amount, exchange_rate_price)
        #     print(f"change A by B {change}")
        # elif self.swap.coinB == asset_to_use:
        #     change = self.exchange_B(amount, exchange_rate_price)
        #     print(f"change B by A {change}")
        # return change

    def get_asset_amount_in_swap(self, asset: pyc.MultiAsset) -> Tuple[pyc.Asset, int]:
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
        oracle_utxos = self.context.utxos(str(self.oracle_addr))
        oracle_feed_utxo = self.get_oracle_feed_utxo()
        oracle_inline_datum: GenericData = GenericData.from_cbor(
            oracle_feed_utxo.output.datum.cbor
        )
        return oracle_inline_datum.price_data.get_price()

    def get_oracle_feed_utxo(self) -> pyc.UTxO:
        oracle_utxos = self.context.utxos(str(self.oracle_addr))
        [single_UTxO] = filter(
            lambda x: x.output.amount.multi_asset >= self.oracle_nft,
            oracle_utxos,
        )
        return single_UTxO

    def get_swap_utxo(self) -> pyc.UTxO:
        swap_utxos = self.context.utxos(str(self.swap_addr))
        return self.get_swap_liquidity_utxo(swap_utxos)

    def get_swap_liquidity_utxo(self, swap_utxos: List[pyc.UTxO]) -> pyc.UTxO:
        [single_UTxO] = filter(
            lambda x: x.output.amount.multi_asset >= self.swap.swap_nft,
            swap_utxos,
        )
        return single_UTxO

    def add_asset_swap(self, selling_amount: int) -> pyc.MultiAsset:
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

    def new_multi_asset_user(self, buying_amount: int) -> pyc.MultiAsset:
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
