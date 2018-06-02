import tempfile
import os
import sys
import argparse
import traceback
import importlib
from subprocess import Popen, PIPE
import csv
import json
import requests as r
import time

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
sys.path[0:0] = [ DIR_PATH + '/../lib', DIR_PATH + '/../validator' ]

from utils import step, tick, success, fail, warning, asset2int
from vanilla_validator import load_erc20_snapshot, CSV_ETH_ADDR, CSV_EOS_ACCOUNT, CSV_EOS_ADDR, CSV_EOS_BALANCE
from gen_tx import gen_tx

def retry(cmd):
  while True:
    with open(os.devnull, 'w') as devnull:
      p = Popen(cmd, stdout=PIPE, stderr=devnull)
    output, err = p.communicate("")
    if p.returncode:
      tick()
    else:
      break
  return output

def send_tx(tmp_file, accounts, info, args):
  tx = gen_tx(accounts, info, args)
  with open(tmp_file,'w') as tmp:
    tmp.write(tx)
  #TODO: rebuild tx if expires!!!!!
  retry([args.cleos,"--url=%s" % args.nodeos_url, "sign","-k",args.priv_key,"-c",info['chain_id'],"-p",tmp_file])

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Insert ERC20 snapshot into a EOSIO chain')
  parser.add_argument('--csv-balance', metavar='csv', help="Path to snapshot.csv (ERC20)", default="./snapshot.csv")
  parser.add_argument('--core-symbol', metavar='symbol', help="Core Symbol Name", default="SYS")
  parser.add_argument('--nodeos-url', metavar='url', help="Nodeos http url", default="http://127.0.0.1:8888")
  parser.add_argument('--accounts-per-tx', metavar='apt', help="Number of account creation per tx", default=200)
  parser.add_argument('--cleos', metavar='cleos', help="Path to cleos", default="cleos")
  parser.add_argument('--priv-key', metavar='priv', help="eosio private key", default="5KZgrDCQqxU5t9vuxeTveMDPWU7xwyqTxt6y61Dy1KQhWWHMBYo")
  parser.add_argument('--accounts-to-inject', metavar='row', help="Number of accounts to inject from CSV", default="0")

  args = parser.parse_args()

  try:
    erc20_snapshot = load_erc20_snapshot(args)
    if not erc20_snapshot: sys.exit(1)

    if int(args.accounts_to_inject) == 0:
      args.accounts_to_inject = len(erc20_snapshot)
    else:
      args.accounts_to_inject = int(args.accounts_to_inject)

    tmp_file = tempfile.mkstemp()[1]

    # Ramp up
    step('Ramp up blockchain limits')
    bparams = json.loads(
      retry([args.cleos,"--url=%s" % args.nodeos_url, "get","table","eosio","eosio","global"])
    )['rows'][0]

    max_block_cpu_usage  = bparams['max_block_cpu_usage']
    max_transaction_cpu_usage = bparams['max_transaction_cpu_usage']

    bparams['max_block_cpu_usage'] = 100000000
    bparams['max_transaction_cpu_usage'] = 99999899

    with open(tmp_file,'w') as tmp:
      tmp.write(json.dumps({'params':bparams}))

    retry([args.cleos,"--url=%s" % args.nodeos_url, "push","action","eosio","setparams",tmp_file,"-p","eosio"])
    success()

    # Get info
    step('Get info/block_prefix/block_num')
    info = json.loads(
      retry([args.cleos,"--url=%s" % args.nodeos_url, "system","newaccount","-s","-d","-j","--buy-ram-kbytes","1","--stake-net","2.5000 EOS","--stake-cpu","2.5000 EOS", "eosio", "test", "EOS6MRyAjQq8ud7hVNYcfnVPJqcVpscN5So8BhtHuGYqET5GDW5CV", "EOS6MRyAjQq8ud7hVNYcfnVPJqcVpscN5So8BhtHuGYqET5GDW5CV"])
    )
    info['chain_id'] = r.get('%s/v1/chain/get_info' % args.nodeos_url).json()['chain_id']
    success()

    args.accounts_per_tx = min(int(args.accounts_to_inject), int(args.accounts_per_tx))
    # Set limit
    step('Setting %d accounts/tx' % int(args.accounts_per_tx))
    limit = int(args.accounts_per_tx)
    success()

    # Inject snapshot
    total = 0
    accounts = []
    for account in erc20_snapshot:
      accounts.append(erc20_snapshot[account])
      if len(accounts) == limit:
        total += len(accounts)
        step('Creating accounts  %d/%d      (%.2f%%)' % (total, args.accounts_to_inject, (100.0*float(total)/float(args.accounts_to_inject)) ))
        send_tx(tmp_file, accounts, info, args)
        success()
        accounts = []

      if total >= args.accounts_to_inject:
        break

    if total < args.accounts_to_inject:
      total += len(accounts)
      step('Creating accounts  %d/%d      (%.2f%%)' % (total, len(erc20_snapshot), (100.0*float(total)/float(args.accounts_to_inject)) ))
      send_tx(tmp_file, accounts, info, args)
      success()

    # Ramp down
    step('Ramp down blockchain limits')
    bparams['max_block_cpu_usage'] = max_block_cpu_usage
    bparams['max_transaction_cpu_usage'] = max_transaction_cpu_usage
    with open(tmp_file,'w') as tmp:
      tmp.write(json.dumps({'params':bparams}))
    retry([args.cleos,"--url=%s" % args.nodeos_url, "push","action","eosio","setparams",tmp_file,"-p","eosio"])
    success()

  except Exception as ex:
    fail()
    print
    print "Unable to inject ERC20 snapshot %s" % args.csv_balance
    print "##########################################################"
    print str(ex)
    print traceback.format_exc()
    print "##########################################################"
