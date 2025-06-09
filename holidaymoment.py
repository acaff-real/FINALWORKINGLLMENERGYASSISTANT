import holidays
import re
from datetime import datetime, timedelta

HOLIDAY_CONFIG = {
    'country': 'IN',
    'state': 'DL',
    'years': range(2020, 2030)
}

HOLIDAY_KEYWORDS = [
    'holiday', 'holidays', 'festival', 'festivals', 'celebration', 'celebrations',
    'diwali', 'holi', 'dussehra', 'navratri', 'eid', 'christmas', 'new year',
    'independence day', 'republic day', 'gandhi jayanti', 'durga puja',
    'karva chauth', 'raksha bandhan', 'janmashtami', 'mahashivratri',
    'vacation', 'leave', 'off day', 'public holiday', 'national holiday',
    'religious festival', 'cultural event', 'traditional celebration', 'non working'
]

# Add weekend-related keywords
WEEKEND_KEYWORDS = [
    'weekend', 'weekends', 'saturday', 'sunday', 'sat', 'sun',
    'week end', 'off days', 'non-working days'
]

def get_holiday_dates():
    india_holidays = holidays.country_holidays(
        country=HOLIDAY_CONFIG['country'],
        state=HOLIDAY_CONFIG['state'],
        years=HOLIDAY_CONFIG['years']
    )
    
    holiday_list = []
    for date, name in sorted(india_holidays.items()):
        holiday_list.append(f"{date.strftime('%Y-%m-%d')}: {name}")
    
    holiday_dates_string = '\n'.join(holiday_list)
    
    return holiday_dates_string

def is_weekend(date):
    """Check if a given date is a weekend (Saturday=5, Sunday=6)"""
    return date.weekday() >= 5

def get_weekends_in_range(start_date, end_date):
    """Get all weekend dates in a given range"""
    weekends = []
    current_date = start_date
    
    while current_date <= end_date:
        if is_weekend(current_date):
            day_name = current_date.strftime('%A')
            weekends.append(f"{current_date.strftime('%Y-%m-%d')}: {day_name}")
        current_date += timedelta(days=1)
    
    return weekends

def get_weekends_for_year(year):
    """Get all weekends for a specific year"""
    start_date = datetime(year, 1, 1).date()
    end_date = datetime(year, 12, 31).date()
    return get_weekends_in_range(start_date, end_date)

def get_weekends_for_month(year, month):
    """Get all weekends for a specific month"""
    start_date = datetime(year, month, 1).date()
    
    # Get last day of month
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    return get_weekends_in_range(start_date, end_date)

def infer_weekend_context(query):
    """Infer weekend context from query"""
    query_lower = query.lower()
    
    # Check if query contains weekend-related keywords
    if not any(keyword in query_lower for keyword in WEEKEND_KEYWORDS):
        return ""
    
    filters = parse_date_filters(query)
    weekend_list = []
    
    # If specific years and months are mentioned
    if filters['years'] and filters['months']:
        for year in filters['years']:
            for month in filters['months']:
                weekends = get_weekends_for_month(year, month)
                weekend_list.extend(weekends)
    
    # If only years are mentioned
    elif filters['years']:
        for year in filters['years']:
            weekends = get_weekends_for_year(year)
            weekend_list.extend(weekends)
    
    # If only months are mentioned (assume current year)
    elif filters['months']:
        current_year = datetime.now().year
        for month in filters['months']:
            weekends = get_weekends_for_month(current_year, month)
            weekend_list.extend(weekends)
    
    # Default: return weekends for current year
    else:
        current_year = datetime.now().year
        weekend_list = get_weekends_for_year(current_year)
    
    return '\n'.join(weekend_list)

def infer_holiday_context(query):
    query_lower = query.lower()
    
    if not any(keyword in query_lower for keyword in HOLIDAY_KEYWORDS):
        return ""
    
    filters = parse_date_filters(query)
    
    india_holidays = holidays.country_holidays(
        country=HOLIDAY_CONFIG['country'],
        state=HOLIDAY_CONFIG['state'],
        years=HOLIDAY_CONFIG['years']
    )
    
    filtered_holidays = _filter_holidays_by_query(india_holidays, filters)
    
    if not filters['years'] and not filters['months']:
        filtered_holidays = india_holidays
    
    holiday_list = []
    for date, name in sorted(filtered_holidays.items()):
        holiday_list.append(f"{date.strftime('%Y-%m-%d')}: {name}")
    
    holiday_dates_string = '\n'.join(holiday_list)
    return holiday_dates_string

def infer_combined_context(query):
    """Combine holiday and weekend context based on query"""
    holiday_context = infer_holiday_context(query)
    weekend_context = infer_weekend_context(query)
    
    combined_context = []
    
    if holiday_context:
        combined_context.append("=== HOLIDAYS ===")
        combined_context.append(holiday_context)
    
    if weekend_context:
        combined_context.append("=== WEEKENDS ===")
        combined_context.append(weekend_context)
    
    return '\n\n'.join(combined_context)

def is_non_working_day(date):
    """Check if a date is either a holiday or weekend"""
    # Check if it's a weekend
    if is_weekend(date):
        return True, "Weekend"
    
    # Check if it's a holiday
    india_holidays = holidays.country_holidays(
        country=HOLIDAY_CONFIG['country'],
        state=HOLIDAY_CONFIG['state'],
        years=[date.year]
    )
    
    if date in india_holidays:
        return True, india_holidays[date]
    
    return False, None

def parse_date_filters(query):
    """
    Parse query to extract specific year, month, or date filters.

    Returns:
        dict: Dictionary with 'years', 'months', and 'dates' filters
    """
    filters = {'years': [], 'months': [], 'dates': []}
    query_lower = query.lower()
    
    years = re.findall(r'\b(20\d{2})\b', query)
    if years:
        filters['years'] = [int(year) for year in years]
    
    month_patterns = {
        'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
        'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
        'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9,
        'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
    }
    
    for month_name, month_num in month_patterns.items():
        if month_name in query_lower:
            filters['months'].append(month_num)
    
    numeric_months = re.findall(r'\b(1[0-2]|[1-9])\s*(?:st|nd|rd|th)?\s*(?:month|/)', query_lower)
    if numeric_months:
        filters['months'].extend([int(m) for m in numeric_months])
    
    return filters

def _filter_holidays_by_query(all_holidays, filters):
    filtered_holidays = {}
    
    for date, name in all_holidays.items():
        include_holiday = True
        
        if filters['years'] and date.year not in filters['years']:
            include_holiday = False
        
        if filters['months'] and date.month not in filters['months']:
            include_holiday = False
        
        if include_holiday:
            filtered_holidays[date] = name
    
    return filtered_holidays
