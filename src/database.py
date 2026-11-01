import sqlite3

def connect(path='tracker.db'):
    return sqlite3.connect(path)
