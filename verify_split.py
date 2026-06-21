import os
import json
import re

dest_root = "/Users/dr.ajayshukla/endo_masterapp/williams_2024_chapters"
williams_json_path = "/Users/dr.ajayshukla/endo_masterapp/noupload/wil/williams2024.pdf_by_PaddleOCR-VL-1.6.json"
endo_json_path = "/Users/dr.ajayshukla/endo_masterapp/noupload/endo2021/endo2021.pdf_by_PaddleOCR-VL-1.6.json"
endo2015_json_path = "/Users/dr.ajayshukla/endo_masterapp/noupload/endo2015/endo2015.pdf_by_PaddleOCR-VL-1.6.json"

def main():
    print("Running verification script (unified flat structure)...")
    
    # 1. Load original JSON files
    with open(williams_json_path, "r", encoding="utf-8") as f:
        williams_orig = json.load(f)
    with open(endo_json_path, "r", encoding="utf-8") as f:
        endo_orig = json.load(f)
    with open(endo2015_json_path, "r", encoding="utf-8") as f:
        endo2015_orig = json.load(f)
        
    total_expected_pages = len(williams_orig) + len(endo_orig) + len(endo2015_orig)
    
    # Calculate unique image URLs
    expected_image_urls = set()
    for p in williams_orig + endo_orig + endo2015_orig:
        images = p['markdown'].get('images', {})
        for remote_url in images.values():
            expected_image_urls.add(remote_url)
            
    print(f"Expected totals: {len(williams_orig)} Williams pages, {len(endo_orig)} Endo2021 pages, {len(endo2015_orig)} Endo2015 pages.")
    print(f"Expected unique image URLs: {len(expected_image_urls)}")
    
    # 2. Scan flat destination root
    if not os.path.exists(dest_root):
        print(f"ERROR: Destination root {dest_root} does not exist!")
        return
        
    all_files = os.listdir(dest_root)
    
    williams_json_files = sorted([f for f in all_files if f.startswith("williams2024_") and f.endswith(".json")])
    williams_md_files = sorted([f for f in all_files if f.startswith("williams2024_") and f.endswith(".md")])
    
    endo_json_files = sorted([f for f in all_files if f.startswith("endo2021_") and f.endswith(".json")])
    endo_md_files = sorted([f for f in all_files if f.startswith("endo2021_") and f.endswith(".md")])
    
    endo2015_json_files = sorted([f for f in all_files if f.startswith("endo2015_") and f.endswith(".json")])
    endo2015_md_files = sorted([f for f in all_files if f.startswith("endo2015_") and f.endswith(".md")])
    
    print(f"Found {len(williams_json_files)} Williams JSON files, {len(williams_md_files)} Williams MD files.")
    print(f"Found {len(endo_json_files)} Endo2021 JSON files, {len(endo_md_files)} Endo2021 MD files.")
    print(f"Found {len(endo2015_json_files)} Endo2015 JSON files, {len(endo2015_md_files)} Endo2015 MD files.")
    
    if len(williams_json_files) != 49 or len(williams_md_files) != 49:
        print(f"ERROR: Expected 49 Williams splits, found {len(williams_json_files)}")
    if len(endo_json_files) != 43 or len(endo_md_files) != 43:
        # Note: Since the duplicate match was ignored, there are 43 matched chapters in endo2021
        print(f"ERROR: Expected 43 Endo2021 splits, found {len(endo_json_files)}")
    if len(endo2015_json_files) != 4 or len(endo2015_md_files) != 4:
        print(f"ERROR: Expected 4 Endo2015 splits, found {len(endo2015_json_files)}")
        
    total_split_pages = 0
    williams_split_pages = 0
    endo_split_pages = 0
    
    williams_pages_list = []
    endo_pages_list = []
    has_remote_urls = False
    
    for jfile in williams_json_files:
        with open(os.path.join(dest_root, jfile), "r", encoding="utf-8") as f:
            chapter_pages = json.load(f)
        williams_split_pages += len(chapter_pages)
        williams_pages_list.extend(chapter_pages)
        
    for jfile in endo_json_files:
        with open(os.path.join(dest_root, jfile), "r", encoding="utf-8") as f:
            chapter_pages = json.load(f)
        endo_split_pages += len(chapter_pages)
        endo_pages_list.extend(chapter_pages)
        
    endo2015_split_pages = 0
    endo2015_pages_list = []
    for jfile in endo2015_json_files:
        with open(os.path.join(dest_root, jfile), "r", encoding="utf-8") as f:
            chapter_pages = json.load(f)
        endo2015_split_pages += len(chapter_pages)
        endo2015_pages_list.extend(chapter_pages)
        
    total_split_pages = williams_split_pages + endo_split_pages + endo2015_split_pages
    
    # Check MD files for remote URLs
    for mfile in williams_md_files + endo_md_files + endo2015_md_files:
        with open(os.path.join(dest_root, mfile), "r", encoding="utf-8") as f:
            content = f.read()
        if "bcebos.com" in content:
            print(f"WARNING: Remote image URLs detected in: {mfile}")
            has_remote_urls = True
            
    # Verify global imgs directory
    global_imgs_dir = os.path.join(dest_root, "imgs")
    total_split_images = 0
    if os.path.exists(global_imgs_dir):
        total_split_images = len([
            f for f in os.listdir(global_imgs_dir)
            if f.lower().endswith((".jpg", ".png", ".jpeg"))
        ])
        
    print("\n--- Summary ---")
    print(f"Williams pages split: {williams_split_pages} (Expected: {len(williams_orig)})")
    print(f"Endo2021 pages split: {endo_split_pages} (Expected: {len(endo_orig)})")
    print(f"Endo2015 pages split: {endo2015_split_pages} (Expected: {len(endo2015_orig)})")
    print(f"Total split pages: {total_split_pages} (Expected: {total_expected_pages})")
    print(f"Total split images: {total_split_images} (Expected: {len(expected_image_urls)})")
    
    errors = []
    if williams_split_pages != len(williams_orig):
        errors.append(f"Williams page count mismatch: split {williams_split_pages} vs original {len(williams_orig)}")
    if endo_split_pages != len(endo_orig):
        errors.append(f"Endo2021 page count mismatch: split {endo_split_pages} vs original {len(endo_orig)}")
    if endo2015_split_pages != len(endo2015_orig):
        errors.append(f"Endo2015 page count mismatch: split {endo2015_split_pages} vs original {len(endo2015_orig)}")
    if total_split_images != len(expected_image_urls):
        errors.append(f"Image count mismatch: downloaded {total_split_images} vs expected unique {len(expected_image_urls)}")
    if has_remote_urls:
        errors.append("One or more MD files still contain remote image URLs.")
        
    # Check page content order for Williams
    for idx in range(min(len(williams_orig), len(williams_pages_list))):
        if williams_orig[idx]['inputImage'] != williams_pages_list[idx]['inputImage']:
            errors.append(f"Williams page mismatch at index {idx}")
            break
            
    # Check page content order for Endo2021
    for idx in range(min(len(endo_orig), len(endo_pages_list))):
        if endo_orig[idx]['inputImage'] != endo_pages_list[idx]['inputImage']:
            errors.append(f"Endo2021 page mismatch at index {idx}")
            break
            
    # Check page content order for Endo2015
    for idx in range(min(len(endo2015_orig), len(endo2015_pages_list))):
        if endo2015_orig[idx]['inputImage'] != endo2015_pages_list[idx]['inputImage']:
            errors.append(f"Endo2015 page mismatch at index {idx}")
            break
            
    if errors:
        print("\nVerification FAILED with errors:")
        for err in errors:
            print(f" - {err}")
    else:
        print("\nVerification PASSED successfully! All checks match perfectly.")

if __name__ == "__main__":
    main()
