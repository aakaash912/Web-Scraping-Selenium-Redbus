import streamlit as st
import psycopg2
from datetime import time
from decimal import Decimal


def connect_db():
    # Replace these with your actual database credentials
    return psycopg2.connect(
        dbname="redbus_db",
        user="postgres",
        password="root",
        host="localhost"
    )

def clean_route_name(route_name, agency):
    """Remove agency name and clean up route display"""
    if route_name.startswith(agency):
        cleaned_name = route_name[len(agency):].strip()
        if cleaned_name.startswith('_'):
            cleaned_name = cleaned_name[1:]
    else:
        cleaned_name = route_name
    return cleaned_name

def get_travel_agencies():
    """Get unique travel agencies from the database"""
    try:
        conn = connect_db()
        cur = conn.cursor()
        
        query = """
        SELECT DISTINCT 
            split_part(route_name, '_', 1) as agency
        FROM bus_routes
        ORDER BY agency
        """
        
        cur.execute(query)
        agencies = [row[0].strip() for row in cur.fetchall()]
        return agencies
    except Exception as e:
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_routes_for_agency(agency):
    """Get all routes for a specific travel agency"""
    try:
        conn = connect_db()
        cur = conn.cursor()
        
        query = """
        SELECT DISTINCT route_name
        FROM bus_routes
        WHERE route_name LIKE %s
        ORDER BY route_name
        """
        
        cur.execute(query, [f"{agency}%"])
        routes = cur.fetchall()
        
        route_mapping = {clean_route_name(route[0], agency): route[0] for route in routes}
        return route_mapping
    except Exception as e:
        return {}
    finally:
        if 'conn' in locals():
            conn.close()

def create_time_ranges():
    """Create a list of 30-minute time range choices, including 'Any Time'"""
    ranges = ["Any Time"]
    for hour in range(0, 24):
        for minute in [0, 30]:
            start = time(hour, minute)
            end_hour = hour + ((minute + 30) // 60)
            end_minute = (minute + 30) % 60
            if end_hour < 24:
                end = time(end_hour, end_minute)
                ranges.append(f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}")
    return ranges

def get_max_seats():
    """Get the maximum number of seats available across all buses"""
    try:
        conn = connect_db()
        cur = conn.cursor()
        query = "SELECT MAX(total_seats) FROM bus_routes"
        cur.execute(query)
        max_seats = cur.fetchone()[0]
        return max_seats or 50
    except Exception as e:
        return 50
    finally:
        if 'conn' in locals():
            conn.close()

def get_max_price():
    """Get the maximum price across all buses"""
    try:
        conn = connect_db()
        cur = conn.cursor()
        query = "SELECT MAX(price_inr) FROM bus_routes"
        cur.execute(query)
        max_price = cur.fetchone()[0]
        # Convert Decimal to int to avoid type mismatches
        return int(max_price) if max_price else 2000
    except Exception as e:
        return 2000
    finally:
        if 'conn' in locals():
            conn.close()

def search_buses(agency, cleaned_route, departure_range, reaching_range, 
                min_seats, min_window_seats, min_price, max_price, min_rating):
    try:
        conn = connect_db()
        cur = conn.cursor()
        
        route_mapping = get_routes_for_agency(agency)
        cleaned_route_str = str(cleaned_route) if cleaned_route is not None else None
        original_route = route_mapping.get(cleaned_route_str)
        
        query = """
        SELECT 
            route_name,
            bus_name,
            bus_type,
            departing_time,
            duration,
            reaching_time,
            star_rating_out_of_5,
            price_inr,
            total_seats,
            window_seats
        FROM bus_routes
        WHERE 1=1
        """
        
        params = []
        
        if original_route:
            query += " AND route_name = %s"
            params.append(original_route)
            
        if departure_range and departure_range != "Any Time":
            start_time, end_time = departure_range.split(" - ")
            query += " AND departing_time::time BETWEEN %s::time AND %s::time"
            params.extend([start_time, end_time])
            
        if reaching_range and reaching_range != "Any Time":
            start_time, end_time = reaching_range.split(" - ")
            query += " AND reaching_time::time BETWEEN %s::time AND %s::time"
            params.extend([start_time, end_time])
            
        query += " AND total_seats >= %s"
        params.append(min_seats)
        
        query += " AND window_seats >= %s"
        params.append(min_window_seats)
            
        query += " AND price_inr BETWEEN %s AND %s"
        params.extend([min_price, max_price])
            
        query += " AND star_rating_out_of_5 >= %s"
        params.append(min_rating)
            
        cur.execute(query, params)
        results = cur.fetchall()
        
        if not results:
            st.warning("No buses found matching your criteria.")
            return
        
        # Display results in a more structured way using Streamlit
        for row in results:
            clean_route = clean_route_name(row[0], agency)
            with st.expander(f"{clean_route} - {row[1]}", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Bus Type:** {row[2]}")
                    st.write(f"**Departure:** {row[3]}")
                    st.write(f"**Duration:** {row[4]}")
                    st.write(f"**Arrival:** {row[5]}")
                with col2:
                    st.write(f"**Rating:** {row[6]}/5")
                    st.write(f"**Price:** ₹{row[7]}")
                    st.write(f"**Total Seats:** {row[8]}")
                    st.write(f"**Window Seats:** {row[9]}")
                
    except Exception as e:
        st.error(f"Error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    st.set_page_config(page_title="Bus Route Search", page_icon="🚌", layout="wide")
    
    st.title("🚌 Bus Route Search")
    
    # Get initial data
    agencies = get_travel_agencies()
    time_ranges = create_time_ranges()
    max_seats = get_max_seats()
    max_price = get_max_price()  # This now returns an int
    
    # Create two columns for the layout
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Search Filters")
        
        # Travel agency and route selection
        agency = st.selectbox("Travel Agency", options=agencies)
        
        # Update routes when agency changes
        if agency:
            route_mapping = get_routes_for_agency(agency)
            route = st.selectbox("Route", options=list(route_mapping.keys()))
        
        # Time selection
        departure_range = st.selectbox("Departure Time Range", 
                                     options=time_ranges, 
                                     index=0)
        
        reaching_range = st.selectbox("Reaching Time Range", 
                                    options=time_ranges, 
                                    index=0)
        
        # Seats filters
        min_seats = st.slider("Minimum Total Seats Required",
                            min_value=1,
                            max_value=max_seats,
                            value=1)
        
        min_window_seats = st.slider("Minimum Window Seats Required",
                                   min_value=0,
                                   max_value=max_seats // 2,
                                   value=0)
        
        # Price filters
        price_col1, price_col2 = st.columns(2)
        with price_col1:
            min_price = st.number_input("Min Price (₹)",
                                      min_value=0,
                                      max_value=max_price,
                                      value=0,
                                      step=50,
                                      format="%d")  # Force integer format
        with price_col2:
            max_price_input = st.number_input("Max Price (₹)",
                                            min_value=0,
                                            max_value=max_price,
                                            value=max_price,
                                            step=50,
                                            format="%d")  # Force integer format
        
        # Rating filter
        min_rating = st.slider("Minimum Rating Required",
                             min_value=1.0,
                             max_value=5.0,
                             value=1.0,
                             step=0.5)
        
        if st.button("Search Buses", type="primary"):
            with col2:
                st.subheader("Search Results")
                search_buses(agency, route, departure_range, reaching_range,
                           min_seats, min_window_seats, min_price, max_price_input,
                           min_rating)

if __name__ == "__main__":
    main()