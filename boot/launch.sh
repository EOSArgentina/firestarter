#!/bin/bash
source params.sh
./clear.sh

mkdir -p $ME/data
cp $ME/config/config.ini $ME/data
cp $ME/config/genesis.json $ME/data

tmp=$(mktemp)

echo 'private-key=["'$EOSIO_PUB'","'$EOSIO_PRIV'"]' >> $ME/data/config.ini
echo '' >> $ME/data/config.ini


# Import keys from folder and set env vars
for filename in $(ls -1 $ME/producers/*.key 2> /dev/null); do
  name=$(basename $filename)
  account="${name%.*}"
  account_priv=$(head -n1 $filename)
  account_pub=$(tail -n1 $filename )
  echo "producer-name= $account" >> $ME/data/config.ini
  echo 'private-key=["'$account_pub'","'$account_priv'"]' >> $ME/data/config.ini
done


nodeos --max-irreversible-block-age 999999999 --abi-serializer-max-time-ms 99999999 --wasm-runtime wavm --data-dir $ME/data --config-dir $ME/data --genesis-json $ME/data/genesis.json --max-transaction-time 100000 > $ME/logs/eos.log 2>&1 &
echo $! > $ME/nodeos.pid
