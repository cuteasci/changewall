import json
from pathlib import Path
from typing import Dict

import requests
from PySide2.QtCore import QObject, Signal, QRunnable

from helpers import short_path
from logger import logger


class Download(QObject):
    """
    Download a file as binary or use json.dump
    if file extension is '.json'.

    Emit "finished_file" signal with file path object
    when the file is downloaded. It is used
    to pass the file to stacked widget or set_wallpaper function.

    Pass "stream = True" to download file in chunks
    and emit "finished_chunk" signal each time a chunk
    is downloaded. It allows to show progress of
    downloading of a large file in progress bar.
    """
    finished_chunk = Signal(Path)
    finished_file = Signal(Path)

    def __init__(self, file: Path, dir_: Path, url: str, stream: bool = False,
                 payload: Dict[str, str] = None, parent=None):
        super().__init__(parent)
        self.dir_: Path = dir_
        self.file: Path = self.dir_.joinpath(file)
        self.url: str = url
        self.stream: bool = stream
        self.payload: Dict[str, str] = payload

        if self.payload is not None:
            if not isinstance(self.payload, dict):
                logger.error("Use {'key', 'value'} as query")

    def save(self):
        r = requests.get(self.url, stream=self.stream, params=self.payload)

        logger.debug(
            f'Trying to save {short_path(self.file)} from {r.url}')

        if r.status_code == 200:
            try:
                if self.file.suffix == '.json':
                    with open(self.file, 'w') as f:
                        json.dump(r.json(), f, indent=4)
                else:
                    with open(self.file, 'wb') as f:
                        logger.debug(
                            f'Opened {short_path(self.file)} for writing data')
                        if self.stream:
                            file_size = int(r.headers.get('Content-Length'))
                            for i, chunk in enumerate(r.iter_content(chunk_size=int(file_size / 23))):
                                f.write(chunk)
                                self.finished_chunk.emit(self.file)
                        else:
                            file_size = f.write(r.content)
                        self.finished_file.emit(self.file)
                        logger.debug(f'{self.file} {file_size / 1024:.1f}KB has been saved')
            except IOError as e:
                logger.debug(f'Could not open {short_path(self.file)} for writing')


class DownloadThread(QRunnable, Download):
    """
    QRunnable, which is used to run Download's save method asynchronously.
    To do that instantiate it and pass the instance to
    QThreadPool.globalInstance().start()
    """

    def __init__(self, file: Path, dir_: Path, url: str, stream: bool = False, payload: Dict[str, str] = None,
                 parent=None):
        super().__init__(parent)
        Download.__init__(self, file, dir_, url, stream=False, payload=None, parent=None)

    def run(self):
        self.save()
