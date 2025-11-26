import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class Database:
    def __init__(self, db_path: str = "auth_system.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                phone_number TEXT UNIQUE NOT NULL,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                is_verified BOOLEAN DEFAULT FALSE,
                is_banned BOOLEAN DEFAULT FALSE,
                ban_until DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                verified_at DATETIME
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS otp_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                phone_number TEXT NOT NULL,
                code TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                is_used BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failed_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                phone_number TEXT NOT NULL,
                attempt_type TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        conn.commit()
        conn.close()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def add_user(self, user_id: int, phone_number: str, first_name: str = None,
                last_name: str = None, username: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users
                (user_id, phone_number, first_name, last_name, username, is_verified)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, phone_number, first_name, last_name, username, False))
            conn.commit()
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
        return True

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()

        return dict(user) if user else None

    def get_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE phone_number = ?', (phone_number,))
        user = cursor.fetchone()
        conn.close()

        return dict(user) if user else None

    def update_user_verification(self, user_id: int, verified: bool = True):
        conn = self.get_connection()
        cursor = conn.cursor()

        verified_at = datetime.now() if verified else None
        cursor.execute('''
            UPDATE users
            SET is_verified = ?, verified_at = ?
            WHERE user_id = ?
        ''', (verified, verified_at, user_id))
        conn.commit()
        conn.close()

    def ban_user(self, user_id: int, duration_hours: int = 24):
        conn = self.get_connection()
        cursor = conn.cursor()

        ban_until = datetime.now() + timedelta(hours=duration_hours)
        cursor.execute('''
            UPDATE users
            SET is_banned = TRUE, ban_until = ?
            WHERE user_id = ?
        ''', (ban_until, user_id))
        conn.commit()
        conn.close()

    def is_user_banned(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False

        if user['is_banned'] and user['ban_until']:
            ban_until = datetime.fromisoformat(user['ban_until'])
            if datetime.now() < ban_until:
                return True
            else:
                self.unban_user(user_id)
                return False
        return False

    def unban_user(self, user_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users
            SET is_banned = FALSE, ban_until = NULL
            WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()

    def save_otp(self, user_id: int, phone_number: str, code: str, expiry_minutes: int = 5):
        conn = self.get_connection()
        cursor = conn.cursor()

        expires_at = datetime.now() + timedelta(minutes=expiry_minutes)

        cursor.execute('''
            UPDATE otp_codes
            SET is_used = TRUE
            WHERE user_id = ? AND is_used = FALSE
        ''', (user_id,))

        cursor.execute('''
            INSERT INTO otp_codes (user_id, phone_number, code, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, phone_number, code, expires_at))

        conn.commit()
        conn.close()

    def verify_otp(self, user_id: int, code: str) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM otp_codes
            WHERE user_id = ? AND code = ? AND is_used = FALSE AND expires_at > ?
        ''', (user_id, code, datetime.now()))

        otp_record = cursor.fetchone()

        if otp_record:
            cursor.execute('''
                UPDATE otp_codes
                SET attempts = attempts + 1
                WHERE id = ?
            ''', (otp_record[0],))

            cursor.execute('''
                UPDATE otp_codes
                SET is_used = TRUE
                WHERE id = ?
            ''', (otp_record[0],))

            conn.commit()
            conn.close()
            return True

        conn.close()
        return False

    def get_otp_attempts(self, user_id: int) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT attempts FROM otp_codes
            WHERE user_id = ? AND is_used = FALSE AND expires_at > ?
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id, datetime.now()))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else 0

    def add_failed_attempt(self, user_id: int, phone_number: str, attempt_type: str):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO failed_attempts (user_id, phone_number, attempt_type)
            VALUES (?, ?, ?)
        ''', (user_id, phone_number, attempt_type))

        conn.commit()
        conn.close()

    def get_recent_failed_attempts(self, user_id: int, minutes: int = 60) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()

        since_time = datetime.now() - timedelta(minutes=minutes)
        cursor.execute('''
            SELECT COUNT(*) FROM failed_attempts
            WHERE user_id = ? AND created_at > ?
        ''', (user_id, since_time))

        count = cursor.fetchone()[0]
        conn.close()

        return count

db = Database()