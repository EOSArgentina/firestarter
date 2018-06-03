#!/bin/bash
YO="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

BLOCKID=00000c75c2ff1742e664af42ea6d0616b995f9fd5e633f6d02236a01a53e674b
GENESIS=$YO/genesis.json
PEERP2P=fullnode.eoslaomao.com:443
ERC20SNAPSHOT=$YO/snapshot.csv