TODO:
 README.md
 Ramp-down
 ABP not producing
 eosio.null not resigned

# Build nodeos (make install)
- merge first https://github.com/EOSIO/eos/pull/3587

# Boot
- If boot get stuck in Creating Account 1000/980000 ...... check ACCOUNTS_PER_TX var inparams.sh 

```
./boot.sh
```

# Take the snapshot after boot

- pick a block (370 in our case)
- cleos get block 370
- take the block id 0000017239cb40966c033ebf0d9f48b1400ed620342ab134afa57b70bf0d9d77
- ./take_snapshot.sh 0000017239cb40966c033ebf0d9f48b1400ed620342ab134afa57b70bf0d9d77
- Ctr-C after seeing this message in the nodeos log
```
1262180ms thread-0   snapshot_plugin.cpp:89        operator()           ]
Taking snapshot at block 370 (0000017239cb40966c033ebf0d9f48b1400ed620342ab134afa57b70bf0d9d77)...
```
 - convert snapshot to json
```
snap2json --in ./files/snapshot.bin --out ./files/snapshot.json
```

# Validate snapshot
```
python validator.py --validator=vanilla_validator --snapshot ./files/snapshot.json \
--genesis ./../boot/config/genesis.json --csv-balance ./files/snapshot.csv
```