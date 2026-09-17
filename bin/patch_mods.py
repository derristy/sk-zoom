"""Правит scene_global игры: отдалённая камера и отключённый туман.

Вход и выход - XML родного экспортёра Tudey. Если хоть одна из целей не нашлась,
скрипт падает с ошибкой, чтобы вызывающий не поставил в игру недопатченный файл.

Обновление игры от 17.09.2026 переписало формат. Раньше камера лежала в
`<implementation class="...$Camera">` со своим массивом `cameras`, а туман
снимался удалением реализации. Теперь и то и другое - производные записи:
у них `<base>` с именем шаблона и список аргументов ключ-значение.

Поэтому правим по правилу, а не по списку имён: любая запись, наследующая
`Camera`, получает своё расстояние и дальность отсечения, любая наследующая
`Environment/Fog` - отодвинутые за горизонт границы тумана.
"""

import sys
import xml.etree.ElementTree as ET

# Расстояние камеры до рыцаря и дальность отсечения. Coords - сферические:
# азимут, наклон, расстояние. Наклон оставляем игровой, меняем только длину.
# Расстояние камеры до рыцаря и дальность отсечения. После обновления 200
# оказалось слишком далеко: уровень сжимался в точку, а экран занимало небо.
# Подбираем от умеренного - игровое значение около 10, прежний мод ставил 200.
# Двести оказалось слишком далеко: уровень виден целиком, а рыцарь теряется.
# Девяносто даёт обзор комнаты и соседних, при этом рыцаря видно.
# Масштаб взят у самой игры: обычный вид - дистанция 9.99 при наклоне 45°,
# её собственная отдалённая камера `Lockdown/ZoomOut` - 24.0 при наклоне 55°.
# Прежние 200 работали до обновления 17.09.2026, после него это вид на весь
# уровень, где рыцаря не видно. Берём чуть дальше игровой отдалённой.
DISTANCE = 200.0
FAR = 550.0

# Туман не убираем, а отодвигаем: начало и конец за пределы любой сцены.
# Это надёжнее удаления - движок продолжает работать со своей структурой.
FOG_START, FOG_END = 10000.0, 20000.0


def args_of(entry):
    base = entry.find('base')
    return (base.findtext('name'), base.find('arguments')) if base is not None else (None, None)


def set_arg(args, key, value, cls):
    """Заменить значение по ключу, а если ключа нет - добавить пару."""
    kids = list(args)
    for i, node in enumerate(kids):
        if node.tag == 'key' and node.text == key and i + 1 < len(kids):
            kids[i + 1].text = value
            kids[i + 1].set('class', cls)
            return
    k = ET.SubElement(args, 'key')
    k.set('class', 'java.lang.String')
    k.text = key
    v = ET.SubElement(args, 'value')
    v.set('class', cls)
    v.text = value


src, dst = sys.argv[1], sys.argv[2]

# комментарии <!--empty--> значимы: без них теряются пустые поля choice
tree = ET.parse(src, ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))

cameras = fogs = 0

for entry in tree.getroot().iter('entry'):
    name, args = args_of(entry)
    if args is None:
        continue

    # Аргументы производных камер не трогаем. Там лежит вид ПО УМОЛЧАНИЮ:
    # у `Environment/Custom/Camera (Default)`, которой пользуется большинство
    # уровней, дистанция задана аргументом 9.99. Переписав её, мы отодвигали
    # обычную камеру, и в миссиях рыцарь оказывался далеко внизу. Зум живёт в
    # пресетах, их и правим - как делал прежний мод.
    elif name == 'Environment/Fog':
        for value in args.iter('value'):
            start = value.find('start')
            end = value.find('end')
            if start is not None:
                start.text = str(FOG_START)
            if end is not None:
                end.text = str(FOG_END)
        fogs += 1

# Зум игра берёт не из аргументов, а из пресетов: у записи камеры есть блок
# `camera` с обычными значениями и массив `cameras` с вариантами приближения.
# Обновление оставило этот механизм прямым записям, а корневую `Camera` сделало
# пустой - производные камеры подземелий наследуют от неё, и без пресета зум
# в этажах не менялся, сколько бы мы ни правили аргументы.
# Отдалённый вид - как в прежнем моде: строго сверху, дистанция 200.
COORDS = f'0.0, 1.5707964, {DISTANCE}'


# Обычный вид игры: наклон 45°, дистанция 9.99, дальность 50. Нужен там, где
# его нет в файле - иначе движку неоткуда взять вид по умолчанию, и он берёт
# первый пресет, то есть наш отдалённый. Так в миссиях ломался вид по
# умолчанию: уровень показывался сверху с огромной высоты.
STOCK_FAR = '50.0'
# Обычный вид ближе игрового: у неё 9.99, ставим 7.0 - рыцарь крупнее, а
# комната всё ещё видна целиком.
STOCK_COORDS = '0.0, 0.7853982, 7.0'


def force_camera(entry):
    """Прописать отдалённый вид одним пресетом зума."""
    # Обычный блок `camera` не трогаем, если он есть: это вид без зума, и
    # переписав его, мы ломаем нормальное состояние камеры. А вот когда его
    # нет вовсе - дописываем игровыми значениями, иначе движок возьмёт за
    # умолчание наш пресет.
    if entry.find('camera') is None:
        cam = ET.SubElement(entry, 'camera')
        ET.SubElement(cam, 'far').text = STOCK_FAR
        ET.SubElement(cam, 'coords').text = STOCK_COORDS
    old = entry.find('cameras')
    if old is not None:
        entry.remove(old)
    item = ET.SubElement(ET.SubElement(entry, 'cameras'), 'entry')
    ET.SubElement(item, 'zoom').text = '1'
    ET.SubElement(item, 'far').text = str(FAR)
    ET.SubElement(item, 'coords').text = COORDS


presets = 0
for entry in tree.getroot().iter('entry'):
    if (entry.get('class') or '').endswith('SceneGlobalConfig$Camera'):
        force_camera(entry)
        presets += 1

# Модели не трогаем вовсе. Очистка имени в пустую строку валит клиент: движок
# грузит модель по имени и падает с NullPointerException прямо в кадровом
# цикле, игра зависает на входе в комнату сбора. Туман гасим только границами.
haze = 0

# Фон не трогаем: он оказался ни при чём, темнило не он, а масштаб камеры.
back = 0

# Мешающие обзору модели убираем так же, как делал прежний мод: удаляем узел
# целиком, а не очищаем ему имя. Пустое имя клиент пытается загрузить и падает
# с NullPointerException прямо в кадровом цикле - игра зависает на входе.
HIDE = ('visionfog', 'horizonfog', 'global_fog')
haze = 0
parents = {child: parent for parent in tree.getroot().iter() for child in parent}
for model in list(tree.getroot().iter('model')):
    node = model.find('name')
    if node is None or not node.text:
        continue
    if any(word in node.text for word in HIDE):
        parents[model].remove(model)
        haze += 1

if presets == 0 or fogs == 0:
    sys.exit(f'структура конфига изменилась: пресетов {presets}, туманов {fogs}')

tree.write(dst, encoding='UTF-8', xml_declaration=True)
print(f'записей изменено: пресетов {presets},'
      f' туманов {fogs}, снято моделей {haze}')
