import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import Firefox
import time as sleep_time
from sqlalchemy import create_engine, text
import streamlit as st
from datetime import datetime, timedelta, time
import re
import psycopg2

def popular_travel_agencies_extraction(empty_dictionary_input): # Custom written function for extraction of most popular Travel agencies with a large number of Buses.
    driver = webdriver.Firefox()
    driver.get('https://www.redbus.in/')
    driver.maximize_window()

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'rtcName')))
    popular_bus_depts = driver.find_elements(By.CLASS_NAME, 'rtcName')
    view_buses_buttons = driver.find_element(By.XPATH, "/html/body/section/div[2]/main/div[3]/div[3]/div[1]/div[2]/a")
    popular_bus_names = [bus.text for bus in popular_bus_depts] 
    driver.get(view_buses_buttons.get_attribute('href'))
    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'D113_link')))
    bus_depts = driver.find_elements(By.CLASS_NAME, 'D113_link')
    for bus in bus_depts:
        for name in popular_bus_names:
            if name in bus.text:
                empty_dictionary_input[name]=bus.get_attribute('href')
    driver.quit()
    return empty_dictionary_input

def extract_travel_links(links_dict, d113_bus_dict):

    driver = webdriver.Firefox()
    driver.maximize_window()

    successful_travel_agencies = 0  # Counter for successful travel agencies
    max_successful_agencies = 10  # Set a maximum limit for processing

    for name_string, link in d113_bus_dict.items():
        if successful_travel_agencies >= max_successful_agencies:
            print("Reached maximum successful travel agency limit. Exiting...")
            break  # Exit if the maximum limit is reached

        try:
            driver.get(link)
            sleep_time.sleep(2)
            body = driver.find_element(By.TAG_NAME, "body")
            
            # Wait for the route elements to be present
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "route"))
            )
            
            try:
                # Check if pagination exists
                parent_div = driver.find_element(By.CLASS_NAME, "DC_117_paginationTable")
                
                try:
                    # Try to find pagination buttons
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.DC_117_pageTabs"))
                    )
                    
                    child_count = driver.execute_script(
                        "return arguments[0].getElementsByTagName('div').length;", parent_div
                    )
                    
                    # If buttons are found, iterate through pagination
                    for i in range(1, child_count + 1):
                        try:
                            button = driver.find_element(By.CSS_SELECTOR, f"div.DC_117_pageTabs:nth-child({i})")
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                            driver.execute_script("arguments[0].click();", button)
                            
                            # Extract route details on each page
                            route_details = WebDriverWait(driver, 5).until(
                                EC.presence_of_all_elements_located((By.CLASS_NAME, 'route'))
                            )
                            for route in route_details:
                                route_link = route.get_attribute('href')
                                travels_links_dict[name_string + '_' + route.text] = route_link
                        
                        except Exception as e:
                            print(f"Error while clicking pagination button {i}: {e}")
                            continue  # Skip to the next button if click fails
                        
                except TimeoutException:
                    # If buttons aren't found but parent div exists, get routes from current page
                    print(f"Pagination buttons not found for travel agency '{name_string}'. Extracting from current page...")
                    route_details = driver.find_elements(By.CLASS_NAME, 'route')
                    for route in route_details:
                        route_link = route.get_attribute('href')
                        travels_links_dict[name_string + '_' + route.text] = route_link
                    
            except NoSuchElementException:
                # If pagination table doesn't exist, get routes from current page
                print(f"No pagination found for travel agency '{name_string}'. Extracting from current page...")
                route_details = driver.find_elements(By.CLASS_NAME, 'route')
                for route in route_details:
                    route_link = route.get_attribute('href')
                    travels_links_dict[name_string + '_' + route.text] = route_link
                
            # Increment successful travel agencies and print success
            successful_travel_agencies += 1
            print(f"Success #{successful_travel_agencies}: Processed travel agency '{name_string}'")

        except Exception as e:
            print(f"Error occurred while processing travel agency '{name_string}': {e}. Skipping...")
            continue  # Skip to the next travel agency

    driver.quit()
    print(f"Total successful travel agencies processed: {successful_travel_agencies}")
    return travels_links_dict

def parse_bus_details(details_box, df, route_name, route_link):
    for element in details_box:
        try:
            # Bus name
            bus_name = element.find_element("css selector", ".travels").text
            
            # Bus type
            bus_type = element.find_element("css selector", ".bus-type.f-12").text
            
            # Departure time
            departure_time = element.find_element("css selector", ".dp-time.f-19").text
            
            # Duration
            duration = element.find_element("css selector", ".dur.l-color").text
            
            # Arrival time + date
            arrival_time = element.find_element("css selector", ".bp-time.f-19").text
            try:
                next_day = element.find_element("css selector", ".next-day-dp-lbl").text
                arrival_datetime = f"{arrival_time} ({next_day})"
            except:
                arrival_datetime = arrival_time
            
            # Rating - handles both numeric and "New"
            try:
                rating_element = element.find_element("css selector", ".lh-18.rating span")
                rating = rating_element.text
            except:
                try:
                    rating = element.find_element("css selector", ".rate_count").text
                except:
                    rating = "N/A"
            
            # Price
            price = element.find_element("css selector", ".fare .f-19").text
            
            # Available seats and window seats
            try:
                seats = element.find_element("css selector", ".seat-left").text.split()[0]
            except:
                seats = "0"
                
            # Window seats - with null handling
            try:
                window_seats = element.find_element("css selector", ".window-left").text.split()[0]
                seats_info = f"{seats} Seats | {window_seats} Window"
            except:
                seats_info = f"{seats} Seats"
            
            # Create new row data
            new_row = {
                'route_name': route_name,
                'route_link': route_link,
                'bus_name': bus_name,
                'bus_type': bus_type,
                'departing_time': departure_time,
                'duration': duration,
                'reaching_time': arrival_datetime,
                'star_rating': rating,
                'price': price,
                'seats_available': seats_info
            }
            
            # Append the new row to the DataFrame
            df.loc[len(df)] = new_row
            
        except Exception as e:
            print(f"Error parsing bus details: {e}")
            continue
    
    return df

def scrape_bus_details(links_dict,df):
    driver = webdriver.Firefox()
    driver.maximize_window()

    print(f"Starting to process {len(travels_links_dict)} routes...")

    for index, (route_name, route_link) in enumerate(travels_links_dict.items(), 1):
        print(f"\nProcessing route {index}/{len(travels_links_dict)}: {route_name}")
        
        try:
            driver.get(route_link)
            driver.maximize_window()
            sleep_time.sleep(10)

            # Wait for the 'View Buses' button
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'button')))
            driver.back()

            body = driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.PAGE_DOWN)

            # Click "View Buses" buttons
            view_buses_buttons = [driver.find_elements(By.CLASS_NAME, "button")]
            for button in view_buses_buttons[0]:
                if button.text == "View Buses" or button.text == "VIEW BUSES":
                    button.click()
                    print("View Buses button clicked successfully")

            print("Starting content loading process...")
            # Scroll to load full content
            scrolling = True
            while scrolling:
                old_page_source = driver.page_source
                body.send_keys(Keys.ARROW_UP)
                new_page_source = driver.page_source
                if new_page_source == old_page_source:
                    scrolling = False

            scrolling = True
            while scrolling:
                old_page_source = driver.page_source
                body.send_keys(Keys.CONTROL + Keys.END)
                sleep_time.sleep(1)
                new_page_source = driver.page_source
                if new_page_source == old_page_source:
                    scrolling = False

            scrolling = True
            while scrolling:
                old_page_source = driver.page_source
                body.send_keys(Keys.ARROW_UP)
                new_page_source = driver.page_source
                if new_page_source == old_page_source:
                    scrolling = False

            print("Content fully loaded, parsing bus details...")
            details_box = driver.find_elements(By.XPATH, "//div[contains(@class, 'clearfix') and contains(@class, 'row-one')]")
            bus_details = parse_bus_details(details_box=details_box,df=df,route_link=route_link,route_name=route_name)
            print(f"Found {len(details_box)} buses for this route")

        except Exception as e:
            print(f"Error processing route {route_name}: {str(e)}")
            continue

    print("\nScraping completed. Final DataFrame size:", len(df))
    driver.quit()
    return df

def db_loader(engine_object_input,df):
    create_table_query = """
    CREATE TABLE bus_details_backup (
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
    try:
        df.to_sql("bus_details_backup", engine_object_input, if_exists="append", index=False)
        print("Data inserted successfully!")
    except Exception as e:
        print("Error:", e)

d113_bus_dict={}
travel_links_dict={}
d113_bus_dict=popular_travel_agencies_extraction(empty_dictionary_input=d113_bus_dict)
travel_links_dict=extract_travel_links(links_dict=travel_links_dict,d113_bus_dict=d113_bus_dict)
print(travel_links_dict)
df = pd.DataFrame(columns=['route_name', 'route_link', 'bus_name', 'bus_type', 'departing_time', 'duration','reaching_time', 'star_rating', 'price', 'seats_available'])
df = scrape_bus_details(links_dict=travels_links_dict, df=df)
engine = create_engine("postgresql://<username>:<password>@localhost:5432/<db_name>")
db_loader(engine_object_input=engine,df=df)