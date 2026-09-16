#!/bin/bash
# Возвращает в scene_global.dat пресет отдалённой камеры после того, как
# getdown перезаписал конфиг при обновлении игры.
#
# Идемпотентен: если в игре уже лежит наш файл, выходит ничего не трогая.
# Патч каждый раз выводится заново из текущих данных игры, поэтому обновления
# контента не откатываются.
set -euo pipefail

HOME_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/sk-zoom"
BIN="$HOME_DIR/bin"
STATE="$HOME_DIR/state"
TMP="$HOME_DIR/tmp"

GAME="$HOME/snap/steam/common/.local/share/Steam/steamapps/common/Spiral Knights"
DAT="$GAME/rsrc/config/scene_global.dat"

CODE="$GAME/code"
CP="$BIN:$CODE/config.jar:$CODE/projectx-config.jar:$CODE/projectx-pcode.jar"
CP="$CP:$CODE/commons-beanutils.jar:$CODE/commons-digester.jar:$CODE/commons-logging.jar"

log () { echo "[sk-zoom] $*"; }

[ -f "$DAT" ] || { log "конфиг не найден: $DAT"; exit 0; }

cur=$(sha256sum "$DAT" | cut -d' ' -f1)
if [ "$cur" = "$(cat "$STATE/patched.sha" 2>/dev/null || true)" ]; then
    log "уже применено"
    exit 0
fi

log "конфиг изменился, накатываю патч заново"
mkdir -p "$TMP"
cp "$DAT" "$STATE/stock.dat"

java -cp "$CP" Conv b2x "$DAT" "$TMP/game.xml"
python3 "$BIN/patch_mods.py" "$TMP/game.xml" "$TMP/patched.xml"
java -cp "$CP" Conv x2b "$TMP/patched.xml" "$TMP/patched.dat"

# сверяем, что обратная конвертация даёт то же число записей
before=$(java -cp "$CP" Conv b2x "$STATE/stock.dat" "$TMP/check_before.xml")
after=$(java -cp "$CP" Conv b2x "$TMP/patched.dat" "$TMP/check_after.xml")
if [ "$before" != "$after" ]; then
    log "ОТМЕНА: состав конфигов разошёлся ($before -> $after)"
    exit 1
fi

cp "$TMP/patched.dat" "$DAT"
sha256sum "$DAT" | cut -d' ' -f1 > "$STATE/patched.sha"
rm -f "$TMP"/*.xml "$TMP/patched.dat"
log "готово: $after"
