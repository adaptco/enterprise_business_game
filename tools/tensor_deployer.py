#!/usr/bin/env python3
"""
Tensor Deployer - Love.io Integration
Packages tensor slices into deployable LÖVE executables.
"""

import os
import sys
import shutil
import zipfile
import json
import argparse
from pathlib import Path

def create_love_file(source_dir: Path, output_path: Path, tensor_slice_path: Path = None):
    """Create a .love file from a source directory."""
    print(f"Packaging {source_dir} into {output_path}...")
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add all files in source_dir
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(source_dir)
                zf.write(file_path, arcname)
        
        # Inject tensor slice if provided
        if tensor_slice_path:
            print(f"Injecting tensor slice: {tensor_slice_path}")
            zf.write(tensor_slice_path, "tensor_slice.json")
            
    print(f"Created {output_path}")

def fuse_executable(love_path: Path, output_exe: Path, love_exe_path: Path = None):
    """Fuse .love file with love.exe to create a standalone executable."""
    if not love_exe_path or not love_exe_path.exists():
        print("⚠️  love.exe not found, skipping fusion.")
        return

    print(f"Fusing {love_path} with {love_exe_path} into {output_exe}...")
    
    with open(output_exe, 'wb') as out_f:
        # 1. Write love.exe
        with open(love_exe_path, 'rb') as love_f:
            out_f.write(love_f.read())
        
        # 2. Append .love file
        with open(love_path, 'rb') as zip_f:
            out_f.write(zip_f.read())
            
    print(f"Created standalone executable: {output_exe}")

def main():
    parser = argparse.ArgumentParser(description="Deploy Tensor Slices as LÖVE Executables")
    parser.add_argument("--source", default="loqer_room", help="Source directory for Love.io project")
    parser.add_argument("--slice", required=True, help="Path to tensor slice JSON")
    parser.add_argument("--output", default="dist/loqer_room.love", help="Output .love file path")
    parser.add_argument("--fuse", help="Path to love.exe for fusion (optional)")
    
    args = parser.parse_args()
    
    root = Path(".")
    source_dir = root / args.source
    slice_path = Path(args.slice)
    output_path = root / args.output
    
    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        sys.exit(1)
        
    if not slice_path.exists():
        print(f"❌ Tensor slice not found: {slice_path}")
        sys.exit(1)
        
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    create_love_file(source_dir, output_path, slice_path)
    
    if args.fuse:
        exe_path = output_path.with_suffix(".exe")
        fuse_executable(output_path, exe_path, Path(args.fuse))

if __name__ == "__main__":
    main()
