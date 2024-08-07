import pycardano as pyc

from charli3_offchain_core.chain_query import ChainQuery
from .lib.datums import GenericData, Nothing
from .lib.redeemers import AddLiquidity, SwapA, SwapB


class Swap:
    """Class Swap for interact with the assets in the swap operation
    and identify the Swap's NFTs

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
        chain_query: ChainQuery,
        oracle_nft: pyc.MultiAsset,
        oracle_addr: pyc.Address,
        swap_addr: pyc.Address,
        swap: Swap,
    ) -> None:
        self.chain_query = chain_query
        self.oracle_addr = oracle_addr
        self.swap_addr = swap_addr
        self.coin_precision = 1000000
        self.swap = swap
        self.oracle_nft = oracle_nft

    def add_liquidity(
        self,
        amountA: int,
        amountB: int,
        user_address: pyc.Address,
        swap_address: pyc.Address,
        script: bytes,
        sk: pyc.PaymentSigningKey,
    ):

        swap_utxo = self.get_swap_utxo()
        available_user_tADA = self.available_user_tlovelace(user_address) // 1000000
        available_user_tUSDT = self.available_user_tusdt(user_address)
        if available_user_tADA < amountB or available_user_tUSDT < amountA:
            print(
                f"""Error! The user's wallet  doesn't have enough liquidity!
            Available: {available_user_tUSDT} tUSDT, {available_user_tADA} tADA"""
            )
        else:
            updated_massetA_for_swap_utxo = self.add_asset_swap(amountA)
            updated_amountA_for_swap_utxo = self.add_asset_swap_amount(amountA)

            updated_amountB_for_swap_utxo = (
                swap_utxo.output.amount.coin + amountB * 1000000
            )

            swap_redeemer = pyc.Redeemer(pyc.RedeemerTag.SPEND, AddLiquidity())

            swap_value = pyc.transaction.Value(
                coin=updated_amountB_for_swap_utxo,
                multi_asset=updated_massetA_for_swap_utxo,
            )

            updated_swap_utxo = pyc.TransactionOutput(
                address=swap_address, amount=swap_value, datum=pyc.PlutusData()
            )

            builder = pyc.TransactionBuilder(self.chain_query)
            (
                builder.add_script_input(
                    utxo=swap_utxo,
                    script=script,
                    redeemer=swap_redeemer,
                )
                .add_input_address(user_address)
                .add_output(updated_swap_utxo)
            )

            self.submit_tx_builder(builder, sk, user_address)

            print(
                f"""Updated swap contract liquidity:
                * {updated_amountB_for_swap_utxo} tlovelaces.
                * {updated_amountA_for_swap_utxo} tUSDT."""
            )

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
        amountB_precision = amountB * self.coin_precision

        swap_amountB_tADA = swap_utxo.output.amount.coin // 1000000
        user_amountB_tUSDT = self.available_user_tusdt(user_address)

        if amountB < 1:
            print(
                "The minimum sale quantity of tADA is 1. Current value {amountB} tADA."
            )

        elif amountB > swap_amountB_tADA:
            print(
                f"""Error! The swap contract doesn't have enough liquidity!
            Available: {swap_amountB_tADA} tADA."""
            )
        elif amountA > user_amountB_tUSDT:
            print(
                f"""Error! The user's wallet doesn't have enough liquidity!
            Available: {user_amountB_tUSDT} tUSDT."""
            )
        else:
            swap_redeemer = pyc.Redeemer(pyc.RedeemerTag.SPEND, SwapA(amountA))

            amount_for_the_user = pyc.transaction.Value(coin=amountB_precision)

            new_output_utxo_user = pyc.TransactionOutput(
                address=user_address, amount=amount_for_the_user
            )

            # swap utxo
            # updated_amountB_for_swap_utxo = swap_amountB_tADA - amountB
            # TODO change units to ada instead of lovelace
            updated_amountB_for_swap_utxo = swap_utxo.output.amount.coin - amountB

            updated_masset_for_swap_utxo = self.add_asset_swap(amountA)
            updated_masset_amount_for_swap_utxo = self.add_asset_swap_amount(amountA)

            amount_swap = pyc.transaction.Value(
                coin=updated_amountB_for_swap_utxo,
                multi_asset=updated_masset_for_swap_utxo,
            )

            new_output_swap = pyc.TransactionOutput(
                address=swap_address, amount=amount_swap, datum=pyc.PlutusData()
            )

            builder = pyc.TransactionBuilder(self.chain_query)
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
            self.submit_tx_builder(builder, sk, user_address)
            print(
                f"""Updated swap contract liquidity:
                * {updated_amountB_for_swap_utxo} tlovelaces.
                * {updated_masset_amount_for_swap_utxo} tUSDT."""
            )

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
        amountA = self.swap_b_with_a(amountB)
        available_user_tADA = self.available_user_tlovelace(user_address) // 1000000

        available_swap_tusdt = self.decrease_asset_swap_amount(0)
        if amountA < 1:
            print(
                f"The minimum sale quantity of tUSDT is 1. Current value {amountA} tUSDT."
            )
        elif amountB > available_user_tADA:
            print(
                f"""Error! The user's wallet doesn't have enough liquidity!
            Available: {available_user_tADA} tADA."""
            )
        elif amountA > available_swap_tusdt:
            print(
                f"""Error! The swap contract doesn't have enough liquidity!
            Available: {available_swap_tusdt} tUSDT."""
            )
        else:
            swap_redeemer = pyc.Redeemer(pyc.RedeemerTag.SPEND, SwapB(amountB))

            multi_asset_for_the_user = self.take_multi_asset_user(amountA)

            # Calculate minimum lovelace a transaction output needs to hold post alonzo
            min_lovelace_amount_for_the_user = pyc.transaction.Value(
                multi_asset=multi_asset_for_the_user
            )
            min_lovelace_output_utxo_user = pyc.TransactionOutput(
                address=user_address, amount=min_lovelace_amount_for_the_user
            )
            min_lovelace = pyc.utils.min_lovelace_post_alonzo(
                min_lovelace_output_utxo_user, self.chain_query
            )

            # Add the minimum lovelace amount to the user value
            amount_for_the_user = pyc.transaction.Value(
                coin=min_lovelace, multi_asset=multi_asset_for_the_user
            )

            # Add the value to the user UTXO
            new_output_utxo_user = pyc.TransactionOutput(
                address=user_address, amount=amount_for_the_user
            )

            amountB_at_swap_utxo = swap_utxo.output.amount.coin
            updated_amountB_for_swap_utxo = amountB_at_swap_utxo + (amountB * 1000000)

            updated_masset_for_swap_utxo = self.decrease_asset_swap(amountA)
            updated_masset_amount_for_swap_utxo = self.decrease_asset_swap_amount(
                amountA
            )

            amount_swap = pyc.transaction.Value(
                coin=updated_amountB_for_swap_utxo,
                multi_asset=updated_masset_for_swap_utxo,
            )

            new_output_swap = pyc.TransactionOutput(
                address=swap_address, amount=amount_swap, datum=pyc.PlutusData()
            )

            builder = pyc.TransactionBuilder(self.chain_query)
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

            print(f"Exchanging {amountB} tADA for {amountA} tUSDT.")
            self.submit_tx_builder(builder, sk, user_address)
            print(
                f"""Updated swap contract liquidity:
                * {updated_amountB_for_swap_utxo // 1000000 } tADA ({updated_amountB_for_swap_utxo} tlovelaces).
                * {updated_masset_amount_for_swap_utxo} tUSDT."""
            )

    def swap_b_with_a(self, amount_b: int) -> int:
        """Operation for swaping coin B with A"""
        exchange_rate_price = self.get_oracle_exchange_rate()
        precision = exchange_rate_price / self.coin_precision
        print(f"Oracle exchange rate: {precision} tADA/tUSDT")
        return (amount_b * self.coin_precision) // exchange_rate_price

    def swap_a_with_b(self, amount_a: int) -> int:
        """Operation for swaping coin A with B"""
        exchange_rate_price = self.get_oracle_exchange_rate()
        precision = exchange_rate_price / self.coin_precision
        print(f"Oracle exchange rate: {precision} tADA/tUSDT")
        return (amount_a * exchange_rate_price) // self.coin_precision

    def get_oracle_exchange_rate(self) -> int:
        """Get the oracle's feed exchange rate"""
        oracle_feed_utxo = self.get_oracle_utxo()
        oracle_inline_datum: GenericData = GenericData.from_cbor(
            oracle_feed_utxo.output.datum.cbor
        )
        return oracle_inline_datum.price_data.get_price()

    def get_oracle_timestamp(self) -> int:
        """Get the oracle's feed exchange rate"""
        oracle_feed_utxo = self.get_oracle_utxo()
        oracle_inline_datum: GenericData = GenericData.from_cbor(
            oracle_feed_utxo.output.datum.cbor
        )
        return oracle_inline_datum.price_data.get_timestamp()

    def get_oracle_expiration(self) -> int:
        """Get the oracle's feed exchange rate"""
        oracle_feed_utxo = self.get_oracle_utxo()
        oracle_inline_datum: GenericData = GenericData.from_cbor(
            oracle_feed_utxo.output.datum.cbor
        )
        return oracle_inline_datum.price_data.get_expiry()

    def get_oracle_utxo(self) -> pyc.UTxO:
        """Retrieve the oracle's feed UTXO using the NFT identifier."""
        oracle_utxos = self.chain_query.get_utxos(str(self.oracle_addr))
        oracle_utxo_nft = next(
            utxo
            for utxo in oracle_utxos
            if utxo.output.amount.multi_asset == self.oracle_nft
        )
        return oracle_utxo_nft

    def get_swap_utxo(self) -> pyc.UTxO:
        """Retrieve the UTxO for the swap using the NFT identifier"""
        swap_utxos = self.chain_query.get_utxos(str(self.swap_addr))
        swap_utxo_nft = next(
            x for x in swap_utxos if x.output.amount.multi_asset >= self.swap.swap_nft
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

    def decrease_asset_swap_amount(self, selling_amount: int) -> int:
        """The updated swap asset amount to be decreased at the address"""
        ((policy_id, assets),) = self.swap.coinA.to_shallow_primitive().items()
        ((asset, _),) = assets.to_shallow_primitive().items()

        swap_utxo = self.get_swap_utxo()
        m_assets = swap_utxo.output.amount.multi_asset.to_shallow_primitive()

        amountA = 0
        for swap_policy_id, assets in m_assets.items():
            if swap_policy_id == policy_id:
                for asset_name, amount in assets.items():
                    if asset_name == asset:
                        amountA = amount - selling_amount
        return amountA

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

    def add_asset_swap_amount(self, buying_amount: int) -> int:
        """The updated swap asset amount to be added at the address"""
        ((policy_id, assets),) = self.swap.coinA.to_shallow_primitive().items()
        ((asset, _),) = assets.to_shallow_primitive().items()

        swap_utxo = self.get_swap_utxo()
        m_assets = swap_utxo.output.amount.multi_asset.to_shallow_primitive()

        amountA = 0
        for swap_policy_id, assets in m_assets.items():
            if swap_policy_id == policy_id:
                for asset_name, amount in assets.items():
                    if asset_name == asset:
                        amountA = amount + buying_amount
        return amountA

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

    def available_user_pure_tlovelace(self, user_address: pyc.Address) -> int:
        """Get the available user's pure lovelace amount"""
        amount = 0
        for utxo in self.chain_query.utxos(str(user_address)):
            if not utxo.output.amount.multi_asset:
                amount += utxo.output.amount.coin
        return amount

    def available_user_tlovelace(self, user_address: pyc.Address) -> int:
        """Get the available user's  lovelace amount"""
        amount = 0
        for utxo in self.chain_query.utxos(str(user_address)):
            amount += utxo.output.amount.coin
        return amount

    def available_user_tusdt(self, user_address: pyc.Address) -> int:
        amount_asset = 0
        ((policy_id, assets),) = self.swap.coinA.to_shallow_primitive().items()
        ((asset, _),) = assets.to_shallow_primitive().items()

        for utxo in self.chain_query.utxos(str(user_address)):
            m_assets = utxo.output.amount.multi_asset.to_shallow_primitive()
            for user_policy_id, assets in m_assets.items():
                if user_policy_id == policy_id:
                    for asset_name, amount in assets.items():
                        if asset_name == asset:
                            amount_asset += amount
        return amount_asset

    def submit_tx_builder(
        self,
        builder: pyc.TransactionBuilder,
        sk: pyc.PaymentSigningKey,
        address: pyc.Address,
    ):
        """Adds collateral and signer to tx, sign and submit tx."""
        non_nft_utxo = self.chain_query.find_collateral(address)

        if non_nft_utxo is None:
            self.chain_query.create_collateral(address, sk)
            non_nft_utxo = self.chain_query.find_collateral(address)

        builder.collaterals.append(non_nft_utxo)
        # print(builder)
        signed_tx = builder.build_and_sign([sk], change_address=address)
        self.chain_query.submit_tx_without_print(signed_tx)
