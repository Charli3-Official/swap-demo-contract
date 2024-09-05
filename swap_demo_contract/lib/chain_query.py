"""This module contains the ChainQuery class, which is used to query the blockchain."""

import asyncio
from typing import List, Literal, Mapping, Optional, Tuple, Union

import cbor2
from blockfrost import ApiError
from pycardano import (
    Address,
    BlockFrostChainContext,
    ExtendedSigningKey,
    GenesisParameters,
    InsufficientUTxOBalanceException,
    OgmiosV6ChainContext,
    PaymentSigningKey,
    PlutusV2Script,
    RawCBOR,
    ScriptHash,
    Transaction,
    TransactionBuilder,
    TransactionId,
    TransactionInput,
    TransactionOutput,
    UTxO,
    UTxOSelectionException,
    VerificationKeyWitness,
    plutus_script_hash,
)


class KupoContext:
    async def utxos_kupo(self, address: str) -> List[UTxO]:
        pass


class ChainQuery:
    """chainQuery methods"""

    def __init__(
        self,
        blockfrost_context: BlockFrostChainContext = None,
        ogmios_context: OgmiosV6ChainContext = None,
        kupo_context: Optional[KupoContext] = None,
        oracle_address: str = None,
        is_local_testnet: bool = False,
    ):
        if blockfrost_context is None and ogmios_context is None:
            raise ValueError("At least one of the chain contexts must be provided.")

        self.blockfrost_context = blockfrost_context
        self.ogmios_context = ogmios_context
        self.kupo_context = kupo_context
        self.oracle_address = oracle_address
        self.context = blockfrost_context if blockfrost_context else ogmios_context
        self.is_local_testnet = is_local_testnet

        self._datum_cache = {}

    async def get_utxos(self, address: Union[str, Address, None] = None) -> List[UTxO]:
        """
        get utxos from oracle address.

        Args:
            address (str, Address, optional): The address to get the utxos from. Defaults to None.

        Returns:
            List[UTxO]: The list of utxos.
        """
        if address is None:
            address = self.oracle_address
        if self.blockfrost_context is not None:
            print("Getting utxos from blockfrost")
            return self.blockfrost_context.utxos(str(address))
        if self.ogmios_context is not None:
            print("Getting utxos from ogmios")
            return await self.kupo_context.utxos_kupo(str(address))

    async def get_reference_script_utxo(
        self,
        oracle_addr: Address,
        reference_script_input: TransactionInput,
        oracle_script_hash: ScriptHash,
    ) -> UTxO:
        """function to get reference script utxo
        Args:
            oracle_addr (Address): oracle address
            reference_script_input (TransactionInput): reference script input
            oracle_script_hash (ScriptHash): oracle script hash

        Returns:
            UTxO: utxo with plutus script
        """
        utxos = await self.get_utxos(oracle_addr)
        if len(utxos) > 0:
            for utxo in utxos:
                if utxo.input == reference_script_input:
                    if isinstance(self.context, BlockFrostChainContext):
                        script = await self.get_plutus_script(oracle_script_hash)
                        utxo.output.script = script
                    return utxo

    async def get_plutus_script(self, scripthash: ScriptHash) -> PlutusV2Script:
        """
        function to get plutus script and verify it's script hash

        Args:
            scripthash (ScriptHash): script hash of plutus script

        Returns:
            PlutusV2Script: plutus script if script hash matches else None

        """
        if isinstance(self.context, BlockFrostChainContext):
            plutus_script = self.context._get_script(str(scripthash))
            if plutus_script_hash(plutus_script) != scripthash:
                plutus_script = PlutusV2Script(cbor2.dumps(plutus_script))
            if plutus_script_hash(plutus_script) == scripthash:
                return plutus_script

            print("script hash mismatch")

        if isinstance(self.context, OgmiosV6ChainContext):
            print("ogmios context does not support get_script")
            return None

    async def submit_tx_builder(
        self,
        builder: TransactionBuilder,
        signing_key: Union[PaymentSigningKey, ExtendedSigningKey],
        address: Address,
        user_defined_expense: int = 0,
    ) -> Tuple[str, Transaction]:
        """adds collateral and signers to tx, sign and submit tx.

        Args:
            builder (TransactionBuilder): transaction builder
            signing_key (Union[PaymentSigningKey, ExtendedSigningKey]):
        signing key
            address (Address): address belonging to signing_key, used for
        balancing, collateral and change
            user_defined_fee: When not equal to 0, a UTxO with the specified
        ADA amount is searched for to cover blockchain fees.

        Returns:
            Tuple[str, Transaction]: The status of the transaction and the
            transaction object.
        """
        # The minimum suggested amount is 15 ADA for the Aggregate transaction,
        # but ~1.3 ADA is commonly used for covering fees.
        # The aggregate tx is considered the most costly transaction.

        if user_defined_expense > 0:
            builder = await self.process_common_inputs(
                builder, address, signing_key, user_defined_expense
            )
        else:
            builder = await self.process_common_inputs(builder, address, signing_key)

        signed_tx = builder.build_and_sign(
            [signing_key],
            change_address=address,
            auto_validity_start_offset=0,
            auto_ttl_offset=120,
        )

        try:
            return await self.submit_tx_with_print(signed_tx)
        except Exception as err:
            print(f"Error submitting transaction: {str(err)}")
            return "collateral error", signed_tx
        except (InsufficientUTxOBalanceException, UTxOSelectionException) as exc:
            print(f"Insufficient Funds in the wallet. {str(exc)}")
            return "insufficient funds", signed_tx
        except Exception as err:
            print("Error submitting transaction: {str(err)}")
            return "error", signed_tx

    async def process_common_inputs(
        self,
        builder: TransactionBuilder,
        address: Address,
        signing_key: Union[PaymentSigningKey, ExtendedSigningKey],
        user_defined_expenses: int = 0,
    ) -> TransactionBuilder:
        """process common inputs for transaction builder

        Args:
            builder (TransactionBuilder): transaction builder
            address (Address): address belonging to signing_key, used for balancing, collateral and change
            signing_key (Union[PaymentSigningKey, ExtendedSigningKey]): signing key
            user_defined_expenses (int): Quantity to cover transaction fees and collateral
        (Default is 0 if not provided, as it will automatically obtain input UTxOs.)

        Returns:
            TransactionBuilder: transaction builder
        """

        # Add input address for tx balancing,
        if user_defined_expenses != 0:
            # Include an input UTXO that exclusively contains ADA (tx fees).
            utxo_for_tx_fees = await self.utxo_for_tx_fees(
                address, signing_key, user_defined_expenses
            )
            builder.add_input(utxo_for_tx_fees)
            builder.required_signers = [address.payment_part]
            return builder
        else:
            # this could include any address utxos and spend them for tx fees
            builder.add_input_address(address)

            # Fresh output for convenience of using for collateral in future
            # **NOTE** This value should align with the user_defined_expenses in the
            # aggregation transaction, as the node executes the aggregation, so the
            # value should cover both collateral and transaction fees.
            # Under normal circumstances, the node updates its value and creates
            # the output  for covering the aggregation, taking advantage of its
            # low memory consumption.
            builder.add_output(TransactionOutput(address, 30000000))

            non_nft_utxo = await self.get_or_create_collateral(address, signing_key)

            if non_nft_utxo is not None:
                builder.collaterals.append(non_nft_utxo)
                builder.required_signers = [address.payment_part]

                return builder

        raise Exception("Unable to find or create collateral.")

    async def get_or_create_collateral(
        self,
        address: Address,
        signing_key: Union[PaymentSigningKey, ExtendedSigningKey],
        collateral_amount: int = 30000000,
    ) -> UTxO:
        """get or create collateral
        Args:
            address (Address): address belonging to signing_key, used for balancing, collateral and change
            signing_key (Union[PaymentSigningKey, ExtendedSigningKey]): signing key
        Returns:
            UTxO: utxo
        """
        non_nft_utxo = await self.find_collateral(address, collateral_amount)

        if non_nft_utxo is None:
            await self.create_collateral(address, signing_key, collateral_amount)
            non_nft_utxo = await self.find_collateral(address, collateral_amount)

        return non_nft_utxo

    async def find_collateral(
        self, target_address: Union[str, Address], required_amount: int
    ) -> UTxO:
        """
        This method finds an UTxO  for the given address with the
        following requirements:
        - required_amount - 1 <= required_amunt < required_amount + 1.
        - no multi asset
        Args:
            target_address (str, Address): The address to find the collateral for.

        Returns:
            UTxO: The  utxo covering the fees if found, None otherwise.

        Note: When used to locate the UTXO for covering expenses in the
        aggregation transaction:
        The aggregation transaction typically consumes approximately 1.3 ADA.
        As we are consolidating collateral and transaction fees into a single UTxO,
        we must ensure that the UTxO used contains at most the required ADA amount.
        We limit the amount to a range of plus and minus 1 because when adding
        collateral, we aim to avoid exposing ourselves to substantial
        potential losses.
        """
        try:
            utxos = await self.get_utxos(address=target_address)
            for utxo in utxos:
                # A collateral should contain no multi asset
                if not utxo.output.amount.multi_asset:
                    if utxo.output.amount < (required_amount + 10000000):
                        if utxo.output.amount.coin >= (required_amount - 1000000):
                            return utxo
        except ApiError as err:
            if err.status_code == 404:
                print("No utxos for tx fees found")
                raise err

            print(
                "Requirements for tx fees couldn't be satisfied. need an utxo of >= 2 %s",
                err,
            )
        return None

    async def create_collateral(
        self,
        target_address: Union[str, Address],
        skey: Union[PaymentSigningKey, ExtendedSigningKey],
        required_amount: int,
    ) -> None:
        """
        This method creates a collateral utxo for the given address with the following requirements:
        - amount = 5000000 lovelaces

        Args:
            target_address (str, Address): The address to create the collateral for.
            skey (PaymentSigningKey, ExtendedSigningKey): The signing key to sign the transaction.
            required_amount: The required ADA amount in the UTxO.

        Returns:
            None
        """
        print("creating collateral UTxO.")
        collateral_builder = TransactionBuilder(self.context)

        collateral_builder.add_input_address(target_address)
        collateral_builder.add_output(
            TransactionOutput(target_address, required_amount)
        )

        await self.submit_tx_with_print(
            collateral_builder.build_and_sign(
                [skey],
                target_address,
                auto_validity_start_offset=0,
                auto_ttl_offset=120,
            )
        )

    async def submit_tx_with_print(self, tx: Transaction) -> Tuple[str, Transaction]:
        """
        This method submits a transaction to the chain and prints the transaction ID.

        Args:
            tx: The transaction to submit.

        Returns:
            Tuple[str, Transaction]: The status of the transaction and the transaction object.
        """
        print(f"Submitting transaction: {str(tx.id)}")
        print(f"tx: {tx}")

        if self.ogmios_context is not None:
            print("Submitting tx with ogmios")
            self.ogmios_context.submit_tx(tx.to_cbor())
        elif self.blockfrost_context is not None:
            print("Submitting tx with blockfrost")
            self.blockfrost_context.submit_tx(tx.to_cbor())

        status, _ = await self.wait_for_tx(str(tx.id))
        return status, tx

    async def wait_for_tx(
        self, tx_id: TransactionId
    ) -> Tuple[str, Optional[Transaction]]:
        """
        Waits for a transaction with the given ID to be confirmed.
        Retries the API call every 20 seconds if the transaction is not found.
        Stops retrying after a certain number of attempts.

        Args:
            tx_id (TransactionId): The transaction ID to wait for.

        Returns:
            Tuple[str, Optional[Transaction]]: The status of the transaction and
            the transaction object if found, None otherwise.
        """

        async def _wait_for_tx(
            context: Union[BlockFrostChainContext, OgmiosV6ChainContext],
            tx_id: TransactionId,
            check_fn: callable,
            retries: int = 0,
            max_retries: int = 10,
        ) -> Tuple[str, Optional[Transaction]]:
            """Wait for a transaction to be confirmed.

            Args:
                context (Union[BlockFrostChainContext, OgmiosV6ChainContext]): The chain context to use. # pylint: disable=line-too-long
                tx_id (TransactionId): The transaction ID to wait for.
                check_fn (callable): The function to use to check if the transaction is confirmed.
                retries (int, optional): The number of retries. Defaults to 0.
                max_retries (int, optional): The maximum number of retries. Defaults to 10.

            Returns:
                The transaction object if found, None otherwise.
            """
            status = "initiated"
            transaction = None
            while retries < max_retries:
                try:
                    transaction = await check_fn(context, tx_id)
                    if transaction:
                        print(f"Transaction submitted with tx_id: {str(tx_id)}")
                        status = "success"
                        return status, transaction

                except ApiError as err:
                    if err.status_code == 404:
                        pass
                    else:
                        status = "error: " + str(err)
                        return status, None

                except Exception as err:
                    status = "error: " + str(err)
                    return status, None

                wait_time = 20
                print(
                    f"Waiting for transaction confirmation: {str(tx_id)}. Retrying in {wait_time} seconds",
                )
                retries += 1
                await asyncio.sleep(wait_time)

            print(f"Transaction not found after {max_retries} retries. Giving up.")
            return status, transaction

        async def check_blockfrost(
            context: BlockFrostChainContext, tx_id: TransactionId
        ) -> Transaction:
            """
            Check if the transaction is confirmed using the blockfrost API.

            Args:
                context (BlockFrostChainContext): The chain context to use.
                tx_id (TransactionId): The transaction ID to wait for.

            Returns:
                The transaction object if found, None otherwise.
            """
            return context.api.transaction(tx_id)

        async def check_ogmios(
            context: OgmiosV6ChainContext, tx_id: TransactionId
        ) -> Transaction:
            """
            Check if the transaction is confirmed using the ogmios API.

            Args:
                context (OgmiosV6ChainContext): The chain context to use.
                tx_id (TransactionId): The transaction ID to wait for.

            Returns:
                The transaction object if found, None otherwise.
            """
            response = context._query_utxos_by_tx_id(tx_id, 0)
            return response if response != [] else None

        if self.ogmios_context:
            return await _wait_for_tx(self.ogmios_context, tx_id, check_ogmios)
        if self.blockfrost_context:
            return await _wait_for_tx(self.blockfrost_context, tx_id, check_blockfrost)
