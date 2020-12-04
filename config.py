import configparser
from pathlib import Path
from typing import Tuple

APP_DIR: Path = Path(__file__).parent.absolute()
SETTINGS: Path = APP_DIR.joinpath('settings.ini')

config = configparser.ConfigParser()
config.read(SETTINGS)

config_program = config['Program']
config_paths = config['Paths']


def set_path_var(dir_: str) -> Path:
    """ Convert dir_ to path object """
    dir_: Path = Path(dir_)
    if dir_.is_absolute():
        return dir_
    else:
        return APP_DIR.joinpath(dir_)


def config_save() -> None:
    """ Save settings.ini file """
    with open(SETTINGS, 'w') as f:
        config.write(f)


JSON_FILE: Path = set_path_var(config_paths['json'])
ICONS_DIR: Path = set_path_var(config_paths['icons'])
THUMBS_DIR: Path = set_path_var(config_paths['thumbs'])
CURRENT_DIR: Path = set_path_var(config_paths['current'])
SAVED_DIR: Path = set_path_var(config_paths['saved'])

SEARCH_URL: str = config_program['search_url']
INFO_COLOR: str = config_program['info_color']
DEBUG_MODE: bool = config_program.getboolean('debug')

w, h = config_program['window_size'].split(',')
win_size: Tuple[int, int] = (int(w), int(h))

try:
    x, y = config_program['window_position'].split(',')
    win_pos: Tuple[int, int] = (int(x), int(y))
except:
    win_pos = None
