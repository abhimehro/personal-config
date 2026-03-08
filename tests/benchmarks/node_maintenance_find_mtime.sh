#!/bin/bash
export NODE_MODULES_MAX_AGE_DAYS=90
export NODE_MODULES_MAX_GB=5

echo "Creating mock data..."
test_dir="/tmp/test_node_modules"
if [[ -d "$test_dir" ]]; then
  rm -rf "$test_dir"
fi
mkdir -p "$test_dir"
for i in {1..200}; do
	mkdir -p "/tmp/test_node_modules/proj_$i/node_modules"
	touch "/tmp/test_node_modules/proj_$i/package.json"
	if ((i % 2 == 0)); then
		touch -t 202001010000 "/tmp/test_node_modules/proj_$i/node_modules"
	fi
done

search_path="/tmp/test_node_modules"

echo "Optimized:"
time {
	count=0
	while IFS= read -r -d '' node_modules_dir; do
		if [[ -d $node_modules_dir ]] && [[ -f "$node_modules_dir/../package.json" ]]; then
			count=$((count + 1))
		fi
	done < <(find "$search_path" -name "node_modules" -type d -mtime +"${NODE_MODULES_MAX_AGE_DAYS:-90}" -print0 2>/dev/null)
	echo "Found $count"
}
