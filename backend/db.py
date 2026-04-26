import mysql.connector
from mysql.connector import Error


# --- YOUR CREDENTIALS ---
DB_USER = #name
DB_PASSWORD = #password
DB_NAME = #mariadb name
# ------------------------

def get_db_connection():
    """Connects directly to the local MariaDB on Turing."""
    try:
        connection = mysql.connector.connect(
            host='127.0.0.1',  # Turing is now 'localhost' relative to this script
            port=3306,         # Default MariaDB port
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return connection
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return None

# --- TEST BLOCK ---
# if __name__ == "__main__":
#     print("Opening SSH Tunnel and connecting to MariaDB...")
#     conn, tunnel = get_db_connection()
    
#     if conn and conn.is_connected():
#         print("SUCCESS! We are through the tunnel and into the database.")
        
#         # Clean up
#         conn.close()
#         tunnel.stop()
#         print("Connection closed.")
#     else:
#         print("FAILED.")