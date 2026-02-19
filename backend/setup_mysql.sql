-- MySQL setup script for NVMe Failure Prediction System

-- Create database
CREATE DATABASE IF NOT EXISTS nvme_failure_db;
USE nvme_failure_db;

-- Create input history table (stores only input data, no predictions)
CREATE TABLE IF NOT EXISTS input_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL COMMENT 'Time when input was recorded',
    
    -- Input features
    power_on_hours FLOAT COMMENT 'Total power-on hours of drive',
    total_tbw_tb FLOAT COMMENT 'Total data written in TB',
    total_tbr_tb FLOAT COMMENT 'Total data read in TB',
    temperature_c FLOAT COMMENT 'Drive temperature in Celsius',
    percent_life_used FLOAT COMMENT 'Estimated life used percentage',
    media_errors INT COMMENT 'Media errors count',
    unsafe_shutdowns INT COMMENT 'Number of unsafe shutdowns',
    crc_errors INT COMMENT 'CRC error count',
    read_error_rate FLOAT COMMENT 'Read error rate',
    write_error_rate FLOAT COMMENT 'Write error rate',
    
    -- Metadata
    temp_threshold FLOAT COMMENT 'Temperature threshold used',
    data_source VARCHAR(50) COMMENT 'Source of data (manual/system/sample)',
    notes TEXT COMMENT 'Additional notes',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
    
    INDEX idx_timestamp (timestamp),
    INDEX idx_source (data_source),
    INDEX idx_temp_threshold (temp_threshold)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Stores NVMe drive input data for analysis';

-- Create view for easy data analysis
CREATE OR REPLACE VIEW input_analysis AS
SELECT 
    DATE(timestamp) as date,
    HOUR(timestamp) as hour,
    data_source,
    COUNT(*) as total_inputs,
    AVG(power_on_hours) as avg_power_hours,
    AVG(temperature_c) as avg_temperature,
    AVG(percent_life_used) as avg_life_used,
    AVG(total_tbw_tb + total_tbr_tb) as avg_total_data_tb,
    MAX(unsafe_shutdowns) as max_unsafe_shutdowns,
    AVG(temp_threshold) as avg_temp_threshold
FROM input_history
GROUP BY DATE(timestamp), HOUR(timestamp), data_source
ORDER BY date DESC, hour DESC;

-- Example queries for reference:

-- 1. Get latest 10 inputs
-- SELECT * FROM input_history ORDER BY timestamp DESC LIMIT 10;

-- 2. Get high-risk drive inputs (high temperature)
-- SELECT timestamp, temperature_c, percent_life_used 
-- FROM input_history 
-- WHERE temperature_c > 70 
-- ORDER BY timestamp DESC;

-- 3. Count by data source
-- SELECT data_source, COUNT(*) as count 
-- FROM input_history 
-- GROUP BY data_source;

-- 4. Daily statistics
-- SELECT DATE(timestamp) as day, 
--        COUNT(*) as inputs,
--        AVG(temperature_c) as avg_temp,
--        AVG(percent_life_used) as avg_wear
-- FROM input_history 
-- GROUP BY DATE(timestamp) 
-- ORDER BY day DESC;
