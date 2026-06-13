import pathlib
HOME_DIR=pathlib.Path.home()
PROJECT_DIR=HOME_DIR/bytes([46,118,110,115,116,111,99,107]).decode()
ID_DIR=PROJECT_DIR/bytes([105,100]).decode()