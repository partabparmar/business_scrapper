import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

# Streamlit UI
st.title("🔍 Google Maps Business Scraper")
st.write("Enter a business category and location to extract details.")

# Input fields
category = st.text_input("Enter Business Category")
location = st.text_input("Enter Country/City Name")

# Function to extract email, phone, and booking link from website
def extract_details_from_website(website_url):
    email = "N/A"
    phone = "N/A"
    booking_link = "N/A"

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(website_url, headers=headers, timeout=5)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract email
            email_match = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", soup.text)
            email = email_match[0] if email_match else "N/A"

            # Extract phone number
            phone_match = re.findall(r"(\+?\d{1,2}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?[\d\-.\s]+", soup.text)
            phone = phone_match[0][0] if phone_match else "N/A"

            # Extract booking link
            booking = soup.find("a", href=re.compile(".*(book|appointment|schedule).*", re.IGNORECASE))
            if booking:
                booking_link = booking['href']

    except Exception as e:
        pass

    return {"Email": email, "Phone": phone, "Booking Link": booking_link}

# Button to start scraping
if st.button("Extract Data"):
    # Set up Selenium WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode for Streamlit Cloud
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Use WebDriver Manager to handle ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    def search_google_maps(category, location):
        search_query = f"{category} in {location}"
        url = f"https://www.google.com/maps/search/{search_query}"
        driver.get(url)
        time.sleep(5)  # Wait for page to load

        business_data = []
        businesses = driver.find_elements(By.CLASS_NAME, "Nv2PK")

        for business in businesses[:10]:  # Extract first 10 results
            try:
                name = business.find_element(By.CLASS_NAME, "qBF1Pd").text
                address = business.find_element(By.CLASS_NAME, "W4Efsd").text
                contact_info = business.find_elements(By.CLASS_NAME, "UsdlK")
                phone = contact_info[0].text if contact_info else "N/A"

                business.click()  # Click to open details
                time.sleep(3)

                # Extract Google Maps URL
                business_url = driver.current_url  

                # Extract website
                try:
                    website_element = driver.find_element(By.CSS_SELECTOR, "a.CsEnBe")
                    website = website_element.get_attribute("href")
                except:
                    website = "N/A"

                # Extract plus code
                try:
                    plus_code_element = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Plus code')]")
                    plus_code = plus_code_element.text
                except:
                    plus_code = "N/A"

                # Extract opening hours
                try:
                    hours_element = driver.find_element(By.CLASS_NAME, "JjSWRd")
                    opening_hours = hours_element.text.replace("\n", " | ")
                except:
                    opening_hours = "N/A"

                # Extract email, phone, and booking link from website
                website_details = extract_details_from_website(website) if website != "N/A" else {"Email": "N/A", "Phone": "N/A", "Booking Link": "N/A"}

                # Append business data to list
                business_data.append({
                    "Name": name,
                    "Address": address,
                    "Plus Code": plus_code,
                    "Phone": phone,
                    "Website": website,
                    "Email": website_details["Email"],
                    "Phone from Website": website_details["Phone"],
                    "Booking Link": website_details["Booking Link"],
                    "Opening Hours": opening_hours,
                    "Google Maps URL": business_url
                })
            except Exception as e:
                continue

        return business_data

    # Extract Data
    business_data = search_google_maps(category, location)

    # Check if data was found
    if business_data:
        # Save to CSV
        df = pd.DataFrame(business_data)
        filename = "business_data.csv"
        df.to_csv(filename, index=False, encoding="utf-8")

        # Display results in Streamlit
        st.success(f"✅ Data extracted successfully!")
        st.dataframe(df)

        # Download CSV Button
        st.download_button(
            label="📥 Download CSV File",
            data=df.to_csv(index=False, encoding="utf-8"),
            file_name="business_data.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ No data found. Please check the category and location.")

    driver.quit()
