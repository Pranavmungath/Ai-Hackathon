from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from openai import OpenAI
import logging

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

client = client = OpenAI(
    base_url = 'http://localhost:11434/v1',
    api_key='ollama', # required, but unused
)

model = "llama3.2:3b"

class check_prompt(BaseModel):
    """First LLM call: Extract basic accomodation information"""

    # description: str = Field(description="Raw description of the event")
    is_accomodation_search: bool = Field(
        description="Whether this text describes a query for finding accomodation?"
    )
    confidence_score: float = Field(description="Confidence score between 0 and 1")

class EventDetails(BaseModel):
    """Second LLM call: Parse specific event details"""

    city: str = Field(description="City in which the accomodation should be booked")
    start_date: str = Field(
        description="Date and time of checking into the accomodation. Use ISO 8601 to format this value."
    )
    end_date: str = Field(
        description="Date and time of checking out of the accomodation. Use ISO 8601 to format this value."
    )




