import sqlite3
from os import path
conn = sqlite3.connect(path.abspath('./data/databases/apikeys.sqlite3'))
