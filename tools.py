import requests
import os


def add_product_to_api(product_data):
    try:
        response = requests.post(os.getenv("PRODUCT_API_URL"), json=product_data)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()  # Return the API response JSON
    except requests.RequestException as e:
        print(f"API request error: {e}")
        return None