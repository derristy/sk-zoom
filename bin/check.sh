#!/bin/bash
# Состояние мода одной командой: стоит ли патч, те ли в нём значения,
# следит ли systemd за файлом и видит ли правку запущенный клиент.
#
#   bin/check.sh            быстрая проверка, с дампом конфига
#   bin/check.sh --fast     без дампа, только хеши и юниты
set -uo pipefail

HOME_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/sk-zoom"
BIN="$HOME_DIR/bin"
STATE="$HOME_DIR/state"
GAME="$HOME/snap/steam/common/.local/share/Steam/steamapps/common/Spiral Knights"
DAT="$GAME/rsrc/config/scene_global.dat"

say () { printf '%s %s\n' "$1" "$2"; }
# Значения берём из самого патчера, чтобы проверка не разошлась с ним.
num () { grep -oP "^$1\s*=\s*\K[0-9.]+" "$BIN/patch_mods.py" | head -1; }
bad=0

if [ ! -f "$DAT" ]; then
    say - "конфига нет: $DAT"
    exit 1
fi

if [ "$(sha256sum "$DAT" | cut -d' ' -f1)" = "$(cat "$STATE/patched.sha" 2>/dev/null)" ]; then
    say + "патч применён"
else
    say - "в игре не наш файл, накатить: bin/apply.sh"
    bad=1
fi

if [ "${1:-}" != "--fast" ]; then
    xml=$(mktemp --suffix=.xml)
    if "$BIN/dump.sh" "$DAT" "$xml" > /dev/null 2>&1; then
        presets=$(grep -c ", $(num DISTANCE)<" "$xml")
        far=$(grep -c ">$(num FAR)<" "$xml")
        normal=$(grep -c "0.7853982, 9.99<" "$xml")
        fog=$(grep -cE "visionfog|horizonfog|global_fog" "$xml")
        empty=$(grep -c "<name></name>" "$xml")

        [ "$presets" -gt 0 ] && say + "пресетов зума: $presets на дистанции $(num DISTANCE), дальность $(num FAR) в $far записях" \
            || { say - "пресетов зума нет"; bad=1; }
        [ "$normal" -gt 0 ] && say + "обычный вид цел: записей $normal с дистанцией 9.99" \
            || { say - "обычный вид переписан, рыцарь окажется далеко внизу"; bad=1; }
        [ "$fog" -eq 0 ] && say + "туманные модели сняты" \
            || { say - "остались туманные модели: $fog"; bad=1; }
        [ "$empty" -eq 0 ] && say + "пустых имён моделей нет" \
            || { say - "пустые имена моделей: $empty, клиент упадёт в кадровом цикле"; bad=1; }
    else
        say - "конфиг не разворачивается в XML, смотреть bin/dump.sh"
        bad=1
    fi
    rm -f "$xml"
fi

watch=$(systemctl --user is-active sk-zoom.path 2>/dev/null)
if [ "$watch" = active ]; then
    say + "слежение за конфигом включено"
else
    say - "sk-zoom.path не работает ($watch), после обновления игры патч не вернётся"
    bad=1
fi

pid=$(pgrep -f "projectx.client.ProjectXApp" | grep -v "^$$\$" | head -1)
if [ -n "$pid" ]; then
    started=$(date -d "$(ps -o lstart= -p "$pid")" +%s)
    if [ "$(stat -c %Y "$DAT")" -gt "$started" ]; then
        say - "конфиг правился после запуска клиента - в игре пока старый вид, нужен перезапуск"
        bad=1
    else
        say + "запущенный клиент читал уже пропатченный конфиг"
    fi
fi

exit $bad
