import argparse
import traceback
import importlib

from utils import fail

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Validate EOS snapshot.')
  parser.add_argument('--genesis', metavar='file', help="Path to genesis.json", default="./genesis.json")
  parser.add_argument('--snapshot', metavar='snapshot', help="Path to EOS snapshot.json generated with snapshot_plugin", default="./snapshot.json")
  parser.add_argument('--csv-balance', metavar='csv', help="Path to snapshot.csv (ERC20)", default="./snapshot.csv")
  parser.add_argument('--validator', metavar='rules', help="Validation rules", default="vanilla_validator")
  parser.add_argument('--core-symbol', metavar='symbol', help="Core Symbol Name", default="EOS")

  args = parser.parse_args()

  try:
    validator = importlib.import_module(args.validator)
    print 'Validating EOS blockchain snapshot against "%s"' % getattr(validator,'description')()

    try:
      getattr(validator,'validate')(args)
    except Exception as ex:
      fail()
      print
      print "##########################################################"
      print str(ex)
      print traceback.format_exc()
      print "##########################################################"

  except Exception as ex:
    print "Unable to load validator %s.py" % args.validator
    print "##########################################################"
    print str(ex)
    print traceback.format_exc()
    print "##########################################################"
