#!/bin/bash
ME="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ -f $ME/nodeos.pid ]; then
  kill `cat $ME/nodeos.pid` 
  rm -f $ME/nodeos.pid
fi
