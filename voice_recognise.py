#!/usr/bin/env python3
import asyncio
import logging
import os
import subprocess
from concurrent.futures.thread import ThreadPoolExecutor
from typing import AsyncIterable

import speech_recognition as sr
from decorator import decorator

curDir = os.path.dirname(os.path.realpath(__file__))
srcDir = os.path.join(curDir, "Data", "SPEECH")
targetDir = os.path.join(curDir, "Data", "converted")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@decorator
def logExcDec(fun, *args, **kwargs):
    try:
        return fun(*args, **kwargs)
    except Exception as e:
        logger.error(e)
        raise


class Converter:
    def __init__(self, language='pl-PL', intermediateConvert=True):
        self.rec = sr.Recognizer()
        self.language = language
        self.intermediateConvert = intermediateConvert
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

    async def convert(self):
        queue = asyncio.Queue()
        await asyncio.gather(self.findNewNames(queue), self.renameFile(queue), loop=self.loop)

    async def findNewNames(self, queue: asyncio.Queue):
        with ThreadPoolExecutor(10, thread_name_prefix='RECOGNISE') as pool:
            features = []
            async for filename in self.wavFileGenerator():
                features.append(self.loop.run_in_executor(pool, self.recogniseFile(filename, queue)))

            x = await asyncio.wait(features)
            print(x)

    async def wavFileGenerator(self) -> AsyncIterable[str]:
        if self.intermediateConvert:
            tmpDir = targetDir.replace("converted", "tmp")
            os.makedirs(tmpDir, exist_ok=True)

            with ThreadPoolExecutor(10, thread_name_prefix='FILE') as pool:
                features = [self.loop.run_in_executor(pool, self._fixWav, file)
                            for file in os.scandir(srcDir)]
                for feature in features:
                    yield await feature

        else:
            for file in os.scandir(srcDir):  # type: os.DirEntry
                yield file.path

    @staticmethod
    @logExcDec
    def _fixWav(fileToFix: os.DirEntry):
        inputFile = fileToFix.path
        outputFile = fileToFix.path.replace("SPEECH", "tmp")
        program = f"ffmpeg -v error -y -i {inputFile} {outputFile}"
        process = subprocess.Popen(program.split())
        process.wait()
        return outputFile

    @logExcDec
    def recogniseFile(self, filename: str, queue: asyncio.Queue):
        with sr.AudioFile(filename) as source:
            audio = self.rec.record(source)

        try:
            text = self.rec.recognize_google(audio, language=self.language)
        except sr.UnknownValueError:
            logger.error("Cannot understand audio")
            raise
        except sr.RequestError as e:
            logger.error(e)
            raise

        logger.debug(f"File={filename.split('/')[-1]} has:'{text}'")
        self.addToQueue(queue, (filename, text))  #TODO
        return text

    async def addToQueue(self, queue, val):
        await queue.put(val)


    @staticmethod
    async def renameFile(queue: asyncio.Queue):
        os.makedirs(targetDir, exist_ok=True)

        while True:
            oldFilename, newFileName = await queue.get()
            if not newFileName.endswith('.wav'):
                newFileName += '.wav'
            logger.debug(f"os.rename({oldFilename}, {newFileName})")
            # os.rename(oldFilename, newFileName)


async def main():
    converter = Converter()
    await converter.convert()


if __name__ == '__main__':
    logging.basicConfig()
    asyncio.run(main())
