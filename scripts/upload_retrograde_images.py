#!/usr/bin/env python3
"""
Script to upload PNG files from data/retrograde_svgs directory to Cloudflare R2 bucket.

This script:
1. Recursively searches for PNG files in data/retrograde_svgs
2. Uploads each file to the Cloudflare R2 bucket
3. Preserves the directory structure in the bucket
4. Skips files that already exist in the bucket (optional)
5. Provides progress bar for uploads

Credentials are loaded from:
1. Environment variables: R2_ENDPOINT, R2_BUCKET_NAME, R2_ACCESS_KEY, R2_SECRET_KEY
2. Config file: ~/.starloom/r2_config.json or config/r2_credentials.json
"""

import os
import sys
import glob
import json
import boto3
from botocore.exceptions import ClientError
from tqdm import tqdm
import mimetypes
from pathlib import Path

# Default values for Cloudflare R2 configuration
DEFAULT_R2_ENDPOINT = "https://d3e407078ac178586d111c0f955f4847.r2.cloudflarestorage.com"
DEFAULT_BUCKET_NAME = "retrograde-observer-images"

# Local directory containing the PNG files
SOURCE_DIR = "data/retrograde_svgs"

def load_credentials():
    """
    Load R2 credentials from environment variables or config file.
    Returns a dictionary with endpoint, bucket_name, access_key, and secret_key.
    """
    # Try to load from environment variables first
    credentials = {
        "endpoint": os.environ.get("R2_ENDPOINT"),
        "bucket_name": os.environ.get("R2_BUCKET_NAME"),
        "access_key": os.environ.get("R2_ACCESS_KEY"),
        "secret_key": os.environ.get("R2_SECRET_KEY"),
    }
    
    # If any credential is missing, try to load from config file
    if None in credentials.values():
        # Check ~/.starloom/r2_config.json first
        home_config = Path.home() / ".starloom" / "r2_config.json"
        # Then check project config/r2_credentials.json
        project_config = Path("config") / "r2_credentials.json"
        
        config_file = None
        if home_config.exists():
            config_file = home_config
        elif project_config.exists():
            config_file = project_config
        
        if config_file:
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                    for key in credentials:
                        if credentials[key] is None and key in config:
                            credentials[key] = config[key]
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading config file {config_file}: {e}", file=sys.stderr)
    
    # Set defaults for endpoint and bucket_name if still missing
    if not credentials["endpoint"]:
        credentials["endpoint"] = DEFAULT_R2_ENDPOINT
    if not credentials["bucket_name"]:
        credentials["bucket_name"] = DEFAULT_BUCKET_NAME
    
    # Verify we have the minimum required credentials
    missing = []
    for key in ["access_key", "secret_key"]:
        if not credentials[key]:
            missing.append(key)
    
    if missing:
        missing_str = ", ".join(missing)
        print(f"ERROR: Missing required credential(s): {missing_str}", file=sys.stderr)
        print("Please set the following environment variables:", file=sys.stderr)
        print("  R2_ACCESS_KEY - Your Cloudflare R2 Access Key ID", file=sys.stderr)
        print("  R2_SECRET_KEY - Your Cloudflare R2 Secret Access Key", file=sys.stderr)
        print("\nOr create a config file at one of these locations:", file=sys.stderr)
        print(f"  {home_config}", file=sys.stderr)
        print(f"  {project_config}", file=sys.stderr)
        print("\nConfig file format:", file=sys.stderr)
        print('  {"access_key": "YOUR_ACCESS_KEY", "secret_key": "YOUR_SECRET_KEY"}', file=sys.stderr)
        sys.exit(1)
    
    return credentials

def get_s3_client(credentials):
    """Create and return an S3 client configured for Cloudflare R2."""
    return boto3.client(
        's3',
        endpoint_url=credentials["endpoint"],
        aws_access_key_id=credentials["access_key"],
        aws_secret_access_key=credentials["secret_key"]
    )

def object_exists(s3_client, bucket, key):
    """Check if an object exists in the bucket."""
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        # If the head_object call fails, the object doesn't exist
        return False

def upload_file(s3_client, file_path, bucket, key, skip_existing=True):
    """Upload a file to the R2 bucket."""
    # Check if file already exists in bucket
    if skip_existing and object_exists(s3_client, bucket, key):
        return False  # File exists, skip upload
    
    # Get content type based on file extension
    content_type = mimetypes.guess_type(file_path)[0]
    extra_args = {}
    if content_type:
        extra_args['ContentType'] = content_type
    
    # Upload the file
    try:
        s3_client.upload_file(
            file_path, 
            bucket, 
            key,
            ExtraArgs=extra_args
        )
        return True  # Upload successful
    except ClientError as e:
        print(f"Error uploading {file_path}: {e}", file=sys.stderr)
        return False

def main():
    """Main function to find and upload PNG files."""
    # Load credentials
    credentials = load_credentials()
    
    # Initialize S3 client
    s3_client = get_s3_client(credentials)
    
    # Find all PNG files in the source directory
    pattern = os.path.join(SOURCE_DIR, "**", "*.png")
    png_files = glob.glob(pattern, recursive=True)
    
    # Check if we found any files
    if not png_files:
        print(f"No PNG files found in {SOURCE_DIR}")
        return
    
    print(f"Found {len(png_files)} PNG files to upload")
    
    # Upload files with progress bar
    uploaded_count = 0
    skipped_count = 0
    
    with tqdm(total=len(png_files), desc="Uploading") as pbar:
        for file_path in png_files:
            # Create key that preserves directory structure
            relative_path = os.path.relpath(file_path, start=SOURCE_DIR)
            key = relative_path
            
            # Upload the file
            result = upload_file(s3_client, file_path, credentials["bucket_name"], key, skip_existing=True)
            
            if result:
                uploaded_count += 1
            else:
                skipped_count += 1
                
            pbar.update(1)
    
    print(f"Upload complete: {uploaded_count} files uploaded, {skipped_count} files skipped")

if __name__ == "__main__":
    main() 