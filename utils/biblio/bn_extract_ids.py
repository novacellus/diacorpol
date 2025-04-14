import json
import csv
import os
import glob
import argparse
from typing import List, Dict, Any

def extract_marc_fields(record: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Extract relevant MARC fields from a single record.
    Only extracts 852 fields where subfield b is '48OMNIS_NETWORK'.
    Returns a list of dictionaries containing the extracted fields with renamed columns.
    """
    results = []

    # Extract basic fields
    record_id = record.get('id', '')

    # Find 001 and 009 fields
    id_bn_full = ''
    id_omnis_src = ''

    for field in record.get('marc', {}).get('fields', []):
        if '001' in field:
            id_bn_full = field['001']
        elif '009' in field:
            id_omnis_src = field['009']

    # Extract 852 fields
    fields_852 = [field['852'] for field in record.get('marc', {}).get('fields', [])
                 if '852' in field]

    # Process each 852 field, but only keep those with subfield b = '48OMNIS_NETWORK'
    for field_852 in fields_852:
        if 'subfields' in field_852:
            subfield_b = None
            subfield_8 = None

            # Extract subfields b and 8
            for subfield in field_852['subfields']:
                if 'b' in subfield:
                    subfield_b = subfield['b']
                elif '8' in subfield:
                    subfield_8 = subfield['8']

            # Only add if subfield b is '48OMNIS_NETWORK'
            if subfield_b == '48OMNIS_NETWORK':
                results.append({
                    'id_bn': record_id,
                    'id_bn_full': id_bn_full,
                    'id_omnis_src': id_omnis_src,
                    'id_omnis': subfield_8 or ''  # Using subfield 8 as id_omnis
                })

    return results

def process_json_file(file_path: str) -> List[Dict[str, str]]:
    """
    Process a single JSON file and return extracted data.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove trailing comma if present
            if content.rstrip().endswith(','):
                content = content.rstrip(',\n\t ') + ']'
            data = json.loads(content)

        all_results = []
        for record in data:
            record_results = extract_marc_fields(record)
            all_results.extend(record_results)

        return all_results

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file {file_path}: {str(e)}")
        return []
    except Exception as e:
        print(f"Error processing file {file_path}: {str(e)}")
        return []

def save_to_csv(data: List[Dict[str, str]], output_file: str):
    """
    Save extracted data to CSV file.
    """
    if not data:
        print("No data to save")
        return

    fieldnames = ['id_bn', 'id_bn_full', 'id_omnis_src', 'id_omnis']

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"Successfully saved data to {output_file}")

    except Exception as e:
        print(f"Error saving CSV file: {str(e)}")

def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='Process JSON files containing MARC records')
    parser.add_argument('pattern', help='File pattern to match JSON files (e.g., "bn_*.json")')
    parser.add_argument('--input-dir', default='.', help='Input directory containing JSON files (default: current directory)')
    parser.add_argument('--output', default='marc_fields_export.csv', help='Output CSV file name (default: marc_fields_export.csv)')
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()

    # Create full path pattern
    file_pattern = os.path.join(args.input_dir, args.pattern)

    # Find matching files
    matching_files = glob.glob(file_pattern)

    if not matching_files:
        print(f"No files found matching pattern: {args.pattern}")
        return

    print(f"Found {len(matching_files)} matching files")

    # Process all matching JSON files
    all_results = []
    records_processed = 0
    records_with_network = 0

    for file_path in matching_files:
        print(f"Processing {os.path.basename(file_path)}...")

        results = process_json_file(file_path)
        all_results.extend(results)

        records_processed += 1
        if results:
            records_with_network += 1

        print(f"Extracted {len(results)} entries from {os.path.basename(file_path)}")

    # Save all results to CSV
    save_to_csv(all_results, args.output)
    print(f"\nSummary:")
    print(f"Total files processed: {len(matching_files)}")
    print(f"Total records processed: {records_processed}")
    print(f"Records with 48OMNIS_NETWORK: {records_with_network}")
    print(f"Total entries in output: {len(all_results)}")

if __name__ == '__main__':
    main()
