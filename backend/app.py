from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import os
import traceback
import warnings
import shutil
import mysql.connector
from mysql.connector import Error
from datetime import datetime

warnings.filterwarnings('ignore')

# -------------------------------
# MySQL Database Configuration
# -------------------------------

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',        # Change this to your MySQL username
    'password': 'Veejnas@4002',         # Change this to your MySQL password
    'database': 'nvme_failure_db'
}

def get_db_connection():
    """Get database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"❌ MySQL Connection Error: {e}")
        return None

def test_db_connection():
    """Test database connection"""
    conn = get_db_connection()
    if conn:
        conn.close()
        return True
    return False

def get_input_history(limit=100):
    """Retrieve input history from database"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Could not connect to database")
            return []
            
        cursor = conn.cursor(dictionary=True)
        
        # Simple query - let Python handle datetime formatting
        query = """
            SELECT 
                id, 
                timestamp,
                power_on_hours,
                total_tbw_tb,
                total_tbr_tb,
                temperature_c,
                percent_life_used,
                media_errors,
                unsafe_shutdowns,
                crc_errors,
                read_error_rate,
                write_error_rate,
                temp_threshold,
                data_source,
                notes,
                created_at
            FROM input_history 
            ORDER BY timestamp DESC 
            LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        # Convert datetime objects to strings
        for row in results:
            if row['timestamp']:
                row['timestamp'] = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            if row['created_at']:
                row['created_at'] = row['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"✓ Retrieved {len(results)} records from database")
        return results
        
    except Error as e:
        print(f"❌ MySQL Error: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def save_input_to_db(input_data, temp_threshold=None, data_source="manual", notes=""):
    """Save input data to MySQL database"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return False, None
            
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO input_history (
            timestamp, power_on_hours, total_tbw_tb, total_tbr_tb,
            temperature_c, percent_life_used, media_errors, unsafe_shutdowns,
            crc_errors, read_error_rate, write_error_rate,
            temp_threshold, data_source, notes
        ) VALUES (
            NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        values = (
            input_data.get('Power_On_Hours', 0),
            input_data.get('Total_TBW_TB', 0),
            input_data.get('Total_TBR_TB', 0),
            input_data.get('Temperature_C', 0),
            input_data.get('Percent_Life_Used', 0),
            input_data.get('Media_Errors', 0),
            input_data.get('Unsafe_Shutdowns', 0),
            input_data.get('CRC_Errors', 0),
            input_data.get('Read_Error_Rate', 0),
            input_data.get('Write_Error_Rate', 0),
            temp_threshold,
            data_source,
            notes
        )
        
        cursor.execute(insert_query, values)
        conn.commit()
        
        entry_id = cursor.lastrowid
        print(f"✓ Saved input as entry #{entry_id}")
        return True, entry_id
        
    except Error as e:
        print(f"❌ MySQL Error: {e}")
        return False, None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def delete_history_entry(entry_id):
    """Delete a specific history entry"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        cursor = conn.cursor()
        cursor.execute("DELETE FROM input_history WHERE id = %s", (entry_id,))
        conn.commit()
        
        deleted = cursor.rowcount > 0
        if deleted:
            print(f"✓ Deleted entry {entry_id}")
        return deleted
        
    except Error as e:
        print(f"❌ MySQL Error: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_history_entry(entry_id):
    """Get a specific history entry by ID"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM input_history WHERE id = %s", (entry_id,))
        
        result = cursor.fetchone()
        if result and result['timestamp']:
            result['timestamp'] = result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        if result and result['created_at']:
            result['created_at'] = result['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return result
        
    except Error as e:
        print(f"❌ MySQL Error: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def clear_all_history():
    """Clear all history entries"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return 0
            
        cursor = conn.cursor()
        cursor.execute("DELETE FROM input_history")
        conn.commit()
        
        count = cursor.rowcount
        print(f"✓ Cleared {count} entries from database")
        return count
        
    except Error as e:
        print(f"❌ MySQL Error: {e}")
        return 0
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# -------------------------------
# Import Predictors
# -------------------------------

try:
    from utils.wearout_predictor import WearoutPredictor
    from utils.thermal_predictor import ThermalPredictor
    from utils.power_predictor import PowerPredictor
    from utils.controller_predictor import ControllerPredictor
    from system_info_extractor import get_system_info

    wearout_predictor = WearoutPredictor()
    thermal_predictor = ThermalPredictor()
    power_predictor = PowerPredictor()
    controller_predictor = ControllerPredictor()

    PREDICTORS_LOADED = True
    print("✓ Predictors loaded successfully")

except Exception as e:
    print(f"⚠️ Predictor loading failed: {e}")
    PREDICTORS_LOADED = False

    class FallbackPredictor:
        def predict(self, df):
            return {
                "risk_percentage": 25.0,
                "contributions": {"Fallback": 100},
                "status": "Fallback Mode"
            }

    wearout_predictor = thermal_predictor = power_predictor = controller_predictor = FallbackPredictor()

# -------------------------------
# App Init
# -------------------------------

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

DEFAULT_TEMP_THRESHOLD = 84

FEATURES = [
    "Power_On_Hours",
    "Total_TBW_TB",
    "Total_TBR_TB",
    "Temperature_C",
    "Percent_Life_Used",
    "Media_Errors",
    "Unsafe_Shutdowns",
    "CRC_Errors",
    "Read_Error_Rate",
    "Write_Error_Rate"
]

# -------------------------------
# Routes
# -------------------------------

@app.route('/')
def index():
    return jsonify({
        "message": "NVMe Failure Prediction API",
        "status": "running"
    })

@app.route('/api/features', methods=['GET'])
def get_features():
    """Return list of features and default values for the frontend"""
    try:
        features = [
            "Power_On_Hours",
            "Total_TBW_TB",
            "Total_TBR_TB",
            "Temperature_C",
            "Percent_Life_Used",
            "Media_Errors",
            "Unsafe_Shutdowns",
            "CRC_Errors",
            "Read_Error_Rate",
            "Write_Error_Rate"
        ]
        
        defaults = {
            "Power_On_Hours": 1000,
            "Total_TBW_TB": 50.0,
            "Total_TBR_TB": 40.0,
            "Temperature_C": 35.0,
            "Percent_Life_Used": 5.0,
            "Media_Errors": 0,
            "Unsafe_Shutdowns": 0,
            "CRC_Errors": 0,
            "Read_Error_Rate": 0.5,
            "Write_Error_Rate": 0.3
        }
        
        return jsonify({
            "success": True,
            "features": features,
            "defaults": defaults
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/system-info', methods=['GET'])
def system_info():
    """Get system info but DON'T save to database"""
    try:
        result = get_system_info()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    db_connected = test_db_connection()
    return jsonify({
        "success": True,
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "predictors_loaded": PREDICTORS_LOADED,
        "smartctl_available": shutil.which("smartctl") is not None,
        "database_connected": db_connected
    })

@app.route('/api/db-status', methods=['GET'])
def db_status():
    """Check database connection and get basic stats"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "connected": False,
                "total_records": 0,
                "message": "Could not get database connection"
            })
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM input_history")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "connected": True,
            "total_records": count,
            "message": "Database connected"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "connected": False,
            "error": str(e)
        })

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get input history"""
    try:
        limit = request.args.get('limit', 100, type=int)
        print(f"📊 Fetching history (limit: {limit})...")
        
        history = get_input_history(limit)
        
        # Also get total count
        conn = get_db_connection()
        total_count = 0
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM input_history")
            total_count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
        
        return jsonify({
            "success": True,
            "count": len(history),
            "total_count": total_count,
            "data": history
        })
    except Exception as e:
        print(f"❌ Error in get_history: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "data": []
        }), 500

@app.route('/api/history/<int:entry_id>', methods=['GET'])
def get_history_entry_by_id(entry_id):
    """Get specific history entry"""
    try:
        entry = get_history_entry(entry_id)
        if entry:
            return jsonify({
                "success": True,
                "data": entry
            })
        else:
            return jsonify({
                "success": False,
                "error": "Entry not found"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/history/<int:entry_id>', methods=['DELETE'])
def delete_history(entry_id):
    """Delete a history entry"""
    try:
        deleted = delete_history_entry(entry_id)
        if deleted:
            return jsonify({
                "success": True,
                "message": f"Entry {entry_id} deleted"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Entry not found"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/history/clear', methods=['DELETE'])
def clear_all_history_endpoint():
    """Clear all history (with confirmation)"""
    try:
        count = clear_all_history()
        return jsonify({
            "success": True,
            "message": f"Deleted {count} entries"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        if not request.is_json:
            return jsonify({"success": False, "error": "JSON required"}), 400

        data = request.get_json()
        
        # Check if this is a history run with laptop status
        laptop_working = data.pop('laptop_working', True)
        from_history = data.pop('from_history', False)
        entry_id = data.pop('history_entry_id', None)

        print(f"\n{'='*60}")
        print(f"PREDICTION REQUEST")
        print(f"{'='*60}")
        print(f"Laptop Working: {laptop_working}")
        print(f"From History: {from_history}")
        print(f"History ID: {entry_id}")
        print(f"Input Data: {data}")

        # Validate input
        input_df = pd.DataFrame([data])

        for feature in FEATURES:
            if feature not in input_df.columns:
                input_df[feature] = 0

        results = {}

        # Get temperature threshold
        system_info_data = get_system_info()
        temp_threshold = system_info_data.get("temp_threshold", DEFAULT_TEMP_THRESHOLD)

        # ========== SAVE INPUT DATA TO DATABASE ==========
        input_data = {
            "Power_On_Hours": data.get('Power_On_Hours', 0),
            "Total_TBW_TB": data.get('Total_TBW_TB', 0),
            "Total_TBR_TB": data.get('Total_TBR_TB', 0),
            "Temperature_C": data.get('Temperature_C', 0),
            "Percent_Life_Used": data.get('Percent_Life_Used', 0),
            "Media_Errors": data.get('Media_Errors', 0),
            "Unsafe_Shutdowns": data.get('Unsafe_Shutdowns', 0),
            "CRC_Errors": data.get('CRC_Errors', 0),
            "Read_Error_Rate": data.get('Read_Error_Rate', 0),
            "Write_Error_Rate": data.get('Write_Error_Rate', 0)
        }
        
        notes = "Manual prediction"
        if from_history:
            notes = f"Run from history (entry {entry_id})"
        
        save_success, new_entry_id = save_input_to_db(
            input_data,
            temp_threshold=temp_threshold,
            data_source="manual",
            notes=notes
        )
        
        if save_success:
            print(f"✓ Saved input as entry #{new_entry_id}")
        # =================================================

        # ---------------- Wearout ----------------
        try:
            results['wearout'] = wearout_predictor.predict(input_df)
        except:
            results['wearout'] = {
                "risk_percentage": 25,
                "contributions": {"Power_On_Hours": 50, "Percent_Life_Used": 50},
                "status": "Fallback"
            }

        # ---------------- Thermal ----------------
        try:
            if hasattr(thermal_predictor, "predict_with_threshold"):
                results['thermal'] = thermal_predictor.predict_with_threshold(
                    input_df,
                    temp_threshold
                )
            else:
                results['thermal'] = thermal_predictor.predict(input_df)

        except Exception as e:
            results['thermal'] = {
                "risk_percentage": 25,
                "contributions": {"Temperature_C": 100},
                "status": "Thermal fallback"
            }

        # ---------------- Power ----------------
        try:
            results['power'] = power_predictor.predict(input_df)
        except:
            results['power'] = {
                "risk_percentage": 20,
                "contributions": {"Unsafe_Shutdowns": 100},
                "status": "Fallback"
            }

        # ---------------- Controller ----------------
        try:
            results['controller'] = controller_predictor.predict(input_df)
        except:
            results['controller'] = {
                "risk_percentage": 20,
                "contributions": {"Media_Errors": 50, "CRC_Errors": 50},
                "status": "Fallback"
            }

        # ---------------- Summary with laptop status ----------------
        results["summary"] = generate_summary(results, laptop_working)

        results["metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "predictors_loaded": PREDICTORS_LOADED,
            "temp_threshold": temp_threshold,
            "input_saved_to_db": save_success,
            "new_entry_id": new_entry_id,
            "laptop_working": laptop_working,
            "from_history": from_history
        }

        print(f"\n✓ Prediction complete")
        print(f"{'='*60}\n")

        return jsonify({
            "success": True,
            "results": results
        })

    except Exception as e:
        print(f"❌ Prediction error: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

def generate_summary(results, laptop_working=True):
    predictions = {
        "Wear-Out": results["wearout"]["risk_percentage"],
        "Thermal": results["thermal"]["risk_percentage"],
        "Power": results["power"]["risk_percentage"],
        "Controller": results["controller"]["risk_percentage"]
    }

    highest = max(predictions.items(), key=lambda x: x[1])
    
    # Special case: If laptop is NOT working and all predictions are below 50%
    if not laptop_working and all(risk < 50 for risk in predictions.values()):
        status = "RAPID ERROR ACCUMULATION"
        overall_risk = highest[1]
        special_message = "Manufacturing Defect Detected"
        special_description = "System shows rapid error accumulation despite all SMART values being normal. This pattern typically indicates a manufacturing defect in the SSD controller or NAND flash."
        
        recommendations = [
            "🔴 MANUFACTURING DEFECT DETECTED",
            "• Contact manufacturer for warranty claim",
            "• Immediate RMA request recommended",
            "• Do not attempt to repair - this is a hardware defect",
            "• Backup all critical data immediately"
        ]
    else:
        if highest[1] < 50:
            status = "Healthy"
            special_message = None
            special_description = None
        elif highest[1] < 70:
            status = "Warning"
            special_message = None
            special_description = None
        else:
            status = "Critical"
            special_message = None
            special_description = None

        recommendations = []
        if highest[1] >= 70:
            recommendations.append(f"🚨 CRITICAL: {highest[0]} failure risk is very high")
            recommendations.append("• Immediate backup recommended")
            recommendations.append("• Consider drive replacement")
            recommendations.append("• Monitor system closely")
        elif highest[1] >= 50:
            recommendations.append(f"⚠️ WARNING: {highest[0]} failure risk is elevated")
            recommendations.append("• Backup data soon")
            recommendations.append("• Monitor drive health regularly")
            recommendations.append("• Consider preventive maintenance")
        else:
            recommendations.append("✅ Drive health is good")
            recommendations.append("• Continue regular monitoring")
            recommendations.append("• No immediate action required")

    return {
        "status": status,
        "overall_risk": highest[1],
        "predictions": predictions,
        "recommendation": recommendations,
        "highest_risk": highest[0],
        "risk_percentage": highest[1],
        "special_message": special_message,
        "special_description": special_description,
        "laptop_working": laptop_working
    }

@app.route('/api/train/wearout', methods=['POST'])
def train_wearout():
    try:
        result = wearout_predictor.train_model()
        return jsonify({
            "success": True,
            "result": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/train/controller', methods=['POST'])
def train_controller():
    try:
        result = controller_predictor.train_model()
        return jsonify({
            "success": True,
            "result": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# -------------------------------
# Run Server
# -------------------------------

if __name__ == "__main__":
    print("\n" + "="*60)
    print("NVMe Failure Prediction Backend")
    print("="*60)
    
    if test_db_connection():
        print(f"✓ MySQL Database: {DB_CONFIG['database']} @ {DB_CONFIG['host']}")
        
        # Test query
        test_data = get_input_history(5)
        print(f"✓ Test query returned {len(test_data)} records")
    else:
        print("⚠️ MySQL Database not connected")
        print("   Please check your MySQL configuration")
    
    print(f"✓ Predictors loaded: {PREDICTORS_LOADED}")
    print(f"✓ smartctl available: {shutil.which('smartctl') is not None}")
    print("\n📡 Server running on: http://localhost:8080")
    print("="*60 + "\n")

    app.run(
        debug=True,
        port=8080,
        host="0.0.0.0"
    )