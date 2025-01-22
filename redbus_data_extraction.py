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

def extract_travel_links(travels_links_dict, d113_bus_dict):

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

d113_bus_dict={}
travel_links_dict={}
d113_bus_dict=popular_travel_agencies_extraction(d113_bus_dict)
travel_links_dict=extract_travel_links(travel_links_dict,d113_bus_dict)
print(travel_links_dict)
