from flask import Flask, request, jsonify, make_response, send_file
import mysql.connector
import requests
import re
import logging
import difflib
import csv
import io
import tempfile
import os
import json
import base64
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
import holidays
from datetime import datetime, timedelta, date
import calendar
import re
from holidaymoment import infer_holiday_context
from flask_cors import CORS
import psutil
import time
from datetime import datetime
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



HOLIDAY_CONFIG = {
    'country': 'IN',  # India
    'state': 'DL',    # Delhi (adjust based on your needs)
    'years': range(2023, 2024)  # Adjust year range as needed
}

# Global configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'password1234',
    'database': 'iexinternetdatacenter',
    'port': 3306
}

LLM_CONFIG = {
    'endpoint': 'http://127.0.0.1:11434',  # Default Ollama port
    'model_name': 'mathstral-7b',  # Replace with your Ollama model name (e.g., 'llama2', 'codellama', 'mistral')
    'temperature': 0.1,
    'max_tokens': 5000  # Note: Ollama calls this 'num_predict'
}

# Table keywords for dynamic schema selection
TABLE_KEYWORDS = {
    "energy_bids_dam": ["dam", "day ahead", "purchase bid", "scheduled volume", "mcp"],
    "energy_bids_gdam": ["gdam", "green market", "solar", "hydro"],
    "energy_bids_rtm": ["rtm", "real time", "session"],
    "energy_bids_tam": ["tam", "term ahead", "contract type"],
    "energy_bids_gtam": ["gtam", "green term ahead"],
}

HOLIDAY_KEYWORDS = [
    'holiday', 'holidays', 'festival', 'festivals', 'celebration', 'celebrations',
    'diwali', 'holi', 'dussehra', 'navratri', 'eid', 'christmas', 'new year',
    'independence day', 'republic day', 'gandhi jayanti', 'durga puja',
    'karva chauth', 'raksha bandhan', 'janmashtami', 'mahashivratri',
    'vacation', 'leave', 'off day', 'public holiday', 'national holiday',
    'religious festival', 'cultural event', 'traditional celebration'
]

# Keyword descriptions for enhanced prompting
COLUMN_DESCRIPTIONS = {
    "Segment": "Market segment (e.g., DAM - Day Ahead Market, RTM - Real Time Market)",
    "Record_Date": "Date of the record(YYYY-MM-DD format)",
    "Record_Hour": "Hour of the day (0-23)",
    "Time_Block": "Time block identifier",
    "Purchase_Bid_MW": "Purchase bid in megawatts",
    "Sell_Bid_MW": "Sell bid in megawatts",
    "MCV_MW": "Market Clearing Volume in megawatts",
    "Final_Scheduled_Volume_MW": "Final scheduled volume in megawatts",
    "MCP_Rs_MWh": "Market Clearing Price in Rupees per MWh",
    "MCP_Rs_MW": "Market Clearing Price in Rupees per MW",
    "Instrument_Name": "Model name of the instrument"
}

# Global state
db_connection = None
schema_cache = {}
query_results_cache = {}  # Cache for storing results for CSV export


# Database functions
def db_connect():
    global db_connection
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        logger.info("Database connection established")
        return True
    except mysql.connector.Error as e:
        logger.error(f"Database connection failed: {e}")
        return False

def infer_relevant_tables(query):
    matched_tables = []
    query_lower = query.lower()
    for table, keywords in TABLE_KEYWORDS.items():
        if any(keyword in query_lower for keyword in keywords):
            matched_tables.append(table)
    if not matched_tables:
        matched_tables.append("energy_bids_dam")
    return matched_tables



def db_get_schema(target_tables=None):
    global schema_cache, db_connection

    if not db_connection or not db_connection.is_connected():
        if not db_connect():
            raise RuntimeError("Failed to connect to database")

    cache_key = tuple(sorted(target_tables)) if target_tables else "__all__"
    if cache_key in schema_cache:
        return schema_cache[cache_key]

    cursor = db_connection.cursor()
    schema_info = []

    try:
        cursor.execute("SHOW TABLES")
        all_tables = [row[0] for row in cursor.fetchall()]
        tables_to_fetch = target_tables or all_tables

        for table_name in tables_to_fetch:
            if table_name not in all_tables:
                continue
            schema_info.append(f"\nTable: {table_name}")
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            for column in columns:
                col_name, col_type, null, key, default, extra = column
                description = COLUMN_DESCRIPTIONS.get(col_name, "")
                key_info = f" ({key})" if key else ""
                desc_str = f" - {description}" if description else ""
                schema_info.append(f"  - {col_name}: {col_type}{key_info}{desc_str}")

    finally:
        cursor.close()

    schema_str = "\n".join(schema_info)
    schema_cache[cache_key] = schema_str
    return schema_str

def db_execute_query(sql):
    global db_connection
    if not db_connection or not db_connection.is_connected():
        if not db_connect():
            return {"success": False, "error": "Database connection failed"}

    cursor = db_connection.cursor()
    try:
        cursor.execute(sql)
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return {"success": True, "columns": columns, "rows": rows, "row_count": len(rows)}
        else:
            db_connection.commit()
            return {"success": True, "affected_rows": cursor.rowcount, "message": "Query executed successfully"}
    except mysql.connector.Error as e:
        logger.error(f"Query execution failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        cursor.close()

def db_close():
    global db_connection
    if db_connection and db_connection.is_connected():
        db_connection.close()
        logger.info("Database connection closed")






def llm_generate_sql(natural_query, schema):
    holiday_dates_string = infer_holiday_context(natural_query)
    prompt = f"""You are an expert MySQL query generator for an electricity market database. Convert natural language queries to valid MySQL SQL.

Database Schemas:
{schema}

IMPORTANT TIME STRUCTURE CONTEXT:
- Each day contains 96 time blocks (15-minute intervals: 00:00, 00:15, 00:30, 00:45, etc.)
- Time_Block field represents these 15-minute intervals within a day
- Record_Hour ranges from 0-23 (24 hours)
- When asked for daily totals/sums, aggregate across ALL time blocks for that day
- When asked for hourly totals/sums, aggregate across 4 time blocks for that hour
- When asked for maximum values for a given day, sum up all the blocks during that day

UNIT CONVERSION RULES:
- For queries spanning MORE THAN ONE DAY (weekly, monthly, yearly, multi-day periods):
  * Convert volume columns (MW, MWh) to MU (Million Units) by dividing by 4000
  * Use ROUND(SUM(column_name)/4000, 2) AS column_name_MU for volume conversions
  * Round all values to 2 decimal places. Example: "ROUND(SUM(Purchase_Bid_MW)/4000, 2) AS Purchase_Bid_MU" 
  * Label converted columns with "_MU" suffix
  * Example: "ROUND(SUM(Purchase_Bid_MW)/4000, 2) AS Purchase_Bid_MU"
- For single day queries or hourly breakdowns within a day:
  * Keep original MW/MWh units
  * No conversion needed, other than maintaining 2 decimal places. 

HOLIDAY DATES FOR REFERENCE:
{holiday_dates_string}

QUERY ANALYSIS FOR UNIT CONVERSION:
- Multi-day indicators: "week", "month", "year", "last month", "past month", "weekly", "monthly", "yearly", "multiple days", "several days", "trend", "over time"
- Single day indicators: "today", "yesterday", "daily", "hourly", "this hour", specific date like "2024-01-15"

Rules:
1. Generate ONLY SELECT statements for safety.
2. Use proper MySQL syntax.
3. Do not use aliases in GROUP BY and ORDER BY unless necessary.
4. Return ONLY the SQL query, no explanations or additional text.
5. Use DATE() function or correct date formatting in WHERE clauses.
6. Use LIMIT where appropriate.
7. For multi-day periods, convert MW/MWh to MU: ROUND(SUM(column)/4000, 2) AS column_MU.
8. Use Final_Scheduled_Volume_MW, MCV_MW or similar for volume-related queries.
9. The word "Segment" must not appear in SELECT.
10. Assume the default table is energy_bids_dam.
11. Always assume current year if year not specified.
12. Average for a month = across all days in the month.
13. Every derived table must have its own alias (e.g., `a`, `b`).
14. When selecting from multiple tables, **use aliases** (e.g., `a.Record_Date`, `b.Record_Date`) to avoid ambiguity.
15. In WHERE, GROUP BY, ORDER BY, always **use fully-qualified column names** when multiple tables are involved.
16. Prefer JOINs with explicit ON conditions, avoid implicit joins.
17. Convert MCP_Rs_MWh to Rs/kWh where asked using ROUND(MCP_Rs_MWh / 1000, 4).
18. Only SELECT statements are allowed. No INSERT, UPDATE, DELETE.
19. Always alias converted values (e.g., `... AS Purchase_Bid_MU`).
20. If a holiday, apply date logic using provided holiday list.
21. When comparing tables (e.g., RTM vs DAM), always alias tables and qualify shared columns like Record_Date, Record_Hour, etc.

EXAMPLES OF UNIT CONVERSION:
Multi-day query: "Show weekly volume trends"
→ SELECT DATE(Record_Date) as Date, ROUND(SUM(Purchase_Bid_MW)/4000, 2) AS Purchase_Bid_MU FROM energy_bids_dam WHERE Record_Date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) GROUP BY DATE(Record_Date);

Single day query: "Show hourly volumes for today"
→ SELECT Record_Hour, SUM(Purchase_Bid_MW) AS Purchase_Bid_MW FROM energy_bids_dam WHERE DATE(Record_Date) = CURDATE() GROUP BY Record_Hour;

Natural Language Query: {natural_query}

SQL Query:"""

    # Ollama API payload structure
    payload = {
        "model": LLM_CONFIG['model_name'],
        "prompt": prompt,  # Ollama uses 'prompt' instead of 'messages'
        "stream": False,
        "options": {
            "temperature": LLM_CONFIG['temperature'],
            "num_predict": LLM_CONFIG['max_tokens'],  # Ollama uses 'num_predict' instead of 'max_tokens'
        }
    }

    try:
        # Ollama endpoint is different - uses /api/generate instead of /v1/chat/completions
        response = requests.post(f"{LLM_CONFIG['endpoint']}/api/generate", json=payload, timeout=300)
        response.raise_for_status()
        result = response.json()
        
        # Ollama response structure is different - response is in 'response' field
        sql_query = result["response"].strip()
        return clean_sql(sql_query)
        
    except requests.RequestException as e:
        logger.error(f"LLM request failed: {e}")
        raise


def clean_sql(sql):
    sql = re.sub(r'```sql\s*', '', sql, flags=re.IGNORECASE)
    sql = re.sub(r'```\s*', '', sql)
    sql = re.sub(r'^.*?SELECT', 'SELECT', sql, flags=re.IGNORECASE | re.DOTALL)
    sql = sql.split(';')[0] + ';'
    lines = sql.split('\n')
    sql_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('--') and not stripped.startswith('#'):
            sql_lines.append(line)
        elif not stripped:
            sql_lines.append(line)
        else:
            break
    sql = '\n'.join(sql_lines)
    if not sql.strip().upper().startswith('SELECT'):
        raise ValueError("Generated query is not a SELECT statement")
    return sql.strip()

def cache_query_to_file(natural_query):
    with open("cached_queries.txt", "a", encoding="utf-8") as f:
        f.write(natural_query.strip() + "\n")

def generate_csv_from_results(columns, rows):
    """Generate CSV content from query results"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(columns)
    
    # Write data rows
    for row in rows:
        # Convert None values to empty strings and handle other data types
        csv_row = []
        for cell in row:
            if cell is None:
                csv_row.append('')
            else:
                csv_row.append(str(cell))
        writer.writerow(csv_row)
    
    return output.getvalue()

def detect_graph_type(columns, rows):
    """Detect appropriate graph type based on data columns"""
    if not columns or not rows:
        return None
    
    # Convert to lowercase for easier matching
    col_lower = [col.lower() for col in columns]
    
    # Check for time-based columns
    time_cols = []
    for i, col in enumerate(col_lower):
        if any(time_word in col for time_word in ['date', 'hour', 'time', 'block']):
            time_cols.append(i)
    
    # Check for volume columns (area chart)
    volume_cols = []
    for i, col in enumerate(col_lower):
        if any(vol_word in col for vol_word in ['volume', 'mw', 'bid']):
            volume_cols.append(i)
    
    # Check for price columns (line chart)
    price_cols = []
    for i, col in enumerate(col_lower):
        if any(price_word in col for price_word in ['price', 'mcp', 'rs']):
            price_cols.append(i)
    
    # Determine graph type and columns to plot
    if time_cols and (volume_cols or price_cols):
        x_col = time_cols[0]  # Use first time column as x-axis
        
        if volume_cols:
            return {
                'type': 'area',
                'x_col': x_col,
                'y_cols': volume_cols,
                'x_label': columns[x_col],
                'y_labels': [columns[i] for i in volume_cols]
            }
        elif price_cols:
            return {
                'type': 'line',
                'x_col': x_col,
                'y_cols': price_cols,
                'x_label': columns[x_col],
                'y_labels': [columns[i] for i in price_cols]
            }
    
    return None


def detect_graph_type(columns, rows):
    """Detect appropriate graph type based on data columns"""
    if not columns or not rows:
        logger.info("No columns or rows for graph detection")
        return None
    
    logger.info(f"=== GRAPH TYPE DETECTION ===")
    logger.info(f"Available columns: {columns}")
    
    # Convert to lowercase for easier matching
    col_lower = [col.lower() for col in columns]
    
    # Find time-based columns (x-axis candidates)
    time_cols = []
    for i, col in enumerate(col_lower):
        if any(time_word in col for time_word in ['date', 'hour', 'time', 'block']):
            time_cols.append(i)
            logger.info(f"Found time column: {columns[i]} at index {i}")
    
    # Find numeric columns that could be y-axis
    numeric_cols = []
    volume_cols = []
    price_cols = []
    
    # Create a small sample to test numeric conversion
    df_sample = pd.DataFrame(rows[:5], columns=columns)  # Just first 5 rows for testing
    
    for i, col in enumerate(columns):
        col_lower = col.lower()
        try:
            # Try to convert to numeric
            sample_data = pd.to_numeric(df_sample.iloc[:, i], errors='coerce')
            valid_count = sample_data.notna().sum()
            
            if valid_count > 0:  # Has some numeric data
                numeric_cols.append(i)
                logger.info(f"Found numeric column: {col} at index {i}")
                
                # Categorize the numeric column
                if any(vol_word in col_lower for vol_word in ['volume', 'mw', 'bid', 'mcv']):
                    volume_cols.append(i)
                    logger.info(f"  -> Categorized as volume column")
                elif any(price_word in col_lower for price_word in ['price', 'mcp', 'rs']):
                    price_cols.append(i)
                    logger.info(f"  -> Categorized as price column")
                
        except Exception as e:
            logger.info(f"Column {col} is not numeric: {e}")
            continue
    
    logger.info(f"Time columns: {[columns[i] for i in time_cols]}")
    logger.info(f"Volume columns: {[columns[i] for i in volume_cols]}")
    logger.info(f"Price columns: {[columns[i] for i in price_cols]}")
    logger.info(f"All numeric columns: {[columns[i] for i in numeric_cols]}")
    
    # Determine graph configuration
    if not time_cols:
        logger.info("No time columns found, cannot create time-series graph")
        return None
    
    if not numeric_cols:
        logger.info("No numeric columns found, cannot create graph")
        return None
    
    # Use the first time column as x-axis
    x_col = time_cols[0]
    
    # Determine y-columns and graph type
    if price_cols:
        # Prefer price data for line charts
        y_cols = price_cols[:2]  # Limit to 2 for readability
        graph_type = 'line'
        logger.info(f"Creating line chart with price data")
    elif volume_cols:
        # Use volume data for area charts
        y_cols = volume_cols[:2]  # Limit to 2 for readability  
        graph_type = 'area'
        logger.info(f"Creating area chart with volume data")
    else:
        # Use any numeric columns
        y_cols = [col for col in numeric_cols if col != x_col][:2]  # Exclude x-column, limit to 2
        graph_type = 'line'
        logger.info(f"Creating line chart with general numeric data")
    
    if not y_cols:
        logger.info("No suitable Y columns found")
        return None
    
    config = {
        'type': graph_type,
        'x_col': x_col,
        'y_cols': y_cols,
        'x_label': columns[x_col],
        'y_labels': [columns[i] for i in y_cols]
    }
    
    logger.info(f"Graph config: {config}")
    return config

def generate_graph(columns, rows, graph_config):
    """Generate graph based on configuration with detailed debugging"""
    if not graph_config:
        logger.info("No graph config provided")
        return None
    
    try:
        # Create DataFrame for easier manipulation
        df = pd.DataFrame(rows, columns=columns)
        
        # Extensive debugging
        logger.info(f"=== GRAPH DEBUG INFO ===")
        logger.info(f"DataFrame shape: {df.shape}")
        logger.info(f"Columns: {list(df.columns)}")
        logger.info(f"Column types: {df.dtypes.to_dict()}")
        logger.info(f"Graph config: {graph_config}")
        logger.info(f"First few rows:\n{df.head()}")
        
        # Validate we have data
        if df.empty:
            logger.warning("DataFrame is empty")
            return None
        
        # Set up matplotlib with explicit backend and clear any existing plots
        plt.ioff()  # Turn off interactive mode
        plt.clf()  # Clear any existing plots
        plt.close('all')  # Close all figures
        
        # Create new figure with explicit settings
        fig, ax = plt.subplots(figsize=(12, 8), dpi=100)
        fig.patch.set_facecolor('white')
        
        x_col_idx = graph_config['x_col']
        y_col_indices = graph_config['y_cols']
        
        # Validate column indices
        if x_col_idx >= len(df.columns):
            logger.error(f"X column index {x_col_idx} out of range. Max index: {len(df.columns)-1}")
            return None
        
        # Get X data
        x_data = df.iloc[:, x_col_idx]
        logger.info(f"X column: {columns[x_col_idx]}")
        logger.info(f"X data type: {type(x_data.iloc[0]) if len(x_data) > 0 else 'empty'}")
        logger.info(f"X data sample: {x_data.head().tolist()}")
        
        # Handle different x-axis data types
        x_values = None
        x_is_time = False
        
        if 'date' in columns[x_col_idx].lower():
            # Handle date columns
            try:
                if isinstance(x_data.iloc[0], str):
                    # String dates
                    x_values = pd.to_datetime(x_data, errors='coerce')
                else:
                    # Already datetime objects
                    x_values = x_data
                x_is_time = True
                logger.info(f"Parsed dates: {x_values.head().tolist()}")
            except Exception as e:
                logger.error(f"Date parsing failed: {e}")
                x_values = range(len(x_data))  # Use indices as fallback
        elif 'hour' in columns[x_col_idx].lower() or 'block' in columns[x_col_idx].lower():
            # Numeric time columns
            try:
                x_values = pd.to_numeric(x_data, errors='coerce')
                logger.info(f"Numeric x values: {x_values.head().tolist()}")
            except:
                x_values = range(len(x_data))
        else:
            # Use row indices
            x_values = range(len(x_data))
        
        # Process Y columns
        plotted_any = False
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        for i, y_col_idx in enumerate(y_col_indices):
            if y_col_idx >= len(df.columns):
                logger.warning(f"Y column index {y_col_idx} out of range. Skipping.")
                continue
            
            y_data = df.iloc[:, y_col_idx]
            y_label = graph_config['y_labels'][i]
            
            logger.info(f"Y column {i}: {columns[y_col_idx]} (index {y_col_idx})")
            logger.info(f"Y data type: {type(y_data.iloc[0]) if len(y_data) > 0 else 'empty'}")
            logger.info(f"Y data sample: {y_data.head().tolist()}")
            
            # Convert to numeric
            try:
                y_numeric = pd.to_numeric(y_data, errors='coerce')
                
                # Check for valid data
                valid_count = y_numeric.notna().sum()
                logger.info(f"Valid Y values: {valid_count}/{len(y_numeric)}")
                
                if valid_count == 0:
                    logger.warning(f"No valid numeric data in column {y_label}")
                    continue
                
                # Fill NaN with 0 or interpolate
                y_numeric = y_numeric.fillna(0)
                
                logger.info(f"Y numeric range: {y_numeric.min()} to {y_numeric.max()}")
                
                # Plot the data
                color = colors[i % len(colors)]
                if graph_config['type'] == 'area':
                    ax.fill_between(x_values, y_numeric, alpha=0.6, label=y_label, color=color)
                    ax.plot(x_values, y_numeric, linewidth=2, color=color, alpha=0.8)
                else:  # line
                    ax.plot(x_values, y_numeric, marker='o', markersize=3, linewidth=2, 
                           label=y_label, color=color)
                
                plotted_any = True
                logger.info(f"Successfully plotted {y_label}")
                
            except Exception as e:
                logger.error(f"Failed to plot column {y_label}: {e}")
                continue
        
        if not plotted_any:
            logger.error("No data was successfully plotted")
            plt.close(fig)
            return None
        
        # Customize the plot
        ax.set_title(f"Market Data Analysis", fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel(graph_config['x_label'], fontsize=12, fontweight='bold')
        ax.set_ylabel(', '.join(graph_config['y_labels']), fontsize=12, fontweight='bold')
        
        # Handle x-axis formatting
        if x_is_time and hasattr(x_values, 'dtype') and 'datetime' in str(x_values.dtype):
            # Format dates nicely
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, len(x_values)//10)))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        elif 'block' in columns[x_col_idx].lower():
            # For time blocks, show every nth tick
            step = max(1, len(x_values) // 20)
            ax.set_xticks(x_values[::step])
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Add legend and grid
        ax.legend(fontsize=10, loc='best')
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        
        # Set background color
        ax.set_facecolor('#f8f9fa')
        
        # Ensure reasonable axis limits with some padding
        ax.margins(x=0.02, y=0.05)
        
        # Improve layout
        plt.tight_layout()
        
        # Save to base64 with high quality
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none', 
                   pad_inches=0.2)
        img_buffer.seek(0)
        
        # Get the image data and encode to base64
        img_data = img_buffer.getvalue()
        img_str = base64.b64encode(img_data).decode('utf-8')
        
        # Clean up
        plt.close(fig)
        img_buffer.close()
        
        logger.info(f"Graph generated successfully. Image size: {len(img_str)} characters")
        logger.info(f"Base64 prefix: {img_str[:50]}...")
        
        return img_str
        
    except Exception as e:
        logger.error(f"Graph generation failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        plt.close('all')  # Ensure cleanup on error
        return None

def process_natural_query(natural_query, return_csv_id=False):
    try:
        cache_query_to_file(natural_query)
        relevant_tables = infer_relevant_tables(natural_query)
        relevant_tables = infer_relevant_tables(natural_query)
        schema = db_get_schema(target_tables=relevant_tables)
        sql_query = llm_generate_sql(natural_query, schema)

        # Improved SQL validation
        schema_columns = set(re.findall(r"- (\w+):", schema))
        sql_keywords = {
            'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'BETWEEN',
            'LIKE', 'IS', 'NULL', 'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT',
            'OFFSET', 'JOIN', 'INNER', 'OUTER', 'LEFT', 'RIGHT', 'FULL',
            'UNION', 'ALL', 'EXISTS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
            'AS', 'ON', 'DISTINCT', 'ASC', 'DESC', 'AVG', 'SUM', 'COUNT',
            'MIN', 'MAX', 'DATE', 'YEAR', 'MONTH', 'DAY', 'NOW', 'CURRENT_DATE',
            'INTERVAL', 'CURRENT_TIMESTAMP', 'DATE_ADD', 'DATE_SUB', 'IF',
            'NULLIF', 'COALESCE', 'EXTRACT', 'CAST', 'CONVERT', 'WITH', 'RECURSIVE', 
            'RTM', 'WEEK', 'CURDATE', 'CHAR_LENGTH', 'LENGTH', 'CONCAT', 'SUBSTRING',
            'UPPER', 'LOWER', 'TRIM', 'LTRIM', 'RTRIM',
            'REPLACE', 'LOCATE', 'POSITION', 'REPEAT',
            'MOD', 'ROUND', 'FLOOR', 'CEIL', 'ABS', 'POWER', 'RAND',
            'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'NTILE',
            'LAG', 'LEAD', 'FIRST_VALUE', 'LAST_VALUE',
            'PARTITION', 'OVER', 'WINDOW', 'DAM', 'Total_Volume'
        }
        
        # Extract column references more accurately
        column_refs = set()
        # Find column references after FROM
        from_pos = sql_query.upper().find('FROM')
        if from_pos == -1:
            raise ValueError("SQL query must contain a FROM clause")
        
        # Split into parts we care about (after FROM)
        remaining_query = sql_query[from_pos:]
        
        # Skip table references and aliases
        table_refs = set()
        table_match = re.search(r'FROM\s+([\w,`"\s]+)(?:\s+WHERE|\s+GROUP|\s+ORDER|\s+HAVING|\s+LIMIT|$)', 
                              remaining_query, re.IGNORECASE)
        if table_match:
            tables_part = table_match.group(1)
            # Extract table names and aliases
            for table_ref in re.findall(r'([\w`"]+)(?:\s+AS\s+([\w`"]+))?', tables_part):
                table_refs.update(r.strip('`"') for r in table_ref if r)
        
        # Find column references in various clauses
        for part in re.split(r'WHERE|GROUP BY|ORDER BY|HAVING|LIMIT', remaining_query, flags=re.IGNORECASE):
            if not part.strip():
                continue
            
            # Find potential column references (words that might be columns)
            for word in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', part):
                word_upper = word.upper()
                if (word_upper not in sql_keywords and 
                    not word.isdigit() and 
                    word not in table_refs and
                    not word.startswith(('"', "'", "`"))):
                    column_refs.add(word)
        
        # Check for unknown columns
        unknown_columns = column_refs - schema_columns
        #if unknown_columns:
            #raise ValueError(f"Generated SQL references unknown columns: {', '.join(unknown_columns)}")

        results = db_execute_query(sql_query)
        
        # Generate graph if data is suitable
        graph_data = None
        if results.get("success") and results.get("rows"):
            graph_config = detect_graph_type(results['columns'], results['rows'])
            if graph_config:
                graph_data = generate_graph(results['columns'], results['rows'], graph_config)
        
        # Cache results for CSV export if requested
        csv_id = None
        if return_csv_id and results.get("success") and results.get("rows"):
            csv_id = f"query_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            query_results_cache[csv_id] = {
                'columns': results['columns'],
                'rows': results['rows'],
                'natural_query': natural_query,
                'sql_query': sql_query,
                'timestamp': datetime.now(),
                'graph_data': graph_data
            }
        
        result = {"natural_query": natural_query, "generated_sql": sql_query, "results": results}
        if csv_id:
            result['csv_id'] = csv_id
        if graph_data:
            result['graph'] = graph_data
            
        return result
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        return {"natural_query": natural_query, "error": str(e), "success": False}
    
# Initialize database connection
db_connect()

app = Flask(__name__)
CORS(app)

@app.route('/query', methods=['POST'])
def query():
    try:
        data = request.get_json()
        natural_query = data.get('query', '').strip()
        include_csv_id = data.get('include_csv_id', False)
        
        if not natural_query:
            return jsonify({'error': 'Query cannot be empty'}), 400
            
        result = process_natural_query(natural_query, return_csv_id=include_csv_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export-csv/<csv_id>')
def export_csv(csv_id):
    try:
        if csv_id not in query_results_cache:
            return jsonify({'error': 'CSV data not found or expired'}), 404
        
        cached_data = query_results_cache[csv_id]
        columns = cached_data['columns']
        rows = cached_data['rows']
        
        # Generate CSV content
        csv_content = generate_csv_from_results(columns, rows)
        
        # Create response
        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=query_results_{csv_id}.csv'
        
        return response
        
    except Exception as e:
        logger.error(f"CSV export failed: {e}")
        return jsonify({'error': 'Failed to generate CSV file'}), 500

@app.route('/schema')
def schema():
    try:
        schema = db_get_schema()
        return jsonify({'schema': schema})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.teardown_appcontext
def cleanup(error):
    db_close()

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000)