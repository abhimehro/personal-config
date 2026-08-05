#!/bin/bash
echo "Testing HTML reports generation..."
mkdir -p /tmp/reports
maintenance/bin/analytics_dashboard.sh --test || true
maintenance/bin/performance_optimizer.sh --test || true
ls -al /tmp/reports
