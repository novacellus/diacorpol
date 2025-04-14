import requests
import time
import json
import csv
from urllib.parse import urlencode, urlparse, parse_qs
from pathlib import Path
import copy
import argparse

# Base API configuration
BASE_URL = "http://data.bn.org.pl/api/networks/bibs.json"

# Query parameters
query_params = {
    "placeOfPublication": "Polska",
    #"publicationYear": "<1850",
    "language": "łaciński",
    "languageOfOriginal": "łaciński",
    "boolean": "true"
}

def prepare_record_for_csv(record):
    # Create a copy of the record and remove the 'marc' field
    clean_record = copy.deepcopy(record)
    clean_record.pop('marc', None)
    return clean_record

def save_records(records, batch_num, base_filename, save_csv=False):
    # Create output directory if it doesn't exist
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    # Save JSON
    json_filename = output_dir / f'{base_filename}_batch_{batch_num}.json'
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # Save CSV if requested
    if save_csv:
        csv_filename = output_dir / f'{base_filename}_batch_{batch_num}.csv'

        # Prepare records for CSV (remove marc field)
        clean_records = [prepare_record_for_csv(record) for record in records]

        if clean_records:  # Make sure we have records
            # Get field names from the first record
            fieldnames = list(clean_records[0].keys())

            with open(csv_filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(clean_records)

    return json_filename

def fetch_all_records(base_url, initial_params, base_filename, batch_size=100, save_csv=False):
    current_batch = []
    total_records = 0
    batch_num = 1
    current_params = initial_params.copy()

    while True:
        try:
            # Construct the full URL for the current request
            current_url = f"{base_url}?{urlencode(current_params)}"

            # Make the API request
            response = requests.get(current_url)
            response.raise_for_status()

            # Parse the JSON response
            data = response.json()

            # Process the current page's records
            if 'bibs' in data:
                new_records = data['bibs']
                if not new_records:  # If no new records, we're done
                    break

                current_batch.extend(new_records)
                total_records += len(new_records)

                # Save batch if it reaches the batch size
                if len(current_batch) >= batch_size:
                    filename = save_records(current_batch, batch_num,
                                         base_filename, save_csv)
                    print(f"Saved batch {batch_num} with {len(current_batch)} records to {filename}")
                    current_batch = []
                    batch_num += 1

            print(f"Total records processed so far: {total_records}")

            # Check for next page
            if 'nextPage' not in data:
                break

            # Extract sinceId from nextPage URL
            next_url = data['nextPage']
            parsed_next = urlparse(next_url)
            next_params = parse_qs(parsed_next.query)

            # Update the current_params with the new sinceId
            current_params = initial_params.copy()
            # Add ALL parameters from nextPage URL
            for key, value in next_params.items():
                current_params[key] = value[0]

            time.sleep(0.5)
        

        except requests.exceptions.RequestException as e:
            print(f"Error during request: {e}")
            if current_batch:
                filename = save_records(current_batch, batch_num,
                                     base_filename, save_csv)
                print(f"Saved remaining {len(current_batch)} records to {filename}")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            if current_batch:
                filename = save_records(current_batch, batch_num,
                                     base_filename, save_csv)
                print(f"Saved remaining {len(current_batch)} records to {filename}")
            break

    # Save any remaining records in the last batch
    if current_batch:
        filename = save_records(current_batch, batch_num, base_filename, save_csv)
        print(f"Saved final batch with {len(current_batch)} records to {filename}")

    return total_records

def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Fetch library records from BN API')
    parser.add_argument('--filename', type=str, default="library_records",
                      help='Base filename for saved records (default: library_records)')
    parser.add_argument('--save-csv', action='store_true',
                      help='Save records in CSV format in addition to JSON')
    parser.add_argument('--batch-size', type=int, default=100,
                      help='Number of records per batch (default: 100)')

    args = parser.parse_args()

    # Add timestamp to filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    full_filename = f'{args.filename}_{timestamp}'

    # Fetch all records
    total_records = fetch_all_records(
        base_url=BASE_URL,
        initial_params=query_params,
        base_filename=full_filename,
        batch_size=args.batch_size,
        save_csv=args.save_csv  # Use the command line argument
    )

    print(f"\nProcess completed. Total records fetched: {total_records}")

if __name__ == "__main__":
    main()
