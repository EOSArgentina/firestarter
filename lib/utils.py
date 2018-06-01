import os
import sys

animation = "|/-\\"
anim_index = 0

class InvalidAsset(Exception):
  pass

def revhex(v):
  return "".join(reversed([v[i:i+2] for i in range(0, len(v), 2)]))

def char_to_symbol(c):
  if( c >= 'a' and c <= 'z' ):
    return (ord(c) - ord('a')) + 6;
  if( c >= '1' and c <= '5' ):
    return (ord(c) - ord('1')) + 1;
  return 0;

def string_to_name(s):
  name = 0;
  i = 0;
  while i < len(s) and i < 12:
    name |= (char_to_symbol(s[i]) & 0x1f) << (64 - 5 * (i + 1));
    i+=1

  if (len(s)==13):
    name |= char_to_symbol(s[12]) & 0x0F;
  return name;

class DictDiffer(object):
  """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
  """
  def __init__(self, current_dict, past_dict):
    self.current_dict, self.past_dict = current_dict, past_dict
    self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
    self.intersect = self.set_current.intersection(self.set_past)

  def added(self):
    return self.set_current - self.intersect
  
  def removed(self):
    return self.set_past - self.intersect

  def changed(self):
    return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])

  def unchanged(self):
    return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])

# def int2name(n):
  

def asset2int(amountstr):
  try:
    parts = amountstr.split()
    if len(parts) != 2 or not parts[1].isupper() or len(parts[1]) > 7: raise
    inx = parts[0].rindex('.')
    if parts[0].index('.') != inx: raise
    if len(parts[0]) - inx - 1 != 4: raise
    v = parts[0].replace('.','')
    return int(v)
  except:
    raise InvalidAsset("Invalid string amount '%s'" % amountstr)

def int2asset(amountint, symbol):
  s = '%d' % amountint
  if( len(s) < 5 ):
    s = (5-len(s))*'0' + s
  return s[:-4] +'.'+ s[-4:] + ' ' + symbol

def tick():
  global anim_index
  sys.stdout.write("\b" + animation[anim_index % len(animation)])
  sys.stdout.flush()
  anim_index = anim_index + 1

def step(name): 
 sys.stdout.write('\r{0: <50}'.format(name))
 sys.stdout.flush()

def fail():
  sys.stdout.write('\b\x1b[1;31m' + 'FAIL' + '\x1b[0m\n')
  sys.stdout.flush()

def success():
  sys.stdout.write('\b\x1b[6;30;42m' + 'OK' + '\x1b[0m\n')
  sys.stdout.flush()

def warning():
  sys.stdout.write('\b\x1b[1;43m' + 'WARNING' + '\x1b[0m\n')
  sys.stdout.flush()