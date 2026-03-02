#!/bin/bash
sed -i.bak '/# Mock command dependencies/a\
sudo() { "$@"; }\
killall() { echo "mock_killall" >/dev/null; }' tests/test_dns_utils.sh
