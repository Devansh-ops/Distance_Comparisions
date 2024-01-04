# Script to Compare Distance given by Google Maps, Distancematrix.ai and geoapify

API from `Distancematrix.ai` was found to be the closest to `google`

## Instructions
1. Rename `.env.example` to `.env` 
2. Add appropriate API Keys to `.env` file
3. Add `coordinates.csv` to the folder (optional: remove `coordinates.csv.example`)
4. Optional: Change the parameter in code from `500` to increase / decrease the number of coordinates to test. 
    
    For example, to test `1000` instead of `500` coordinates, change the last lines (driver code):
    
    From
    ```python3
    if __name__ == "__main__":
    comparator = DistanceComparator()
    comparator.process_and_average_metrics('coordinates.csv', 500)
    ```

    To
    ```python3
    if __name__ == "__main__":
    comparator = DistanceComparator()
    comparator.process_and_average_metrics('coordinates.csv', 100)
    ```