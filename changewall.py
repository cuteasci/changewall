"""
Simple program to download and set wallpapers from wallheaven.cc
"""
import json
import sys
from pathlib import Path
from typing import Dict

from PySide2.QtCore import QThreadPool, QTimer
from PySide2.QtGui import QGuiApplication
from PySide2.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
                               QVBoxLayout, QMessageBox)

from widgets import (Button, ProgressBar,
                     StackedWidget)
from downloader import Download, DownloadThread
from helpers import (create_dirs, image_info, is_dir_contains_images,
                     short_path, set_wall, get_screen_res)
from logger import logger
from config import APP_DIR, JSON_FILE, SEARCH_URL, THUMBS_DIR, CURRENT_DIR, SAVED_DIR, INFO_COLOR, config, config_save, \
    win_size, win_pos


class Changewall(QDialog):
    """ Parent of all the widgets """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.screen_width, self.screen_height = get_screen_res(screen)
        self.screen_res: str = f'{self.screen_width}x{self.screen_height}'
        self.payload: Dict[str, str] = {'sorting': 'random', 'categories': '100', 'atleast': self.screen_res}

        self.sw = StackedWidget()

        self.progressbar = ProgressBar()
        self.progressbar.hide()

        self.prev_btn = Button('angle-left.svg', key='left')
        self.next_btn = Button('angle-right.svg', key='right')
        self.update_btn = Button('sync-alt.svg', ' Update', key='r')
        self.apply_btn = Button('check.svg', 'Apply')
        self.save_btn = Button('save.svg', 'Save')

        self.prev_btn.clicked.connect(self.prev)
        self.next_btn.clicked.connect(self.next)
        self.apply_btn.clicked.connect(self.apply)
        self.update_btn.clicked.connect(self.update_)
        self.save_btn.clicked.connect(self.save)

        self.saved_msg = QLabel('Saved')
        self.image_count = QLabel()
        self.image_res = QLabel()
        self.saved_msg.setStyleSheet(f'color: {INFO_COLOR}')
        self.image_count.setStyleSheet(f'color: {INFO_COLOR}')
        self.image_res.setStyleSheet(f'color: {INFO_COLOR}')

        self.info_layout = QHBoxLayout()
        self.info_layout.addWidget(self.progressbar)
        self.info_layout.addStretch()
        self.info_layout.addWidget(self.image_count)
        self.info_layout.addWidget(self.image_res)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.prev_btn)
        button_layout.addWidget(self.next_btn)
        button_layout.addWidget(self.update_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.save_btn)

        self.main_layout = QVBoxLayout()
        self.main_layout.addLayout(self.info_layout)
        self.main_layout.addWidget(self.sw)
        self.main_layout.addLayout(button_layout)
        self.setLayout(self.main_layout)

        self.sw.added.connect(self.change_image_count)

    def prev(self) -> None:
        """ Show previous image in stacked widget """
        current_index: int = self.sw.currentIndex()
        if current_index > 0:
            self.sw.setCurrentIndex(current_index - 1)
        logger.debug(
            f"Stacked widget's current index is {self.sw.currentIndex()}")
        self.change_info()

    def next(self) -> None:
        """ Show next image in stacked widget """
        current_index: int = self.sw.currentIndex()
        self.sw.setCurrentIndex(current_index + 1)
        logger.debug(
            f"Stacked widget's current index is {self.sw.currentIndex()}")
        self.change_info()

    def update_(self) -> None:
        """
        Download new json, new thumbnails and delete old ones
        with clearing stacked widget
        """
        for file in THUMBS_DIR.iterdir():
            logger.debug(f'Deleting {short_path(file)}')
            file.unlink()

        # Clear stacked widget
        for _ in range(self.sw.count()):
            widget = self.sw.widget(0)
            self.sw.removeWidget(widget)
            del widget

        download = Download(JSON_FILE, APP_DIR, SEARCH_URL, payload=self.payload)
        download.save()

        self.progressbar.show()
        self.download_thumbs()

    def apply(self) -> None:
        """ Set current image as wallpaper """
        for file in CURRENT_DIR.iterdir():
            file.unlink()
            logger.debug(f'Deleted {short_path(file)}')

        image_id: str = self.sw.current_image_id()
        info: Dict[str, str] = image_info(image_id)
        image: Path = Path(info['image_id'] + info['extension'])

        self.progressbar.show()
        download = Download(image, CURRENT_DIR, info['full_image_url'], stream=True)
        download.finished_chunk.connect(self.set_progressbar)
        download.finished_file.connect(set_wall)
        download.save()

    def save(self) -> None:
        """
        Save image to CURRENT_DIR
        When image is saved, show Saved label
        """
        image_id: str = self.sw.current_image_id()
        info: Dict[str, str] = image_info(image_id)
        image: Path = Path(info['image_id'] + info['extension'])

        self.progressbar.show()
        download = Download(image, SAVED_DIR, info['full_image_url'], stream=True)
        download.finished_chunk.connect(self.set_progressbar)
        download.save()

        # Show message "Saved" for 3 seconds in info layout
        self.info_layout.insertWidget(2, self.saved_msg)
        self.saved_msg.show()
        QTimer.singleShot(3000, self.hide_msg)

        save_msg: bool = config.getboolean('Program', 'show_save_message')

        def disable_save_msg():
            config['Program']['show_save_message'] = 'no'
            config_save()
            logger.debug('Save message is now disabled')

        # Create and show "save message box" if it is set to True
        if save_msg:
            msgBox = QMessageBox(self)
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText('Saved')
            msgBox.setInformativeText(f'The image has been saved to \n{str(SAVED_DIR)}')
            msgBox.setStandardButtons(QMessageBox.Ok)
            dontshow_btn = msgBox.addButton("Don't show again", QMessageBox.ActionRole)
            dontshow_btn.clicked.connect(disable_save_msg)
            msgBox.exec_()

    def hide_msg(self) -> None:
        """ Remove save label from info layout and hide it """
        self.info_layout.removeWidget(self.saved_msg)
        self.saved_msg.hide()

    def download_thumbs(self) -> None:
        """
        Parse JSON_FILE then download thumbnails asynchronously.

        Each time thumbnail is downloaded, signals are emitted to
        stacked widget and progressbar
        """
        with open(JSON_FILE, 'r') as f:
            data: Dict = json.load(f)
            for item in data['data']:
                url: str = item['thumbs']['large']
                name: Path = Path(item['id'] + '.' + url[-3:])
                dt = DownloadThread(name, THUMBS_DIR, url)
                dt.finished_file.connect(self.sw.add)
                dt.finished_file.connect(self.set_progressbar)
                QThreadPool.globalInstance().start(dt)

    def change_image_count(self) -> None:
        """
        Update info of current image position in stacked widget
        and total number of images
        """
        self.image_count.setText(self.sw.count_info())

    def change_info(self) -> None:
        """
        Everytime change_info is called
        it get info of current image to
        update label 'image_res' with
        image resolution and image
        position in stacked widget
        """
        info: Dict[str, str] = image_info(self.sw.current_image_id())
        self.change_image_count()
        if len(info) > 0:
            self.image_res.setText(info['resolution'])
        else:
            self.image_res.setText('Image info not found')

    def set_progressbar(self, _) -> None:
        """
        Update progressbar and hide it
        when it reaches its maximum
        """
        current: int = self.progressbar.value()
        self.progressbar.setValue(current + 1)
        if current == self.progressbar.maximum():
            self.progressbar.hide()
            self.progressbar.setValue(0)

    def load(self) -> None:
        """
        Download thumbnails if THUMBS_DIR is empty
        or JSON_FILE don't exist.
        Otherwise fill stacked widget with existing thumbnails
        """
        create_dirs(THUMBS_DIR, CURRENT_DIR, SAVED_DIR)

        if JSON_FILE.exists():
            if not is_dir_contains_images(THUMBS_DIR):
                logger.debug(f"{short_path(THUMBS_DIR)} is empty. Downloading new thumbnails")
                self.progressbar.show()
                self.download_thumbs()
            else:
                logger.debug('Filling stacked widget')
                self.sw.fill()
                self.change_info()
        else:
            logger.debug(f"{short_path(JSON_FILE)} doesn't exist. Updating")
            self.update_()

    def resize_move(self) -> None:
        """ Resize and move window using parameters from settings """
        try:
            self.resize(*win_size)
            logger.debug(f'Resized window to {win_size}')
        except:
            logger.warning('Could not resize window')

        if win_pos:
            try:
                self.move(*win_pos)
                logger.debug(f'Moved window to {win_pos}')
            except:
                logger.warning('Could not move window to a new position')

    def closeEvent(self, event) -> None:
        """ Save window size and position before closing the window"""
        config['Program']['window_size'] = f'{self.width()}, {self.height()}'
        config['Program']['window_position'] = f'{self.x()}, {self.y()}'
        config_save()


def run_spp():
    app = QApplication([])
    global screen
    screen = QGuiApplication.screens()[0]

    main = Changewall()
    main.resize_move()
    main.setWindowTitle('Changewall')
    main.show()
    main.load()
    sys.exit(app.exec_())


if __name__ == "__main__":
    logger.debug(f'APP_DIR is {APP_DIR}')
    run_spp()
