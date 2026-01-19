#!/bin/bash
services=()
while read -r line; do
  services+=("$line")
done < <(echo -e "A\nB\nC")
echo "Count: ${#services[@]}"
for s in "${services[@]}"; do echo "Service: $s"; done
