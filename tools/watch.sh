#!/bin/bash
#
# Simple wrapper to watch agent activity live
# Usage: ./tools/watch.sh

echo "🔴 LIVE AGENT MONITORING"
echo "========================"
echo "Watching ALL sessions for activity..."
echo "(Press Ctrl+C to stop)"
echo ""

# Watch ALL sessions in follow mode
python3 tools/tail_logs.py --all -f