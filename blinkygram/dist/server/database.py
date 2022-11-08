import time
import aiosqlite
import dataclasses

from typing import Iterable, List, Optional, Tuple


INIT_SQL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        pubkey TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER NOT NULL,
        uid_src INTEGER NOT NULL,
        uid_dst INTEGER NOT NULL,
        content TEXT NOT NULL,
        delivered INTEGER NOT NULL,
        FOREIGN KEY (uid_src) REFERENCES users (id),
        FOREIGN KEY (uid_dst) REFERENCES users (id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS currencies (
        id INTEGER PRIMARY KEY AUTOINCREMENT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS balances (
        uid INTEGER NOT NULL,
        currency_id INTEGER NOT NULL,
        balance INTEGER NOT NULL,
        PRIMARY KEY (uid, currency_id),
        FOREIGN KEY (uid) REFERENCES users (id),
        FOREIGN KEY (currency_id) REFERENCES currencies (id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS spent_receipts (
        receipt BLOB PRIMARY KEY
    );
    """,
]


class DatabaseException(Exception):
    pass


class UserExists(DatabaseException):
    pass


class UserNotExists(DatabaseException):
    pass


class CurrencyNotExists(DatabaseException):
    pass


class Database:
    def __init__(self, path: str, concurrency: int = 1):
        self._path = path
        self._conn: aiosqlite.Connection = None
        self._concurrency = concurrency

    @property
    def concurrency(self):
        return self._concurrency

    async def connect(self):
        self._conn = await aiosqlite.connect(self._path, isolation_level=None)

        await self._conn.execute('PRAGMA journal_mode = WAL;')
        await self._conn.execute('PRAGMA synchronous = NORMAL;')
        await self._conn.execute('PRAGMA mmap_size = 268435456;')

        await self._conn.execute('PRAGMA foreign_keys = ON;')

        for stmt in INIT_SQL:
            await self._conn.execute(stmt)

    async def close(self):
        await self._conn.close()

    async def insert(self, sql: str, parameters: list = []) -> int:
        row = await self._conn.execute_insert(sql, parameters)
        row_id = row[0]
        return row_id

    async def update(self, sql: str, parameters: list = []) -> int:
        async with self._conn.execute(sql, parameters) as cursor:
            row_count = cursor.rowcount
        return row_count

    async def select(self, sql: str, parameters: list = []) -> Iterable[Tuple]:
        return await self._conn.execute_fetchall(sql, parameters)


@dataclasses.dataclass
class User:
    username: str
    password: str
    pubkey: str
    id: int = None

    async def commit(self, db: Database):
        params = [self.username, self.password, self.pubkey]
        if self.id is None:
            try:
                row_id = await db.insert(
                    'INSERT INTO users VALUES (NULL, ?, ?, ?)',
                    params
                )
            except aiosqlite.IntegrityError:
                raise UserExists('User already exists')
            self.id = row_id
        else:
            await db.update(
                'UPDATE users SET username = ?, password = ?, pubkey = ? '
                'WHERE id = ?',
                params + [self.id]
            )

    @staticmethod
    async def by_id(db: Database, id: int) -> Optional['User']:
        rows = await User._select(db, 'SELECT * FROM users WHERE id = ?', [id])
        return rows[0] if rows else None

    @staticmethod
    async def by_name(db: Database, username: str) -> Optional['User']:
        rows = await User._select(
            db, 'SELECT * FROM users WHERE username = ?', [username])
        return rows[0] if rows else None

    @staticmethod
    async def _select(db: Database, sql: str, parameters: list = []) -> List['User']:
        rows = await db.select(sql, parameters)
        return [
            User(id=row[0], username=row[1], password=row[2], pubkey=row[3])
            for row in rows
        ]


@dataclasses.dataclass
class Message:
    uid_src: int
    uid_dst: int
    content: str
    id: int = None
    timestamp: int = None
    delivered: bool = False

    async def commit(self, db: Database):
        ts = int(time.time()) if self.timestamp is None else self.timestamp
        params = [ts, self.uid_src, self.uid_dst, self.content, self.delivered]
        if self.id is None:
            try:
                row_id = await db.insert(
                    'INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)',
                    params
                )
            except aiosqlite.IntegrityError:
                raise UserNotExists('User does not exist')
            self.id = row_id
        else:
            await db.update(
                'UPDATE messages SET timestamp = ?, uid_src = ?, uid_dst = ?, '
                'content = ?, delivered = ? WHERE id = ?',
                params + [self.id]
            )
        self.timestamp = ts

    @staticmethod
    async def read_one(db: Database, uid_dst: int) -> Optional['Message']:
        msgids = await db.select(
            'SELECT id FROM messages '
            'WHERE uid_dst = ? AND delivered = 0 ORDER BY id ASC '
            f'LIMIT {db.concurrency}',
            [uid_dst])
        for msgid, in msgids:
            row_count = await db.update(
                'UPDATE messages SET delivered = 1 WHERE id = ? AND delivered = 0',
                [msgid])
            if row_count > 0:
                msg, = await Message._select(db, 'SELECT * FROM messages WHERE id = ?', [msgid])
                return msg
        return None

    @staticmethod
    async def all_by_user(db: Database, userid: int) -> List['Message']:
        return await Message._select(db,
                                     'SELECT * FROM messages WHERE uid_dst = ? OR uid_src = ? '
                                     'ORDER BY id ASC', [userid, userid])

    @staticmethod
    async def _select(db: Database, sql: str, parameters: list = []) -> List['Message']:
        rows = await db.select(sql, parameters)
        return [
            Message(id=row[0], timestamp=row[1], uid_src=row[2], uid_dst=row[3],
                    content=row[4], delivered=bool(row[5]))
            for row in rows
        ]


@dataclasses.dataclass
class Currency:
    id: int = None

    async def commit(self, db: Database):
        if self.id is None:
            row_id = await db.insert('INSERT INTO currencies VALUES (NULL)')
            self.id = row_id


@dataclasses.dataclass
class Balance:
    uid: int
    currency_id: int
    balance: int

    async def commit(self, db: Database):
        try:
            await db.update(
                'INSERT OR REPLACE INTO balances VALUES (?, ?, ?)',
                [self.uid, self.currency_id, self.balance])
        except aiosqlite.IntegrityError:
            raise CurrencyNotExists('Currency does not exist')

    @staticmethod
    async def find(db: Database, uid: int, currency_id: int) -> Optional['Balance']:
        rows = await Balance._select(db,
                                     'SELECT * FROM balances WHERE uid = ? AND currency_id = ?',
                                     [uid, currency_id])
        return rows[0] if rows else None

    @staticmethod
    async def adjust(db: Database, uid: int, currency_id: int, delta: int) -> bool:
        row_count = await db.update(
            'UPDATE balances SET balance = balance + ? '
            'WHERE uid = ? AND currency_id = ? AND balance + ? >= 0',
            [delta, uid, currency_id, delta])
        return row_count > 0

    @staticmethod
    async def all_by_user(db: Database, uid: int) -> List['Balance']:
        return await Balance._select(db,
                                     'SELECT * FROM balances WHERE uid = ?', [uid])

    @staticmethod
    async def _select(db: Database, sql: str, parameters: list = []) -> List['Balance']:
        rows = await db.select(sql, parameters)
        return [
            Balance(uid=row[0], currency_id=row[1], balance=row[2])
            for row in rows
        ]


class SpentReceipt:
    @staticmethod
    async def find(db: Database, receipt: bytes) -> bool:
        rows = await db.select(
            'SELECT * FROM spent_receipts WHERE receipt = ?', [receipt])
        return len(rows) > 0

    @staticmethod
    async def spend(db: Database, receipt: bytes) -> bool:
        try:
            await db.insert('INSERT INTO spent_receipts VALUES (?)', [receipt])
        except aiosqlite.IntegrityError:
            return False
        return True
