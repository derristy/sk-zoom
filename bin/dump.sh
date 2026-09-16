#!/bin/bash
# Показывает любой бинарный конфиг игры в виде XML.
#
#   dump.sh <файл.dat> [выход.xml]
#
# Без второго аргумента печатает в stdout. Работает с любым .dat движка Tudey:
# rsrc/config/*.dat, rsrc/ui/**/*.dat, rsrc/world/**/*.dat.
set -euo pipefail

BIN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAME="$HOME/snap/steam/common/.local/share/Steam/steamapps/common/Spiral Knights"
CODE="$GAME/code"

CP="$BIN:$CODE/config.jar:$CODE/projectx-config.jar:$CODE/projectx-pcode.jar"
CP="$CP:$CODE/commons-beanutils.jar:$CODE/commons-digester.jar:$CODE/commons-logging.jar"

src="$1"
# короткий путь: dump.sh config/scene_global.dat
[ -f "$src" ] || src="$GAME/rsrc/$1"

if [ $# -ge 2 ]; then
    java -cp "$CP" Conv b2x "$src" "$2" >/dev/null
    echo "$2"
else
    out=$(mktemp --suffix=.xml)
    java -cp "$CP" Conv b2x "$src" "$out" >/dev/null
    cat "$out"
    rm -f "$out"
fi
