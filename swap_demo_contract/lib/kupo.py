"""Kupo context to query on-chain data"""

from typing import Any, Dict, List, Optional, Tuple, Union

import cbor2
import pycardano as pyc
from cachetools import LRUCache
from pycardano.hash import TransactionId

from swap_demo_contract.lib.api import Api


class KupoContext(Api):
    """Kupo Class"""

    def __init__(self, kupo_url):
        self.api_url = kupo_url
        self.datum_cache = LRUCache(maxsize=100)

    def _try_fix_script(
        self, scripth: str, script: Union[pyc.PlutusV1Script, pyc.PlutusV2Script]
    ) -> Union[pyc.PlutusV1Script, pyc.PlutusV2Script]:
        if str(pyc.script_hash(script)) == scripth:
            return script
        new_script = script.__class__(cbor2.loads(script))
        if str(pyc.script_hash(new_script)) == scripth:
            return new_script
        raise ValueError("Cannot recover script from hash.")

    def _extract_asset_info(
        self,
        asset_hash: str,
    ) -> Tuple[str, pyc.ScriptHash, pyc.AssetName]:  # noqa
        split_result = asset_hash.split(".")

        if len(split_result) == 1:
            policy_hex, asset_name_hex = split_result[0], ""
        elif len(split_result) == 2:
            policy_hex, asset_name_hex = split_result
        else:
            raise ValueError(f"Unable to parse asset hash: {asset_hash}")

        policy = pyc.ScriptHash.from_primitive(policy_hex)
        asset_name = pyc.AssetName.from_primitive(asset_name_hex)

        return policy_hex, policy, asset_name

    async def _get_datum_from_kupo(self, datum_hash: str) -> Optional[pyc.RawCBOR]:
        """Get datum from Kupo.

        Args:
            datum_hash (str): A datum hash.

        Returns:
            Optional[RawCBOR]: A datum.
        """
        datum = self.datum_cache.get(datum_hash, None)

        if datum is not None:
            return datum

        if self.api_url is None:
            raise AssertionError(
                "api_url object attribute has not been assigned properly."
            )

        kupo_datum_url = "/datums/" + datum_hash
        result = await self._get(path=kupo_datum_url)
        datum_result = result.json
        if datum_result and datum_result["datum"] != datum_hash:
            datum = pyc.RawCBOR(bytes.fromhex(datum_result["datum"]))

        self.datum_cache[datum_hash] = datum
        return datum

    async def get_metadata_cbor(
        self, tx_id: TransactionId, slot: int
    ) -> Optional[pyc.RawCBOR]:
        """Get metadata cbor from Kupo.

        Args:
            tx_id (TransactionId): Transaction id for metadata to query.
            slot (int): Slot number.

        Returns:
            Optional[RawCBOR]: Metadata cbor."""
        url_path = f"/metadata/{slot}?transaction_id={tx_id}"
        result = await self._get(path=url_path)
        payload = result.json
        if not payload or len(payload) == 0 or "raw" not in payload[0]:
            return None

        return pyc.RawCBOR(bytes.fromhex(payload[0]["raw"]))

    async def utxos_kupo(self, address: str) -> List[pyc.UTxO]:
        """Get all UTxOs associated with an address with Kupo.
        Since UTxO querying will be deprecated from Ogmios in next
        major release: https://ogmios.dev/mini-protocols/local-state-query/.

        Args:
            address (str): An address encoded with bech32.

        Returns:
            List[UTxO]: A list of UTxOs.
        """
        utxos_with_slot = await self.utxos_created_at_kupo(address)
        return [utxo for utxo, _ in utxos_with_slot]

    async def utxos_created_at_kupo(self, address: str) -> List[Tuple[pyc.UTxO, int]]:
        """Get all UTxOs associated with an address with Kupo
        together with absolute slot number they were created at.
        Since UTxO querying will be deprecated from Ogmios in next
        major release: https://ogmios.dev/mini-protocols/local-state-query/.

        Args:
            address (str): An address encoded with bech32.

        Returns:
            List[Tuple[pyc.UTxO, int]]: A list of UTxOs and their slot timestamps.
        """
        if self.api_url is None:
            raise AssertionError(
                "api_url object attribute has not been assigned properly."
            )

        kupo_utxo_url = "/matches/" + address + "?unspent"
        results = await self._get(path=kupo_utxo_url)

        if results.json is None:
            raise AssertionError("Error")
        utxos = await self._unpack_outputs(address, results.json)

        return utxos

    async def outputs_created_after(
        self, address: str, created_after_slot: int
    ) -> List[Tuple[pyc.UTxO, int]]:
        """Get all UTxOs associated with an address with Kupo
        together with absolute slot number they were created at.
        Only fetch results that were created at and after the given slot,
        sorted by slot most recent results are returned first.

        Args:
            address (str): An address encoded with bech32.
            created_after_slot (int): Point after we get relevant results

        Returns:
            List[Tuple[pyc.UTxO, int]]: A list of UTxOs and their slot timestamps.
        """
        if self.api_url is None:
            raise AssertionError(
                "api_url object attribute has not been assigned properly."
            )

        kupo_utxo_url = (
            "/matches/" + address + "?spent" + f"&created_after={created_after_slot}"
        )
        results = await self._get(path=kupo_utxo_url)

        if results.json is None:
            raise AssertionError("Error")
        utxos = await self._unpack_outputs(address, results.json)

        return utxos

    async def _unpack_outputs(
        self, address: str, api_response: List[Any]
    ) -> List[Tuple[pyc.UTxO, int]]:
        utxos: List[Tuple[pyc.UTxO, int]] = []

        for result in api_response:
            tx_id = result["transaction_id"]
            index = result["output_index"]

            created_at_slot = result["created_at"]["slot_no"]

            tx_in = pyc.TransactionInput.from_primitive([tx_id, index])

            lovelace_amount = result["value"]["coins"]

            script = None
            script_hash = result.get("script_hash", None)
            if script_hash:
                kupo_script_url = "/scripts/" + script_hash
                script_resp = await self._get(path=kupo_script_url)
                script = script_resp.json
                if script["language"] == "plutus:v2":
                    script = pyc.PlutusV2Script(bytes.fromhex(script["script"]))  # noqa
                    script = self._try_fix_script(script_hash, script)
                elif script["language"] == "plutus:v1":
                    script = pyc.PlutusV1Script(bytes.fromhex(script["script"]))  # noqa
                    script = self._try_fix_script(script_hash, script)
                else:
                    raise ValueError("Unknown plutus script type")

            datum = None
            datum_hash = (
                pyc.DatumHash.from_primitive(result["datum_hash"])
                if result["datum_hash"]
                else None
            )
            if datum_hash and result.get("datum_type", "inline"):
                datum = await self._get_datum_from_kupo(result["datum_hash"])
                if datum:
                    datum_hash = None

            if not result["value"]["assets"]:
                tx_out = pyc.TransactionOutput(
                    pyc.Address.from_primitive(address),
                    amount=lovelace_amount,
                    datum_hash=datum_hash,
                    datum=datum,
                    script=script,
                )
            else:
                multi_assets = pyc.MultiAsset()

                for asset, quantity in result["value"]["assets"].items():
                    policy_hex, policy, asset_name_hex = self._extract_asset_info(asset)
                    multi_assets.setdefault(policy, pyc.Asset())[
                        asset_name_hex
                    ] = quantity

                tx_out = pyc.TransactionOutput(
                    pyc.Address.from_primitive(result["address"]),
                    amount=pyc.Value(lovelace_amount, multi_assets),
                    datum_hash=datum_hash,
                    datum=datum,
                    script=script,
                )
            utxos.append((pyc.UTxO(tx_in, tx_out), created_at_slot))

        return utxos
