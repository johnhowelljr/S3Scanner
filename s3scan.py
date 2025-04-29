#!/usr/bin/env python3
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import sys
import socket
import ssl

def scan_bucket(bucket_name):
    """Scan an S3 bucket using just HTTP protocol"""
    url = f"https://{bucket_name}.s3.amazonaws.com/"
    
    try:
        # Set a timeout to avoid hanging on slow responses
        context = ssl.create_default_context()
        response = urllib.request.urlopen(url, timeout=10, context=context)
        
        # If we get here, the bucket exists and is accessible
        if response.status == 200:
            try:
                # Parse XML response to get bucket contents
                content = response.read()
                root = ET.fromstring(content)
                
                # Extract files from XML
                files = []
                # Look for Contents tags within the XML
                namespace = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
                for item in root.findall(".//s3:Contents", namespace):
                    key = item.find("s3:Key", namespace).text
                    size = item.find("s3:Size", namespace).text
                    files.append(f"  {key} ({size} bytes)")
                
                return {
                    "status": "open",
                    "name": bucket_name,
                    "contents": files,
                    "count": len(files)
                }
            except ET.ParseError:
                # If we can't parse XML but got a 200 response, the bucket might still be open
                return {
                    "status": "open",
                    "name": bucket_name,
                    "contents": ["  (Unable to parse bucket contents)"],
                    "count": 0
                }
    
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return {"status": "exists_access_denied", "name": bucket_name}
        elif e.code == 404:
            return {"status": "nonexistent", "name": bucket_name}
        else:
            return {"status": f"error_{e.code}", "name": bucket_name}
    
    except (urllib.error.URLError, socket.timeout, ssl.SSLError) as e:
        return {"status": "error", "name": bucket_name, "error": str(e)}

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <wordlist_file>")
        sys.exit(1)
    
    wordlist_file = sys.argv[1]
    
    try:
        with open(wordlist_file, 'r') as f:
            wordlist = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Wordlist file '{wordlist_file}' not found.")
        sys.exit(1)
    
    print(f"Loaded {len(wordlist)} potential bucket names. Starting scan...")
    
    open_buckets = 0
    for bucket_name in wordlist:
        print(f"Scanning: {bucket_name}", end="\r")
        result = scan_bucket(bucket_name)
        
        if result['status'] == 'open':
            open_buckets += 1
            print(f"\n[OPEN] s3://{result['name']} - {result['count']} objects found")
            if result['contents']:
                for item in result['contents']:
                    print(item)
        elif result['status'] == 'exists_access_denied':
            print(f"\n[EXISTS BUT PROTECTED] s3://{result['name']}")
        elif result['status'].startswith('error'):
            error_msg = result.get('error', result['status'])
            print(f"\n[ERROR] s3://{result['name']} - {error_msg}")
    
    print(f"\nScan complete. Found {open_buckets} open buckets.")

if __name__ == "__main__":
    main()
