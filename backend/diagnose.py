import mysql.connector
from mysql.connector import Error
import sys
import os
from datetime import datetime

# Update these with your credentials
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',        # Change this
    'password': 'Veejnas@4002',         # Change this
    'database': 'nvme_failure_db'
}

def print_header(text):
    print("\n" + "="*100)
    print(f" {text}")
    print("="*100)

def format_timestamp(dt):
    """Format datetime object to string"""
    if dt and isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return str(dt) if dt else "NULL"

def main():
    print_header("NVMe FAILURE PREDICTION - DATABASE CHECKER")
    
    try:
        # Connect to database
        print("\n🔌 Connecting to MySQL...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        print("✅ Connected to MySQL successfully")
        
        # Check if table exists
        cursor.execute("SHOW TABLES LIKE 'input_history'")
        if not cursor.fetchone():
            print("❌ Table 'input_history' does not exist!")
            
            # Create table
            print("\n📝 Creating table...")
            create_table_query = """
            CREATE TABLE IF NOT EXISTS input_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                power_on_hours FLOAT,
                total_tbw_tb FLOAT,
                total_tbr_tb FLOAT,
                temperature_c FLOAT,
                percent_life_used FLOAT,
                media_errors INT,
                unsafe_shutdowns INT,
                crc_errors INT,
                read_error_rate FLOAT,
                write_error_rate FLOAT,
                temp_threshold FLOAT,
                data_source VARCHAR(50),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(create_table_query)
            conn.commit()
            print("✅ Table created successfully")
            
            # Insert sample data
            print("\n📝 Inserting sample data...")
            insert_query = """
            INSERT INTO input_history (
                timestamp, power_on_hours, total_tbw_tb, total_tbr_tb,
                temperature_c, percent_life_used, media_errors, unsafe_shutdowns,
                crc_errors, read_error_rate, write_error_rate,
                temp_threshold, data_source, notes
            ) VALUES 
            (NOW(), 15000, 245.7, 198.3, 47.5, 65.2, 1, 2, 0, 3.7, 2.4, 84, 'manual', 'Sample entry 1'),
            (NOW() - INTERVAL 1 DAY, 12000, 189.3, 152.1, 52.3, 45.8, 0, 1, 0, 2.1, 1.8, 84, 'system', 'Sample entry 2'),
            (NOW() - INTERVAL 2 DAY, 8760, 150.5, 120.2, 38.9, 32.0, 0, 0, 0, 0.5, 0.3, 84, 'sample', 'Sample entry 3')
            """
            cursor.execute(insert_query)
            conn.commit()
            print("✅ Sample data inserted")
        
        # Get total count
        cursor.execute("SELECT COUNT(*) as count FROM input_history")
        total = cursor.fetchone()['count']
        print(f"\n📊 Total records in database: {total}")
        
        if total == 0:
            print("\n❌ No records found!")
            print("\nTo insert test data, run these SQL commands:")
            print("-" * 50)
            print("USE nvme_failure_db;")
            print("""
INSERT INTO input_history (
    timestamp, power_on_hours, total_tbw_tb, total_tbr_tb,
    temperature_c, percent_life_used, media_errors, unsafe_shutdowns,
    crc_errors, read_error_rate, write_error_rate,
    temp_threshold, data_source, notes
) VALUES 
(NOW(), 15000, 245.7, 198.3, 47.5, 65.2, 1, 2, 0, 3.7, 2.4, 84, 'manual', 'Test entry 1'),
(NOW() - INTERVAL 1 DAY, 12000, 189.3, 152.1, 52.3, 45.8, 0, 1, 0, 2.1, 1.8, 84, 'system', 'Test entry 2'),
(NOW() - INTERVAL 2 DAY, 8760, 150.5, 120.2, 38.9, 32.0, 0, 0, 0, 0.5, 0.3, 84, 'sample', 'Test entry 3');
            """)
            return
        
        # Get ALL records without using DATE_FORMAT
        cursor.execute("SELECT * FROM input_history ORDER BY timestamp DESC")
        records = cursor.fetchall()
        
        print(f"\n📋 DISPLAYING ALL {len(records)} RECORDS:")
        print("="*100)
        
        for i, record in enumerate(records, 1):
            print(f"\n📌 RECORD #{i} (ID: {record['id']})")
            print("-" * 60)
            
            # Format each field properly
            for key, value in record.items():
                if value is None:
                    formatted_value = "NULL"
                elif isinstance(value, datetime):
                    formatted_value = value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, float):
                    if key in ['temperature_c', 'temp_threshold']:
                        formatted_value = f"{value:.1f}°C"
                    elif key in ['percent_life_used']:
                        formatted_value = f"{value:.1f}%"
                    elif key in ['total_tbw_tb', 'total_tbr_tb']:
                        formatted_value = f"{value:.2f} TB"
                    elif key in ['read_error_rate', 'write_error_rate']:
                        formatted_value = f"{value:.3f}"
                    else:
                        formatted_value = str(value)
                elif isinstance(value, int):
                    if key in ['power_on_hours']:
                        formatted_value = f"{value:,} hours"
                    elif key in ['media_errors', 'unsafe_shutdowns', 'crc_errors']:
                        formatted_value = str(value)
                    else:
                        formatted_value = str(value)
                else:
                    formatted_value = str(value)
                
                # Print with proper spacing
                print(f"   {key:20}: {formatted_value}")
        
        print("\n" + "="*100)
        print(f"✅ Total {len(records)} records displayed")
        print("="*100)
        
        # Show summary statistics
        print("\n📊 SUMMARY STATISTICS:")
        print("-" * 60)
        
        temps = [r['temperature_c'] for r in records if r['temperature_c'] is not None]
        lives = [r['percent_life_used'] for r in records if r['percent_life_used'] is not None]
        data_written = [r['total_tbw_tb'] for r in records if r['total_tbw_tb'] is not None]
        
        if temps:
            avg_temp = sum(temps) / len(temps)
            max_temp = max(temps)
            print(f"   Average Temperature : {avg_temp:.1f}°C")
            print(f"   Maximum Temperature : {max_temp:.1f}°C")
        
        if lives:
            avg_life = sum(lives) / len(lives)
            print(f"   Average Life Used   : {avg_life:.1f}%")
        
        if data_written:
            total_data = sum(data_written)
            print(f"   Total Data Written  : {total_data:.2f} TB")
        
        # Count by source
        sources = {}
        for r in records:
            src = r['data_source'] or 'unknown'
            sources[src] = sources.get(src, 0) + 1
        
        if sources:
            print("\n   Records by Source:")
            for src, count in sources.items():
                print(f"      {src}: {count}")
        
        cursor.close()
        conn.close()
        print("\n✅ Database connection closed")
        
    except Error as e:
        print(f"\n❌ MySQL Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check if MySQL is running:")
        print("      brew services list | grep mysql")
        print("   2. Start MySQL if not running:")
        print("      brew services start mysql")
        print("   3. Update credentials in DB_CONFIG:")
        print("      DB_CONFIG = {")
        print("          'host': 'localhost',")
        print("          'user': 'YOUR_USERNAME',  # Change this")
        print("          'password': 'YOUR_PASSWORD',  # Add your password")
        print("          'database': 'nvme_failure_db'")
        print("      }")
        print("   4. Create database if not exists:")
        print("      mysql -u root -p -e 'CREATE DATABASE nvme_failure_db;'")

if __name__ == "__main__":
    main()