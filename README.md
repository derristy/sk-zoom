# Моды конфигов Spiral Knights

Правится один файл игры - `rsrc/config/scene_global.dat`. Всё остальное
содержимое не трогается.

Игра: `~/snap/steam/common/.local/share/Steam/steamapps/common/Spiral Knights`

## Что изменено

**Камера - пресет зума** в каждой записи типа `SceneGlobalConfig$Camera`
(сейчас их 5, включая корневую `Camera`):

```
zoom   = 1
far    = 550.0
coords = 0.0, 1.5707964, 200.0     наклон 90°, дистанция 200
```

Обычный вид (`<camera>`) **не трогается**: там остаётся игровое - наклон 45°,
дистанция 9.99, far 50. Правится только массив `<cameras>`, то есть варианты
приближения. Переписав обычный блок, ломаешь вид без зума.

**Туман - отодвинутые границы** во всех записях, наследующих `Environment/Fog`
(сейчас 38):

```
start = 10000.0
end   = 20000.0
```

**Туманные модели - сняты целиком** (сейчас 34 узла): `visionfog`, `horizonfog`,
`global_fog`. Это то, что застилает обзор при отдалённой камере.

Купол неба, звездопад, дождь, лучи и фон **не трогаются**: их снятие убирает то,
что должно быть видно, а помехи не убирает.

## Формат после обновления 17.09.2026

Обновление переписало `scene_global.dat`: записей стало 1455 вместо 273, и форма
стала другой. Старый патчер сломался именно на этом, а не на обфускации.

**Было:** камера лежала в `<implementation class="...$Camera">` со своим массивом
`cameras`, туман снимался удалением всей реализации.

**Стало:** камеры и туман - производные записи `DerivedConfig`, у них `<base>` с
именем шаблона и список аргументов ключ-значение:

```xml
<entry class="com.threerings.config.DerivedConfig">
  <name>Environment/Custom/Clockwork Tunnels/Spooky/Camera</name>
  <base>
    <name>Camera</name>
    <arguments>
      <key class="java.lang.String">Coords</key>
      <value class="com.threerings.math.SphereCoords">0.0, 0.7853982, 9.99</value>
      <key class="java.lang.String">Far</key>
      <value class="java.lang.Float">55.0</value>
    </arguments>
  </base>
</entry>
```

Прямые записи `SceneGlobalConfig$Camera` (корневая и три городские) сохранили
старое устройство с блоками `<camera>` и `<cameras>`.

Поэтому патчер теперь работает **по правилу, а не по списку имён**: всё, что
наследует `Camera`, получает своё расстояние, всё, что наследует
`Environment/Fog`, - отодвинутые границы. Следующее обновление такой патчер
переживёт легче.

## Грабли, на которые уже наступали

**Пустое имя модели валит клиент.** Очистка `<name>` у `<model>` в пустую строку
даёт бесконечный `NullPointerException` в кадровом цикле: движок грузит модель по
имени. Игра зависает на входе в комнату сбора, в `projectx.log` сотни повторов
`Caught exception in frame loop`. Убирать модель надо **удалением узла целиком** -
так делал и прежний мод.

**Зум берётся из пресета, а не из аргументов.** Корневая `Camera` после
обновления пустая, одни описания параметров. Производные камеры подземелий
наследуют от неё, и без пресета в ней зум в этажах не меняется, сколько ни правь
`Coords` и `Far` в аргументах.

**`state/stock.dat` перезаписывается при каждом запуске** из текущего файла игры.
Если в игре уже испорченный файл, оригинал теряется. Чистая копия отложена
отдельно: `state/stock-clean.dat`, её же можно вернуть руками.

**`state/patched.sha` мешает при правке скрипта.** Хеш файла игры не меняется от
того, что ты поправил патчер, и `apply.sh` выходит с «уже применено». Перед
проверкой правок: `rm state/patched.sha`.

**Что оказалось ни при чём.** Фон (`Environment/Background Color`), купол неба,
звездопад и лучи - к затемнению обзора отношения не имеют. Их правка только
убирает нужное.

## Как это держится

Патч **выводится из текущих данных игры**, а не ставится готовым файлом. Поэтому
обновления контента не откатываются: после патча в файле столько же записей,
отличаются только наши.

```
scene_global.dat --Conv b2x--> XML --patch_mods.py--> XML --Conv x2b--> scene_global.dat
```

Возврат после обновления игры делают юниты systemd (user):

- `sk-zoom.path` следит за `scene_global.dat`
- `sk-zoom.service` запускает `bin/apply.sh`, когда файл изменился, и при входе в систему

`apply.sh` идемпотентен: если в игре уже наш файл, он выходит молча, поэтому
собственная запись не вызывает зацикливания. Прогонять руками безопасно сколько
угодно.

## Файлы

| Путь | Что |
|---|---|
| `bin/Conv.java`, `Conv.class` | конвертер `.dat` <-> XML поверх классов игры |
| `bin/patch_mods.py` | сам патч, значения задаются в начале файла |
| `bin/apply.sh` | собирает и ставит, идемпотентно |
| `bin/dump.sh` | посмотреть любой конфиг игры в XML |
| `state/stock.dat` | снимок файла игры перед последней правкой |
| `state/stock-clean.dat` | заведомо чистый оригинал, для отката |
| `state/patched.sha` | отпечаток нашего файла, по нему проверяется «уже применено» |

## Частые операции

Посмотреть любой конфиг игры (работает и с интерфейсом, и с моделями):

```bash
bin/dump.sh config/scene_global.dat > /tmp/cfg.xml
bin/dump.sh ui/hud_v2/interface_status.dat | less
```

Изменить зум или состав правок - править константы в начале `bin/patch_mods.py`
(`DISTANCE`, `FAR`, `FOG_START`, `FOG_END`, `HIDE`), затем:

```bash
rm state/patched.sha && bin/apply.sh
```

Проверить, что встало в игру:

```bash
bin/dump.sh config/scene_global.dat /tmp/check.xml
grep -c '1.5707964, 200.0' /tmp/check.xml     # пресетов зума
grep -c '0.7853982, 9.99'  /tmp/check.xml     # обычный вид цел
grep -c 'visionfog\|horizonfog\|global_fog' /tmp/check.xml   # должно быть 0
grep -c '<name></name>' /tmp/check.xml        # должно быть 0, иначе клиент упадёт
```

Полный откат:

```bash
systemctl --user disable --now sk-zoom.path sk-zoom.service
cp state/stock-clean.dat "$HOME/snap/steam/common/.local/share/Steam/steamapps/common/Spiral Knights/rsrc/config/scene_global.dat"
```

Посмотреть, что происходило:

```bash
journalctl --user -u sk-zoom.service -n 50
tail -40 "$HOME/snap/steam/common/.local/share/Steam/steamapps/common/Spiral Knights/projectx.log"
```

## Если перестало работать

Скрипт никогда не ставит полуфабрикат: файл собирается во временной папке и
копируется в игру только после успешной сборки и сверки состава записей. Если
что-то сломалось, в игре остаётся предыдущий файл, а причина видна в журнале.

- **«структура конфига изменилась»** - игра переименовала или перестроила записи.
  Посмотреть текущее состояние через `dump.sh` и поправить правила в
  `patch_mods.py`. Ориентироваться на `<base><name>`, а не на имена записей.
- **Игра зависает на входе, в `projectx.log` сыплется `NullPointerException`** -
  где-то осталась ссылка на несуществующую модель. Проверить `<name></name>`
  и вернуть `state/stock-clean.dat`.
- **`NoSuchMethodError` или `ClassNotFoundException`** - обновились jar'ы игры.
  Пересобрать конвертер (javac есть внутри снапов IDE, в системе стоит только JRE):

  ```bash
  G="$HOME/snap/steam/common/.local/share/Steam/steamapps/common/Spiral Knights"
  CP="$G/code/config.jar:$G/code/projectx-config.jar:$G/code/projectx-pcode.jar"
  CP="$CP:$G/code/commons-beanutils.jar:$G/code/commons-digester.jar:$G/code/commons-logging.jar"
  /snap/android-studio/current/jbr/bin/javac -cp "$CP" -d bin bin/Conv.java
  ```

  Сам `Conv` ищет методы импортёра и экспортёра рефлексией по сигнатуре, а не по
  обфусцированным именам, так что переименования при обфускации он переживает.

## Почему правка вообще живёт

Распакованные файлы `rsrc/` в `digest.txt` не перечислены - getdown сверяет только
бандл `rsrc/full-rest-bundle.jar`, а распаковывает его один раз на версию (метка в
`unpacked.dat`). Плюс сама проверка маркерная, а не хеширующая: в `launcher.log`
видно `Verified resources [count=29, alreadyValid=29, size=452887k, duration=6ms]`.

## Бот в том же клиенте

Бот (`~/sk-bot`) встраивается в `code/projectx-pcode.jar` и с этим модом не
связан, но ломается тем же обновлением. Чинится так:

```bash
cd ~/sk-bot && bin/install.sh
```

**Важно:** патчер бота берёт исходник из `code/projectx-pcode.jar.stock`. После
обновления игры этот файл - копия **старой** версии, и установка вернёт клиенту
старый jar. Перед установкой старый `.stock` убрать, чтобы исходником стал
свежий jar.

Сам патчер ищет классы по устройству, а не по именам (контроллер сцены - по
очереди `InputFrame` и методам клавиш, фабрику кадров - по сигнатуре метода),
поэтому обфускация ему безразлична.
