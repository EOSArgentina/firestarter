#TODO : ordenar para que sea leible

ME="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# change eosroot to your eos/build folder, defaults to home
CORE_SYMBOL=EOS

EOSROOT=${EOSROOT:-~/eos/build}
CONTRACT_FOLDER=$EOSROOT/contracts
SYSTEM_ACCOUNTS="eosio.bpay eosio.msig eosio.names eosio.ram eosio.ramfee eosio.saving eosio.stake eosio.token eosio.vpay"

# Amout of eos to create
EOS_CREATE="10000000000.0000 "$CORE_SYMBOL
# Amount of eos to issue
EOS_ISSUE="1000000000.0000 "$CORE_SYMBOL
MEMO="hola mundo :)"

ACCOUNTS_PER_TX=500
ACCOUNTS_TO_INJECT=0

###################################################
#      KEYS
###################################################
EOSIO_PUB=EOS51kDfvFa9ahwoHD1ybjFaZPTgwYZ76TtyWK6TNGsKgr8p3WcsC
EOSIO_PRIV=5KZgrDCQqxU5t9vuxeTveMDPWU7xwyqTxt6y61Dy1KQhWWHMBYo