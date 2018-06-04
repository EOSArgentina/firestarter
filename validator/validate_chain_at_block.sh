#!/bin/bash
ME="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

usage () {
cat << EOF
NAME

    EOS validator chain


SYNOPSIS

    validate_chain_at_block.sh [-h|--help]
                    [--network=<chain_to_validate>]
                    [--block=<block_id_after_eosio_resigns>]
                    [--p2p=<address>:<port>]

DESCRIPTION

    Validate_chaiin_at_block takes a snapshot of the blockchain
    at the block you select with --block, and validates:

    The genesis.json.
    The global Parameters.
    Global Parameter - Max RAM Size
    The System Accounts.
    The System Contracts.
    The erc20 Snapshot/account creation.
    Accounts Stakes.
    Account Permissions.
    Validate that there are no codes in the snapshots accounts.
    Validate Constitution
    EOS Token Existence & Consistency



OPTIONS

    -h, --help
            help help
    --network
            Selects the chain you want to validate, please put
            the genesis and the snapshot inside the folder.

    --block
            select the block number to take a snapshot

EXAMPLES

    SHELL> ./validate_chain_at_block.sh --network=ghostbios --block=000017dee519f1785e571480fe72989ac2dc7e4d00ecd0aa925aba6e7af414e4 --p2p=127.0.0.1:9876


EOF
}


check(){

GENESIS=$ME/$NETWORK/genesis.json
ERC20SNAPSHOT=$ME/$NETWORK/snapshot.csv

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

if [[ ! -f "$GENESIS" ]]; then
  echo "Genesis file does not exists in $NETWORK folder"
  exit
fi

if [[ ! -f "$ERC20SNAPSHOT" ]]; then
  echo "ERC20 snapshot does not exists in $NETWORK folder"
  exit
fi


}

validatesnapshot(){


BINSNAPSHOT=$ME/$NETWORK/files/snapshot.bin
JSONSNAPSHOT=$ME/$NETWORK/files/snapshot.json

VALIDSNAPSHOT=0
if [[ -f $JSONSNAPSHOT ]]; then
  jq --help > /dev/null 2>&1
  if [[ $? -eq 0 ]]; then
    SNAPSHOTBLOCK=$(cat $JSONSNAPSHOT | jq -r '.block_header_state.id')
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

  FILES=$ME/$NETWORK/files
  DATA=$ME/$NETWORK/data
  LOG=$DATA/eos.log

  mkdir -p $FILES
  rm -rf $BINSNAPSHOT
  rm -rf $DATA
  mkdir -p $DATA

  nodeos --plugin eosio::snapshot_plugin \
  --snapshot-at-block $BLOCKID --snapshot-to $BINSNAPSHOT \
  --data-dir $DATA --http-server-address 127.0.0.1:9998 \
  --p2p-listen-endpoint 127.0.0.1:9999 --p2p-peer-address $PEERP2P \
  --genesis-json $GENESIS > $LOG 2>&1 &
  nodeospid=$!

  fifo=/tmp/tmpfifo.$$
  mkfifo "${fifo}" || exit 1
  tail -f $LOG >${fifo} &
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

python validator.py --validator=vanilla_validator \
   --snapshot $JSONSNAPSHOT --genesis $GENESIS \
   --csv-balance $ERC20SNAPSHOT

}



##Argumentos
while true; do
    case $1 in
        -h | --help )
            clear > /dev/null;
            usage | less;
            exit 0
            ;;
        --network=* )
            NETWORK="${1#*=}";
            shift
            ;;
        --block=* )
            BLOCKID="${1#*=}";
            shift
            ;;
        --P2P=* )
            PEERP2P="${1#*=}";
            shift
            ;;
        -* )
            printf 'recatate y leete el usage "%s" no es una opcion \n' "${1}";
            exit 0
            ;;
        * )
            usage;
            exit 0
            ;;
        esac
done

echo $NETWORK
echo $BLOCKID
echo $PEERP2P
