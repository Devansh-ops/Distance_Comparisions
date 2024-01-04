
import csv
import json
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time
import random

class DistanceComparator:
    def __init__(self):
        load_dotenv()
        self.google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        self.geoapify_api_key = os.getenv('GEOAPIFY_API_KEY')

    def read_csv_file(self, file_path):
        with open(file_path, mode='r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            next(csv_reader)  # Skip header row if present
            for row in csv_reader:
                data = json.loads(row[0])
                yield (data['startLang'], data['startLat'], data['endLang'], data['endLat'])
    
    def read_random_rows(self, file_path, num_rows, seed=42):
        total_rows = sum(1 for _ in open(file_path)) - 1  # Assuming there's a header

        random.seed(seed)
        
        # Generate a set of unique random row indices
        if total_rows < num_rows:
            row_indices = set(range(total_rows))
        else:
            row_indices = set(random.sample(range(total_rows), num_rows))

        with open(file_path, mode='r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            next(csv_reader)  # Skip header

            for row_index, row in enumerate(csv_reader):
                if row_index in row_indices:
                    data = json.loads(row[0])
                    yield (data['startLang'], data['startLat'], data['endLang'], data['endLat'])
                    row_indices.remove(row_index)  # Optional: to stop iteration earlier

                    # Stop if all desired rows have been read
                    if not row_indices:
                        break

    def get_departure_time(self):
        return (datetime.utcnow() + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def get_distance_google_maps(self, start_long, start_lat, end_long, end_lat):
        url = 'https://routes.googleapis.com/directions/v2:computeRoutes'
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.google_maps_api_key,
            'X-Goog-FieldMask': 'routes.distanceMeters'
        }
        payload = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": start_lat,
                        "longitude": start_long
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": end_lat,
                        "longitude": end_long
                    }
                }
            },
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
            "departureTime": self.get_departure_time(),
            "computeAlternativeRoutes": False,
            "routeModifiers": {
                "avoidTolls": False,
                "avoidHighways": False,
                "avoidFerries": False
            },
            "languageCode": "en-IN",
            "units": "METRIC"
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            if 'routes' in data and len(data['routes']) > 0:
            # Extracting the distance from the first route in the response
                distance_meters = data['routes'][0]['distanceMeters']
            return distance_meters
        else:
            print("error in google api")
            print(response.json())
            return None  # No routes found in the response
    
    def get_distance_geoapify_balanced(self, start_long, start_lat, end_long, end_lat):
        url = f'https://api.geoapify.com/v1/routing?waypoints={start_lat},{start_long}|{end_lat},{end_long}&mode=drive&traffic=approximated&type=balanced&apiKey={self.geoapify_api_key}'
        
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'features' in data and len(data['features']) > 0 and 'properties' in data['features'][0]:
                distance_meters = data['features'][0]['properties']['distance']
                return distance_meters
            else:
                print("error in geoapify - no property found")
                print(response.json())
                return None  # No feature or properties found in the response
        else:
            print("error in geoapify")
            print(response.json())
            return None  # API request failed

    def get_distance_geoapify_short(self, start_long, start_lat, end_long, end_lat):
        url = f'https://api.geoapify.com/v1/routing?waypoints={start_lat},{start_long}|{end_lat},{end_long}&mode=drive&traffic=approximated&type=short&apiKey={self.geoapify_api_key}'
        
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'features' in data and len(data['features']) > 0 and 'properties' in data['features'][0]:
                distance_meters = data['features'][0]['properties']['distance']
                return distance_meters
            else:
                print("error in geoapify - no property found")
                print(response.json())
                return None  # No feature or properties found in the response
        else:
            print("error in geoapify")
            print(response.json())
            return None  # API request failed

    def get_distance_geoapify(self, start_long, start_lat, end_long, end_lat):
        geoapify_distance_short = self.get_distance_geoapify_short(start_long, start_lat, end_long, end_lat)
        geoapify_distance_balanced = self.get_distance_geoapify_balanced(start_long, start_lat, end_long, end_lat)
        
        if geoapify_distance_short is None and geoapify_distance_balanced is None:
            return None
        elif geoapify_distance_short is None:
            return geoapify_distance_balanced
        elif geoapify_distance_balanced is None:
            return (geoapify_distance_short)
        else:
            return (geoapify_distance_short+geoapify_distance_balanced) // 2


    def compare_distances(self, google_distance, geoapify_distance):
        if google_distance is None or geoapify_distance is None:
            return "Error: One or both distances are unavailable."

        # Calculate absolute error
        absolute_error = abs(google_distance - geoapify_distance)

        # Calculate relative error (compared to Google distance)
        relative_error = (absolute_error / google_distance) * 100 if google_distance != 0 else None

        # Calculate accuracy
        accuracy = (min(google_distance, geoapify_distance) / max(google_distance, geoapify_distance)) * 100

        # Prepare and return the comparison metrics
        comparison_metrics = {
            "Google Distance (meters)": google_distance,
            "Geoapify Distance (meters)": geoapify_distance,
            "Absolute Error (meters)": absolute_error,
            "Relative Error (%)": relative_error,
            "Accuracy (%)": accuracy
        }

        return comparison_metrics

    def process_and_average_metrics(self, csv_file_path, limit=100):
        # Initialize counters and sums
        request_counter = 0
        sum_google_distance = 0
        sum_geoapify_distance = 0
        sum_absolute_error = 0
        sum_relative_error = 0
        sum_accuracy = 0

        for start_long, start_lat, end_long, end_lat in self.read_random_rows(csv_file_path, limit):
            try:
                print(request_counter)
                # start_time = time.time()
                google_distance = self.get_distance_google_maps(start_long, start_lat, end_long, end_lat)
                # end_time = time.time()
                # print(f"Google Maps API Request Time: {end_time - start_time} seconds")
                # start_time = time.time()
                geoapify_distance = self.get_distance_geoapify(start_long, start_lat, end_long, end_lat)
                # end_time = time.time()
                # print(f"Geoapify API Request Time: {end_time - start_time} seconds")
                # print()
                metrics = self.compare_distances(google_distance, geoapify_distance)
                # print("metrics", metrics)
                # print()
                if isinstance(metrics, dict):
                    request_counter += 1
                    sum_google_distance += metrics["Google Distance (meters)"]
                    sum_geoapify_distance += metrics["Geoapify Distance (meters)"]
                    sum_absolute_error += metrics["Absolute Error (meters)"]
                    if metrics["Relative Error (%)"] is not None:
                        sum_relative_error += metrics["Relative Error (%)"]
                    sum_accuracy += metrics["Accuracy (%)"]

                    if request_counter % 10 == 0:
                        self.print_average_metrics(request_counter, sum_google_distance, sum_geoapify_distance, sum_absolute_error, sum_relative_error, sum_accuracy)

            except KeyboardInterrupt:
                sys.exit(0)
            except:
                print("\nError:\nstart: lat:", start_lat, "long:", start_long, "\nend: lat:", end_lat, "long:", end_long, "\n")

        # Check if there are any remaining entries to process after the loop
        if request_counter > 0:
            print()
            print("FINAL")
            self.print_average_metrics(request_counter, sum_google_distance, sum_geoapify_distance, sum_absolute_error, sum_relative_error, sum_accuracy)

    def print_average_metrics(self, total_entries, sum_google_distance, sum_geoapify_distance, sum_absolute_error, sum_relative_error, sum_accuracy):
        avg_google_distance = sum_google_distance / total_entries
        avg_geoapify_distance = sum_geoapify_distance / total_entries
        avg_absolute_error = sum_absolute_error / total_entries
        avg_relative_error = sum_relative_error / total_entries
        avg_accuracy = sum_accuracy / total_entries

        print("\nAverage Metrics since the last 10 requests:")
        print(f"Average Google Distance: {avg_google_distance} meters")
        print(f"Average Geoapify Distance: {avg_geoapify_distance} meters")
        print(f"Average Absolute Error: {avg_absolute_error} meters")
        print(f"Average Relative Error: {avg_relative_error} %")
        print(f"Average Accuracy: {avg_accuracy} %")
            

if __name__ == "__main__":
    comparator = DistanceComparator()
    comparator.process_and_average_metrics('coordinates.csv', 500)
