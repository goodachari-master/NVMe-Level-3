import mysql.connector
from mysql.connector import Error

# Update these with your credentials
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Veejnas@4002',  # Add your password
    'database': 'nvme_failure_db'
}

def check_database():
    try:
        # Connect to database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Check if table exists
        cursor.execute("SHOW TABLES LIKE 'input_history'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("❌ Table 'input_history' does not exist!")
            return
        
        # Get total count
        cursor.execute("SELECT COUNT(*) as count FROM input_history")
        count = cursor.fetchone()['count']
        print(f"\n📊 Total records in database: {count}")
        
        if count == 0:
            print("❌ No records found in database")
            print("\nTo insert test data, run:")
            print("INSERT INTO input_history (timestamp, power_on_hours, temperature_c, percent_life_used, total_tbw_tb, data_source) VALUES (NOW(), 15000, 47.5, 65.2, 245.7, 'manual');")
            return
        
        # Get latest 5 records
        cursor.execute("""
            SELECT 
                id,
                DATE_FORMAT(timestamp, '%Y-%m-%d %H:%i:%s') as timestamp,
                power_on_hours,
                temperature_c,
                percent_life_used,
                total_tbw_tb,
                data_source
            FROM input_history 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        
        records = cursor.fetchall()
        
        print("\n📋 Latest 5 records:")
        print("-" * 100)
        print(f"{'ID':<5} {'Timestamp':<20} {'Power Hours':<12} {'Temp':<8} {'Life Used':<10} {'Data Written':<12} {'Source':<10}")
        print("-" * 100)
        
        for record in records:
            print(f"{record['id']:<5} {record['timestamp']:<20} {record['power_on_hours']:<12} "
                  f"{record['temperature_c']:<8} {record['percent_life_used']:<10}% "
                  f"{record['total_tbw_tb']:<12} {record['data_source']:<10}")
        
        print("-" * 100)
        
    except Error as e:
        print(f"❌ MySQL Error: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("\n✅ Database connection closed")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("NVMe Failure Prediction - Database Checker")
    print("="*60)
    check_database()