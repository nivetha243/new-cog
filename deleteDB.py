import psycopg2

# Database connection details
DB_HOST = 'dpg-crc4s9jv2p9s73dm93eg-a.oregon-postgres.render.com'
DB_NAME = 'nivi'
DB_USER = 'nivi_user'
DB_PASSWORD = 'R9q17MQwi3rXUVO3vGVCvyXdfNOEGSuM'

def connect_db():
    # Connect to the PostgreSQL database
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def view_users():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user')
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    conn.close()

def delete_all_users():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM "user"')
    conn.commit()
    print("All users have been deleted.")
    conn.close()

if __name__ == '__main__':
    # Example usage
    view_users()
    confirm = input("Are you sure you want to delete all users? (yes/no): ")
    if confirm.lower() == 'yes':
        delete_all_users()
    view_users()
