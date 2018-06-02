# Build nodeos (make install)
- Merge https://github.com/EOSIO/eos/pull/3587 first

# Boot
- If boot get stuck in Creating Account 1000/980000 ...... check ACCOUNTS_PER_TX var inparams.sh 

```
./boot.sh
```

# Take snapshot and validate
- pick a block (370 in our case)
- cleos get block 370
- take the block id 0000017239cb40966c033ebf0d9f48b1400ed620342ab134afa57b70bf0d9d77
- ./validate_chain_at_bloc.sh 0000017239cb40966c033ebf0d9f48b1400ed620342ab134afa57b70bf0d9d77

# Take snapshot from a remote node
- obtain the genesis.json used in the chain
- pick a block where you want to validate the chain at (ej:4000)
- ```cleos --url=http://the.remote.node.com:8888 get block 4000```
- take the block id 0000017239cb40966c033ebf0d9f48b1400ed620342ab134afa57b70bf0d9d77
- PEERP2P=the.remote.node.com:9876 GENESIS=/path/to/genesis ./validate_chain_at_bloc.sh 0000017239cb40966c033ebf0d9f48b1400ed620342ab134afa57b70bf0d9d77

![Alt Text](https://i.imgur.com/3ZHH5LU.gif)