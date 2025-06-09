from flask import Flask, jsonify, render_template_string
import psutil
import time
import requests
import json
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration - Update these to match your setup
LLM_CONFIG = {
    'endpoint': 'http://localhost:11434',  # Default Ollama endpoint
    'model_name': 'llama2'  # Replace with your actual model name
}

# Monitoring functions
def get_ollama_status():
    """Check if Ollama is running and get basic info"""
    try:
        response = requests.get(f"{LLM_CONFIG['endpoint']}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json()
            return {
                'status': 'running',
                'models': models.get('models', []),
                'model_count': len(models.get('models', []))
            }
    except Exception as e:
        logger.error(f"Error checking Ollama status: {e}")
        return {'status': 'not_running', 'models': [], 'model_count': 0}

def get_system_resources():
    """Get system resource usage"""
    try:
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
            'disk_usage_percent': psutil.disk_usage('/').percent
        }
    except Exception as e:
        logger.error(f"Error getting system resources: {e}")
        return {
            'cpu_percent': 0,
            'memory_percent': 0,
            'memory_available_gb': 0,
            'disk_usage_percent': 0
        }

def test_ollama_connectivity():
    """Test basic Ollama connectivity without sending a query"""
    start_time = time.time()
    try:
        # Just ping the tags endpoint to test connectivity
        response = requests.get(f"{LLM_CONFIG['endpoint']}/api/tags", timeout=10)
        end_time = time.time()
        
        if response.status_code == 200:
            return {
                'success': True,
                'response_time_seconds': round(end_time - start_time, 2),
                'status_code': response.status_code,
                'test_type': 'connectivity_check'
            }
        else:
            return {
                'success': False,
                'response_time_seconds': round(end_time - start_time, 2),
                'status_code': response.status_code,
                'error': response.text,
                'test_type': 'connectivity_check'
            }
    except Exception as e:
        return {
            'success': False,
            'response_time_seconds': round(time.time() - start_time, 2),
            'error': str(e),
            'test_type': 'connectivity_check'
        }

# Flask routes
@app.route('/')
def index():
    """Serve the monitoring dashboard"""
    # Read the HTML content from your second file
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ollama Monitor</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }

        .header h1 {
            margin: 0;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }

        .card h3 {
            margin: 0 0 15px 0;
            color: #333;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
        }

        .status-running { background: #4CAF50; }
        .status-error { background: #f44336; }
        .status-warning { background: #ff9800; }

        .metric {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }

        .metric:last-child {
            border-bottom: none;
        }

        .metric-label {
            font-weight: 500;
            color: #666;
        }

        .metric-value {
            font-weight: bold;
            color: #333;
        }

        .refresh-btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            transition: transform 0.2s ease;
        }

        .refresh-btn:hover {
            transform: translateY(-2px);
        }

        .loading {
            text-align: center;
            color: white;
            font-size: 18px;
        }

        .models-list {
            max-height: 200px;
            overflow-y: auto;
        }

        .model-item {
            padding: 5px 0;
            border-bottom: 1px solid #eee;
            font-size: 14px;
        }

        .model-item:last-child {
            border-bottom: none;
        }

        .timestamp {
            text-align: center;
            color: rgba(255,255,255,0.8);
            font-size: 14px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1> Ollama Monitor</h1>
            <button class="refresh-btn" onclick="loadStatus()">🔄 Refresh Status</button>
        </div>

        <div id="loading" class="loading">Loading Ollama status...</div>
        
        <div id="content" style="display: none;">
            <div class="cards">
                <div class="card">
                    <h3>
                        <span class="status-indicator" id="status-indicator"></span>
                        Ollama Status
                    </h3>
                    <div class="metric">
                        <span class="metric-label">Service Status:</span>
                        <span class="metric-value" id="service-status">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Current Model:</span>
                        <span class="metric-value" id="current-model">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Available Models:</span>
                        <span class="metric-value" id="model-count">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Connectivity Test:</span>
                        <span class="metric-value" id="response-time">-</span>
                    </div>
                </div>

                <div class="card">
                    <h3>💻 System Resources</h3>
                    <div class="metric">
                        <span class="metric-label">CPU Usage:</span>
                        <span class="metric-value" id="cpu-usage">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Memory Usage:</span>
                        <span class="metric-value" id="memory-usage">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Available Memory:</span>
                        <span class="metric-value" id="memory-available">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Disk Usage:</span>
                        <span class="metric-value" id="disk-usage">-</span>
                    </div>
                </div>

                <div class="card">
                    <h3>📋 Available Models</h3>
                    <div class="models-list" id="models-list">
                        Loading models...
                    </div>
                </div>
            </div>
        </div>

        <div class="timestamp" id="timestamp"></div>
    </div>

    <script>
        async function loadStatus() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('content').style.display = 'none';

            try {
                const response = await fetch('/ollama/status');
                const data = await response.json();

                // Update status indicator
                const indicator = document.getElementById('status-indicator');
                const serviceStatus = document.getElementById('service-status');
                
                if (data.ollama.status === 'running') {
                    indicator.className = 'status-indicator status-running';
                    serviceStatus.textContent = '✅ Running';
                } else {
                    indicator.className = 'status-indicator status-error';
                    serviceStatus.textContent = '❌ Not Running';
                }

                // Update metrics
                document.getElementById('current-model').textContent = data.current_model;
                document.getElementById('model-count').textContent = data.ollama.model_count;
                
                const responseTest = data.response_test;
                if (responseTest.success) {
                    document.getElementById('response-time').textContent = `${responseTest.response_time_seconds}s ✅`;
                } else {
                    document.getElementById('response-time').textContent = `Failed ❌`;
                }

                // Update system resources
                const resources = data.system_resources;
                document.getElementById('cpu-usage').textContent = `${resources.cpu_percent}%`;
                document.getElementById('memory-usage').textContent = `${resources.memory_percent}%`;
                document.getElementById('memory-available').textContent = `${resources.memory_available_gb} GB`;
                document.getElementById('disk-usage').textContent = `${resources.disk_usage_percent}%`;

                // Update models list
                const modelsList = document.getElementById('models-list');
                if (data.ollama.models && data.ollama.models.length > 0) {
                    modelsList.innerHTML = data.ollama.models.map(model => 
                        `<div class="model-item">${model.name} (${(model.size / 1e9).toFixed(1)} GB)</div>`
                    ).join('');
                } else {
                    modelsList.innerHTML = '<div class="model-item">No models found</div>';
                }

                // Update timestamp
                document.getElementById('timestamp').textContent = 
                    `Last updated: ${new Date(data.timestamp).toLocaleString()}`;

                document.getElementById('loading').style.display = 'none';
                document.getElementById('content').style.display = 'block';

            } catch (error) {
                console.error('Error loading status:', error);
                document.getElementById('loading').innerHTML = 
                    '<div style="color: #ff4444;">❌ Error loading Ollama status</div>';
            }
        }

        // Load status on page load
        loadStatus();

        // Auto-refresh every 10 seconds
        setInterval(loadStatus, 30000);
    </script>
</body>
</html>"""
    return render_template_string(html_content)

@app.route('/ollama/status')
def ollama_status():
    """Get comprehensive Ollama status"""
    try:
        ollama_info = get_ollama_status()
        system_resources = get_system_resources()
        response_test = test_ollama_connectivity()
        
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'ollama': ollama_info,
            'system_resources': system_resources,
            'response_test': response_test,
            'current_model': LLM_CONFIG['model_name'],
            'endpoint': LLM_CONFIG['endpoint']
        })
    except Exception as e:
        logger.error(f"Error getting ollama status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/ollama/models')
def ollama_models():
    """List all available Ollama models with details"""
    try:
        response = requests.get(f"{LLM_CONFIG['endpoint']}/api/tags")
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to fetch models'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ollama/health')
def ollama_health():
    """Simple health check endpoint"""
    try:
        response = requests.get(f"{LLM_CONFIG['endpoint']}/api/tags", timeout=5)
        if response.status_code == 200:
            return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
        else:
            return jsonify({'status': 'unhealthy', 'timestamp': datetime.now().isoformat()}), 503
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e), 'timestamp': datetime.now().isoformat()}), 503

# Optional: Performance logging
def log_query_performance(natural_query, sql_query, execution_time, success):
    """Log query performance metrics"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'natural_query': natural_query[:100] + '...' if len(natural_query) > 100 else natural_query,
        'sql_query': sql_query[:200] + '...' if len(sql_query) > 200 else sql_query,
        'execution_time_seconds': execution_time,
        'success': success
    }
    
    # Log to file
    try:
        with open('query_performance.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        logger.error(f"Error logging performance: {e}")

if __name__ == '__main__':
    print("Starting Ollama Monitor...")
    print(f"Ollama endpoint: {LLM_CONFIG['endpoint']}")
    print(f"Current model: {LLM_CONFIG['model_name']}")
    print("Dashboard will be available at: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=7000)