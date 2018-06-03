#!/bin/bash
ME="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

PEERP2P=${PEERP2P:-127.0.0.1:9876}
GENESIS=${GENESIS:-}
ERC20SNAPSHOT=${ERC20SNAPSHOT:-}
BLOCKID=${BLOCKID:-$1}

echo "##########################"
echo $ERC20SNAPSHOT
echo "##########################"

nodeos --help | grep snapshot > /dev/null 2>&1
if [[ $? -ne 0 ]]; then
  echo "nodeos doesnt support snapshot"
  echo "please merge: https://github.com/EOSIO/eos/pull/3587 first"
  exit
fi

if [[ "$BLOCKID" == "" ]]; then
  echo "Plase specify the block id"
  exit
fi

if [[ "$GENESIS" == "" ]]; then
  GENESIS=$ME/../boot/config/genesis.json
fi

if [[ "$ERC20SNAPSHOT" == "" ]]; then
  ERC20SNAPSHOT=$ME/../inject/files/snapshot.csv
fi

BINSNAPSHOT=$ME/files/snapshot.bin
JSONSNAPSHOT=$ME/files/snapshot.json

VALIDSNAPSHOT=0
if [[ -f $JSONSNAPSHOT ]]; then
  jq --help > /dev/null 2>&1
  if [[ $? -eq 0 ]]; then
    SNAPSHOTBLOCK=$(cat $ME/files/snapshot.json | jq -r '.block_header_state.id')
    if [[ "$SNAPSHOTBLOCK" == "$BLOCKID" ]]; then
      echo "We have detected a valid snapshot for $BLOCKID"
      echo "Do you wish to use it?"
      select yn in "Yes" "No"; do
          case $yn in
              Yes ) VALIDSNAPSHOT=1; break;;
          esac
      done      
    fi
  fi
fi

if [[ $VALIDSNAPSHOT -eq 0 ]]; then

  mkdir -p $ME/files
  rm -rf $BINSNAPSHOT
  rm -rf $ME/data
  mkdir -p $ME/data

  nodeos --plugin eosio::snapshot_plugin \
  --snapshot-at-block $BLOCKID --snapshot-to $BINSNAPSHOT \
  --data-dir $ME/data --http-server-address 127.0.0.1:9998 \
  --p2p-listen-endpoint 127.0.0.1:9999 --p2p-peer-address $PEERP2P \
  --genesis-json $GENESIS > $ME/data/eos.log 2>&1 &
  nodeospid=$!

  fifo=/tmp/tmpfifo.$$
  mkfifo "${fifo}" || exit 1
  tail -f $ME/data/eos.log >${fifo} &
  tailpid=$!
  echo "Waiting for snapshot to be taken ........ (please wait)"
  grep -m 1 "$BLOCKID" "${fifo}" 2> /dev/null
  kill "${tailpid}" 2> /dev/null
  wait "${tailpid}" 2>/dev/null
  kill "${nodeospid}" 2> /dev/null
  wait "${nodeospid}" 2>/dev/null
  rm -f "${fifo}"

  echo "Snapshot saved in $BINSNAPSHOT"

  echo "Converting snapshot to json ..."
  snap2json --in $BINSNAPSHOT --out $JSONSNAPSHOT

fi

echo python validator.py --validator=vanilla_validator \
   --snapshot $JSONSNAPSHOT --genesis $GENESIS \
   --csv-balance $ERC20SNAPSHOT
