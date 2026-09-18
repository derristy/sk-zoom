#!/usr/bin/env python3
"""Достаёт конфиги старой версии игры из бандла на CDN, не скачивая его целиком.

Бандл `rsrc/intro-bundle.jar` весит ~100 МБ, а нужны из него два-три файла по
несколько сотен килобайт. S3 отдаёт куски по Range, поэтому zip читается прямо
по сети: сначала оглавление с конца файла, потом только нужные записи.

    bin/fetch-old.py 20260916140813 /tmp/old config/attack.dat config/item.dat

Номер старой версии видно в логе лаунчера игры:

    grep "Performing unpack" launcher.log
    INFO Performing unpack [version=20260916140813, aversion=20260918113549]

Здесь `version` - то, что было распаковано до обновления, `aversion` - то, что
приехало. Текущая лежит в `version.txt` рядом с игрой.
"""
import io
import os
import sys
import urllib.request
import zipfile

APPBASE = "http://gamemedia2.spiralknights.com/spiral/{version}/rsrc/intro-bundle.jar"


class HttpFile(io.RawIOBase):
    """Файл только для чтения поверх HTTP Range."""

    def __init__(self, url):
        self.url = url
        self.pos = 0
        head = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(head, timeout=30) as resp:
            self.size = int(resp.headers["Content-Length"])

    def seek(self, offset, whence=os.SEEK_SET):
        if whence == os.SEEK_SET:
            self.pos = offset
        elif whence == os.SEEK_CUR:
            self.pos += offset
        else:
            self.pos = self.size + offset
        return self.pos

    def tell(self):
        return self.pos

    def seekable(self):
        return True

    def readable(self):
        return True

    def readinto(self, buf):
        if not len(buf) or self.pos >= self.size:
            return 0
        last = min(self.pos + len(buf), self.size) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{last}"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        buf[:len(data)] = data
        self.pos += len(data)
        return len(data)


def main():
    if len(sys.argv) < 4:
        print(__doc__, file=sys.stderr)
        return 2
    version, out_dir, names = sys.argv[1], sys.argv[2], sys.argv[3:]
    os.makedirs(out_dir, exist_ok=True)
    url = APPBASE.format(version=version)
    with zipfile.ZipFile(io.BufferedReader(HttpFile(url), buffer_size=1 << 16)) as bundle:
        for name in names:
            data = bundle.read(name)
            target = os.path.join(out_dir, name.replace("/", "_"))
            with open(target, "wb") as out:
                out.write(data)
            print(f"{name}: {len(data)} байт -> {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
