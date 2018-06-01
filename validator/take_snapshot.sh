#!/bin/bash
ME="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [[ "$1" -eq "" ]]; then
	echo "You must specify the block id"
	exit
fi

mkdir -p $ME/files
rm -rf $ME/files/snapshot.bin

rm -rf $ME/data && time nodeos --plugin eosio::snapshot_plugin \
--snapshot-at-block $1 --snapshot-to $ME/files/snapshot.bin \
--data-dir $ME/data --http-server-address 127.0.0.1:9998 \
--p2p-listen-endpoint 127.0.0.1:9999 --p2p-peer-address 127.0.0.1:9876 \
--genesis-json $ME/../boot/config/genesis.json