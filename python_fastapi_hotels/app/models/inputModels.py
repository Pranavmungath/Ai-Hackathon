from pydantic import BaseModel
from typing import Union, List, Dict, Any

# Pydantic models for structured response
class Hotel(BaseModel):
    name: str = None
    hotelId: str = None
    address: dict = None
    chainCode: str = None
    iataCode: str = None
    dupeId: int = None
    geoCode: dict = None
    distance: dict = None
    lastUpdate: str = None



class CityResponse(BaseModel):
    city: str = None
    iata_code: str = None
    hotels: List[Hotel] = None


class ErrorResponse(BaseModel):
    error: str = None



