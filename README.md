# RedBus Data Scraper and Analytics

A Python application that scrapes bus route data from RedBus.in, processes it, and provides a streamlined search interface.

## Features

- Automated scraping of popular bus routes and travel agencies
- Data cleaning and standardization
- Interactive search interface with multiple filtering options
- PostgreSQL database integration
- Real-time bus availability tracking

## Architecture

1. **Data Extraction** (`redbus_data_extraction.py`)
   - Scrapes bus route information using Selenium
   - Handles pagination and dynamic content loading
   - Extracts details like prices, timings, and seat availability
   - Creates initial database backup

2. **Data Cleaning** (`redbus_data_cleaning.py`)
   - Standardizes time and date formats
   - Processes seat availability information
   - Cleans duration strings
   - Creates final cleaned database table

3. **Frontend** (`redbus_frontend.py`)
   - Streamlit-based user interface
   - Advanced filtering options
   - Real-time search capabilities
   - Responsive layout

## Data Extraction Process

### 1. Travel Agency Discovery
The `popular_travel_agencies_extraction()` function:
- Navigates to RedBus homepage
- Identifies popular travel agencies from the featured section
- Extracts agency names and their corresponding URLs
- Returns a dictionary mapping agency names to their listing pages

### 2. Route Extraction
The `extract_travel_links()` function:
- For each travel agency:
  - Navigates to agency's listing page
  - Handles pagination using dynamic page loading
  - Extracts individual route URLs
  - Processes up to 10 agencies by default (configurable)
  - Returns a dictionary of route names and URLs

### 3. Bus Details Scraping
The `scrape_bus_details()` function:
- For each route:
  - Loads the route page
  - Clicks "View Buses" button
  - Implements progressive scrolling to trigger dynamic content loading
  - Extracts detailed information:
    - Bus names and types
    - Departure/arrival times
    - Duration
    - Ratings
    - Pricing
    - Seat availability
  - Handles next-day arrival indicators
  - Manages pagination for routes with multiple pages

### 4. Error Handling
- Implements retry mechanisms for network issues
- Handles dynamic content loading timeouts
- Manages stale element references
- Provides detailed logging for debugging

## Prerequisites

- Python 3.8+
- PostgreSQL
- Firefox Browser (for Selenium)

## Required Packages

```
selenium
pandas
streamlit
psycopg2
sqlalchemy
```

## Database Setup

1. Create PostgreSQL database
2. Update connection strings in all files:
   ```python
   postgresql://<username>:<password>@localhost:5432/<db_name>
   ```

## Usage

1. Run data extraction:
   ```bash
   python redbus_data_extraction.py
   ```

2. Clean the data:
   ```bash
   python redbus_data_cleaning.py
   ```

3. Launch the frontend:
   ```bash
   streamlit run redbus_frontend.py
   ```

## Features

### Search Filters
- Travel agency selection
- Route selection
- Departure/arrival time ranges
- Seat availability (total and window)
- Price range
- Minimum rating

### Data Points
- Bus type
- Departure/arrival times
- Journey duration
- Star rating
- Price
- Seat availability

## Note

This scraper is for educational purposes. Please review RedBus's terms of service before deployment.
