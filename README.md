
<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a name="readme-top"></a>
<!--
*** Thanks for checking out the Best-README-Template. If you have a suggestion
*** that would make this better, please fork the repo and create a pull request
*** or simply open an issue with the tag "enhancement".
*** Don't forget to give the project a star!
*** Thanks again! Now go create something AMAZING! :D
-->



<!-- PROJECT LOGO -->
<br />

  <h3 align="center">Swap Contract</h3>

  <p align="center">
    A Cardano smart contract written on Python
    <br />
    <a href="https://charli3-oracles.gitbook.io/charli3-documentation/charli3s-documentation/swap-contract"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/Charli3-Official/swap-pycardano/issues">Report Bug</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
    </li>
    <li>
      <a href="#swap-contract-overview">Swap Contract Overview</a>
    </li>
    <li>
      <a href="#odv-request-on-demand-validation">ODV Request (On Demand Validation)</a>
      <ul>
        <li><a href="#overview">Overview</a></li>
        <li><a href="#technical-process">Technical Process</a></li>
        <li><a href="#benefits">Benefits</a></li>
        <li><a href="#integration">Integration</a></li>
      </ul>
    </li>
    <li>
      <a href="#built-with">Built With</a>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li>
      <a href="#usage">Usage</a>
      <ul>
        <li><a href="#common-examples">Common Examples</a>
          <ul>
            <li><a href="#fetch-latest-oracle-price">Fetch Latest Oracle Price</a></li>
            <li><a href="#get-oracle-contract-address">Get Oracle Contract Address</a></li>
            <li><a href="#check-user-wallet-liquidity">Check User Wallet Liquidity</a></li>
            <li><a href="#monitor-swap-contract-liquidity">Monitor Swap Contract Liquidity</a></li>
          </ul>
        </li>
      </ul>
    </li>
  </ol>
</details>
<!-- ABOUT THE PROJECT -->

## About The Project

### Educational Resource Disclaimer
This project serves as an educational resource designed to teach developers how to access and utilize Charli3's oracle infrastructure. All contract addresses, wallets, tokens, NFTs, and related components included in this repository are intended exclusively for test environments and should not be deployed in production systems.

### Important Notes:

The payment token used in this demonstration (TestC3) is a simulated asset with no real-world value in relation to the official Charli3 token.
All reward quantities, distribution mechanisms, and payment calculations presented here are for illustrative purposes only and do not reflect actual production values or economics.
The examples provided are not subject to real-world pricing and are simplified for educational clarity.

While this is a test environment implementation, the architecture, logic, and methodologies demonstrated in this repository provide a solid foundation for developing contracts that interact with Charli3's production oracle feeds.
### Production Considerations:


Blockchain fees will vary depending on the network environment (testnet, mainnet, etc.)
Operational costs scale with the number of oracle nodes utilized
Production implementations should include additional security measures beyond what is demonstrated here

We encourage developers to thoroughly test their implementations in appropriate test environments before considering any production deployment.


## Swap Contract Overview

The swap contract facilitates the exchange of native tokens through a wallet based on exchange rates provided by an oracle. The contract uses a UTXO to store different tokens, such as BTC and tADA. The contract supports several off-chain operations:

* **Run Swap**: Initiates the creation of a UTXO at the contract address containing a minted NFT. This NFT serves as an identifier for the UTXO that will hold two assets.
* **Add Liquidity**: Enables the addition of specific token amounts to the swap's UTXO. These tokens must be present in the wallet of the swap's creator.
* **Swap A**: Allows exchange of asset A from the user's wallet to the swap's UTXO in exchange for asset B.
* **Swap B**: Enables exchange of asset B from the user's wallet to the swap's UTXO in exchange for asset A.

## ODV Request (On Demand Validation)

### Command Showcase

![Charli3 ODV request](https://raw.githubusercontent.com/Charli3-Official/swap-demo-contract/main/swap_demo_contract/utils/assets/odv-request.gif)

### Overview
The ODV (On-Demand Validation) request is a specialized API protocol that enables real-time oracle data retrieval from the Charli3 network. This mechanism allows smart contracts to access reliable, multi-source exchange rate data precisely when needed, rather than depending solely on periodically updated feeds.

### Technical Process

1. **Initial API Request**: The client sends an API request to multiple Charli3 nodes, specifying the desired exchange rate pair (e.g., ADA/USD).
2. **Data Collection**: Charli3 nodes operate independently using [Charli3 Dendrite](https://github.com/Charli3-Official/charli3-dendrite), our specialized solution for on-chain data retrieval
   - Queries multiple predefined data sources based on their configuration
   - Performs data quality checks and outlier detection
   - Normalizes the collected data for consistency

3. **Aggregation**: Nodes apply statistical methods to aggregate data from multiple sources into a single reliable value, reducing the impact of any single anomalous source.

4. **Response Generation**: The aggregated data is returned to the requesting client along with metadata about the sources and aggregation methods used.

5. **Transaction Construction**: Using the received data, the client constructs an aggregate transaction that incorporates all node-provided feed information.

6. **Verification & Signing**: In a second API call, the constructed transaction is sent back to the Charli3 nodes for verification:
   - Each node validates that its feed data was correctly included
   - Upon successful verification, nodes cryptographically sign the transaction
   - Signed transactions are returned to the requesting client

7. **Signature Consolidation**: The client consolidates all signatures from participating nodes into a complete, multi-signed transaction.

8. **Blockchain Submission**: The fully signed transaction is submitted to the blockchain for inclusion in the next block.
9. **Payment Processing**: As part of the transaction, the client includes token payments to compensate node operators for their services, creating a sustainable economic model.

### Benefits

- **Real-Time Data**: Provides up-to-date exchange rates at the exact moment they're needed
- **Multi-Source Reliability**: Combines data from multiple sources to ensure accuracy
- **Same-Block Execution**: The feed data and its consumption can occur within the same blockchain block
- **Cryptographic Verification**: All data is verifiably signed by multiple independent node operators
- **Economic Incentives**: Built-in payment mechanism ensures network sustainability and service quality

### Integration

For detailed implementation instructions and code examples for integrating ODV requests into your applications, refer to the [odv-request documentation](https://github.com/Charli3-Official/swap-demo-contract/blob/main/swap_demo_contract/docs/odv-request.org).
### Built With

* [Charli3/Pycardano 0.12.0 (fork)](https://github.com/Charli3-Official/pycardano/pull/6)

*Note:* Tested with: ogmios:v6.11.0, kupo:v2.10.0, and cardano-node:10.1.4
<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

The initial configuration follows the pycardano repository guidelines. For project environment variables setup, we recommend reviewing the documentation at [using Pycardano](https://pycardano.readthedocs.io/en/latest/tutorial.html#using-pycardano).

### Prerequisites
Before beginning, ensure you have [Poetry](https://python-poetry.org/docs/#installing-manually) installed on your system for package management. Then install all required dependencies:
```sh
poetry update
```
1. Installation

Clone the Repository
```sh
git clone https://github.com/Charli3-Official/swap-pycardano.git
cd swap-pycardano
```
2. Install Project Dependencies
```sh
poetry install
```

3. Set Up Blockchain Connections

This tutorial requires connections to Ogmios and Kupo services for blockchain interaction. There are currently no alternative connection methods supported.

Create your configuration file by copying the template:
```sh
cp config.sample.yaml config.yaml.
```
Then edit `config.yaml` with your specific settings:
```yaml
# Required connection settings
environment:
  network: testnet
  ogmios_kupo:
    ogmios_url: "YOUR_OGMIOS_URL_HERE"  # Required
    kupo_url: "YOUR_KUPO_URL_HERE"      # Required

wallet:
  MNEMONIC_24: "MNEMONIC_HERE" # Required

# The rest of the configuration contains functional defaults
```

To perform ODV requests, you will need `TestC3` tokens for transaction payments
Request test tokens by joining our Discord server.


**Note**: All endpoints, addresses, and token configurations in the sample file have been pre-verified to work correctly. You only need to add your connection URLs and obtain test tokens.

Once configuration is complete, your environment will be ready for testing ODV requests and interacting with the swap contract.

## Usage

The project includes a comprehensive command-line interface (CLI) for seamless transaction submission. To begin using the CLI, follow these steps:

1. Navigate to the root directory of the project
2. Ensure you have run `poetry install` to set up the environment
3. Execute `charli3 --help` to display detailed information on all available command-line options

## Usage

The project includes a comprehensive command-line interface (CLI) for seamless transaction submission. To begin using the CLI, follow these steps:

1. Navigate to the root directory of the project
2. Ensure you have run `poetry install` to set up the environment
3. Execute `charli3 --help` to display detailed information on all available command-line options

### Common Examples

Below are some frequently used commands:

#### Fetch Latest Oracle Price
Retrieve the most recent price data from the oracle contract:
```sh
charli3 ogmios preprod oracle-contract --feed
```
### Get Oracle Contract Address
Obtain the address of the oracle contract:

```sh
charli3 ogmios preprod oracle-contract --address
```
### Check User Wallet Liquidity
View the available liquidity in your user wallet:

```sh
charli3 ogmios preprod user --liquidity
```
### Monitor Swap Contract Liquidity
Inspect the current liquidity within the swap contract:
```sh
charli3 ogmios preprod swap-contract --liquidity
```

### Data Sources (BTC/USD)
For this demo, each Charli3 node pulls BTC/USD price information from these data sources. For more information, check [CCXT](https://github.com/ccxt/ccxt)

```
sources:
   - binanceus
   - bingx
   - bitfinex1
   - bitget
   - bitmart
   - bitmex
   - bitstamp
   - coinbase
   - coinbaseexchange
   - coinlist
   - coinmetro
   - coinsph
   - cryptocom
   - delta
   - deribit
   - digifinex
   - gemini
   - hashkey
   - hitbtc
   - hollaex
   - htx
```
