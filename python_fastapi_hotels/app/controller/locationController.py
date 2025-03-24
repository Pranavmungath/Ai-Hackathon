import json
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List
import httpx
import os
import requests
from typing_extensions import Optional

from app import config
from app.models.inputModels import *

router = APIRouter()

# Helper function to get access token
async def get_access_token() -> str:
    async with httpx.AsyncClient() as client:
        payload = {
            "grant_type": "client_credentials",
            "client_id": config.CLIENT_ID,
            "client_secret": config.CLIENT_SECRET
        }
        response = await client.post(config.TOKEN_URL, data=payload)
        response.raise_for_status()
        return response.json().get("access_token")


# Helper function to get IATA code
async def get_iata_code(city: str, token: str) -> str:
    async with httpx.AsyncClient() as client:
        headers = {'Authorization': f'Bearer {token}'}
        params = {"keyword": city, "subType": "CITY"}

        response = await client.get(config.BASE_URL, headers=headers, params=params)
        response.raise_for_status()

        city_data = response.json().get("data", [])
        if not city_data:
            raise HTTPException(status_code=404, detail="City not found")

        return city_data[0]["iataCode"]


# Helper function to get hotels by IATA code
async def get_hotels_by_iata(iata_code: str, token: str, **kwargs: Dict[str, Any]) -> List[dict]:
    async with httpx.AsyncClient() as client:
        hotels_url = f"{config.BASE_URL}/hotels/by-city"
        headers = {'Authorization': f'Bearer {token}'}
        params = {
            "cityCode": iata_code,
            **{k:v for k, v in kwargs.items() if v}
        }

        response = await client.get(hotels_url, headers=headers, params=params)
        response.raise_for_status()

        return response.json().get("data", [])


@router.get('/hotels', response_model= CityResponse, responses={404: {"model": ErrorResponse}})
async def search_hotels(city: str = Query(..., description="City name"),
                        amenities: Optional[List[str]] = Query(None, description="Amenities available in hotel"),
                        ratings: Optional[List[str]] = Query(None, description="Hotel stars. Up to four values can be requested at the same time in a comma separated list."),):
    try:
        token = await get_access_token()
        iata_code = await get_iata_code(city, token)

        params = {}
        if amenities:
            params['amenities'] = amenities
        if ratings:
            params['ratings'] = ratings

        hotels = await get_hotels_by_iata(iata_code, token, **params)

        return {"city": city, "iata_code": iata_code, "hotels": hotels}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Endpoint to get city IATA code only
@router.get('/hotels/city/{city}', response_model=CityResponse, responses={404: {"model": ErrorResponse}})
async def get_city_iata(city: str):
    try:
        token = await get_access_token()
        iata_code = await get_iata_code(city, token)

        return {"city": city, "iata_code": iata_code, "hotels": []}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Hotel by ID endpoint with renamed path
@router.get('/hotels/id/{hotel_id}', response_model=Hotel, responses={404: {"model": ErrorResponse}})
async def search_hotel_by_id(hotel_id: str):
    try:
        token = await get_access_token()
        async with httpx.AsyncClient() as client:
            hotels_url = f"{config.BASE_URL}/hotels/by-hotels"
            headers = {'Authorization': f'Bearer {token}'}
            param = {'hotelIds': hotel_id}
            response = await client.get(hotels_url, headers=headers, params=param)
            response.raise_for_status()
            hotels = response.json().get("data", [])

            if not hotels:
                raise HTTPException(status_code=404, detail="Hotel not found")

            return hotels[0]

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get('/hotels/review/{hotel_id}')
async def search_review_by_id(hotel_id: str):
    try:
        token = await get_access_token()
        async with httpx.AsyncClient() as client:
            review_url = f"{config.REVIEW_URL}/e-reputation/hotel-sentiments"
            headers = {'Authorization': f'Bearer {token}'}
            param = {'hotelIds': hotel_id}
            response = await client.get(review_url, headers=headers, params=param)
            response.raise_for_status()
            hotels = response.json().get("data", [])

            if not hotels:
                raise HTTPException(status_code=404, detail="Hotel not found")

            return hotels[0]

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


