
This tool contains 
# Introduction

This repo contains a set of tools that allows to boot and validate an EOSIO chain.

Boot, Snapshot, and validation tools can be used together or separatedly, eg: if you already have your boot in place, then you can only use validation tool to verify and validate 

Current Validation tool includes these features:

* The genesis.json.
* The global Parameters.
* Global Parameter - Max RAM Size
* The System Accounts.
* The System Contracts.
* The erc20 Snapshot/account creation.
* Accounts Stakes.
* Account Permissions.
* Validate that there are no codes in the snapshots accounts.
* Validate Constitution  
* EOS Token Existence & Consistency

# 1) Boot Tool
- Automatically setups and starts a chain.
- Includes injection of EOS ERC20 Tokens.
- Consider that this script recreates your wallet and starts a nodeos with custom parameters, please customize configuration files as needed.


Steps:
- Before build add snapshot plugin
```
cd /eos
git merge origin/snapshot-plugin
```
- Merge https://github.com/EOSIO/eos/pull/3587 first
- Remember change CORE_SYMBOL_NAME="EOS" to be EOS (vi ./eosio_build.sh)

- If boot get stuck in Creating Account 1000/980000 ...... check ACCOUNTS_PER_TX var inparams.sh 

```
cd boot
./boot.sh
```
# 2) Chain State Snapshot & Validation Tool

Take snapshot locally
- pick a block (370 in our case)
```
cleos get block 370
```
- take the block id 0000017239cb40966c033ebf0d9f48b1400ed620342ab134afa57b70bf0d9d77
```
cd validator
./validate_chain_at_bloc.sh 0000017239cb40966c033ebf0d9f48b1400ed620342ab134afa57b70bf0d9d77
```

Take snapshot from a remote node
- obtain the genesis.json used in the chain
- pick a block where you want to validate the chain at (ej:4000)
```
cleos --url=http://the.remote.node.com:8888 get block 4000
```
- take the block id 0000017239cb40966c033ebf0d9f48b1400ed620342ab134afa57b70bf0d9d77
```
PEERP2P=the.remote.node.com:9876 GENESIS=/path/to/genesis ./validate_chain_at_bloc.sh 0000017239cb40966c033ebf0d9f48b1400ed620342ab134afa57b70bf0d9d77
```

![Alt Text](https://i.imgur.com/3ZHH5LU.gif)