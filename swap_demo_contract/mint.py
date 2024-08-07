"""offchain code containing mint class"""

from dataclasses import dataclass

from charli3_offchain_core.chain_query import ChainQuery
from pycardano import (
    Address,
    AlonzoMetadata,
    AuxiliaryData,
    ExecutionUnits,
    Metadata,
    MultiAsset,
    PaymentSigningKey,
    PaymentVerificationKey,
    PlutusData,
    PlutusV2Script,
    Redeemer,
    RedeemerTag,
    TransactionBuilder,
    TransactionOutput,
    Value,
    plutus_script_hash,
    utils,
)


@dataclass
class MintToken(PlutusData):
    CONSTR_ID = 0


class Mint:
    def __init__(
        self,
        context: ChainQuery,
        signing_key: PaymentSigningKey,
        user_address: Address,
        swap_address: Address,
        plutus_v2_mint_script: PlutusV2Script,
    ) -> None:
        self.context = context
        self.signing_key = signing_key
        self.user_address = user_address
        self.swap_address = swap_address
        self.minting_script_plutus_v2 = plutus_v2_mint_script

    def mint_nft_with_script(self):
        """mint tokens with plutus v2 script"""
        policy_id = plutus_script_hash(self.minting_script_plutus_v2)
        asset_name = "SWAP3-PYCARDANO"
        nft_swap = MultiAsset.from_primitive(
            {
                policy_id.payload: {
                    bytes(asset_name, "utf-8"): 1,
                }
            }
        )

        metadata = {
            0: {
                policy_id.payload.hex(): {
                    "Swap": {
                        "description": "This is a test token",
                        "name": asset_name,
                    }
                }
            }
        }

        print(
            f"Swap's NFT information:\nCurrency Symbol (Policy ID): {policy_id.payload.hex()}\nToken Name: {asset_name}"
        )
        # Place metadata in AuxiliaryData, the format acceptable by a transaction.
        auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(metadata)))

        # Create a transaction builder
        builder = TransactionBuilder(self.context)

        # Add our own address as the input address
        builder.add_input_address(self.user_address)

        # Add minting script with an empty datum and a minting redeemer
        builder.add_minting_script(
            self.minting_script_plutus_v2,
            redeemer=Redeemer(
                RedeemerTag.MINT, MintToken(), ExecutionUnits(1000000, 300979640)
            ),
        )

        # Set nft we want to mint
        builder.mint = nft_swap

        # Set transaction metadata
        builder.auxiliary_data = auxiliary_data

        min_lovelace_amount = Value(multi_asset=nft_swap)

        min_lovelace_output_utxo = TransactionOutput(
            address=self.swap_address,
            amount=min_lovelace_amount,
            datum=PlutusData(),
        )
        min_lovelace = utils.min_lovelace_post_alonzo(
            min_lovelace_output_utxo, self.context
        )

        # Add the minimum lovelace amount to the user value
        value_swap_utxo = Value(coin=min_lovelace, multi_asset=nft_swap)
        # Send the NFT to our own address
        swap_nft_output = TransactionOutput(
            address=self.swap_address, amount=value_swap_utxo, datum=PlutusData()
        )

        builder.add_output(swap_nft_output)

        self.submit_tx_builder(builder)

    def submit_tx_builder(self, builder: TransactionBuilder):
        """Adds collateral and signer to tx, sign and submit tx."""
        non_nft_utxo = self.context.find_collateral(self.user_address)

        if non_nft_utxo is None:
            self.context.create_collateral(self.user_address, self.signing_key)
            non_nft_utxo = self.context.find_collateral(self.user_address)

        builder.collaterals.append(non_nft_utxo)
        signed_tx = builder.build_and_sign(
            [self.signing_key], change_address=self.user_address
        )
        self.context.submit_tx_without_print(signed_tx)
