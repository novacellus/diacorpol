import requests
import time
import json
import csv
from pathlib import Path
import copy
import argparse

# Base API configuration
BASE_URL = "https://dbn.bn.org.pl/api/descriptor/dbn/list"

# Query parameters
query_params = {
     "type": "PERSONAL_DESCRIPTOR",
    "metadata.associatedPlaceCountry": "Polska",
    "metadata.associatedLanguage": "łaciński",
    "page.pageNumber": 0,
    "page.pageSize": 100,
}

def prepare_record_for_csv(record):
    # Create a copy of the record
    clean_record = copy.deepcopy(record)

    # Helper function to safely join array fields
    def safe_join(field_value):
        if isinstance(field_value, list):
            return ';'.join(str(item) for item in field_value)
        elif field_value is None:
            return ''
        return str(field_value)

    # Safely process array fields
    array_fields = ['alternateNames', 'sourceDataFound', 'sourceDataNotFound', 'publicGeneralNote']
    for field in array_fields:
        if field in clean_record:
            clean_record[field] = safe_join(clean_record[field])

    # Handle externalId array
    if 'externalId' in clean_record:
        if isinstance(clean_record['externalId'], list):
            external_ids = []
            for ext_id in clean_record['externalId']:
                if isinstance(ext_id, dict):
                    string_value = ext_id.get('stringValue', '')
                    data_associated = ext_id.get('dataAssociated', '')
                    external_ids.append(f"{string_value}:{data_associated}")
            clean_record['externalId'] = ';'.join(external_ids)
        else:
            clean_record['externalId'] = ''

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
    if save_csv and records:
        csv_filename = output_dir / f'{base_filename}_batch_{batch_num}.csv'

        try:
            # Prepare records for CSV
            clean_records = [prepare_record_for_csv(record) for record in records]

            if clean_records:
                # Get field names from the first record
                fieldnames = list(clean_records[0].keys())

                with open(csv_filename, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(clean_records)
        except Exception as e:
            print(f"Error saving CSV file: {e}")
            print("Continuing with JSON only...")

    return json_filename

def fetch_all_records(base_url, initial_params, base_filename, batch_size=100, save_csv=False):
    current_batch = []
    total_records = 0
    batch_num = 1
    current_params = initial_params.copy()
    current_page = 0

    while True:
        try:
            # Update the page number in parameters
            current_params['page.pageNumber'] = current_page

            # Add logging to verify request parameters
            print(f"\nMaking request with parameters:")
            print(f"Page Number: {current_params['page.pageNumber']}")
            print(f"Page Size: {current_params['page.pageSize']}")

            # Make the API request
            response = requests.get(base_url, params=current_params)
            response.raise_for_status()

            # Parse the JSON response
            data = response.json()

            # Add logging to verify response data
            print(f"Response status code: {response.status_code}")
            print(f"Response URL: {response.url}")  # This will show the actual URL with parameters
            print(f"Total pages in response: {data.get('totalPages', 1)}")
            print(f"Records in current page: {len(data.get('result', []))}")

            # Process the current page's records
            if 'result' in data and data['result']:
                new_records = data['result']

                # Add logging to check for duplicate records
                if new_records:
                    print(f"First record ID in batch: {new_records[0].get('id', 'No ID')}")

                current_batch.extend(new_records)
                total_records += len(new_records)

                # Save batch if it reaches the batch size
                if len(current_batch) >= batch_size:
                    filename = save_records(current_batch, batch_num,
                                         base_filename, save_csv)
                    print(f"Saved batch {batch_num} with {len(current_batch)} records to {filename}")
                    current_batch = []
                    batch_num += 1

            print(f"Processed page {current_page + 1} of {data.get('totalPages', 1)}")
            print(f"Total records processed so far: {total_records}")

            # Check if we've reached the last page
            if current_page >= data.get('totalPages', 1) - 1:
                break

            # Move to next page
            current_page += 1
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
    parser = argparse.ArgumentParser(description='Fetch descriptor records from DBN API')
    parser.add_argument('--filename', type=str, default="descriptor_records",
                      help='Base filename for saved records (default: descriptor_records)')
    parser.add_argument('--save-csv', action='store_true',
                      help='Save records in CSV format in addition to JSON')
    parser.add_argument('--batch-size', type=int, default=100,
                      help='Number of records per batch (default: 100)')
    parser.add_argument('--page-size', type=int, default=100,
                      help='Number of records per API request (default: 100)')

    args = parser.parse_args()

    # Update page size in query parameters
    query_params['pageSize'] = args.page_size

    # Add timestamp to filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    full_filename = f'{args.filename}_{timestamp}'

    # Fetch all records
    total_records = fetch_all_records(
        base_url=BASE_URL,
        initial_params=query_params,
        base_filename=full_filename,
        batch_size=args.batch_size,
        save_csv=args.save_csv
    )

    print(f"\nProcess completed. Total records fetched: {total_records}")

if __name__ == "__main__":
    main()
