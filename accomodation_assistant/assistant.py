from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from openai import OpenAI
import requests
import logging
import json
from collections import defaultdict
from datetime import datetime

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Set up ollama client
client = OpenAI(
    base_url = 'http://localhost:11434/v1',
    api_key='ollama', # required, but unused
)

# LLM model name
model = "llama3.2:3b"

# ---------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------

class check_prompt(BaseModel):
    """First LLM call: Extract basic accomodation information"""

    # description: str = Field(description="Raw description of the event")
    is_accomodation_search: bool = Field(
        description="Is the text a query related to finding an accomodation?"
    )


class EventDetails(BaseModel):
    """Second LLM call: Parse specific event details"""

    city: str = Field(description="City in which the accomodation should be booked")
    start_date: str = Field(
        description="Date and time of checking into the accomodation. Strictly use 'yyyy-mm-dd' date format for this value. Example is 2025-03-25"
    )
    end_date: str = Field(
        description="Date and time of checking out of the accomodation. Strictly use 'yyyy-mm-dd' date format for this value. Example is 2025-03-25"
    )


class WeatherResponse(BaseModel):
    weather_report: str = Field(
        description="A text summary on the weather in natural language based on the weather forcast data")
    

# ---------------------------------------------------------------
# Functions
# ---------------------------------------------------------------

def get_weather_forecast(latitude, longitude, start_date, end_date):
    response = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=temperature_2m,relative_humidity_2m,rain&start_date={start_date}&end_date={end_date}"
    )
    data = response.json()
    
    time = data['hourly'].get('time', [])
    temperature = data['hourly'].get('temperature_2m', [])
    humidity = data['hourly'].get('relative_humidity_2m', [])
    rain = data['hourly'].get('rain', [])

    if not (time and temperature and humidity and rain):
        return {"error": "Incomplete weather data."}

    daily_data = defaultdict(lambda: {'temperature': [], 'humidity': [], 'total_rain': 0, 'rain_times': []})

    for i in range(len(time)):
        date = datetime.fromisoformat(time[i]).date()
        daily_data[date]['temperature'].append(temperature[i])
        daily_data[date]['humidity'].append(humidity[i])
        daily_data[date]['total_rain'] += rain[i]

        if rain[i] > 0:
            daily_data[date]['rain_times'].append({"time": time[i].split('T')[1], "rain": rain[i]})

    result = {}
    for date, values in daily_data.items():
        avg_temp = sum(values['temperature']) / len(values['temperature'])
        avg_humidity = sum(values['humidity']) / len(values['humidity'])
        result[str(date)] = {
            "average_temperature": round(avg_temp, 1),
            "average_humidity": round(avg_humidity, 1),
            "total_rain": round(values['total_rain'], 1),
            "rain_times": values['rain_times']
        }

    return result, data


def check_accomodation_request(input: str):
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an assistant for finding accomodation. \
                    You are allowed to answer only to queries related to accomodation search. \
                    In case of other requests, you must decline. \
                    In this context, Analyze if the text describes a query for finding accomodation. \
                    Say yes if the text describes a query for finding accomodation, else say no",
            },
            {"role": "user", "content": input},
        ],
        response_format=check_prompt
    )

    return completion.choices[0].message.parsed.is_accomodation_search


def extract_stay_details(input:str):
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": f"You are an assistant for finding accomodation. \
                    Extract the name of the city/place in which the user wishes to stay. If city is not found, strictly use the placeholder [None].\
                    Extract the check-in date. Check-in date is date on which the user will start staying in the accomodation. Strictly use 'yyyy-mm-dd' date format. If check-in date is not found, strictly use the placeholder [None].\
                    Extract the check-out date. Check-out date is date on which the user will leave the accomodation.  Strictly use 'yyyy-mm-dd' date format. If check-out date is not found, strictly use the placeholder [None]. \
                    Do not make any assumptions for the city, check-in date and check-out date.",
            },
            {"role": "user", "content": input},
        ],
        response_format=EventDetails
    )

    return completion


def process_accomodation_search(input: str):
    logger.info("Checking if prompt is accomodation search request...")
    is_accomodation_request = check_accomodation_request(input)

    if not is_accomodation_request:
        logger.info("Not an accomodation search request...")
        return None
    
    logger.info("Extracting details of stay...")
    stay_details = extract_stay_details(input)

    place_of_stay = stay_details.choices[0].message.parsed.city
    check_in_date = stay_details.choices[0].message.parsed.start_date
    check_out_date = stay_details.choices[0].message.parsed.end_date
    logger.info(f"Stay Details - City: {place_of_stay}, Start Date: {check_in_date}, End Date: {check_out_date}")

    

if __name__ == "__main__":
    user_input = input()
    process_accomodation_search(user_input)


