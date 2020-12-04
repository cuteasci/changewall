from pathlib import Path

from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QPixmap, QIcon, QKeySequence
from PySide2.QtWidgets import QLabel, QStackedWidget, QProgressBar, QPushButton

from helpers import (list_images)
from config import THUMBS_DIR, ICONS_DIR, INFO_COLOR


class ImageLabel(QLabel):
    """ 
    QLabel widget for displaying thumbnails
    Take thumbnail as image 
    """

    def __init__(self, image: Path, parent=None):
        super().__init__(parent)
        self.image: Path = image
        self.image_id: str = self.image.name[:-4]
        self.pixmap = QPixmap(str(self.image))
        self.setPixmap(self.pixmap)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(432, 243)

    def resizeEvent(self, event):
        self.setPixmap(self.pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


class StackedWidget(QStackedWidget):
    """ QStackWidget for displaying thumbnails """
    added = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def add(self, image: Path) -> None:
        """
        Add ImageLabel widget
        Emit signal when added
        """
        image_label = ImageLabel(image)
        self.addWidget(image_label)
        self.added.emit()

    def fill(self) -> None:
        """ 
        Populate StackedWidget with thumbnails 
        from THUMBS_DIR
        """
        for image in list_images(THUMBS_DIR):
            self.add(image)

    def count_info(self) -> str:
        """ 
        Return a string in format 
        currentIndex + 1 / count
        """
        return f'{self.currentIndex() + 1} / {self.count()}'

    def current_image_id(self) -> str:
        """
        Return current image id
        """
        return self.currentWidget().image_id


class Button(QPushButton):
    """
    QPushbutton
    """

    def __init__(self, icon_path: str, text: str = '', key: str = None, parent=None):
        super().__init__(parent)
        self.icon_path: Path = ICONS_DIR.joinpath(icon_path)
        self.text: str = text
        self.setIcon(QIcon(str(self.icon_path)))
        self.setText(text)
        self.setAutoDefault(False)

        if key:
            self.setShortcut(QKeySequence(key))

        self.setMinimumHeight(35)


class ProgressBar(QProgressBar):
    """
    QProgressBar
    Default range is 24 which is number of images in json
    """

    def __init__(self, maxrange: int = 23, parent=None):
        super().__init__(parent)
        style = f"""
        QProgressBar 
        {{
        border-radius: 4px;
        color: {INFO_COLOR};
        }}
        QProgressBar::chunk
        {{
        background-color: {INFO_COLOR};
        border-radius: 4px;
        }}        
        """
        self.setStyleSheet(style)
        self.setTextVisible(False)
        self.setMaximumHeight(10)
        self.setRange(0, maxrange)
        self.setValue(0)
        self.setAlignment(Qt.AlignRight)
