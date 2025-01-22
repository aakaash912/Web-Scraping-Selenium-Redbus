import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta, time
import re

def db_loader_cleaned(engine_object_input,df):
    create_table_query = """
    CREATE TABLE bus_routes (
        route_name TEXT,
        route_link TEXT,
        bus_name TEXT,
        bus_type TEXT,
        departing_time TIME,
        duration TEXT,
        reaching_time TIME,
        star_rating_out_of_5 NUMERIC(2, 1),
        price_inr NUMERIC(10, 2),
        total_seats INTEGER,
        window_seats INTEGER,
        departing_date DATE,
        reaching_date DATE
    );

    """

    # Execute the query using the engine
    with engine_object_input.connect() as connection:
        connection.execute(text(create_table_query))
        connection.commit()

    print("Table created successfully!")

def clean_duration(duration_str):
    """Cleans up duration by standardizing the format to 'Xh Ym'."""
    try:
        match = re.search(r'(\d+)h(?:\s*(\d+)m)?|(\d+)m', duration_str)
        if match:
            hours = match.group(1) or 0
            minutes = match.group(2) or match.group(3) or 0
            return f"{int(hours)}h {int(minutes)}m"
        else:
            return "0h 0m"
    except Exception as e:
        print(f"Error cleaning duration: {duration_str} - {e}")
        return "0h 0m"

# Split 'reaching_time' into time and date
def split_reaching_time(reaching_time_str):
    """Splits reaching_time into time and date."""
    try:
        if '(' in reaching_time_str:
            time_part, date_part = reaching_time_str.split('(')
            date_part = date_part.strip(')')  # Remove closing parenthesis
            return time_part.strip(), date_part.strip()
        else:
            return reaching_time_str.strip(), None
    except Exception as e:
        print(f"Error splitting reaching_time: {reaching_time_str} - {e}")
        return None, None

df[['reaching_time', 'reaching_date']] = df['reaching_time'].apply(
    lambda x: pd.Series(split_reaching_time(x))
)

# Convert 'departing_date' and 'reaching_date' into datetime format
df['departing_date'] = pd.to_datetime(df['departing_date'], format='%d-%m-%Y')

def parse_reaching_date(date_str):
    """Parses reaching_date with dynamic format detection and assigns year 2025."""
    try:
        if pd.notnull(date_str):
            # Handle day-month and full date formats
            if '-' in date_str:  # Example: "15-Jan" or "15-01-2025"
                if len(date_str.split('-')[-1]) == 4:  # Full date case
                    return pd.to_datetime(date_str, format='%d-%m-%Y', errors='coerce')
                else:  # Day-Month case (e.g., "15-Jan")
                    date_obj = datetime.strptime(date_str, "%d-%b")
                    date_obj = date_obj.replace(year=2025)
                    return date_obj
            else:
                return pd.to_datetime(date_str, format='%d-%b-%Y', errors='coerce')
        else:
            return None
    except Exception as e:
        print(f"Error parsing reaching_date: {date_str} - {e}")
        return None

df['reaching_date'] = df['reaching_date'].apply(parse_reaching_date)

# Split 'seats_available' into separate columns
def split_seats(seats_str):
    """Splits seats and window numbers."""
    try:
        parts = seats_str.split('|')
        seats = int(parts[0].strip().split()[0])
        window = int(parts[1].strip().split()[0]) if len(parts) > 1 else 0
        return seats, window
    except Exception as e:
        print(f"Error splitting seats: {seats_str} - {e}")
        return 0, 0


#Fetching the Raw Scraped Data from the Backup Database for Cleaning
select_query="select * from bus_details_backup"
with engine.connect() as connection:
    results=connection.execute(text(select_query))
df=pd.DataFrame(results)

# Fetch today's date and format it for PostgreSQL
today_date = datetime.now().strftime("%d-%m-%Y")

# Assign it to the DataFrame column
df['departing_date'] = today_date

df[['total_seats', 'window_seats']] = df['seats_available'].apply(
    lambda x: pd.Series(split_seats(x))
)

# Drop the original combined 'seats_available' column
df.drop(columns=['seats_available'], inplace=True)

# Rename columns for clarity
df.rename(columns={
    'price': 'price_inr',
    'star_rating': 'star_rating_out_of_5',
}, inplace=True)
# Replace 'New' with 0.0 in the 'star_rating_out_of_5' column
df['star_rating_out_of_5'] = df['star_rating_out_of_5'].replace('New', 0.0)

# Convert the column to numeric, if not already done
df['star_rating_out_of_5'] = pd.to_numeric(df['star_rating_out_of_5'], errors='coerce')

engine = create_engine("postgresql://<username>:<password>@localhost:5432/<db_name>")

db_loader_cleaned(engine_object_input=engine,df=df)