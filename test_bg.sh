#!/bin/bash
exec sleep 10 &
kill -15 $!
