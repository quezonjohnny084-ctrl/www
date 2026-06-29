import sqlite3

conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()

# ================= USERS TABLE =================
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    referrals INTEGER DEFAULT 0,
    referred_by INTEGER DEFAULT NULL,
    last_claim REAL DEFAULT 0
)
""")

# ================= BANNED USERS TABLE =================
c.execute("""
CREATE TABLE IF NOT EXISTS banned_users (
    user_id INTEGER PRIMARY KEY
)
""")
conn.commit()


# ================= USER FUNCTIONS =================

def add_user(uid, username):
    c.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    if c.fetchone() is None:
        c.execute("""
            INSERT INTO users (user_id, username, referrals, referred_by, last_claim)
            VALUES (?, ?, 0, NULL, 0)
        """, (uid, username))
        conn.commit()
        return True
    return False


def get(uid):
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    return c.fetchone()


def update_username(uid, username):
    c.execute("UPDATE users SET username=? WHERE user_id=?", (username, uid))
    conn.commit()


def set_referral(new_user, ref_user):
    if new_user == ref_user:
        return None

    c.execute("SELECT referred_by FROM users WHERE user_id=?", (new_user,))
    row = c.fetchone()

    if row and row[0] is None:
        c.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?", (ref_user,))
        c.execute("UPDATE users SET referred_by=? WHERE user_id=?", (ref_user, new_user))
        conn.commit()
        return ref_user
    return None


def update_time(uid, t):
    c.execute("UPDATE users SET last_claim=? WHERE user_id=?", (t, uid))
    conn.commit()


def deduct_referrals(uid, amount):
    c.execute("UPDATE users SET referrals = referrals - ? WHERE user_id=?", (amount, uid))
    conn.commit()


def top():
    c.execute("SELECT username, referrals FROM users ORDER BY referrals DESC LIMIT 10")
    return c.fetchall()


# ================= ADMIN FUNCTIONS =================

def ban_user(uid):
    c.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (uid,))
    conn.commit()


def unban_user(uid):
    c.execute("DELETE FROM banned_users WHERE user_id=?", (uid,))
    conn.commit()


def is_banned(uid):
    c.execute("SELECT user_id FROM banned_users WHERE user_id=?", (uid,))
    return c.fetchone() is not None


def delete_user(uid):
    c.execute("DELETE FROM users WHERE user_id=?", (uid,))
    c.execute("DELETE FROM banned_users WHERE user_id=?", (uid,))
    conn.commit()


def search_user(uid):
    c.execute("SELECT user_id, username, referrals, referred_by, last_claim FROM users WHERE user_id=?", (uid,))
    return c.fetchone()


def get_all_users():
    c.execute("SELECT user_id, username, referrals FROM users ORDER BY user_id ASC")
    return c.fetchall()


# ================= STATISTICS =================

def get_stats():
    c.execute("SELECT COUNT(*) FROM users")
    users_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM banned_users")
    banned_count = c.fetchone()[0]
    
    c.execute("SELECT COALESCE(SUM(referrals), 0) FROM users")
    total_refs = c.fetchone()[0]
    
    return {
        "users": users_count,
        "banned": banned_count,
        "referrals": total_refs
    }


def reset_all_data():
    c.execute("DELETE FROM users")
    c.execute("DELETE FROM banned_users")
    conn.commit()