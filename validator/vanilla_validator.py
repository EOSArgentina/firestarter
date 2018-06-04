import os
import sys
import json
import csv
import tempfile
from hashlib import sha256

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
sys.path[0:0] = [ DIR_PATH + '/../lib' ]

from utils import step, tick, success, fail, warning, asset2int, DictDiffer, symbol2int, string_to_name

CSV_ETH_ADDR     = 0
CSV_EOS_ACCOUNT  = 1
CSV_EOS_ADDR     = 2
CSV_EOS_BALANCE  = 3

system_accounts = {
  'eosio' : {
    'privileged' : True,
    'actor'      : 'eosio.prods',
    'permission' : 'active',
    'code'       : "",
    'code'       : 'daf48f1b958af29180b2c33c8b239fa976ddb91cabe662e7b5e82c57c4c6b19f' ,
    'abi'        : 'eosio.system.abi'
   }, 
  'eosio.bpay' : {
    'privileged' : False,
    'actor'      : 'eosio',
    'permission' : 'active',
    'code'       : "",
    'abi'        : ""
   },
  'eosio.msig' : {
    'privileged' : True,
    'actor'      : 'eosio',
    'permission' : 'active',
    'code'       : '5cf017909547b2d69cee5f01c53fe90f3ab193c57108f81a17f0716a4c83f9c0',
    'abi'        : 'eosio.msig.abi',
   },
  'eosio.names' : {
    'privileged' : False,
    'actor'      : 'eosio',
    'permission' : 'active',
    'code'       : "",
    'abi'        : ""
   },
  'eosio.ram' : {
    'privileged' : False,
    'actor'      : 'eosio',
    'permission' : 'active',
    'code'       : "",
    'abi'        : ""
   },
  'eosio.ramfee' : {
    'privileged' : False,
    'actor'      : 'eosio',
    'permission' : 'active',
    'code'       : "",
    'abi'        : ""
   },
  'eosio.saving' : {
    'privileged' : False,
    'actor'      : 'eosio',
    'permission' : 'active',
    'code'       : "",
    'abi'        : ""
   },
  'eosio.stake' : {
    'privileged' : False,
    'actor'      : 'eosio',
    'permission' : 'active',
    'code'       : "",
    'abi'        : ""
   },
  'eosio.token' : {
    'privileged' : False,
    'actor'      : 'eosio',
    'permission' : 'active',
    'code'       : '3e0cf4172ab025f9fff5f1db11ee8a34d44779492e1d668ae1dc2d129e865348',
    'abi'        : 'eosio.token.abi',
   },
  'eosio.vpay' : {
    'privileged' : False,
    'actor'      : 'eosio',
    'permission' : 'active',
    'code'       : "",
    'abi'        : ""
   },
  'eosio.null' : {
    'privileged' : False,
    'code'       : "",
    'abi'        : ""
    },
  'eosio.prods' : {
    'privileged' : False,
    'actor'      : 'eosio',
    'permission' : 'active',
    'code'       : "",
    'abi'        : ""
  }
}

def description():
  return "EOS Vanilla validator (v0.1)"

class ValidationException(Exception):
  pass

def authority_controlled_by_one_actor(perm, actor, permission):
    if perm['auth']['threshold'] != 1: return False
    if len(perm['auth']['keys']) != 0: return False
    if len(perm['auth']['accounts']) != 1: return False
    if perm['auth']['accounts'][0]['weight'] != 1: return False
    if perm['auth']['accounts'][0]['permission']['actor'] != actor: return False
    if perm['auth']['accounts'][0]['permission']['permission'] != permission: return False
    if len(perm['auth']['waits']) != 0: return False
    return True

def authority_controlled_by_one_key(perm, key):
    if perm['auth']['threshold'] != 1: return False
    if len(perm['auth']['keys']) != 1: return False
    if len(perm['auth']['accounts']) != 0: return False
    if perm['auth']['keys'][0]['key'] != key: return False
    if perm['auth']['keys'][0]['weight'] != 1: return False
    if len(perm['auth']['waits']) != 0: return False
    return True

def load_eos_snapshot(args):
  step('Loading EOS snapshot')
  with open(args.snapshot) as file:
    snapshot = json.load(file)

    # Convert list to dictionary
    accounts = {}
    for acc in snapshot['accounts']:
      tick()
      accounts[acc['name']] = acc
    snapshot['accounts'] = accounts

    # Add permissions to account dict
    for perm in snapshot['permissions']:
      tick()
      if perm['id']['_id'] == 0: continue
      owner = perm['owner']
      if owner not in snapshot['accounts']: raise ValidationException("invalid snapshot: permission owner not found")
      if 'permissions' not in snapshot['accounts'][owner]:
        snapshot['accounts'][owner]['permissions'] = {}
      snapshot['accounts'][owner]['permissions'][perm['name']] = perm

    # Tables
    tables = {}
    for t in snapshot['tables']:
      tick()
      code  = t['tid']['code']
      scope = t['tid']['scope']
      table = t['tid']['table']
      if code not in tables:
        tables[code] = {}
      if scope not in tables[code]:
        tables[code][scope] = {}
      tables[code][scope][table] = t['rows']
    snapshot['tables'] = tables

  success()
  return snapshot

def load_erc20_snapshot(args):
  step('Loading ETH snapshot')
  with open(args.csv_balance, 'rb') as csvfile:
    balances = {}
    for row in csv.reader(csvfile, delimiter=','):
      tick()
      row = [unicode(i) for i in row]
      row[CSV_EOS_BALANCE] = '{0} {1}'.format(row[CSV_EOS_BALANCE], args.core_symbol)
      balances[row[CSV_EOS_ACCOUNT]] = row
  success()
  return balances

def load_genesis(args):
  step('Load EOS genesis')
  with open(args.genesis, 'rb') as file:
    genesis = json.load(file)
  success()
  return genesis

def validate_genesis(snapshot, genesis):
  step('Validating genesis')
  ddiff = DictDiffer(snapshot['genesis_state'], genesis)
  added   = ddiff.added()
  removed = ddiff.removed()
  changed = ddiff.changed()

  if len(added) != 0 or len(removed) != 0 or len(changed) != 0:
    fail()
    tmp = tempfile.mkstemp()[1]
    with open(tmp,'w') as out:
      if len(added) != 0:
        out.write("> Snapshot has '%s' and your genesis dont\n" % (','.join(added)))
      if len(removed) != 0:
        out.write("> Your genesis has %s and snapshot dont\n" % (','.join(removed)))
      if len(changed) != 0:
        out.write("> Your genesis and snapshot have different '%s'\n" % (','.join(changed)))
    
      out.write('\n')
      out.write("# Snapshot genesis\n")
      out.write(json.dumps(snapshot['genesis_state'], indent=2, sort_keys=True))
      out.write('\n')
      out.write("# Your genesis\n")
      out.write(json.dumps(genesis, indent=2, sort_keys=True))
      out.write('\n')

    print "> please check %s for details" % tmp
    return True
  
  success()
  return True

def print_some(print_count, to_print):
  if print_count == 0: fail()
  if print_count <= 5:
    print "** {0}".format(to_print)
    print_count += 1
  return print_count

def validate_account_creation(snapshot, balances):
  found_users = {}
  print_count = 0
  step('Verifying user account creation')
  for account in balances.keys():
    tick()
    if account not in snapshot['accounts']:
      print_count = print_some(print_count, account)
      continue
    found_users[account] = balances[account]
  
  not_found = len(balances) - len(found_users)
  if not_found:
    print "> %d (out of %d) accounts were not found in the EOS snapshot" % (not_found, len(balances))
    # TODO: uncomment
    # return False
  else:
    success()
  
  return found_users

def get_account_stake(snapshot, account, symbol):
  
  sym = str(symbol2int(symbol))
  
  liquid = 0
  if account in snapshot['tables']['eosio.token']:
    table = snapshot['tables']['eosio.token'][account]['accounts']
    liquid = asset2int(table[sym]['data']['balance'])

  net = 0
  cpu = 0
  if account in snapshot['tables']['eosio']:
    table = snapshot['tables']['eosio'][account]['userres']
    k = str(string_to_name(account))
    net = asset2int(table[k]['data']['net_weight'])
    cpu = asset2int(table[k]['data']['cpu_weight'])

  return liquid, net, cpu

def validate_account_stake(snapshot, balances, args):
  step('Verifying user account stake')
  invalid_stake = 0
  print_count = 0
  total_accounts = len(balances)

  for account in balances:
    
    total = asset2int(balances[account][CSV_EOS_BALANCE])

    liquid, net, cpu = get_account_stake(snapshot, account, args.core_symbol)

    # TODO: validate F(stake) ?
    if total != liquid + cpu + net:
      print_count = print_some(print_count, '{0} => TOTAL: [{1}] L:[{2}] C:[{3}] N:[{4}]'.format(account,total,liquid,cpu,net))
      invalid_stake += 1

  if invalid_stake > 0:
    print "> %d accounts with invalid stake" % (invalid_stake)
    return False
  else:
    success()
  return True

def validate_system_accounts(snapshot):

  step('Verifying system accounts')

  found = []
  for name in system_accounts:
      tick()

      # Verify exists
      if name not in snapshot['accounts']:
        fail()
        print "> %s account does not exists" % (name)
        return False

      account = snapshot['accounts'][name]

      # Verify code
      current  = sha256(account['code'].decode('hex')).digest().encode('hex')
      expected = system_accounts[name]['code']
      if current != expected:
        fail()
        print "> wrong code on %s account\n\texpected : %s\n\tcurrent  : %s" % (name,expected,current)
        return False

      # Verify ABI

      # Verify privileged
      if account['privileged'] != system_accounts[name]['privileged']:
        fail()
        print "> %s account wrong privileged setting" % (name)
        return False

      # Verify resignement
      if name != "eosio.null" and name != "eosio.prods":
        actor = system_accounts[name]['actor']
        permission = system_accounts[name]['permission']
        if authority_controlled_by_one_actor(account['permissions']["owner"], actor, permission) != True or \
           authority_controlled_by_one_actor(account['permissions']["owner"], actor, permission) != True:
          fail()
          print "> %s account NOT PROPERLY RESIGNED" % (name)
          return False

      found.append(name)

  not_found = set(system_accounts.keys()) - set(found)
  if len(not_found):
    fail()
    print "> missing system accounts %s" % (','.join(not_found))
    return False

  success()
  return True

def validate_no_code_in_accounts(snapshot, balances):
  step('Verifying user account code')
  with_code = 0
  for account in balances:
    tick()
    acnt = snapshot['accounts'][account]
    if int('0x'+acnt['code_version'],16) != 0 or \
       acnt['abi'] != "" or \
       acnt['vm_type'] != 0 or \
       acnt['vm_version'] != 0:
      with_code += 1
  if with_code > 0:
    warning()
    print "> %d accounts with code set" % (with_code)
    return False
  else:
    success()

  return True

def validate_account_permissions(snapshot, balances):

  step('Verifying user account permission')
  accounts = snapshot['accounts']
  invalid_perm = 0
  for account in balances:
    perms = snapshot['accounts'][account]['permissions']
    if authority_controlled_by_one_key(perms["active"], balances[account][CSV_EOS_ADDR]) != True or \
       authority_controlled_by_one_key(perms["owner"], balances[account][CSV_EOS_ADDR]) != True:
      invalid_perm += 1

  if invalid_perm > 0:
    warning()
    print "> %d accounts with invalid permission" % (with_code)
    return False
  else:
    success()
  return True

def validate_no_privileged_accounts(snapshot):
  step('Verifying privileged accounts')

  privileged_accounts = []
  for sa in system_accounts:
    if system_accounts[sa]['privileged']:
      privileged_accounts.append(sa)

  for name in snapshot['accounts']:
    if snapshot['accounts'][name]['privileged'] and name not in privileged_accounts:
      fail()
      print "> Invalid privileged account found : %s" % name
      return False
  else:
    success()
  return True

def validate_global_params_against_genesis(snapshot, genesis):
  
  step('Verifying global params vs genesis')

  table = snapshot['tables']['eosio']['eosio']['global']
  params = table[table.keys()[0]]['data']
  
  if not 'initial_configuration' in genesis:
    fail()
    print "> Unable to compare global params, initial_configuration not found in genesis"
    return True

  diff = []
  for gp in genesis['initial_configuration']:
    if genesis['initial_configuration'][gp] != params[gp]:
      diff.append(gp)

  if len(diff):
    warning()
    print "> Global params different from genesis : %s" % diff
  else:
    success()
  return True

def validate_extra_accounts(snapshot, balances):

  step('Verifying extra accounts')

  print_count = 0
  for account in snapshot['accounts']:
    if print_count == 0 : tick()
    if account not in balances and account not in system_accounts:
      print_count = print_some(print_count, "> Extra account found %s" % account )

  if print_count != 0:
    return False
  
  success()
  return True

# Vanilla validation
def validate(args):

  eos_snapshot   = load_eos_snapshot(args)
  erc20_snapshot = load_erc20_snapshot(args)
  genesis        = load_genesis(args)

  if not validate_genesis(eos_snapshot, genesis): return

  if not validate_global_params_against_genesis(eos_snapshot, genesis): return

  #if not validate_system_accounts(eos_snapshot): return

  #if not validate_constitution(eos_snapshot): return

  erc20_snapshot = validate_account_creation(eos_snapshot, erc20_snapshot)
  if not erc20_snapshot: return

  if not validate_account_stake(eos_snapshot, erc20_snapshot, args): return

  if not validate_no_code_in_accounts(eos_snapshot, erc20_snapshot): return

  if not validate_account_permissions(eos_snapshot, erc20_snapshot): return

  if not validate_no_privileged_accounts(eos_snapshot): return

  if not validate_extra_accounts(eos_snapshot, erc20_snapshot): return

  # token only one EOS / supply / maxsupply
  # balance of system accounts
