
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
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#license">License</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project
This repository contains a Python-based Cardano smart contract that utilizes pre-production test data from Charli3 oracle feeds as a use case.

This project has been designed as an educational resource to teach the general public how to access Charli3's oracles information. Therefore, the contract addresses, wallets, tokens, NFTs, and related information are intended for use in test environments only and should not be used in a production environment. Nonetheless, the structure, logic, and methods used in this repository can be used as a foundation for developing contracts that interact with production Charli3's feeds.

The swap contract enables the exchange of native tokens through a wallet, based on exchange rates provided by an oracle. The contract utilizes a UTXO to store different tokens, such as tUSDT and tADA. Off-chain operations supported by the contract include:

* The "Run swap" transaction initiates the creation of a UTXO at the contract address, which contains a minted NFT. This serves as an identifier for the UTXO that will hold two assets.
* "Add liquidity" transaction enables the addition of specific amounts of tokens to the swap's UTXO. These quantities must be present in the wallet of the swap's creator.
* "Swap A" transaction allows the exchange of asset A from the user's wallet to the swap's UTXO in exchange for asset B.
* "Swap B" transaction enables the exchange of asset B from the user's wallet to the swap's UTXO in exchange for asset A.


*Note:* Documentation for the off-chain integration of the send-odv-request can be found [here](https://github.com/Charli3-Official/swap-demo-contract/blob/main/swap_demo_contract/docs/odv-request.org).
<p align="right">(<a href="#readme-top">back to top</a>)</p>



### Built With

* [Pycardano 0.11.1](https://pycardano.readthedocs.io/en/latest/index.html)

*Note:* Tested with: ogmios:v6.6.1, kupo:v2.9.0, and cardano-node:9.1.1 and Blockfrost
<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- GETTING STARTED -->
## Getting Started

The initial configuration is sourced from the pycardano repository. To create the project environment variables, we recommend reading the documentation at [using Pycardano](https://pycardano.readthedocs.io/en/latest/tutorial.html#using-pycardano).

### Prerequisites


The required packages can be installed using pip with the following command:

  ```sh
  poetry update
  ```

### Installation

1. Get an API Key at [Blockfrost](https://blockfrost.io/), Ogmios/Kupo configuration or your personal configuration.
2. Clone the repo:
   ```sh
   git clone https://github.com/Charli3-Official/swap-pycardano.git
   ```
3. Enter your API and personal configuration based on `config.sample.yaml`.
   ```
   MNEMONIC_24:

   # Swap Contract
   swap_contract_address: addr_test1wp5p6ztmlsc5agr2crc3yhrqpwrkq7a29a2muyzn3ekdrhqmzzdjz
   swap_minting_policy: c6f192a236596e2bbaac5900d67e9700dec7c77d9da626c98e0ab2ac

   token_a_minting_policy: c6f192a236596e2bbaac5900d67e9700dec7c77d9da626c98e0ab2ac
   token_a_asset_name: USDT
   swap_asset_name: SWAP

   # Oracle Contract Configuration
   oracle_contract_address: addr_test1wzy5k07lnrrdjjqwzq4t3vvn0zp5de34s4z7res9y4jjuwcaz3amy

   aggstate_minting_policy: a71cbfd2e54d057612ca21f8d9a3637fbb307bd74fa33d4f6174e82f
   aggstate_asset_name: AggState

   oracle_nft_minting_policy: a71cbfd2e54d057612ca21f8d9a3637fbb307bd74fa33d4f6174e82f
   oracle_nft_asset_name: OracleFeed

   c3_token_hash: c9c4ada29e8640077a03ec2a6982f867f356ba1d7e25d19232372828
   c3_token_name: TestC3

   script_input_oracle: 236d7c1e189c39f0ed2a7a6aa079cfc180d1a089abb2f38173c50e7547e0d9f9#0

   ## Dynamic payment oracle
   dynamic_payment_oracle_addr:
   dynamic_payment_oracle_minting_policy:
   dynamic_payment_oracle_asset_name:

   # Contract Addresses
   blockfrost:
     project_id: preprodXXX
   ogmios:
       ws_url: ws://0.0.0.0:1337
       kupo_url: http://0.0.0.0:1442

   ```

  <p align="right">(<a href="#readme-top">back to top</a>)</p>
<!-- USAGE EXAMPLES -->



## Usage
The project includes a command-line interface for easy transaction submission. To use it, first navigate to the root directory and ensure you have run `poetry install`. Then, execute the command `poetry run odv-demo --help` to display detailed information on the available command-line options.

```
usage: python main.py [-h] [{blockfrost,ogmios}] [{preprod,mainnet}] {trade,user,swap-contract,oracle-contract,send-odv-request} ...

The swap python script is a demonstrative smart contract (Plutus v2) featuring the interaction with a Charli3's oracle. This script uses the inline oracle feed as reference input simulating the exchange rate
between tADA and tUSDT to sell or buy assets from a swap contract in the test environment of preproduction.

positional arguments:
  {blockfrost,ogmios}   External service to read blockhain information
  {preprod,mainnet}     Blockchain environment
  {trade,user,swap-contract,oracle-contract,send-odv-request}
    trade               Call the trade transaction to exchange a user asset with another asset at the swap contract. Supported assets tADA and tUSDT.
    user                Obtain information about the wallet of the user who participate in the trade transaction.
    swap-contract       Obtain information about the SWAP smart contract.
    oracle-contract     Obtain information about the ORACLE smart contract.
    send-odv-request    Send a validation request on demand to ODV-Charli3 Oracle.

options:
  -h, --help            show this help message and exit

Copyrigth: (c) 2020 - 2024 Charli3
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

Documentation for the off-chain integration of the send-odv-request can be found [here](https://github.com/Charli3-Official/swap-demo-contract/blob/main/swap_demo_contract/docs/odv-request.org).

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
