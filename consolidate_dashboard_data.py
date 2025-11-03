import json
import glob
import os
from pathlib import Path
from datetime import datetime

def consolidate_dashboard_data():
    """
    Consolidate data from all agent artifacts into a single dashboard JSON file.
    """
    # Define the artifacts directory
    artifacts_dir = Path("artifacts")
    
    # Initialize the consolidated data structure
    consolidated_data = {
        "timestamp": datetime.now().isoformat(),
        "agents": {
            "lici": {},
            "wherex": {},
            "senegocia": {},
            "meta": {}
        },
        "summary": {
            "total_ofertas": 0,
            "total_keywords": 0,
            "total_files_processed": 0
        }
    }
    
    # Define agent prefixes
    agent_prefixes = {
        "lici": "lici_",
        "wherex": "wherex_",
        "senegocia": "senegocia_",
        "meta": "meta_"
    }
    
    # Process each agent's JSON files
    for agent_name, prefix in agent_prefixes.items():
        pattern = str(artifacts_dir / f"{prefix}*.json")
        json_files = glob.glob(pattern)
        
        agent_data = []
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    agent_data.append({
                        "file": os.path.basename(json_file),
                        "data": data
                    })
                    consolidated_data["summary"]["total_files_processed"] += 1
                    
                    # Update summary statistics
                    if isinstance(data, dict):
                        if "ofertas" in data:
                            consolidated_data["summary"]["total_ofertas"] += len(data["ofertas"])
                        if "keywords" in data:
                            consolidated_data["summary"]["total_keywords"] += len(data["keywords"])
            except Exception as e:
                print(f"Error reading {json_file}: {e}")
        
        consolidated_data["agents"][agent_name] = {
            "file_count": len(json_files),
            "files": agent_data
        }
    
    # Save consolidated data
    output_file = artifacts_dir / "dashboard_data.json"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(consolidated_data, f, indent=2, ensure_ascii=False)
    
    print(f"Dashboard data consolidated successfully at {output_file}")
    print(f"Total files processed: {consolidated_data['summary']['total_files_processed']}")
    print(f"Total ofertas: {consolidated_data['summary']['total_ofertas']}")
    print(f"Total keywords: {consolidated_data['summary']['total_keywords']}")

if __name__ == "__main__":
    consolidate_dashboard_data()
