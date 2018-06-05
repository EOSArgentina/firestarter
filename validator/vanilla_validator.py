import os
import sys
import json
import csv
import tempfile
from hashlib import sha256

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
sys.path[0:0] = [ DIR_PATH + '/../lib' ]

from utils import step, tick, success, warning, asset2int, name_to_string, DictDiffer, symbol2int, string_to_name

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

def authority_is_empty(perm):
    if perm['auth']['threshold'] != 0: return False
    if len(perm['auth']['keys']) != 0: return False
    if len(perm['auth']['accounts']) != 0: return False
    if len(perm['auth']['waits']) != 0: return False
    return True

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
    warning()
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
  else:
    success()

  return True

def print_some(print_count, to_print):
  if print_count == 0: warning()
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
  else:
    success()

  return True

def validate_system_accounts(snapshot):

  step('Verifying system accounts')

  errs = []
  for name in system_accounts:
      
      # Verify exists
      if name not in snapshot['accounts']:
        errs.append("> missing system account %s" % (name))
        continue

      account = snapshot['accounts'][name]

      # Verify code
      expected = None
      if system_accounts[name]['code']:
        expected = system_accounts[name]['code']

      current  = account['code_version'] if account['code_version'] != "0000000000000000000000000000000000000000000000000000000000000000" else None
      real     = sha256(account['code'].decode('hex')).digest().encode('hex') if expected else None

      if not (expected == current == real):
        print
        print "[%s][%s][%s]" % (expected,current,real)
        print
        errs.append("> wrong code on %s account\n\texpected : %s\n\tcurrent  : %s\n\tcalculated : %s" % (name,expected if expected else "<none>", current if current else "<none>", real if real else "<none>"))

      # Verify ABI / Constitution
      abi = system_accounts[name]['abi']
      if abi:
        with open('{0}/abi-files/{1}'.format(DIR_PATH, abi)) as f:
          expected_abi = json.load(f)
          current_abi  = account['abi']

          if name == "eosio":
            print
            print "####################################"
            print
            print type(expected_abi)
            print type(current_abi)
            print
            # print expected_abi["ricardian_clauses"][0]["body"]
            # with open("/tmp/c1",'w') as f:
            #   f.write(expected_abi["ricardian_clauses"][0]["body"])

            print
            print current_abi["ricardian_clauses"][0]["body"]
            with open("/tmp/c2",'w') as f:
              f.write(current_abi["ricardian_clauses"][0]["body"])

            print
            print current_abi["ricardian_clauses"][0]["body"] == expected_abi["ricardian_clauses"][0]["body"]
            print
            print "####################################"

          ddiff = DictDiffer(expected_abi, current_abi)
          added   = ddiff.added()
          removed = ddiff.removed()
          changed = ddiff.changed()

          # SPECIAL CASE SKIP
          skip = ["____comment", "error_messages"]
          for s in skip:
            if s in added: added.remove(s)
            if s in removed: removed.remove(s)
            if s in changed: changed.remove(s)

          if len(added) != 0 or len(removed) != 0 or len(changed) != 0:
            
            tmp = tempfile.mkstemp()[1]

            is_constitution = name == "eosio" and "ricardian_clauses" in added or "ricardian_clauses" in removed or "ricardian_clauses" in changed
            if is_constitution:
              errs.append("> Constitution missmatch - please check %s" % (tmp))
            else:
              errs.append("> ABI missmatch in %s - please check %s" % (name,tmp))
            
            with open(tmp,'w') as out:
              if len(added) != 0:
                out.write("> Chain ABI has '%s' and expected ABI dont\n" % (','.join(added)))
              if len(removed) != 0:
                out.write("> Expected ABI has %s and chain ABI dont\n" % (','.join(removed)))
              if len(changed) != 0:
                out.write("> They both differ '%s'\n" % (','.join(changed)))
            
              out.write('\n')
              out.write("# Chain ABI\n")
              out.write(json.dumps(current_abi, indent=2, sort_keys=True))
              out.write('\n')
              out.write("# Expected ABI\n")
              out.write(json.dumps(expected_abi, indent=2, sort_keys=True))
              out.write('\n')

      # Verify privileged
      if account['privileged'] != system_accounts[name]['privileged']:
        errs.append("> %s account wrong privileged setting" % (name))

      # Verify resignement
      if name != "eosio.null" and name != "eosio.prods":
        actor = system_accounts[name]['actor']
        permission = system_accounts[name]['permission']
        if authority_controlled_by_one_actor(account['permissions']["owner"], actor, permission) != True or \
           authority_controlled_by_one_actor(account['permissions']["owner"], actor, permission) != True:
          errs.append("> %s account NOT PROPERLY RESIGNED" % (name))

  if len(errs):
    warning()
    for er in errs: print er
  else:
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
      warning()
      print "> Invalid privileged account found : %s" % name
  else:
    success()
  return True

def validate_global_params_against_genesis(snapshot, genesis):
  
  step('Verifying global params vs genesis')

  table = snapshot['tables']['eosio']['eosio']['global']
  params = table[table.keys()[0]]['data']
  
  if not 'initial_configuration' in genesis:
    warning()
    print "> Unable to compare global params, initial_configuration not found in genesis"
    return True

  diff = []
  for gp in genesis['initial_configuration']:
    if genesis['initial_configuration'][gp] != params[gp]:
      diff.append(gp)

  if len(diff):
    warning()
    print "> The global params are different from genesis : %s" % diff
  else:
    success()

  return True

def validate_memory(snapshot): 
  
  step('Verifying 64Gb max ram size')

  table = snapshot['tables']['eosio']['eosio']['global']
  params = table[table.keys()[0]]['data']

  max_ram_size = int(params["max_ram_size"])>>30
  if max_ram_size != 64:
    warning()
    print "> Max ram size != 64Gb : (%d)" % max_ram_size
  else:
    success()

  return True

def validate_extra_accounts(snapshot, balances, args):

  step('Verifying extra accounts')

  extras = []
  total_balance = 0
  for account in snapshot['accounts']:
    if account not in balances and account not in system_accounts:
      extras.append(account)
      l,c,n = get_account_stake(snapshot, account, args.core_symbol)
      total_balance += l+c+n

  not_abp = []
  not_resigned = []
  abps = [abp['producer_name'] for abp in snapshot['block_header_state']['active_schedule']['producers']]

  for extra in extras:
    if extra not in abps:
      not_abp.append(extra)

    if authority_is_empty(snapshot['accounts'][extra]["permissions"]["active"]) or \
       authority_is_empty(snapshot['accounts'][extra]["permissions"]["owner"]):
      not_resigned.append(extra)

  ok = True

  if len(extra) > 21:
    if ok: warning(); ok=False
    print "> More than 21 extra accounts found"

  if len(not_abp) > 0:
    if ok: warning(); ok=False
    print "> At least one extra account is not an ABP"

  if total_balance > 0:
    if ok: warning(); ok=False
    print "> At least one extra account has liquid/staked balance"

  if not ok:
    tmp = tempfile.mkstemp()[1]
    with open(tmp,'w') as f:
      f.write("Extra accounts:")
      f.write('extras:' + str(extras) + '\n')
      f.write('not_abp:' + str(not_abp) + '\n')
      f.write('total_balance:' + str(total_balance) + '\n')
      f.write('not_resigned:' + str(not_resigned) + '\n')
      
    print "> Please check %s" % tmp
  else:  
    success()

  return True

def validate_EOS_token(snapshot, args):

  step('Verifying EOS token')

  symbol = args.core_symbol
  key = name_to_string(symbol2int(symbol), False)
  sym = str(symbol2int(symbol))

  eos_token = snapshot['tables']['eosio.token'][key]['stat'][sym]['data']
  
  ok = True
  if asset2int(eos_token['max_supply']) != 100000000000000:
    if ok: warning(); ok = False
    print "> EOS max supply != 10000M (%s)" % eos_token['max_supply']

  tokens = 0
  code = snapshot['tables']['eosio.token']
  for s in code:
    if 'stat' in code[s]: tokens += 1

  if tokens != 1:
    if ok: warning(); ok = False
    print "> more than one token found in eosio.token"

  if ok:
    success()

  return True

# Vanilla validation
def validate(args):

  # Load data
  eos_snapshot   = load_eos_snapshot(args)
  erc20_snapshot = load_erc20_snapshot(args)
  genesis        = load_genesis(args)

  # Genesis
  if not validate_genesis(eos_snapshot, genesis): return

  # Token
  if not validate_EOS_token(eos_snapshot, args): return

  # System
  if not validate_global_params_against_genesis(eos_snapshot, genesis): return

  if not validate_memory(eos_snapshot): return

  if not validate_system_accounts(eos_snapshot): return

  # Accounts
  erc20_snapshot = validate_account_creation(eos_snapshot, erc20_snapshot)
  if not erc20_snapshot: return

  if not validate_account_stake(eos_snapshot, erc20_snapshot, args): return

  if not validate_no_code_in_accounts(eos_snapshot, erc20_snapshot): return

  if not validate_account_permissions(eos_snapshot, erc20_snapshot): return

  if not validate_no_privileged_accounts(eos_snapshot): return

  if not validate_extra_accounts(eos_snapshot, erc20_snapshot, args): return
