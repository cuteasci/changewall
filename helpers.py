# import asyncio
import ctypes
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

from PySide2.QtGui import QImageReader

from config import APP_DIR, JSON_FILE
from logger import logger


def short_path(path: Path):
    """
    Take path object and returns 'APPDIR' + the final component of path
    if the parent of file_ equals APP_DIR or full path if not
    """
    if str(path).startswith(str(APP_DIR)):
        path = 'APPDIR/' + str(path.relative_to(APP_DIR))
    else:
        path = str(path)

    return path


def supported_image_formats() -> List[str]:
    """ Return list of supported image formats """
    supported_formats: List[Any] = QImageReader.supportedImageFormats()
    return [format_.data().decode() for format_ in supported_formats]


def is_image(file: Path) -> bool:
    """ Take file path object and return True if file is an image """
    return file.suffix[1:] in supported_image_formats()


def is_dir_contains_images(dir_: Path) -> bool:
    """
    Take dir path object and return True
    if dir contains at least one image file
    """
    if not dir_.exists():
        logger.error(f"{dir_.absolute} doesn't exists")
    return len(list_images(dir_)) > 0


def list_images(dir_: Path) -> List[Path]:
    """ Return list of images in dir_ """
    return [file for file in dir_.iterdir() if is_image(file)]


def create_dirs(*dirs: Path) -> None:
    """ Take dir path objects and create them if they don't exists """
    for dir_ in dirs:
        if not dir_.exists():
            try:
                dir_.mkdir()
                logger.debug(f'Created {dir_}')
            except Exception as e:
                logger.error(f'Cannot create {dir_} {e}')
            else:
                logger.debug(f'{dir_} directory is created')


def image_info(image_id: str) -> Dict[str, str]:
    """
    Take image id as parameter and return a dictionary with keys:
    image_id, full_image_url, extension, page_url, resolution
    """
    info: Dict[str, str] = dict()

    logger.debug(f'Getting info of image with id {image_id}')

    with open(JSON_FILE, 'r') as f:
        data: Dict = json.load(f)
        for wallpaper in data['data']:
            if wallpaper['id'] == image_id:
                info['image_id'] = wallpaper['id']
                info['full_image_url'] = wallpaper['path']
                info['extension'] = wallpaper['path'][-4:]
                info['page_url'] = wallpaper['url']
                info['resolution'] = wallpaper['resolution']

    if not info:
        logger.error(f'Info for {image_id} not found')

    return info


def get_screen_res(screen) -> Tuple[int, int]:
    """ Take QScreen and return (screen_width, screen_height) """
    screen_width: int = screen.geometry().width()
    screen_height: int = screen.geometry().height()
    logger.debug(f'Screen resolution is {screen_width}x{screen_height}')
    return screen_width, screen_height


def save_settings(old: str, new: str) -> None:
    settings_file: Path = APP_DIR.joinpath('settings.py')
    with open(settings_file, 'r') as f:
        data = f.read()
    data = data.replace(old, new)
    with open(settings_file, 'w') as f:
        f.write(data)


def set_wall(file: Path) -> None:
    logger.debug(f'Trying to set {file} as wallpaper')
    logger.debug(f'Platform is {sys.platform}')
    if sys.platform == 'win32':
        set_wall_win(file)
    if sys.platform == 'linux':
        if os.environ.get('KDE_FULL_SESSION') == 'true':
            logger.debug(f'Environment is KDE')
            # asyncio.run(set_wall_kde(file))
            set_wall_kde(file)
        if os.environ.get('DESKTOP_SESSION') in ['gnome', 'ubuntu']:
            logger.debug(f'Environment is Gnome')
            set_wall_gnome(file)


#
# async def set_wall_kde(file: Path) -> None:
#     import dbus_next
#     uri: str = file.absolute().as_uri()
#     jscript = """
#     var allDesktops = desktops();
#     for (i=0;i<allDesktops.length;i++) {
#         d = allDesktops[i];
#         d.wallpaperPlugin = "org.kde.image";
#         d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
#         d.writeConfig("Image", '%s')
#
#     }
#     """
#
#     bus = await dbus_next.aio.MessageBus().connect()
#     introspect = await bus.introspect('org.kde.plasmashell', '/PlasmaShell')
#     proxy = bus.get_proxy_object(
#         'org.kde.plasmashell', '/PlasmaShell', introspect)
#     interface = proxy.get_interface('org.kde.PlasmaShell')
#     await interface.call_evaluate_script(jscript % uri)


def set_wall_kde(file: Path, plugin: str = 'org.kde.image'):
    import dbus
    jscript: str = """
    var allDesktops = desktops();
    for (i=0;i<allDesktops.length;i++) {
        d = allDesktops[i];
        d.wallpaperPlugin = "%s";
        d.currentConfigGroup = Array("Wallpaper", "%s", "General");
        d.writeConfig("Image", "file://%s")
    }
    """
    bus = dbus.SessionBus()
    plasma = dbus.Interface(bus.get_object('org.kde.plasmashell', '/PlasmaShell'), dbus_interface='org.kde.PlasmaShell')
    plasma.evaluateScript(jscript % (plugin, plugin, file))


def set_wall_win(file: Path) -> None:
    ctypes.windll.user32.SystemParametersInfoW(
        20, 0, str(file.absolute()), 0)


def set_wall_gnome(file: Path) -> None:
    import subprocess
    args = ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", str(file.absolute())]
    subprocess.Popen(args)
