import sqlite3


class ClosingConnection(sqlite3.Connection):
    """A connection that closes itself at the end of a `with` block.

    A plain sqlite3 connection only commits or rolls back when used as a
    context manager. It stays open until Python's garbage collector happens
    to remove it, and on Windows an open connection blocks replacing or
    deleting the database file. With this class, `with` commits (or rolls
    back on an error) and then closes the connection.
    """

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()
