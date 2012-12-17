#!/bin/bash
rm -rf /tmp/build
mkdir /tmp/build
THERET=`$* 2> /tmp/errors 1> /tmp/log`
if [ $? -gt 0 ]
then
    exit 2
fi
