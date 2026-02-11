"""
Code Sight - Packaging Script

Creates a portable bundle of the Code Sight framework for sharing
across different Antigravity workspaces and projects.

Usage:
    python code_sight/package_module.py

Output:
    code_sight_bundle.zip - Contains all necessary files for portability
"""

import os
import zipfile
from pathlib import Path
from datetime import datetime

# Define the files to include in the bundle
BUNDLE_FILES = [
    "__init__.py",
    "core.py",
    "server.py",
    "client.ts",
    "demo_pinn_integration.py",
    "README.md",
    "IMPLEMENTATION_SUMMARY.md",
    "PORTABILITY_GUIDE.md"
]

def create_bundle(output_path: str = "code_sight_bundle.zip"):
    """
    Create a zip bundle of the Code Sight framework.
    
    Args:
        output_path: Path where the zip file will be created
    """
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Output path relative to project root
    output_file = project_root / output_path
    
    print("=" * 60)
    print("Code Sight - Packaging Script")
    print("=" * 60)
    print(f"Source Directory: {script_dir}")
    print(f"Output File: {output_file}")
    print()
    
    # Create the zip file
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_name in BUNDLE_FILES:
            file_path = script_dir / file_name
            
            if not file_path.exists():
                print(f"WARNING: {file_name} not found, skipping...")
                continue
            
            # Add file to zip with relative path
            arcname = f"code_sight/{file_name}"
            zipf.write(file_path, arcname)
            
            # Get file size
            size_kb = file_path.stat().st_size / 1024
            print(f"[OK] Added: {file_name} ({size_kb:.2f} KB)")
    
    # Get bundle size
    bundle_size_kb = output_file.stat().st_size / 1024
    
    print()
    print("=" * 60)
    print(f"[SUCCESS] Bundle created successfully!")
    print(f"[FILE] {output_file}")
    print(f"[SIZE] {bundle_size_kb:.2f} KB")
    print(f"[TIME] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    print("Next Steps:")
    print("1. Transfer code_sight_bundle.zip to your target workspace")
    print("2. Extract: unzip code_sight_bundle.zip")
    print("3. Install dependencies: pip install numpy websockets")
    print("4. Run demo: python code_sight/demo_pinn_integration.py --mode first_light")
    print()
    print("For detailed integration instructions, see:")
    print("  code_sight/PORTABILITY_GUIDE.md")
    print()
    
    return output_file

def verify_bundle(bundle_path: str = "code_sight_bundle.zip"):
    """
    Verify the contents of the created bundle.
    
    Args:
        bundle_path: Path to the bundle zip file
    """
    project_root = Path(__file__).parent.parent
    bundle_file = project_root / bundle_path
    
    if not bundle_file.exists():
        print(f"[ERROR] Bundle not found: {bundle_file}")
        return False
    
    print()
    print("=" * 60)
    print("Bundle Verification")
    print("=" * 60)
    
    with zipfile.ZipFile(bundle_file, 'r') as zipf:
        file_list = zipf.namelist()
        
        print(f"Total files: {len(file_list)}")
        print()
        print("Contents:")
        for file_name in sorted(file_list):
            info = zipf.getinfo(file_name)
            size_kb = info.file_size / 1024
            compressed_kb = info.compress_size / 1024
            ratio = (1 - info.compress_size / info.file_size) * 100 if info.file_size > 0 else 0
            print(f"  {file_name}")
            print(f"    Size: {size_kb:.2f} KB | Compressed: {compressed_kb:.2f} KB | Ratio: {ratio:.1f}%")
        
        # Check for required files
        print()
        print("Required Files Check:")
        required = [f"code_sight/{f}" for f in BUNDLE_FILES]
        for req_file in required:
            if req_file in file_list:
                print(f"  [OK] {req_file}")
            else:
                print(f"  [MISSING] {req_file}")
    
    print("=" * 60)
    print()
    return True

if __name__ == "__main__":
    # Create the bundle
    bundle_path = create_bundle()
    
    # Verify the bundle
    verify_bundle()
    
    print("[COMPLETE] Packaging complete! Code Sight is ready for portability.")
