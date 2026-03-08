#!/bin/bash
export NODE_MODULES_MAX_AGE_DAYS=90
export NODE_MODULES_MAX_GB=0

echo "Creating mock data..."
search_path=$(mktemp -d -t test_node_modules.XXXXXX)
trap 'rm -rf "$search_path"' EXIT
for i in {1..200}; do
  mkdir -p "/tmp/test_node_modules/proj_$i/node_modules"
  touch "/tmp/test_node_modules/proj_$i/package.json"
  if (( i % 2 == 0 )); then
    touch -t 202001010000 "/tmp/test_node_modules/proj_$i/node_modules"
  fi
done

search_path="/tmp/test_node_modules"

echo "Optimized:"
time {
  count=0
  find "$search_path" -name "node_modules" -type d -mtime +"${NODE_MODULES_MAX_AGE_DAYS:-90}" -print0 2>/dev/null | while IFS= read -r -d '' node_modules_dir; do
      if [[ -f "$node_modules_dir/../package.json" ]]; then
          count=$((count + 1))
      fi
  done
  echo "Found $count"
}
