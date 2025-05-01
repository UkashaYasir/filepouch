import sqlite3 , os
try:
    # Define the path to the SQLite database
    db_path = "path/to/your/database.db"

    # Connect to the SQLite database
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Get the schema for the 'users' table
    cursor.execute("PRAGMA table_info(users);")
    users_table_info = cursor.fetchall()
    print("Users Table Schema:", users_table_info)

    # Get the schema for the 'reviews' table
    cursor.execute("PRAGMA table_info(reviews);")
    reviews_table_info = cursor.fetchall()
    print("Reviews Table Schema:", reviews_table_info)

except sqlite3.Error as error: 
    print("Error:", error)

finally:
    if 'connection' in locals() and connection:
        connection.close()
