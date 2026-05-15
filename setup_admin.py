"""
setup_admin.py — Full schema setup + admin seed.
Run ONCE: python setup_admin.py
Also handles migrating existing tables (adds missing columns safely).
"""
import sys, getpass, os
os.environ["PYTHONIOENCODING"] = "utf-8"
import mysql.connector
from werkzeug.security import generate_password_hash
import config


def column_exists(cursor, table, column):
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
    """, (config.DB_NAME, table, column))
    return cursor.fetchone()[0] > 0


def run():
    pwd = config.DB_PASSWORD
    if not pwd:
        pwd = getpass.getpass("[?] MySQL password for root: ")

    try:
        conn   = mysql.connector.connect(
            host=config.DB_HOST, port=config.DB_PORT,
            user=config.DB_USER, password=pwd
        )
        cursor = conn.cursor()
        print(f"[OK] Connected to MySQL at {config.DB_HOST}:{config.DB_PORT}")
    except mysql.connector.Error as e:
        print(f"[FAIL] Cannot connect to MySQL: {e}")
        print("  --> Please update DB_PASSWORD in .env and retry.")
        sys.exit(1)

    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cursor.execute(f"USE `{config.DB_NAME}`")
    print(f"[OK] Database '{config.DB_NAME}' ready.")

    # ── users ──────────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            username      VARCHAR(50)  NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role          ENUM('admin','auctioneer','viewer') NOT NULL DEFAULT 'viewer',
            full_name     VARCHAR(100),
            email         VARCHAR(120) UNIQUE,
            is_active     TINYINT(1) NOT NULL DEFAULT 1,
            is_deleted    TINYINT(1) NOT NULL DEFAULT 0,
            created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    # migrate: add is_deleted if missing (handles existing databases)
    if not column_exists(cursor, "users", "is_deleted"):
        cursor.execute("ALTER TABLE users ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0")
        print("[OK] Migrated: added is_deleted to users.")
    if not column_exists(cursor, "users", "updated_at"):
        cursor.execute("ALTER TABLE users ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")

    # ── teams ──────────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id              INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            team_id         VARCHAR(10)  NOT NULL UNIQUE,
            team_name       VARCHAR(100) NOT NULL,
            team_short_name VARCHAR(5)   NOT NULL,
            owner_name      VARCHAR(100),
            home_ground     VARCHAR(100),
            team_logo       VARCHAR(255),
            player_purse    DECIMAL(10,2) NOT NULL DEFAULT 80.00,
            player_spent    DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            mgmt_purse      DECIMAL(10,2) NOT NULL DEFAULT 20.00,
            mgmt_spent      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            total_purse     DECIMAL(10,2) NOT NULL DEFAULT 100.00,
            spent_amount    DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            username        VARCHAR(50) NOT NULL UNIQUE,
            password_hash   VARCHAR(255) NOT NULL,
            is_active       TINYINT(1) NOT NULL DEFAULT 1,
            is_deleted      TINYINT(1) NOT NULL DEFAULT 0,
            created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # Migration for teams table
    if not column_exists(cursor, "teams", "player_purse"):
        cursor.execute("ALTER TABLE teams ADD COLUMN player_purse DECIMAL(10,2) NOT NULL DEFAULT 80.00")
        cursor.execute("UPDATE teams SET player_purse = total_purse") # Initial data sync
    if not column_exists(cursor, "teams", "player_spent"):
        cursor.execute("ALTER TABLE teams ADD COLUMN player_spent DECIMAL(10,2) NOT NULL DEFAULT 0.00")
        cursor.execute("UPDATE teams SET player_spent = spent_amount") # Initial data sync
    if not column_exists(cursor, "teams", "mgmt_purse"):
        cursor.execute("ALTER TABLE teams ADD COLUMN mgmt_purse DECIMAL(10,2) NOT NULL DEFAULT 20.00")
    if not column_exists(cursor, "teams", "mgmt_spent"):
        cursor.execute("ALTER TABLE teams ADD COLUMN mgmt_spent DECIMAL(10,2) NOT NULL DEFAULT 0.00")
    print("[OK] Migrated: added dual-purse columns to teams.")


    # ── players ────────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id              INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            player_id       VARCHAR(15) NOT NULL UNIQUE,
            player_name     VARCHAR(100) NOT NULL,
            role            ENUM('Batsman','Bowler','All-Rounder','Wicket-Keeper') NOT NULL,
            nationality     VARCHAR(50) NOT NULL DEFAULT 'Indian',
            age             INT,
            batting_style   ENUM('Right-Hand','Left-Hand'),
            bowling_style   VARCHAR(50),
            capped          TINYINT(1) NOT NULL DEFAULT 0,
            base_price      DECIMAL(10,2) NOT NULL DEFAULT 0.20,
            photo           VARCHAR(255),
            is_sold         TINYINT(1) NOT NULL DEFAULT 0,
            sold_to_team_id INT DEFAULT NULL,
            is_active       TINYINT(1) NOT NULL DEFAULT 1,
            is_deleted      TINYINT(1) NOT NULL DEFAULT 0,
            created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (sold_to_team_id) REFERENCES teams(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # ── bids ───────────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bids (
            id             INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            bid_id         VARCHAR(15) NOT NULL UNIQUE,
            player_id      INT NOT NULL,
            team_id        INT NOT NULL,
            bid_amount     DECIMAL(10,2) NOT NULL,
            bid_time       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_winning_bid TINYINT(1) NOT NULL DEFAULT 0,
            is_active      TINYINT(1) NOT NULL DEFAULT 1,
            is_deleted     TINYINT(1) NOT NULL DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (team_id)   REFERENCES teams(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # ── auction_results ────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auction_results (
            id          INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            result_id   VARCHAR(15) NOT NULL UNIQUE,
            player_id   INT NOT NULL,
            team_id     INT NOT NULL,
            final_price DECIMAL(10,2) NOT NULL,
            sold_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_active   TINYINT(1) NOT NULL DEFAULT 1,
            is_deleted  TINYINT(1) NOT NULL DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (team_id)   REFERENCES teams(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # ── security_logs ──────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_logs (
            id          INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            event_type  VARCHAR(50) NOT NULL,
            username    VARCHAR(50),
            ip_address  VARCHAR(45),
            user_agent  TEXT,
            status      VARCHAR(20) DEFAULT 'success',
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    conn.commit()
    print("[OK] All 6 tables created / verified.")



    # ── Seed admin ─────────────────────────────────────────────────────────────
    cursor.execute("""
        INSERT INTO users (username, password_hash, role, full_name, email)
        VALUES (%s, %s, 'admin', 'Admin User', 'admin@ipl.com')
        ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash)
    """, ("admin", generate_password_hash("admin123")))
    conn.commit()
    cursor.close()
    conn.close()

    print("\n✅ Setup complete!")
    print("   Admin login → username: admin  |  password: admin123")
    print("   Run: python app.py")


if __name__ == "__main__":
    run()
