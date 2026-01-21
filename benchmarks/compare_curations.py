"""
Compare manual vs automated curation JSON files with specific fields as columns.
"""

import json
import pandas as pd
from pathlib import Path


def compare_curations():
    """Compare manual and automated JSON files and export to CSV."""
    
    print("Starting comparison...")
    
    # Define base paths
    manual_dir = Path("benchmarks/data/manual")
    automated_dir = Path("benchmarks/data/automated")
    output_dir = Path("benchmarks/results")
    
    # Define fields to compare
    fields_to_compare = [
        "contact",
        "description",
        "example",
        "homepage",
        "keywords",
        "name",
        "pattern",
        "publications",
        "uri_format"
    ]
    
    # Get all JSON files
    manual_files = list(manual_dir.glob("*.json"))
    print(f"Found {len(manual_files)} manual files")
    
    results = []
    
    # Compare each file
    for i, manual_file in enumerate(manual_files, 1):
        resource_id = manual_file.stem
        print(f"[{i}/{len(manual_files)}] Processing {resource_id}...", end=" ")
        
        auto_file = automated_dir / f"{resource_id}.json"
        
        # Skip if automated version doesn't exist
        if not auto_file.exists():
            print(f"SKIPPED (no automated version)")
            continue
        
        # Load both files
        with open(manual_file) as f:
            manual_outer = json.load(f)
        with open(auto_file) as f:
            automated_outer = json.load(f)
        
        # Extract the nested data (data is under the resource_id key)
        manual = manual_outer.get(resource_id, {})
        automated = automated_outer.get(resource_id, {})
        
        # Add manual row
        manual_row = {'Resource': resource_id, 'Source': 'Manual'}
        for field in fields_to_compare:
            manual_row[field] = manual.get(field)
        results.append(manual_row)
        
        # Add automated row
        auto_row = {'Resource': resource_id, 'Source': 'Automated'}
        for field in fields_to_compare:
            auto_row[field] = automated.get(field)
        results.append(auto_row)
        
        print("✓")
    
    print("\nCreating DataFrame...")
    # Create DataFrame and export
    columns = ['Resource', 'Source'] + fields_to_compare
    df = pd.DataFrame(results, columns=columns)
    
    print("Exporting to CSV...")
    output_path = output_dir / "comparison_results.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
    print(f"\n✓ Comparison complete!")
    print(f"✓ Compared {len(manual_files)} resources")
    print(f"✓ Results saved to: {output_path}")


if __name__ == "__main__":
    compare_curations()
