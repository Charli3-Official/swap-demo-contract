"""Oracle user related transactions"""

from copy import deepcopy
from typing import Optional, Union

from charli3_offchain_core.chain_query import ChainQuery
from charli3_offchain_core.utils.logging_config import logging
from pycardano import (
    Address,
    AlonzoMetadata,
    Asset,
    AssetName,
    AuxiliaryData,
    ExtendedSigningKey,
    Metadata,
    MultiAsset,
    Network,
    PaymentExtendedSigningKey,
    PaymentSigningKey,
    PaymentVerificationKey,
    Redeemer,
    ScriptHash,
    TransactionBuilder,
    TransactionInput,
)

from .dynamic_rewards import DynamicRewardsMixin
from .redeemers import OdvRequest

logger = logging.getLogger("Oracle-User")


class OracleUser(DynamicRewardsMixin):
    """
    Oracle user related transactions
    """

    def __init__(
        self,
        network: Network,
        chain_query: ChainQuery,
        signing_key: Union[
            ExtendedSigningKey, PaymentExtendedSigningKey, PaymentSigningKey
        ],
        verification_key: PaymentVerificationKey,
        stake_key: Optional[PaymentVerificationKey],
        oracle_addr: str,
        aggstate_nft: MultiAsset,
        reference_script_input: Optional[TransactionInput],
        c3_token_hash: ScriptHash,
        c3_token_name: AssetName,
        dynamic_payment_oracle_addr: Optional[Address],
        dynamic_payment_oracle_nft: Optional[MultiAsset],
    ):
        super().__init__(
            network=network,
            chain_query=chain_query,
            oracle_addr=oracle_addr,
            aggstate_nft=aggstate_nft,
            oracle_rate_addr=dynamic_payment_oracle_addr,
            oracle_rate_nft=dynamic_payment_oracle_nft,
        )

        self.signing_key = signing_key
        self.pub_key_hash = verification_key.hash()
        if stake_key:
            self.stake_key_hash = stake_key.hash()
        else:
            self.stake_key_hash = None
        self.address = Address(
            payment_part=self.pub_key_hash,
            staking_part=self.stake_key_hash,
            network=self.network,
        )

        self.oracle_script_hash = self.oracle_addr.payment_part
        self.reference_script_input = reference_script_input
        self.c3_token_hash = c3_token_hash
        self.c3_token_name = c3_token_name

    async def send_odv_request(self, funds: int):
        """
        send ODV request by adding funds (payment token) to aggstate UTxO of oracle script.
        """

        aggstate_utxo, aggstate_datum = await self._get_aggstate_utxo_and_datum()
        script_utxo = await self.chain_query.get_reference_script_utxo(
            self.oracle_addr, self.reference_script_input, self.oracle_script_hash
        )

        assert funds > 0, "Funds should be greater than 0."
        recommended_funds = await self.calc_recommended_funds_amount(aggstate_datum)
        if funds < recommended_funds:
            logger.warn(f"Recommended funds amount is {recommended_funds}, got {funds}")

        # prepare datums, redeemers and new node utxos for eligible nodes
        builder = TransactionBuilder(self.chain_query.context)
        builder.add_script_input(
            aggstate_utxo,
            script=script_utxo,
            redeemer=Redeemer(OdvRequest()),
        )

        aggstate_tx_output = deepcopy(aggstate_utxo.output)

        # check if c3 token already exist in aggstate utxo
        if (
            self.c3_token_hash in aggstate_tx_output.amount.multi_asset
            and self.c3_token_name
            in aggstate_tx_output.amount.multi_asset[self.c3_token_hash]
        ):
            aggstate_tx_output.amount.multi_asset[self.c3_token_hash][
                self.c3_token_name
            ] += funds
        else:
            c3_asset = MultiAsset(
                {self.c3_token_hash: Asset({self.c3_token_name: funds})}
            )
            aggstate_tx_output.amount.multi_asset += c3_asset
        builder.add_output(aggstate_tx_output)

        metadata = {413: "charli3-odv-oracle-request"}
        auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(metadata)))
        builder.auxiliary_data = auxiliary_data

        await self.chain_query.submit_tx_builder(
            builder, self.signing_key, self.address
        )
