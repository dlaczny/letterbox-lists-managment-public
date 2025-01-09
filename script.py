import os
import requests
import time
from bs4 import BeautifulSoup
from tqdm import tqdm

def create_tmdb_session():
    # Step 1: Create request token
    url = "https://api.themoviedb.org/3/authentication/token/new"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {os.getenv('TMDB_API_KEY', '')}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data["success"]:
            request_token = data["request_token"]
            print(f"Request token created: {request_token}")
        else:
            print("Failed to create request token.")
            return None
    else:
        print(f"Error: {response.status_code}")
        return None

    # Step 2: Validate with login and request token
    url = "https://api.themoviedb.org/3/authentication/token/validate_with_login"
    payload = {
        "username": os.getenv('TMDB_LOGIN', ''),
        "password": os.getenv('TMDB_PASSWORD', ''),
        "request_token": request_token
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data["success"]:
            print("Login successful!")
        else:
            print("Login failed.")
            return None
    else:
        print(f"Error: {response.status_code}")
        return None

    # Step 3: Create a session
    url = "https://api.themoviedb.org/3/authentication/session/new"
    payload = {
        "request_token": request_token
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data["success"]:
            session_id = data["session_id"]
            print(f"Session created successfully! Session ID: {session_id}")
            return session_id
        else:
            print("Failed to create session.")
            return None
    else:
        print(f"Error: {response.status_code}")
        return None


def fetch_tmdb_watch_providers(tmdb_id, country, providers, session_id):
    # Construct the URL for the providers API
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/watch/providers"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {os.getenv('TMDB_API_KEY', '')}",
        "Session-ID": session_id  # Add session ID to headers if needed
    }

    # Send the GET request to fetch watch provider information
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch providers for TMDb ID {tmdb_id}. Status code: {response.status_code}")
        return None

    # Parse the JSON response
    data = response.json()

    # Get the country-specific results (e.g., "PL" for Poland)
    country_results = data.get("results", {}).get(country, {})

    # If no data is found for the country, return None
    if not country_results or "flatrate" not in country_results:
        return None

    # Get the list of available providers under the "flatrate" key
    available_providers = [
        provider["provider_name"] for provider in country_results["flatrate"]
        if provider["provider_name"].lower() in [p.lower() for p in providers]
    ]

    return available_providers


def get_existing_movie_ids_from_list(list_id, session_id):
    # Fetch the movie IDs in the list
    url = f"https://api.themoviedb.org/3/list/{list_id}?session_id={session_id}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {os.getenv('TMDB_API_KEY', '')}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch movies from list {list_id}. Status code: {response.status_code}")
        return []

    data = response.json()
    existing_ids = [item["id"] for item in data.get("items", [])]
    return existing_ids


def add_movie_to_list(movie_id, list_id, session_id):
    url = f"https://api.themoviedb.org/3/list/{list_id}/add_item?session_id={session_id}"

    payload = {
        "media_type": "movie",
        "media_id": movie_id
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {os.getenv('TMDB_API_KEY', '')}"
    }

    print(f"Attempting to add movie {movie_id} to list {list_id} with payload {payload}")

    response = requests.post(url, json=payload, headers=headers)
    
    # Log status and response for better troubleshooting
    print(f"Response status code: {response.status_code}")
    print(f"Response text: {response.text}")

    if response.status_code == 200:
        data = response.json()
        if data["success"]:
            print(f"Successfully added movie {movie_id} to list {list_id}")
        else:
            print(f"Failed to add movie {movie_id} to list {list_id} with message: {data.get('status_message', 'No status message provided')}")
    else:
        # Print detailed error message for troubleshooting
        print(f"Error: {response.status_code} - {response.text}")


def get_last_page(username):
    print(f"Getting last page for user: {username}")
    url = f'https://letterboxd.com/{username}/watchlist/'
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch the list page. Status code: {response.status_code}")
        return 1

    soup = BeautifulSoup(response.content, 'html.parser')
    pagination = soup.find('div', class_='paginate-pages')
    if pagination:
        pages = pagination.find_all('a')
        if pages:
            # Extract the page numbers and convert them to integers
            page_numbers = [int(page.text.strip()) for page in pages if page.text.strip().isdigit()]
            if page_numbers:
                return max(page_numbers)
    return 1

def get_last_movie_on_last_page(username):
    print(f"Fetching the last movie ID for user: {username}")
    last_page = get_last_page(username)
    print(f"Last page found: {last_page}")
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f'https://letterboxd.com/{username}/watchlist//page/{last_page}/'

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch the last page. Status code: {response.status_code}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    films = soup.find_all('li', class_='poster-container')
    if films:
        last_film = films[-1]
        film_card = last_film.find('div', {'data-target-link': True})
        if film_card:
            film_page = 'https://letterboxd.com' + film_card['data-target-link']
            print(f"Last film page URL: {film_page}")
            film_response = requests.get(film_page, headers=headers)
            if film_response.status_code == 200:
                film_soup = BeautifulSoup(film_response.content, 'html.parser')
                tmdb_link_tag = film_soup.find('a', href=True, class_='micro-button track-event', string='TMDb')
                if tmdb_link_tag:
                    tmdb_id = tmdb_link_tag['href'].split('/')[-2]
                    print(f"TMDb ID of the last film: {tmdb_id}")
                    return tmdb_id
    return None

first_movie_checked = None  # Global variable

def scrape_watchlist_and_check_providers(username, country, general_providers):
    global first_movie_checked
    base_url = f'https://letterboxd.com/{username}/watchlist/'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    # Retrieve list IDs from environment variables
    my_watchlist_id = os.getenv('MY_WATCHLIST_ID')
    not_on_streaming_id = os.getenv('NOT_ON_STREAMING_ID')
    streaming_max_id = os.getenv('STREAMING_MAX_ID')
    streaming_disney_id = os.getenv('STREAMING_DISNEY_ID')
    streaming_ama_prime_id = os.getenv('STREAMING_AMA_PRIME_ID')  # Amazon Prime Video list ID
    streaming_skyshowtime_id = os.getenv('STREAMING_SKYSHOWTIME_ID')  # SkyShowtime list ID

    currentLastMovie = get_last_movie_on_last_page(username)

    if first_movie_checked == currentLastMovie:
        print("Last movie added to letterboxed was already processed")
        return
    else:
        print("##first_movie_checked value added")
        first_movie_checked = currentLastMovie

    session_id = create_tmdb_session()  # Session is created here for the loop
    if not session_id:
     print("Session creation failed. Exiting.")
     
    # Get the existing movie IDs once before processing films
    existing_movie_ids = get_existing_movie_ids_from_list(my_watchlist_id, session_id) 

    page = 1
    while True:
        url = f'{base_url}page/{page}/'
        print(f"Fetching page {page} from {url}...")  # Debug: Log page being fetched
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f'Failed to retrieve page {page}. Status code: {response.status_code}')
            break

        soup = BeautifulSoup(response.content, 'html.parser')
        films = soup.find_all('li', class_='poster-container')

        if not films:
            print(f"No films found on page {page}. Ending process.")  # Debug: No films found
            break  # Exit the loop if no films are found

        print(f"Found {len(films)} films on page {page}. Processing...")  # Debug: Films found

        # Save the ID of the first movie on the current loop
        if first_movie_checked is None:
            first_movie_checked = None

        # Loop through films
        for film in tqdm(films, desc=f'Processing page {page}'):

            film_card = film.find('div', {'data-target-link': True})
            if film_card:
                film_page = 'https://letterboxd.com' + film_card['data-target-link']
                film_response = requests.get(film_page, headers=headers)
                if film_response.status_code == 200:
                    film_soup = BeautifulSoup(film_response.content, 'html.parser')

                    # Get the TMDb link and extract the TMDb ID
                    tmdb_link_tag = film_soup.find('a', href=True, class_='micro-button track-event', string='TMDb')  # Fix: Use string instead of text
                    if tmdb_link_tag:
                        tmdb_id = tmdb_link_tag['href'].split('/')[-2]  # Extract the TMDb ID from the link

                        # Skip if movie is already in the watchlist
                        if int(tmdb_id) in existing_movie_ids:
                            print(f"Movie {tmdb_id} already in watchlist, skipping.")
                            continue

                        # Now perform TMDb API integration after the first movie check
                        tmdb_url = f"https://www.themoviedb.org/movie/{tmdb_id}"

                        # Log movie title and TMDb link
                        print(f"Movie is available on: {tmdb_url}")

                        # Check available streaming providers
                        providers = fetch_tmdb_watch_providers(tmdb_id, country, general_providers, session_id)

                        # Add to "my-watchlist" list
                        add_movie_to_list(tmdb_id, my_watchlist_id, session_id)

                        if providers:
                            # Log and Add to provider-specific lists
                            for provider in providers:
                                print(f"Movie '{tmdb_url}' is available on: {provider}")
                                provider_lower = provider.lower()
                                if provider_lower == 'max':
                                    add_movie_to_list(tmdb_id, streaming_max_id, session_id)
                                elif provider_lower == 'amazon prime video':
                                    add_movie_to_list(tmdb_id, streaming_ama_prime_id, session_id)
                                elif provider_lower == 'disney plus':
                                    add_movie_to_list(tmdb_id, streaming_disney_id, session_id)
                                elif provider_lower == 'skyshowtime':
                                    add_movie_to_list(tmdb_id, streaming_skyshowtime_id, session_id)
                        else:
                            # Log and Add to "Not-on-streaming" list
                            print(f"Movie '{tmdb_url}' is not available on specified providers.")
                            add_movie_to_list(tmdb_id, not_on_streaming_id, session_id)

                    else:
                        print(f"TMDb link not found for movie '{tmdb_id}'.")
                else:
                    print(f"Failed to load film page: {film_page}")
        page += 1  # Move to the next page


def main_task():
    username = os.getenv('LETTERBOXED_USERNAME', 'default_username')
    tmdb_api_key = os.getenv('TMDB_API_KEY')
    country = os.getenv('COUNTRY', 'PL')
    general_providers = os.getenv('GENERAL_PROVIDERS', 'max,amazon prime video,disney plus,skyshowtime').split(',')
    loop_interval = int(os.getenv('LOOP_INTERVAL', 600))  # Default to 10 minutes if not set


    # #DEBUG
    # scrape_watchlist_and_check_providers(username, country, general_providers)
    # print("22222222222222222222222222222222222222222222222222222222")
    # scrape_watchlist_and_check_providers(username, country, general_providers)
    # return
    # #DEBUG

    if not tmdb_api_key:
        print("TMDB API key is not set. Please set the TMDB_API_KEY environment variable.")
    elif username == 'default_username':
        print("No username provided. Set the LETTERBOXED_USERNAME environment variable.")
    else:
        while True:
            print(f"Starting the task at {time.ctime()}...")
            scrape_watchlist_and_check_providers(username, country, general_providers)
            
            # Sleep for the configured interval
            print(f"Waiting for {loop_interval} seconds before the next run...")
            time.sleep(loop_interval)

if __name__ == '__main__':
    main_task()