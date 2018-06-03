import os
import sys
import json
import csv

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
sys.path[0:0] = [ DIR_PATH + '/../lib' ]

from utils import step, tick, success, fail, warning, asset2int, DictDiffer, symbol2int, string_to_name

CSV_ETH_ADDR     = 0
CSV_EOS_ACCOUNT  = 1
CSV_EOS_ADDR     = 2
CSV_EOS_BALANCE  = 3

######################################
# NAME | PRIVILEGED | RESIGN ACCOUNT #
######################################
system_accounts = {
    'eosio'       : {'privileged':True ,'actor':'eosio.prods','permission':'active'}, 
    'eosio.bpay'  : {'privileged':False,'actor':'eosio','permission':'active'},
    'eosio.msig'  : {'privileged':True ,'actor':'eosio','permission':'active'},
    'eosio.names' : {'privileged':False,'actor':'eosio','permission':'active'},
    'eosio.ram'   : {'privileged':False,'actor':'eosio','permission':'active'},
    'eosio.ramfee': {'privileged':False,'actor':'eosio','permission':'active'},
    'eosio.saving': {'privileged':False,'actor':'eosio','permission':'active'},
    'eosio.stake' : {'privileged':False,'actor':'eosio','permission':'active'},
    'eosio.token' : {'privileged':False,'actor':'eosio','permission':'active'},
    'eosio.vpay'  : {'privileged':False,'actor':'eosio','permission':'active'},
    'eosio.null'  : {'privileged':False},
    'eosio.prods' : {'privileged':False,'actor':'eosio','permission':'active'}
}

def description():
  return "EOS Vanilla validator (v0.1)"

class ValidationException(Exception):
  pass

# def get_balance(snapshot, account, symbol='EOS'):
#   if account not in snapshot['tables']['eosio.token']:
#     raise ValidationException("Balance not found")
#   if symbol not in snapshot['tables']['eosio.token'][account]['accounts']:
#     raise ValidationException("Balance not found")

#   return snapshot['tables']['eosio.token'][account]['accounts'][symbol]['data']['balance']

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
    if len(added) != 0:
      print "> Snapshot has: '%s' and your genesis" % (','.join(added))
    if len(removed) != 0:
      print "> Your genesis has %s and snapshot dont" % (','.join(removed))
    if len(changed) != 0:
      print "> Your genesis and snapshot have different '%s'" % (','.join(changed))

    print "# Snapshot genesis"
    print json.dumps(snapshot['genesis_state'], indent=2, sort_keys=True)
    print
    print "# Your genesis"
    print json.dumps(genesis, indent=2, sort_keys=True)
    return False
  
  success()
  return True

def validate_account_creation(snapshot, balances):
  found_users = {}
  step('Verifying user account creation')
  for account in balances.keys():
    tick()
    if account not in snapshot['accounts']:
      continue
    found_users[account] = balances[account]
  
  not_found = len(balances) - len(found_users)
  if not_found:
    fail()
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

  total_accounts = len(balances)

  for account in balances:
    
    total = asset2int(balances[account][CSV_EOS_BALANCE])

    liquid, net, cpu = get_account_stake(snapshot, account, args.core_symbol)

    # if account == 'b1': continue
    # TODO: validate F(stake) ?

    if total != liquid + cpu + net:
      invalid_stake += 1

  if invalid_stake > 0:
    fail()
    print "> %d accounts with invalid stake" % (invalid_stake)
    return False
  else:
    success()
  return True

def validate_system_accounts(snapshot):

  step('Verifying system accounts')

  found = []
  for name, account in snapshot['accounts'].iteritems():
    tick()
    if name in system_accounts:

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
  else:
    success()

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
  else:
    success()

def validate_global_params_against_genesis(snapshot, genesis):
  
  step('Verifying global params vs genesis')

  table = snapshot['tables']['eosio']['eosio']['global']
  params = table[table.keys()[0]]['data']
  
  diff = []
  for gp in genesis['initial_configuration']:
    if genesis['initial_configuration'][gp] != params[gp]:
      diff.append(gp)

  if len(diff):
    warning()
    print "Global params different from genesis : %s" % diff
  else:
    success()
  return True

# Vanilla validation
def validate(args):

  eos_snapshot   = load_eos_snapshot(args)
  erc20_snapshot = load_erc20_snapshot(args)
  genesis        = load_genesis(args)

  #if not validate_genesis(eos_snapshot, genesis): return

  #if not validate_global_params_against_genesis(eos_snapshot, genesis): return

  #if not validate_system_accounts(eos_snapshot): return

  #if not validate_system_contracts(eos_snapshot): return

  erc20_snapshot = validate_account_creation(eos_snapshot, erc20_snapshot)
  if not erc20_snapshot: return

  if not validate_account_stake(eos_snapshot, erc20_snapshot, args): return

  if not validate_no_code_in_accounts(eos_snapshot, erc20_snapshot): return

  if not validate_account_permissions(eos_snapshot, erc20_snapshot): return

  #if not validate_extra_accounts(eos_snapshot, erc20_snapshot): return

  # token only one EOS / supply / maxsupply
  # balance of system accounts
