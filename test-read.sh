#!/bin/bash
while true; do
  read -r -p "Ready? (y/N) " reply
  reply=${reply:-N}
  if [[ "$reply" =~ ^[Yy]([Ee][Ss])?$ ]]; then
    echo "Accepted YES"
    break
  elif [[ "$reply" =~ ^[Nn]([Oo])?$ ]]; then
    echo "Accepted NO"
    break
  else
    echo "Invalid input, please type y or n."
  fi
done
