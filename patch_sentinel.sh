#!/bin/bash
file=".jules/sentinel.md"
sed -i '/<<<<<<< HEAD/d' "$file"
sed -i '/=======/d' "$file"
sed -i '/>>>>>>> origin\/main/d' "$file"
