import pymysql
from dotenv import load_dotenv
import os
load_dotenv()
host=os.getenv("client_host")
user=os.getenv("client_user")
password=os.getenv("client_password")
database=os.getenv("client_database")
port=int(os.getenv("client_port"))

db_configs = [
    {"host": host,"port":port,"user":user, "password":password, "database":database, "table": "BREEZEAWAY_RESERVATIONS"},
    {"host": host,"port":port,"user":user, "password":password , "database": database, "table": "GUESTY_RESERVATIONS_FULL"},
    {"host": host, "port":port,"user": user, "password":password, "database": database, "table": "GUESTY_RESERVATIONS" }#"ssl": {"ca": "/etc/ssl/certs/ca-certificates.crt"}
]



def find_reference_id(reference_id: str) -> str:
    """Search for a reference ID in multiple databases and return where it was found."""

    for i, db_config in enumerate(db_configs, start=1):
        try:
            # Connect to the database
            conn = pymysql.connect(
                host=db_config["host"],
                port=db_config["port"],
                user=db_config["user"],
                password=db_config["password"],
                database=db_config["database"]
            )
            cursor = conn.cursor()

            # Step 1: Check if reservation_id exists
            check_reservation_query = f"SELECT 1 FROM {db_config['table']} WHERE reservation_id = %s LIMIT 1"
            cursor.execute(check_reservation_query, (reference_id,))
            reservation_exists = cursor.fetchone()

            if not reservation_exists:
                cursor.close()
                conn.close()
                continue  # Move to the next database if reservation_id is not found

            # Step 2: Check if propertyId exists for that reservation_id
            if i==1:
                get_property_query = f"SELECT property_id FROM {db_config['table']} WHERE reservation_id = %s LIMIT 1"
            elif i==2:
                get_property_query = f"SELECT listing_nickname FROM {db_config['table']} WHERE reservation_id = %s LIMIT 1"
            else:
                get_property_query = f"SELECT id FROM {db_config['table']} WHERE reservation_id = %s LIMIT 1"
            cursor.execute(get_property_query, (reference_id,))
            result = cursor.fetchone()

            cursor.close()
            conn.close()

            if result and result[0]:
                return result[0]
            else:
                return 0

        except pymysql.MySQLError as e:
            print(f"Error in database {i}: {e}") 

    return -1

