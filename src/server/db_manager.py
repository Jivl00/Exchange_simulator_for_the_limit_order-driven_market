import sqlite3

def create_user_db(db_path='users.db'):
    # Connect to the SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the users table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            uuid TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE
        )
    ''')

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

# Call the function to create the database and table
create_user_db()