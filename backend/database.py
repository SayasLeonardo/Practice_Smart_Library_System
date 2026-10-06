"""SQLite setup and starter records for the Smart Library System."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from werkzeug.security import generate_password_hash


DATABASE_PATH = Path(__file__).resolve().parent.parent / "smart_library.db"


@contextmanager
def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT,
                role TEXT NOT NULL CHECK (role IN ('MIS Admin', 'Librarian', 'Student', 'Faculty')),
                department TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_number TEXT NOT NULL UNIQUE,
                barcode TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                category TEXT NOT NULL,
                published_date TEXT NOT NULL DEFAULT '',
                quantity INTEGER NOT NULL CHECK (quantity >= 0),
                available_quantity INTEGER NOT NULL CHECK (available_quantity >= 0),
                cover_image TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS book_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL REFERENCES books(id),
                borrower_id INTEGER NOT NULL REFERENCES users(id),
                processed_by INTEGER NOT NULL REFERENCES users(id),
                barcode TEXT NOT NULL DEFAULT '',
                institutional_email TEXT NOT NULL DEFAULT '',
                borrow_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                return_date TEXT,
                status TEXT NOT NULL DEFAULT 'borrowed' CHECK (status IN ('borrowed', 'returned')),
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS attendance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL REFERENCES users(id),
                time_in TEXT NOT NULL,
                time_out TEXT,
                attendance_date TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'face_recognition',
                status TEXT NOT NULL DEFAULT 'inside' CHECK (status IN ('inside', 'completed', 'admin_closed')),
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE UNIQUE INDEX IF NOT EXISTS one_open_attendance_per_person
                ON attendance_records(person_id) WHERE time_out IS NULL;
            CREATE INDEX IF NOT EXISTS attendance_time_in_date ON attendance_records(time_in);
            """
        )

        book_columns = {row["name"] for row in connection.execute("PRAGMA table_info(books)")}
        if "cover_image" not in book_columns:
            connection.execute("ALTER TABLE books ADD COLUMN cover_image TEXT NOT NULL DEFAULT ''")
        if "book_number" not in book_columns:
            connection.execute("ALTER TABLE books ADD COLUMN book_number TEXT NOT NULL DEFAULT ''")
            legacy_books = connection.execute("SELECT id, barcode FROM books ORDER BY id").fetchall()
            for book in legacy_books:
                book_number = book["barcode"]
                barcode = f"SL{book['id']:010d}"
                suffix = 1
                while connection.execute(
                    "SELECT 1 FROM books WHERE barcode = ? AND id != ?", (barcode, book["id"])
                ).fetchone():
                    barcode = f"SL{book['id']:08d}{suffix:02d}"
                    suffix += 1
                connection.execute(
                    "UPDATE books SET book_number = ?, barcode = ? WHERE id = ?",
                    (book_number, barcode, book["id"]),
                )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS books_book_number_unique ON books(book_number)"
        )

        transaction_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(book_transactions)")
        }
        if "barcode" not in transaction_columns:
            connection.execute("ALTER TABLE book_transactions ADD COLUMN barcode TEXT NOT NULL DEFAULT ''")
            connection.execute(
                """UPDATE book_transactions
                   SET barcode = (SELECT barcode FROM books WHERE books.id = book_transactions.book_id)"""
            )
        if "institutional_email" not in transaction_columns:
            connection.execute(
                "ALTER TABLE book_transactions ADD COLUMN institutional_email TEXT NOT NULL DEFAULT ''"
            )
            connection.execute(
                """UPDATE book_transactions
                   SET institutional_email = (SELECT email FROM users WHERE users.id = book_transactions.borrower_id)"""
            )

        user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
        for column, definition in (
            ("person_type", "TEXT NOT NULL DEFAULT ''"),
            ("contact", "TEXT NOT NULL DEFAULT ''"),
            ("face_image", "TEXT NOT NULL DEFAULT ''"),
            ("face_encoding", "TEXT NOT NULL DEFAULT ''"),
            ("last_login_at", "TEXT"),
        ):
            if column not in user_columns:
                connection.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")

        user_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count == 0:
            users = [
                ("MIS-001", "PTC MIS", "admin@smartlibrary.local", "admin123", "MIS Admin", "MIS"),
                ("LIB-001", "PTC Librarian", "librarian@smartlibrary.local", "librarian123", "Librarian", "Library"),
                ("2023-10252", "Sandara Panis", "2023-10252@student.ptc.local", None, "Student", "BSIT"),
                ("2022-09512", "Leonardo Sayas", "2022-09512@student.ptc.local", None, "Student", "BSIT"),
                ("2023-87463", "Kathleen Mangui", "2023-87463@student.ptc.local", None, "Student", "BSIT"),
            ]
            for school_id, name, email, password, role, department in users:
                password_hash = generate_password_hash(password) if password else None
                connection.execute(
                    """INSERT INTO users (school_id, name, email, password_hash, role, department)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (school_id, name, email, password_hash, role, department),
                )

        book_count = connection.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        if book_count == 0:
            books = [
                ("BK-001", "Harry Potter and the Sorcerer's Stone", "J.K. Rowling", "Fiction", "1997-06-26", 1),
                ("BK-002", "A Brief History of Time", "Stephen Hawking", "Science", "1988-04-01", 3),
                ("BK-003", "Learning Python", "Mark Lutz", "Technology", "2016-07-01", 4),
                ("BK-004", "Computer Networking: A Top-Down Approach", "James F. Kurose", "Technology", "2016-03-15", 2),
                ("BK-005", "Sapiens: A Brief History of Humankind", "Yuval Noah Harari", "History", "2014-09-04", 2),
                ("BK-006", "Romeo and Juliet", "William Shakespeare", "Literature", "1597-01-01", 7),
                ("BK-007", "Mastering the Art of Cooking", "Julia Child", "Culinary", "1961-10-16", 3),
                ("BK-008", "Rich Dad Poor Dad", "Robert Kiyosaki", "Business", "1997-04-08", 5),
                ("BK-009", "Gregg Shorthand College Book 1", "Charles E. Zoubek", "Business", "1989-04-28", 3),
                ("BK-010", "Gregg Shorthand College Book 2", "Louis A. Leslie", "Business", "1989-04-28", 4),
            ]
            connection.executemany(
                """INSERT INTO books
                   (book_number, barcode, title, author, category, published_date, quantity, available_quantity)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (book[0], f"SL{index:010d}", *book[1:], book[-1])
                    for index, book in enumerate(books, start=1)
                ],
            )