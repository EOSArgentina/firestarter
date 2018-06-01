from datetime import datetime, timedelta
from base58 import Base58
from utils import asset2int, int2asset, string_to_name, revhex
from vanilla_validator import CSV_ETH_ADDR, CSV_EOS_ACCOUNT, CSV_EOS_ADDR, CSV_EOS_BALANCE

def account2hex(account):
  return revhex('%016x' % string_to_name(account))

def pub2hex(pub):
  return repr(Base58(pub))

def bytes2hex(b):
  return revhex('%08x'%(b))

def asset2hex(asset):
  p1 = revhex('%016x' % asset2int(asset))
  p2 = '04'
  for i in asset.split()[1]:
    p2 += ('%02x'%ord(i))
  while len(p2) < 16:
    p2 += '00'
  return p1+p2

def newaccount(account, pubkey):
	return """
	{
    "account": "eosio",
    "name": "newaccount",
    "authorization": [{
      "actor": "eosio",
      "permission": "active"
    }],
    "data": "0000000000ea3055%s010000000100%s01000000010000000100%s01000000"
	}""" % (account2hex(account),pub2hex(pubkey),pub2hex(pubkey))

def buyrambytes(account,kbytes):
	return """
	{
    "account": "eosio",
    "name": "buyrambytes",
    "authorization": [{
      "actor": "eosio",
      "permission": "active"
    }],
    "data": "0000000000ea3055%s%s"
  }
	""" % (account2hex(account),bytes2hex(kbytes*1024))

def delegatebw(account,net,cpu):
	return """
	{
    "account": "eosio",
    "name": "delegatebw",
    "authorization": [{
      "actor": "eosio",
      "permission": "active"
    }],
    "data": "0000000000ea3055%s%s%s01"
  }
	""" % (account2hex(account),asset2hex(net),asset2hex(cpu))


def gen_tx(accounts, info, args):
  utc_datetime = datetime.utcnow() + timedelta(seconds=10)
  
  actions = []
  for acc in accounts:
    actions.append(newaccount(acc[CSV_EOS_ACCOUNT], acc[CSV_EOS_ADDR]))
    actions.append(buyrambytes(acc[CSV_EOS_ACCOUNT],8))

    total = asset2int(acc[CSV_EOS_BALANCE])

    #TODO: ???
    net = total / 2
    cpu = total - net

    actions.append(delegatebw(acc[CSV_EOS_ACCOUNT], int2asset(net, args.core_symbol), int2asset(cpu, args.core_symbol)))

  tx = """
  {
    "max_net_usage_words": 0,
    "max_cpu_usage_ms": 0,
    "delay_sec": 0,
    "context_free_actions": [],
    "expiration": "%s",
    "ref_block_num": %s,
    "ref_block_prefix": %s,
    "delay_sec": 0,
    "actions": [%s]
  }
  """ % (utc_datetime.strftime("%Y-%m-%dT%H:%M:%S"), info['ref_block_num'], info['ref_block_prefix'],
         ','.join(actions))

  return tx
