// Configuration
const API_BASE_URL = 'http://localhost:8080/api';
let featureDefaults = {};
let radarCharts = {};
let currentInputData = {};
let pendingDeleteId = null;

// Function to update laptop status button appearance
function updateLaptopStatusButton(isWorking) {
    const btn = document.getElementById('laptopStatusBtn');
    if (btn) {
        // Remove both classes
        btn.classList.remove('working', 'not-working');
        
        if (isWorking) {
            btn.classList.add('working');
            btn.innerHTML = '<i class="fas fa-check"></i> Working';
        } else {
            btn.classList.add('not-working');
            btn.innerHTML = '<i class="fas fa-times"></i> Not Working';
        }
    }
}

// Initialize application
document.addEventListener('DOMContentLoaded', async function() {
    await initializeApp();
    setupEventListeners();
    checkBackendConnection();
    
    // Initialize laptop status button after everything is loaded
    const laptopCheckbox = document.getElementById('laptopWorking');
    if (laptopCheckbox) {
        updateLaptopStatusButton(laptopCheckbox.checked);
    }
});

async function initializeApp() {
    try {
        const response = await fetch(`${API_BASE_URL}/features`);
        const data = await response.json();
        
        if (data.success) {
            featureDefaults = data.defaults;
            createInputFields(data.features);
            populateDefaultValues();
            initializeRadarCharts();
        } else {
            throw new Error(data.error || 'Failed to load features');
        }
        
    } catch (error) {
        console.error('Error initializing app:', error);
        showError('Failed to initialize application. Please check if backend is running.');
    }
}

function createInputFields(features) {
    const formGrid = document.getElementById('inputForm');
    formGrid.innerHTML = '';
    
    features.forEach(feature => {
        const inputGroup = document.createElement('div');
        inputGroup.className = 'input-group';
        
        const label = document.createElement('label');
        label.htmlFor = feature;
        label.textContent = formatLabel(feature);
        
        const input = document.createElement('input');
        input.type = 'number';
        input.id = feature;
        input.name = feature;
        input.step = feature.includes('Error') ? '1' : '0.01';
        input.min = '0';
        input.value = featureDefaults[feature] || 0;
        input.addEventListener('input', () => saveCurrentInputData());
        
        inputGroup.appendChild(label);
        inputGroup.appendChild(input);
        formGrid.appendChild(inputGroup);
    });
}

function formatLabel(text) {
    let formatted = text.replace(/_/g, ' ');
    formatted = formatted.replace(/\b\w/g, l => l.toUpperCase());
    formatted = formatted.replace('Tb', 'TB');
    formatted = formatted.replace(/ C(?=\s|$)/g, ' (°C)');
    return formatted;
}

function populateDefaultValues() {
    Object.entries(featureDefaults).forEach(([feature, value]) => {
        const input = document.getElementById(feature);
        if (input) {
            input.value = value;
        }
    });
    saveCurrentInputData();
}

function saveCurrentInputData() {
    currentInputData = collectInputData();
}

function initializeRadarCharts() {
    const chartIds = ['wearoutRadar', 'thermalRadar', 'powerRadar', 'controllerRadar'];
    
    chartIds.forEach(id => {
        const ctx = document.getElementById(id);
        if (!ctx) return;
        
        radarCharts[id] = new Chart(ctx.getContext('2d'), {
            type: 'radar',
            data: {
                labels: Object.keys(featureDefaults).map(f => formatLabel(f)),
                datasets: [{
                    label: 'Feature Values',
                    data: Object.values(featureDefaults).map(v => normalizeFeatureValue(v, 0)),
                    backgroundColor: 'rgba(52, 152, 219, 0.2)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 2,
                    pointBackgroundColor: 'rgba(52, 152, 219, 1)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(52, 152, 219, 1)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: { display: false, stepSize: 20 },
                        pointLabels: { font: { size: 10 }, color: '#666' },
                        grid: { color: 'rgba(0, 0, 0, 0.1)' },
                        angleLines: { color: 'rgba(0, 0, 0, 0.1)' }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const feature = context.chart.data.labels[context.dataIndex];
                                const value = getOriginalValueFromNormalized(context.parsed.r, feature);
                                return `${feature}: ${value}`;
                            }
                        }
                    }
                }
            }
        });
    });
}

function normalizeFeatureValue(value, index) {
    const featureNames = Object.keys(featureDefaults);
    const featureName = featureNames[index];
    
    const maxValues = {
        'Power_On_Hours': 60000,
        'Total_TBW_TB': 1000,
        'Total_TBR_TB': 800,
        'Temperature_C': 90,
        'Percent_Life_Used': 150,
        'Media_Errors': 10,
        'Unsafe_Shutdowns': 10,
        'CRC_Errors': 5,
        'Read_Error_Rate': 20,
        'Write_Error_Rate': 15
    };
    
    const maxValue = maxValues[featureName] || 100;
    return Math.min((value / maxValue) * 100, 100);
}

function getOriginalValueFromNormalized(normalizedValue, featureLabel) {
    const featureName = featureLabel.replace(/\s*\(°C\)/g, ' C').replace(/\s+/g, '_').toLowerCase();
    
    const maxValues = {
        'power_on_hours': 60000,
        'total_tbw_tb': 1000,
        'total_tbr_tb': 800,
        'temperature_c': 90,
        'percent_life_used': 150,
        'media_errors': 10,
        'unsafe_shutdowns': 10,
        'crc_errors': 5,
        'read_error_rate': 20,
        'write_error_rate': 15
    };
    
    const maxValue = maxValues[featureName] || 100;
    return ((normalizedValue / 100) * maxValue).toFixed(2);
}

function setupEventListeners() {
    document.getElementById('predictBtn').addEventListener('click', () => predictAllFailures(false, null));
    document.getElementById('resetBtn').addEventListener('click', resetForm);
    document.getElementById('autoFillBtn').addEventListener('click', autoFillSystemData);
    document.getElementById('trainWearoutBtn').addEventListener('click', () => trainModel('wearout'));
    document.getElementById('trainControllerBtn').addEventListener('click', () => trainModel('controller'));
    
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            switchTab(this.dataset.tab);
        });
    });
    
    // Set up laptop status button toggle
    const laptopStatusBtn = document.getElementById('laptopStatusBtn');
    const laptopCheckbox = document.getElementById('laptopWorking');
    
    if (laptopStatusBtn && laptopCheckbox) {
        // Initialize button state based on checkbox
        updateLaptopStatusButton(laptopCheckbox.checked);
        
        // Toggle state when button is clicked
        laptopStatusBtn.addEventListener('click', function() {
            // Toggle the checkbox state
            laptopCheckbox.checked = !laptopCheckbox.checked;
            
            // Update button appearance
            updateLaptopStatusButton(laptopCheckbox.checked);
        });
    }
    

}

async function checkBackendConnection() {
    const statusEl = document.getElementById('connectionStatus');
    if (!statusEl) {
        console.warn('⚠️ Connection status element not found');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            const dbStatus = data.database_connected ? 'Connected' : 'Disconnected';
            statusEl.innerHTML = `
                <div style="background-color: #d4edda; color: #155724; padding: 12px; border-radius: 5px; border: 1px solid #c3e6cb;">
                    <i class="fas fa-check-circle"></i> 
                    <strong>Backend Connected</strong> | Port: 8080 | Database: ${dbStatus}
                </div>
            `;
            console.log('✅ Backend connected');
        } else {
            statusEl.innerHTML = `
                <div style="background-color: #f8d7da; color: #721c24; padding: 12px; border-radius: 5px; border: 1px solid #f5c6cb;">
                    <i class="fas fa-exclamation-triangle"></i> 
                    <strong>Backend Connection Issue</strong>
                </div>
            `;
        }
    } catch (error) {
        statusEl.innerHTML = `
            <div style="background-color: #f8d7da; color: #721c24; padding: 12px; border-radius: 5px; border: 1px solid #f5c6cb;">
                <i class="fas fa-exclamation-triangle"></i> 
                <strong>Backend Not Reachable</strong><br>
                Please start the server on port 8080: cd backend && python app.py
            </div>
        `;
        console.error('❌ Backend not reachable:', error);
    }
}

async function autoFillSystemData() {
    const button = document.getElementById('autoFillBtn');
    const originalText = button.innerHTML;
    
    button.innerHTML = '<span class="loading"></span> Scanning...';
    button.disabled = true;
    
    const statusElement = document.getElementById('autoFillStatus');
    statusElement.innerHTML = '<p><i class="fas fa-search"></i> Scanning system...</p>';
    statusElement.style.color = '#f39c12';
    
    try {
        const response = await fetch(`${API_BASE_URL}/system-info`);
        
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const result = await response.json();
        
        if (result.success) {
            Object.entries(result.data).forEach(([feature, value]) => {
                const input = document.getElementById(feature);
                if (input && value !== null && value !== undefined) {
                    input.value = value;
                }
            });
            
            saveCurrentInputData();
            
            statusElement.innerHTML = `
                <p><i class="fas fa-check-circle"></i> System info retrieved!</p>
                <p><i class="fas fa-thermometer"></i> Temp threshold: ${result.temp_threshold}°C</p>
            `;
            statusElement.style.color = '#27ae60';
            
            if (result.temp_threshold) {
                window.tempThreshold = result.temp_threshold;
            }
            
        } else {
            throw new Error(result.message || 'Failed to retrieve system info');
        }
        
    } catch (error) {
        console.error('Error auto-filling:', error);
        provideSampleData();
        
        statusElement.innerHTML = `
            <p><i class="fas fa-exclamation-triangle"></i> Using sample data</p>
            <p class="auto-fill-note">${error.message}</p>
        `;
        statusElement.style.color = '#f39c12';
        
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

function provideSampleData() {
    const sampleData = {
        'Power_On_Hours': 15000,
        'Total_TBW_TB': 245.7,
        'Total_TBR_TB': 198.3,
        'Temperature_C': 47.5,
        'Percent_Life_Used': 65.2,
        'Media_Errors': 1,
        'Unsafe_Shutdowns': 2,
        'CRC_Errors': 0,
        'Read_Error_Rate': 3.7,
        'Write_Error_Rate': 2.4
    };
    
    Object.entries(sampleData).forEach(([feature, value]) => {
        const input = document.getElementById(feature);
        if (input) input.value = value;
    });
    
    saveCurrentInputData();
    window.tempThreshold = 84;
}

async function predictAllFailures(fromHistory = false, historyId = null) {
    const inputData = collectInputData();
    const laptopWorking = document.getElementById('laptopWorking')?.checked ?? true;
    
    if (!validateInputs(inputData)) {
        alert('Please fill all fields with valid numbers');
        return;
    }
    
    showLoading(true);
    
    try {
        const payload = {
            ...inputData,
            laptop_working: laptopWorking,
            from_history: fromHistory,
            history_entry_id: historyId,
            ...(window.tempThreshold && { temp_threshold: window.tempThreshold })
        };
        
        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const result = await response.json();
        if (!result.success) throw new Error(result.error || 'Prediction failed');
        
        displayResults(result.results, inputData);
        
        // Refresh history after prediction
        setTimeout(() => loadHistory(), 500);
        
    } catch (error) {
        console.error('Error predicting:', error);
        alert('Failed to get predictions. Please try again.');
    } finally {
        showLoading(false);
    }
}

function collectInputData() {
    const inputs = {};
    document.querySelectorAll('#inputForm input').forEach(input => {
        const value = parseFloat(input.value);
        inputs[input.id] = isNaN(value) ? 0 : value;
    });
    return inputs;
}

function validateInputs(data) {
    return Object.values(data).every(value => 
        typeof value === 'number' && !isNaN(value) && isFinite(value)
    );
}

function displayResults(results, inputData) {
    displaySummary(results.summary);
    displayPrediction('wearout', results.wearout, inputData);
    displayPrediction('thermal', results.thermal, inputData);
    displayPrediction('power', results.power, inputData);
    displayPrediction('controller', results.controller, inputData);
    switchTab('summary');
}

function displaySummary(summary) {
    const statusElement = document.getElementById('overallStatus');
    const riskMeters = document.getElementById('riskMeters');
    const recommendationsList = document.getElementById('recommendationsList');
    const specialMessage = document.getElementById('specialMessage');
    
    if (!statusElement || !riskMeters || !recommendationsList) return;
    
    let icon = 'fa-check-circle';
    if (summary.status?.includes('RAPID ERROR')) {
        icon = 'fa-exclamation-triangle';
    } else if (summary.overall_risk >= 50) {
        icon = 'fa-exclamation-triangle';
    }
    
    statusElement.innerHTML = `<i class="fas ${icon}"></i> ${summary.status || 'No data'}`;
    
    statusElement.className = 'status-healthy';
    if (summary.status?.includes('RAPID ERROR')) {
        statusElement.className = 'status-danger';
    } else if (summary.overall_risk > 50) {
        statusElement.className = 'status-warning';
    }
    if (summary.overall_risk > 70) {
        statusElement.className = 'status-danger';
    }
    
    if (specialMessage) {
        if (summary.special_message) {
            specialMessage.style.display = 'block';
            document.getElementById('specialMessageTitle').textContent = summary.special_message;
            document.getElementById('specialMessageDesc').textContent = summary.special_description;
        } else {
            specialMessage.style.display = 'none';
        }
    }
    
    riskMeters.innerHTML = '';
    if (summary.predictions) {
        Object.entries(summary.predictions).forEach(([type, risk]) => {
            riskMeters.innerHTML += `
                <div class="risk-meter">
                    <h4>${type}</h4>
                    <div class="speed-meter-small">
                        <div class="speed-meter-track">
                            <div class="speed-meter-fill" style="width: ${risk}%"></div>
                        </div>
                        <div class="speed-meter-value">${risk.toFixed(1)}%</div>
                    </div>
                    <div class="meter-label">${risk < 50 ? 'Low' : risk < 70 ? 'Medium' : 'High'} Risk</div>
                </div>
            `;
        });
    }
    
    recommendationsList.innerHTML = '';
    if (summary.recommendation?.length > 0) {
        summary.recommendation.forEach(rec => {
            const li = document.createElement('li');
            li.textContent = rec;
            recommendationsList.appendChild(li);
        });
    } else {
        recommendationsList.innerHTML = '<li>No recommendations available</li>';
    }
}

function displayPrediction(type, data, inputData) {
    const riskIndicator = document.getElementById(`${type}RiskIndicator`);
    if (riskIndicator) {
        const riskValue = riskIndicator.querySelector('.risk-value');
        if (riskValue) riskValue.textContent = `${(data.risk_percentage || 0).toFixed(1)}%`;
    }
    
    const meter = document.getElementById(`${type}Meter`);
    if (meter) {
        const meterFill = meter.querySelector('.meter-fill');
        if (meterFill) meterFill.style.width = `${Math.min(data.risk_percentage || 0, 100)}%`;
    }
    
    updateSpeedMeter(type, data.risk_percentage || 0);
    updateRadarChart(type, inputData);
    displayTopContributions(type, data.contributions);
}

function updateSpeedMeter(type, riskPercentage) {
    const needle = document.getElementById(`${type}Needle`);
    const meterValue = document.getElementById(`${type}SpeedMeterValue`);
    
    if (!needle || !meterValue) return;
    
    meterValue.textContent = `${riskPercentage.toFixed(1)}%`;
    
    const minAngle = -135;
    const maxAngle = 135;
    const angle = minAngle + (riskPercentage / 100) * (maxAngle - minAngle);
    needle.style.transform = `rotate(${angle}deg)`;
    
    let color;
    if (riskPercentage < 30) color = '#27ae60';
    else if (riskPercentage < 70) color = '#f39c12';
    else color = '#e74c3c';
    meterValue.style.color = color;
}

function updateRadarChart(type, inputData) {
    const chart = radarCharts[`${type}Radar`];
    if (!chart) return;
    
    const normalizedValues = Object.values(inputData).map((value, index) => 
        normalizeFeatureValue(value, index)
    );
    
    chart.data.datasets[0].data = normalizedValues;
    chart.update();
}

function displayTopContributions(type, contributions) {
    const container = document.getElementById(`${type}Contributions`);
    if (!container) return;
    
    if (!contributions || Object.keys(contributions).length === 0) {
        container.innerHTML = `
            <div class="contribution-item">
                <div class="contribution-info">
                    <span class="contribution-name">No data available</span>
                    <span class="contribution-value">0%</span>
                </div>
                <div class="speed-meter-mini">
                    <div class="speed-meter-track-mini">
                        <div class="speed-meter-fill-mini" style="width: 0%"></div>
                    </div>
                </div>
            </div>
        `;
        return;
    }
    
    const sortedContributions = Object.entries(contributions)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);
    
    let html = '';
    sortedContributions.forEach(([feature, percentage]) => {
        const formattedFeature = formatLabel(feature);
        const barWidth = Math.min(percentage, 100);
        
        let barColor = '#3498db';
        if (percentage > 30) barColor = '#f39c12';
        if (percentage > 60) barColor = '#e74c3c';
        
        html += `
            <div class="contribution-item">
                <div class="contribution-info">
                    <span class="contribution-name">${formattedFeature}</span>
                    <span class="contribution-value">${percentage.toFixed(1)}%</span>
                </div>
                <div class="speed-meter-mini">
                    <div class="speed-meter-track-mini">
                        <div class="speed-meter-fill-mini" style="width: ${barWidth}%; background: ${barColor}"></div>
                    </div>
                    <div class="speed-meter-mini-labels">
                        <span>0</span><span>50</span><span>100</span>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

async function trainModel(modelType) {
    const button = document.getElementById(`train${modelType.charAt(0).toUpperCase() + modelType.slice(1)}Btn`);
    const originalText = button.innerHTML;
    
    button.innerHTML = '<span class="loading"></span> Training...';
    button.disabled = true;
    
    const statusElement = document.getElementById('trainingStatus');
    statusElement.innerHTML = `<p>Training ${modelType} model...</p>`;
    statusElement.style.color = '#f39c12';
    
    try {
        const response = await fetch(`${API_BASE_URL}/train/${modelType}`, {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const result = await response.json();
        
        if (result.success && result.result?.status === 'success') {
            statusElement.innerHTML = `
                <p><i class="fas fa-check-circle"></i> ${modelType} model trained!</p>
                <p>Accuracy: ${(result.result.accuracy * 100).toFixed(2)}%</p>
            `;
            statusElement.style.color = '#27ae60';
        } else {
            throw new Error(result.message || 'Training failed');
        }
        
    } catch (error) {
        statusElement.innerHTML = `<p><i class="fas fa-times-circle"></i> Error: ${error.message}</p>`;
        statusElement.style.color = '#e74c3c';
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

function resetForm() {
    populateDefaultValues();
    
    document.getElementById('overallStatus').innerHTML = '<i class="fas fa-check-circle"></i> No analysis performed yet';
    document.getElementById('overallStatus').className = 'status-healthy';
    
    const specialMessage = document.getElementById('specialMessage');
    if (specialMessage) specialMessage.style.display = 'none';
    
    ['wearout', 'thermal', 'power', 'controller'].forEach(type => {
        const meter = document.getElementById(`${type}Meter`);
        if (meter) {
            const fill = meter.querySelector('.meter-fill');
            if (fill) fill.style.width = '0%';
        }
        
        const indicator = document.getElementById(`${type}RiskIndicator`);
        if (indicator) {
            const value = indicator.querySelector('.risk-value');
            if (value) value.textContent = '0%';
        }
        
        const needle = document.getElementById(`${type}Needle`);
        if (needle) needle.style.transform = 'rotate(-135deg)';
        
        const speedValue = document.getElementById(`${type}SpeedMeterValue`);
        if (speedValue) {
            speedValue.textContent = '0%';
            speedValue.style.color = '#27ae60';
        }
        
        const chart = radarCharts[`${type}Radar`];
        if (chart) {
            chart.data.datasets[0].data = Object.values(featureDefaults).map((v, i) => normalizeFeatureValue(v, i));
            chart.update();
        }
        
        const contributions = document.getElementById(`${type}Contributions`);
        if (contributions) {
            contributions.innerHTML = `
                <div class="contribution-item">
                    <div class="contribution-info">
                        <span class="contribution-name">No data</span>
                        <span class="contribution-value">0%</span>
                    </div>
                    <div class="speed-meter-mini">
                        <div class="speed-meter-track-mini">
                            <div class="speed-meter-fill-mini" style="width: 0%"></div>
                        </div>
                        <div class="speed-meter-mini-labels">
                            <span>0</span><span>50</span><span>100</span>
                        </div>
                    </div>
                </div>
            `;
        }
    });
    
    document.getElementById('recommendationsList').innerHTML = '<li>Enter drive parameters and click "Predict All Failures"</li>';
    document.getElementById('riskMeters').innerHTML = '';
    document.getElementById('autoFillStatus').innerHTML = '';
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.toggle('active', pane.id === tabName);
    });
    

}

function showLoading(show) {
    const button = document.getElementById('predictBtn');
    if (button) {
        if (show) {
            button.innerHTML = '<span class="loading"></span> Predicting...';
            button.disabled = true;
        } else {
            button.innerHTML = '<i class="fas fa-chart-line"></i> Predict All Failures';
            button.disabled = false;
        }
    }
}

function showError(message) {
    alert(`Error: ${message}`);
}

// ==================== COMPLETE HISTORY FUNCTIONS ====================







// Close modals when clicking outside
window.onclick = function(event) {
    // No history modals to close since history functionality removed
}