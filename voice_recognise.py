#!/usr/bin/env python3
import asyncio
import logging
import os
import subprocess
from concurrent.futures.thread import ThreadPoolExecutor
from queue import Queue
from typing import AsyncIterable

from decorator import decorator

try:
    import speech_recognition as sr
except ImportError:
    import mock as sr

curDir = os.path.dirname(os.path.realpath(__file__))
srcDir = os.path.join(curDir, "Data", "SPEECH")
targetDir = os.path.join(curDir, "Data", "converted")
tmpDir = os.path.join(curDir, "Data", "tmp")

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
    def __init__(self, language='pl-PL', intermediateConvert=True,
                 recogniseNumber=4, converterNumber=10):
        self.rec = sr.Recognizer()
        self.language = language
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

        self.intermediateConvert = intermediateConvert
        self.recogniseNumber = recogniseNumber
        self.converterNumber = converterNumber

        self.paths = None

    async def convert(self):
        queue = asyncio.Queue()
        prod: asyncio.Task = self.loop.create_task(self.produceNames(queue))
        cons: asyncio.Task = self.loop.create_task(self.renameFile(queue))
        await prod
        await queue.put(None)
        await cons

    async def produceNames(self, queue: asyncio.Queue):
        limit = self.recogniseNumber
        localQueue = Queue()
        gen = self.wavFileGenerator()

        with ThreadPoolExecutor(limit) as pool:
            async for filename in gen:
                localQueue.put(self.loop.run_in_executor(pool, self.recogniseFile, filename))
                limit -= 1
                if limit == 0:
                    break

            async for filename in gen:
                localQueue.put(self.loop.run_in_executor(pool, self.recogniseFile, filename))
                await queue.put(await (localQueue.get()))

            while not localQueue.empty():
                await queue.put(await (localQueue.get()))

    async def wavFileGenerator(self) -> AsyncIterable[str]:
        if self.intermediateConvert:
            os.makedirs(tmpDir, exist_ok=True)
            gen = self.paths if self.paths else os.scandir(srcDir)

            with ThreadPoolExecutor(10, thread_name_prefix='FILE') as pool:
                futures = [self.loop.run_in_executor(pool, self._fixWav, file) for file in gen]
                for future in futures:
                    yield await future
        else:
            for file in os.scandir(srcDir):  # type: os.DirEntry
                yield file.path

    @staticmethod
    @logExcDec
    def _fixWav(fileToFix: os.DirEntry):
        outputFile = os.path.join(tmpDir, fileToFix.name)
        inputFile = fileToFix.path

        program = "ffmpeg -v error -y -i".split()
        program.extend([inputFile, outputFile])

        process = subprocess.Popen(program, stdout=subprocess.DEVNULL)
        process.wait()
        return outputFile

    @logExcDec
    def recogniseFile(self, filename: str):
        with sr.AudioFile(filename) as source:
            audio = self.rec.record(source)

        text = None
        try:
            text = self.rec.recognize_google(audio, language=self.language)
        except sr.UnknownValueError:
            logger.error("Cannot understand audio")
        except sr.RequestError as e:
            logger.error(e)

        if not text:
            text = os.path.basename(filename)

        logger.debug(f"File={filename.split('/')[-1]} has:'{text}'")
        return filename, text

    async def renameFile(self, queue: asyncio.Queue):
        os.makedirs(targetDir, exist_ok=True)

        while True:
            data = await queue.get()
            if data is None:
                break

            oldFilename, decoded = data  # type: str, str
            os.rename(oldFilename, self.getFileName(decoded))

        if self.intermediateConvert:
            os.rmdir(tmpDir)

    @staticmethod
    def getFileName(fileName) -> str:
        if not fileName.lower().endswith('.wav'):
            fileName += '.wav'

        pathTemplate = os.path.join(targetDir, '{}')
        baseName, ext = os.path.splitext(fileName)
        newPath = pathTemplate.format(fileName)

        counter = 1
        while os.path.exists(newPath):
            newPath = pathTemplate.format(f"{baseName}_{counter}{ext}")
            counter += 1

        return newPath


async def main():
    converter = Converter()
    import log_conver
    missing = log_conver.getMissingByReplaced()
    converter.paths = [p for p in os.scandir(srcDir) if p.name in missing]
    await converter.convert()


if __name__ == '__main__':
    logging.basicConfig()
    asyncio.run(main())
