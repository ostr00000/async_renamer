import logging
import os
import re
from collections import defaultdict

from typing import Dict, List

curDir = os.path.dirname(os.path.realpath(__file__))
pattern = re.compile("DEBUG:__main__:File=([A-Z_0-9]+.WAV) has:'(.*?)'")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def getFromLog():
    path = os.path.join(curDir, "Data", "log.txt")
    data = {}
    with open(path, 'r') as file:
        for line in file:
            if line.startswith('ERROR'):
                continue
            line = line.rstrip()
            match = pattern.match(line)
            if match:
                key = match.group(1)
                val = match.group(2)
                data[key] = val
            else:
                logger.error(f"Pattern doesn't match: {line}")
    return data


def getMissing():
    data = getFromLog()
    path = os.path.join(curDir, "Data", "SPEECH")
    names = {dirEntry.name for dirEntry in os.scandir(path)}
    converted = {k for k in data}
    logger.info(f"All:{len(names)}")
    unconverted = names.difference(converted)
    logger.info(f"Without recognised: {len(unconverted)}")

    return unconverted


def toJson(data: dict):
    import json
    output = 'index.json'
    path = os.path.join(curDir, "Data", output)
    with open(path, 'w') as file:
        json.dump(data, file, indent=4, sort_keys=True, ensure_ascii=False)


def getMissingByReplaced() -> List[str]:
    org2tr = getFromLog()
    tr2listOrg = defaultdict(list)
    for k, v in org2tr.items():
        tr2listOrg[v].append(k)

    rev = [elem for orgList in tr2listOrg.values() if len(orgList) != 1 for elem in orgList]
    rev.sort()
    return rev


def replaceDoubleWAV():
    for dirEntry in os.scandir(os.path.join(curDir, "Data", 'converted')):  # type: os.DirEntry
        name: str = dirEntry.name
        if name.lower().endswith('.wav.wav'):
            newPath = os.path.join(os.path.dirname(dirEntry.path), name[:-8] + '.wav')
            os.rename(dirEntry.path, newPath)


if __name__ == '__main__':
    logging.basicConfig()
    replaceDoubleWAV()
    toJson(getFromLog())
