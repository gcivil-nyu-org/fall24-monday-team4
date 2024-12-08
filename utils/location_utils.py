import requests


def reverse_geocode(lat, lng):
    """Convert coordinates to address using Nominatim"""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
        headers = {"User-Agent": "RoutePals/1.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        return data.get("display_name")
    except Exception:
        return None


def search_location(query):
    """Convert address query to coordinates using Nominatim"""
    try:
        url = (
            f"https://nominatim.openstreetmap.org/search?q={query}&limit=1&format=json"
        )
        headers = {"User-Agent": "RoutePals/1.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        return data[0] if data else None
    except Exception:
        return None
