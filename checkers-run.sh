#!/usr/bin/env bash

SCRIPTPATH="$(cd "$(dirname "$BASH_SOURCE")" && pwd)"
cd "$SCRIPTPATH"

if [ $# -eq 0 ]; then
  echo "USAGE: $0 <target-ip>"
  exit 1
else
  TARGET=$1
  shift
fi

echo "Testing all service checkers against $TARGET ..."

for d in services/*/ ; do
  servicename=$(basename "$d")
  echo ""
  echo "=== Checking service '$servicename' ==="
  echo "(full log in /tmp/service-checkers-$servicename.log)"
  timeout 120 ${d}gamelib/run-checkers "$TARGET" run "$@" 2>&1 | tee "/tmp/service-checkers-$servicename.log" | tail -7
done

echo ""
echo "[[DONE]]"
