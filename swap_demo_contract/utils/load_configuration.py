from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from pycardano import (
    Address,
    AssetName,
    ExtendedSigningKey,
    HDWallet,
    Network,
    OgmiosV6ChainContext,
    PaymentVerificationKey,
    ScriptHash,
)
from pycardano.backend.kupo import KupoChainContextExtension

from swap_demo_contract.lib.chain_query import ChainQuery


def load_yaml_config(path: Path | str) -> dict[str, Any]:
    """Load and process YAML configuration file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data


def parse_ws_url(url: str) -> tuple[str, int, bool]:
    """Parse WebSocket URL into host, port, and secure flag."""
    parsed = urlparse(url)

    # Determine if secure based on scheme
    secure = parsed.scheme in ("wss", "https")

    # Extract host without port if port is in the URL
    host = parsed.hostname or parsed.netloc.split(":")[0]
    port = parsed.port or (443 if secure else 1337)
    return host, port, secure


@dataclass
class NodeNetworkId:
    """Network identification for oracle node."""

    root_url: str
    pub_key: str

    @classmethod
    def from_dict(cls, data: dict) -> "NodeNetworkId":
        """Create node config from dictionary."""
        return cls(
            root_url=data["root_url"],
            pub_key=data["pub_key"],
        )


@dataclass
class OdvClientConfig:
    """Complete Odv Client configuration."""

    address: Address
    policy_id: ScriptHash
    nft_aggstate: AssetName
    payment_token_policy_id: ScriptHash
    payment_token_asset_name: AssetName
    odv_validity_length: int  # milliseconds
    nodes: list[NodeNetworkId]

    @classmethod
    def from_yaml(cls, path: Path | str) -> "OdvClientConfig":
        """Load configuration from YAML file."""
        data = load_yaml_config(path)
        odv = data.get("odv_contract")
        if odv is None:
            raise ValueError
        return cls(
            address=Address.from_primitive(odv.get("address")),
            policy_id=ScriptHash.from_primitive(odv.get("policy_id")),
            nft_aggstate=AssetName((odv.get("nft").get("aggstate")).encode()),
            payment_token_policy_id=ScriptHash.from_primitive(
                odv.get("payment_token").get("policy_id")
            ),
            payment_token_asset_name=AssetName(
                odv.get("payment_token").get("asset_name").encode()
            ),
            odv_validity_length=int(odv.get("odv_validity_length")),
            nodes=[NodeNetworkId.from_dict(node) for node in odv["nodes"]],
        )


@dataclass
class EnvironmentConfig:
    chain_query: ChainQuery

    @classmethod
    def from_yaml(cls, path: Path | str, args) -> "EnvironmentConfig":
        data = load_yaml_config(path)
        ogmios_kupo = data.get("environment").get("ogmios_kupo")
        conf_network = data.get("environment").get("network")
        if not ogmios_kupo:
            raise ValueError

        network = Network.TESTNET
        if args.environment == "mainnet" or conf_network == "mainnet":
            network = Network.MAINNET

        if args.connection == "blockfrost":
            print("TODO")
        elif args.connection == "ogmios":
            ogmios_url = ogmios_kupo.get("ogmios_url")
            host, port, secure = parse_ws_url(ogmios_url)
            kupo_url = ogmios_kupo.get("kupo_url")

            ogmios_context = OgmiosV6ChainContext(
                host=host, port=port, secure=secure, network=network
            )
            kupo_context = KupoChainContextExtension(
                ogmios_context,
                kupo_url,
            )
            chain_query = ChainQuery(kupo_ogmios_context=kupo_context)
            return cls(chain_query)


@dataclass
class WalletConfig:
    address: Address
    spend_vk: PaymentVerificationKey
    stake_vk: PaymentVerificationKey
    esigning_key: ExtendedSigningKey

    @classmethod
    def from_yaml(cls, path: Path | str, args) -> "Wallet":
        data = load_yaml_config(path)
        wallet = data.get("wallet")
        if wallet is None:
            raise ValueError

        network = Network.TESTNET
        if args.environment == "mainnet":
            network = Network.MAINNET

        mnemonic_24 = wallet.get("MNEMONIC_24")

        hdwallet = HDWallet.from_mnemonic(mnemonic_24)
        hdwallet_spend = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
        extended_signing_key = ExtendedSigningKey.from_hdwallet(hdwallet_spend)

        spend_public_key = hdwallet_spend.public_key
        spend_vk = PaymentVerificationKey.from_primitive(spend_public_key)

        hdwallet_stake = hdwallet.derive_from_path("m/1852'/1815'/0'/2/0")
        stake_public_key = hdwallet_stake.public_key
        stake_vk = PaymentVerificationKey.from_primitive(stake_public_key)

        address = Address(
            payment_part=spend_vk.hash(), staking_part=stake_vk.hash(), network=network
        )

        return cls(address, spend_vk, stake_vk, extended_signing_key)


@dataclass
class SwapConfig:
    """Class Swap for interact with the assets in the swap operation
    and identify the Swap's NFTs

    Attribures:
        swap_nft: The NFT identifier of the swap utxo
        coinA: Asset
    """

    address: Address
    policy_id: ScriptHash
    nft_swap: AssetName
    token_a_policy_id: ScriptHash
    token_a_asset_name: AssetName
    token_b_policy_id: ScriptHash | None
    token_b_asset_name: AssetName | None

    @classmethod
    def from_yaml(cls, path: Path | str) -> "SwapConfig":
        data = load_yaml_config(path)
        swap = data.get("swap_contract")
        if swap is None:
            raise ValueError
        b_policy_id = swap.get("token_b").get("policy_id")
        b_asset_name = swap.get("token_b").get("asset_name")
        return cls(
            address=Address.from_primitive(swap.get("address")),
            policy_id=ScriptHash.from_primitive(swap.get("policy_id")),
            nft_swap=AssetName(swap.get("nft").get("swap").encode()),
            token_a_policy_id=ScriptHash.from_primitive(
                swap.get("token_a").get("policy_id")
            ),
            token_a_asset_name=AssetName(
                swap.get("token_a").get("asset_name").encode()
            ),
            token_b_policy_id=(
                ScriptHash.from_primitive(b_policy_id) if b_policy_id else None
            ),
            token_b_asset_name=(
                AssetName(b_asset_name.encode()) if b_asset_name else None
            ),
        )
