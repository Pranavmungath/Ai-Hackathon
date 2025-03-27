import os
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
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

# LLM model name
model = "llama-3.3-70b-versatile"

# Tools
tools = [
  {
    "type": "function",
    "function": {
      "name": "get_weather_forecast",
      "description": "Retrieve the weather forecast including average temperature (°C), average relative humidity (%), total rainfall (mm), and rain timing for specified coordinates within a given date range.",
      "parameters": {
        "type": "object",
        "properties": {
          "latitude": {
            "type": "number",
            "description": "Latitude of the location (in decimal degrees, range: -90 to 90).",
            "minimum": -90,
            "maximum": 90
          },
          "longitude": {
            "type": "number",
            "description": "Longitude of the location (in decimal degrees, range: -180 to 180).",
            "minimum": -180,
            "maximum": 180
          },
          "start_date": {
            "type": "string",
            "description": "Start date for the forecast period (format: YYYY-MM-DD).",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
          },
          "end_date": {
            "type": "string",
            "description": "End date for the forecast period (format: YYYY-MM-DD).",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
          }
        },
        "required": ["latitude", "longitude", "start_date", "end_date"],
        "additionalProperties": False
      },
      "strict": True
    }
  }
]

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


# Define the Pydantic model for hotel ranking
class HotelRanking(BaseModel):
    hotel_name: str = Field(description=f"Name of the hotel exactly as in the input")
    reason: str = Field(description="A short explanation as to why the hotel was chosen for this rank?")
    pros: str = Field(description="A bullet points about the pros of the hotel")
    cons: str = Field(description="A bullet points about the cons of the hotel")


class HotelRankingsResponse(BaseModel):
    rank_1: HotelRanking = Field(description="The name, reason for being assigned first rank, pros and cons of the first ranked hotel")
    rank_2: HotelRanking = Field(description="The name, reason for being assigned second rank, pros and cons of the second ranked hotel")
    rank_3: HotelRanking = Field(description="The name, reason for being assigned third rank, pros and cons of the third ranked hotel")

# ---------------------------------------------------------------
# Functions
# ---------------------------------------------------------------\

def call_function(name, args):
    if name == "get_weather_forecast":
        return get_weather_forecast(**args)


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

    return result


def get_reviews_by_city_and_hotel(json_file, city_name, hotel_name):
    # Load JSON data
    with open(json_file, 'r') as file:
        data = json.load(file)

    # Iterate through cities
    for city in data.get("cities", []):
        if city["city"].lower() == city_name.lower():
            # Iterate through hotels
            for hotel in city.get("hotels", []):
                if hotel["hotel_name"].lower() == hotel_name.lower():
                    return hotel.get("reviews", [])

    return []


def check_accomodation_request(input_prompt: str):
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": f"""
                    You are an assistant for finding accomodation. 
                    You are allowed to answer only to queries related to accomodation search.
                    In case of other requests, you must decline.
                    In this context, Analyze if the text describes a query for finding accomodation.
                    Say yes if the text describes a query for finding accomodation, else say no.
                    Output should be in json format:
                    {json.dumps(check_prompt.model_json_schema(), indent=2)}
                    """ 
            },
            {"role": "user", "content": input_prompt},
        ],
        response_format={"type": "json_object"}
    )

    return check_prompt.model_validate_json(completion.choices[0].message.content)


def extract_stay_details(input:str):
    today = datetime.now()
    date_context = f"Today is {today.strftime('%A, %B %d, %Y')}."

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": f"""
                    You are an assistant for finding accomodation.
                    Extract the name of the city in which the user wishes to stay. If city is not found, strictly use the placeholder [None].
                    {date_context} When dates reference 'next Tuesday' or similar relative dates, use this current date as reference.
                    Extract the check-in date. Check-in date is date on which the user will start staying in the accomodation. Strictly use 'yyyy-mm-dd' date format. If check-in date is not found, strictly use the placeholder [None].
                    Extract the check-out date. Check-out date is date on which the user will leave the accomodation.  Strictly use 'yyyy-mm-dd' date format. If check-out date is not found, strictly use the placeholder [None].
                    Do not make any assumptions for the city, check-in date and check-out date.
                    Output should be in json format:
                    {json.dumps(EventDetails.model_json_schema(), indent=2)}
                """
            },
            {"role": "user", "content": input},
        ],
        response_format={"type": "json_object"}
    )

    return EventDetails.model_validate_json(completion.choices[0].message.content)


def get_weather_forecast_summary(place_of_stay:str, check_in_date:str, check_out_date:str):
    # system_prompt = "You are a helpful weather assistant. \
    #             You can determine the latitude and longitude based on the name of the city/place \
    #             You strictly use 'yyyy-mm-dd' format for dates. \
    #             Based on the temperature, relative humidity and rain data, you can provide a human-like concise report on the weather using natural language. \
    #             An example report for Coimbatore from 26 March 2025 to 27 March 2025 will look like - The weather is "

    system_prompt = """
        **Goal:**
        Generate a clear, concise, and human-like weather forecast summary from structured weather data. The summary should use **future tense** and present the information in a natural, easy-to-understand tone.

        **Input Format:**
        The model will receive a JSON object representing the weather forecast. Each key is a date in `YYYY-MM-DD` format, and the corresponding value is an object containing the following attributes:

        - `average_temperature` (float): The average temperature in Celsius.
        - `average_humidity` (float): The average humidity as a percentage.
        - `total_rain` (float): The total rainfall in millimeters.
        - `rain_times` (list): A list of times (in `HH:MM` format) when rain is expected. An empty list means no rain is forecasted.

        **Example Input:**
        ```json
        {
        "2025-03-27": {"average_temperature": 27.6, "average_humidity": 74.7, "total_rain": 0.0, "rain_times": []},
        "2025-03-28": {"average_temperature": 28.9, "average_humidity": 68.4, "total_rain": 0.0, "rain_times": []},
        "2025-03-29": {"average_temperature": 29.2, "average_humidity": 67.4, "total_rain": 0.0, "rain_times": []}
        }
        ```

        **Output Format:**
        A natural language weather forecast summary using future tense.

        **Example Output:**
        "**Weather Forecast (March 27–29, 2025):**
        Expect **warm and dry** weather over these three days. Temperatures will gradually rise from **27.6°C** on March 27 to **29.2°C** by March 29. Humidity will decrease slightly, dropping from **74.7%** to **67.4%**, making the air feel a bit less sticky. **No rain** is expected during this period, so the days should stay **clear and dry** throughout."

        **Instructions for the Model:**
        1. **Identify the Date Range:** Parse the JSON object and determine the range of dates to include in the forecast.

        2. **Summarize Temperature Trends:** Describe how temperatures will change over the forecast period, mentioning specific values and whether they will rise, fall, or remain stable.

        3. **Summarize Humidity Trends:** Comment on how humidity levels will shift, focusing on whether they will increase, decrease, or stay the same.

        4. **Describe Rain Conditions:**
        - If `total_rain` is greater than 0, mention the likelihood of rain and its expected timing using `rain_times`.
        - If no rain is expected, explicitly state that the forecast predicts dry weather.

        5. **Use a Natural Tone:** Use conversational language with phrases like "expect," "will be," and "should remain" to make the summary feel human and approachable.

        6. **Prioritize Clarity and Brevity:** Keep the summary concise while ensuring all key weather trends are covered.

        **Edge Cases:**
        - If the input contains only one date, generate a forecast for that single day.
        - If the temperature or humidity remains unchanged, explicitly state that conditions will be stable.
        - If rain is expected, include specific times when available; otherwise, mention general rainy conditions.

    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"What is the weather forecast for {place_of_stay} between {check_in_date} and {check_out_date}?"},
    ]

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
    )

    for tool_call in completion.choices[0].message.tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        messages.append(completion.choices[0].message)

        result = call_function(name, args)
        messages.append(
            {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)}
        )

    weather_summary = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools
    )

    return weather_summary, result


def review_hotels(city_name:str, reviews_json_file_path:str):
    logger.info(f"Searching hotels...")
    response = requests.get(f"http://localhost:8084/hotels?city={city_name}&ratings=%5B5%2C4%2C3%5D")
    logger.info(response)
    data = response.json()

    logger.info(f"Summarizing reviews...")
    reviews_string = ""
    hotels_list = []
    for hotel in data['hotels']:
        if not hotel['name'].startswith('TEST'):
            reviews = get_reviews_by_city_and_hotel(reviews_json_file_path, 'Bengaluru', hotel['name'])

            if reviews:
                hotels_list.append(hotel['name'])
                reviews_string += (f"\nHotel name: {hotel['name']}")
                for i, review in enumerate(reviews):
                    reviews_string += (f"\nReview {i} (posted on {review['date']}): {review['comment']}")
                reviews_string += "\n" + "-" * 50
    
    # System prompt for hotel ranking
    system_prompt = f"""
        You are a Hotel Ranking Assistant.
        Your task is to evaluate and rank the hotels based on provided guest reviews.
        After ranking the hotels, choose the top three hotels.
        Safety should be most important criteria when evaluating the hotels.

        Other Evaluation Criteria are as follows,
        1. Service Quality: Friendliness, attentiveness, and responsiveness of staff.
        2. Cleanliness & Maintenance: Cleanliness of rooms, public areas, and general upkeep.
        3. Location & Accessibility: Proximity to key city areas, convenience of transport.
        4. Amenities & Comfort: Quality of rooms, dining options, event spaces, and technology.
        5. Guest Satisfaction: Consistency of positive feedback, handling of issues, and special gestures.

        Ranking Logic:
        - Analyze and compare the hotels across all criteria with safety being the utmost priority.
        - Rank hotels from best to worst, clearly explaining why each hotel holds its position.
        - Highlight both positive aspects (pros) and negative aspects (cons) for each hotel.

        Output should be in below json format:
        {json.dumps(HotelRankingsResponse.model_json_schema(), indent=2)}
    """

    completion_reviews = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": f"Based on the following reviews, summarise and choose the top 3 hotels. Reviews:\n{reviews_string}"},
        ],
        response_format={"type": "json_object"}
    )

    return HotelRankingsResponse.model_validate_json(completion_reviews.choices[0].message.content)


def process_accomodation_search(input: str, reviews_json_file_path:str):
    logger.info("Checking if prompt is accomodation search request...")
    is_accomodation_request = check_accomodation_request(input)

    if not is_accomodation_request:
        logger.info("Not an accomodation search request...")
        return None
    
    logger.info("Extracting details of stay...")
    stay_details = extract_stay_details(input)

    place_of_stay = stay_details.city
    check_in_date = stay_details.start_date
    check_out_date = stay_details.end_date
    logger.info(f"Stay Details - City: {place_of_stay}, Start Date: {check_in_date}, End Date: {check_out_date}")

    logger.info("Getting Weather Forecast...")
    weather_summary, weather_data = get_weather_forecast_summary(place_of_stay, check_in_date, check_out_date)
    weather_summary = weather_summary.choices[0].message.content

    logger.info(f"Weather data: {weather_data}")
    logger.info(f"Weather summary: {weather_summary}")

    top_3_hotels = review_hotels(place_of_stay, reviews_json_file_path)

    logger.info(f"Top 3 Hotels: {top_3_hotels}")
    
if __name__ == "__main__":
    reviews_json_file_path = 'knowledge_base/hotel_reviews.json'

    user_input = input()
    process_accomodation_search(user_input, reviews_json_file_path)


