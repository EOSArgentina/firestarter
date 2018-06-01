#!/bin/bash
for i in {a..v} ;do 
  cleos create key | grep key | cut -d " " -f3 >> $(head -c 12 < /dev/zero | tr '\0' $i).key ;
done
