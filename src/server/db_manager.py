import sqlite3

def create_user_db(db_path='users.db'):
    # Connect to the SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the users table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    # Insert initial users
    initial_users = [
        ('market_maker', 'password123'),
        ('liquidity_generator', 'password123'),
        ('lstm_trader', 'password123'),
        ('momentum_trader', 'password123'),
        ('ql_trader', 'password123'),
        ('range_trader', 'password123'),
        ('lr_trader', 'password123'),
        ('scalping_trader', 'password123'),
        ('spoofing_trader', 'password123'),
        ('swing_trader', 'password123'),
        ('test_trader', 'password123'),
    ]

    for email, password in initial_users:
        try:
            cursor.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, password))
        except sqlite3.IntegrityError:
            # Skip if the user already exists
            pass
        except sqlite3.Error as e:
            print(f"Error inserting user {email}: {e}")
            pass

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

if __name__ == "__main__":
    db_path = 'users.db'
    create_user_db(db_path)
