"""A class to read an oracle feed"""
import pycardano as pyc
from typing import List, Tuple
from lib.chain_query import ChainQuery
import cbor2

from lib.datums import GenericData, PriceData
from lib.redeemers import SwapA, SwapB
from lib.datums import *


class Oracle:
    def __init__(
        self,
        oracle_creator: pyc.PaymentVerificationKey,
        oracle_NFT: pyc.MultiAsset,
        aggState_NFT: pyc.MultiAsset,
        fee_token: pyc.MultiAsset,
        node_token: pyc.MultiAsset,
    ) -> None:
        self.oracle_creator = oracle_creator
        self.oracle_NFT = oracle_NFT
        self.aggState_NFT = aggState_NFT
        self.fee_token = fee_token
        self.node_token = node_token


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
        swap_addr: pyc.Address,
        oracle: Oracle,
        swap: Swap,
    ) -> None:
        self.context = context
        self.oracle_addr = oracle_addr
        self.swap_addr = swap_addr
        self.oracle = oracle
        self.coin_precision = 1000000
        self.swap = swap
        self.swap_script_hash = self.swap_addr.payment_part

    def create_contract_instance(self):
        """Create an oracle contract using the oracle as input"""
        # the instance should use an referce script utxo at the swap address
        pass

    def add_liquidity(self, coinA: int, coinB: int):
        """Add liquidity of two predifined coins"""
        pass

    def swap_A(
        self,
        amountA: int,
        user_address: pyc.Address,
        swap_address: pyc.Address,
        script: bytes,
    ):
        amountB = self.swap_use(amountA, self.swap.coinA)

        swap_redeemer = pyc.Redeemer(
            pyc.RedeemerTag.SPEND, SwapA(amountA), pyc.ExecutionUnits(1000000, 80000000)
        )
        # utxo_to_spend = self.context.utxos(str(swap_address))[0]

        # builder = pyc.TransactionBuilder(self.context)

        # input_utxo = build.add_script_input(
        # utxo_to_spend, script, Nothing(), swap_redeemer
        # )

        # output_utxo_swap = TransactionOutput(address=swap_address, amount=2)
        # output_utxo_user = TransactionOutput(
        # address=user_address,
        # )

        print(f"Swap: {amountA} USDT by {amountB} ADA.")

    def swap_B(
        self,
        amountB: int,
        user_address: pyc.Address,
        swap_address: pyc.Address,
        script: bytes,
        sk: pyc.PaymentSigningKey,
    ):
        oracle_utxos = self.context.utxos(str(self.oracle_addr))
        oracle_feed_utxo = self.get_oracle_feed_utxo(oracle_utxos)

        swap_utxo_to_spend = self.context.utxos(str(swap_address))[0]
        available_amount = swap_utxo_to_spend.output.amount.coin
        amountA = self.swap_use_ada(amountB, available_amount)
        swap_redeemer = pyc.Redeemer(
            pyc.RedeemerTag.SPEND, SwapB(amountB), pyc.ExecutionUnits(1000000, 80000000)
        )

        builder = pyc.TransactionBuilder(self.context)

        # OUTPUT
        new_asset_user = self.new_asset_user(amountA)
        amount_user = pyc.transaction.Value(coin=2000000, multi_asset=new_asset_user)

        output_user = pyc.TransactionOutput(
            address=user_address, amount=amount_user, datum=Nothing()
        )

        amount_swap_before = swap_utxo_to_spend.output.amount.coin

        print(f"Available amount in swap contract: {amount_swap_before}")

        sending_amount = available_amount + (amountB * self.coin_precision)
        sending_m_asset = self.add_asset_swap(amountA)

        amount_swap = pyc.transaction.Value(
            coin=sending_amount, multi_asset=sending_m_asset
        )

        output_swap = pyc.TransactionOutput(
            address=swap_address, amount=amount_swap, datum=Nothing()
        )

        (
            builder.add_script_input(
                swap_utxo_to_spend, script, PlutusData(), swap_redeemer
            )
            .add_input_address(user_address)
            .add_output(output_user)
            .add_output(output_swap)
            .reference_inputs.add(oracle_feed_utxo)
        )
        print(builder)

        signed_tx = builder.build_and_sign([sk], change_address=user_address)
        self.context.submit_tx(signed_tx.to_cbor())

        print(f"Traded: {amountB} ADA by {amountA} USDT.")

    def swap_use_ada(self, amount: int, a_amount: int) -> int:
        exchange_rate_price = self.get_oracle_exchange_rate()
        print(f"Oracle exchange rate: {exchange_rate_price} USDT/ADA")
        change = self.exchange_B(amount, exchange_rate_price)
        return change

    def swap_use(self, amount: int, asset_to_use: pyc.MultiAsset) -> int:
        exchange_rate_price = self.get_oracle_exchange_rate()
        print(f"Oracle exchange rate: {exchange_rate_price} USDT/ADA")
        tokenName, amount_in_swap = self.get_asset_amount_in_swap(asset_to_use)
        print(f"Amount of {tokenName} in liquidity: {amount_in_swap}")
        change = 0
        if self.swap.coinA == asset_to_use:
            change = self.exchange_A(amount, exchange_rate_price)
            print(f"change A by B {change}")
        elif self.swap.coinB == asset_to_use:
            change = self.exchange_B(amount, exchange_rate_price)
            print(f"change B by A {change}")
        return change

    def exchange_A(self, amountA: int, rateAB: int) -> int:
        return (amountA * rateAB) // self.coin_precision  # TODO: review the precision

    def exchange_B(self, amountB: int, rateAB: int) -> int:
        return (amountB * self.coin_precision) // rateAB

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
        oracle_feed_utxo = self.get_oracle_feed_utxo(oracle_utxos)
        oracle_inline_datum: GenericData = GenericData.from_cbor(
            oracle_feed_utxo.output.datum.cbor
        )
        return oracle_inline_datum.price_data.get_price()

    def get_oracle_feed_utxo(self, oracle_utxos: List[pyc.UTxO]) -> pyc.UTxO:
        [single_UTxO] = filter(
            lambda x: x.output.amount.multi_asset >= self.oracle.oracle_NFT,
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
        [policy_id] = self.swap.coinA
        ((test1, test2),) = self.swap.coinA.to_shallow_primitive().items()
        ((a, b),) = test2.to_shallow_primitive().items()

        swap_utxo = self.get_swap_utxo()
        m_assets = swap_utxo.output.amount.multi_asset.to_shallow_primitive()

        new_multi_asset_dict = pyc.MultiAsset()
        multi_asset_assets_names = pyc.Asset()
        for swap_policy_id, assets in m_assets.items():
            if swap_policy_id == policy_id:
                for asset_name, amount in assets.items():
                    if asset_name == a:
                        multi_asset_assets_names[asset_name] = amount - selling_amount
                    else:
                        multi_asset_assets_names[asset_name] = amount
            else:
                new_multi_asset_dict[swap_policy_id] = assets
        new_multi_asset_dict[policy_id] = multi_asset_assets_names
        return new_multi_asset_dict

    def new_asset_user(self, buying_amount: int) -> pyc.MultiAsset:
        [policy_id] = self.swap.coinA
        ((test1, test2),) = self.swap.coinA.to_shallow_primitive().items()
        ((a, b),) = test2.to_shallow_primitive().items()

        swap_utxo = self.get_swap_utxo()
        m_assets = swap_utxo.output.amount.multi_asset.to_shallow_primitive()

        new_multi_asset_dict = pyc.MultiAsset()
        multi_asset_assets_names = pyc.Asset()
        for swap_policy_id, assets in m_assets.items():
            if swap_policy_id == policy_id:
                for asset_name, amount in assets.items():
                    if asset_name == a:
                        multi_asset_assets_names[asset_name] = buying_amount
        new_multi_asset_dict[policy_id] = multi_asset_assets_names
        return new_multi_asset_dict

    # def submit_tx_builder(self, builder: pyc.TransactionBuilder, address: pyc.Address):
    #     """adds collateral and signers to tx , sign and submit tx."""
    #     non_nft_utxo = self.context.find_collateral(address)

    #     builder.collaterals.append(non_nft_utxo)
    #     builder.required_signers = [self.pub_key_hash]

    #     signed_tx = builder.build_and_sign([self.signing_key], change_address=address)
    #     self.context.submit_tx_with_print(signed_tx)
