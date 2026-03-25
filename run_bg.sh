#!/bin/bash
bash -c 'kill -15 $$' >out.log 2>&1
cat out.log
