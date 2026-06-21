import os
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import shutil

dest_root = "/Users/dr.ajayshukla/endo_masterapp/williams_2024_chapters"

# --- Williams 2024 Config ---
williams_json_path = "/Users/dr.ajayshukla/endo_masterapp/noupload/wil/williams2024.pdf_by_PaddleOCR-VL-1.6.json"
williams_md_path = "/Users/dr.ajayshukla/endo_masterapp/noupload/wil/williams2024.pdf_by_PaddleOCR-VL-1.6.md"
williams_chapter_configs = [
    (0, "Front Matter", 0, None),
    (1, "Principles of Endocrinology", 12, "# Principles of Endocrinology"),
    (2, "Principles of Hormone Action", 25, "# Principles of Hormone Action"),
    (3, "Genetics of Endocrinology", 59, "# Genetics of Endocrinology"),
    (4, "Laboratory Techniques for Recognition of Endocrine Disorders", 84, "# Laboratory Techniques for Recognition of Endocrine Disorders"),
    (5, "Neuroendocrinology", 119, "# Neuroendocrinology"),
    (6, "Pituitary Physiology and Diagnostic Evaluation", 213, "# Pituitary Physiology and Diagnostic Evaluation"),
    (7, "Pituitary Adenomas and Masses", 279, "# Pituitary Adenomas and Masses"),
    (8, "Posterior Pituitary", 296, "# Posterior Pituitary"),
    (9, "Thyroid Pathophysiology and Diagnostic Evaluation", 412, "# Thyroid Pathophysiology and Diagnostic Evaluation"),
    (10, "Hyperthyroid Disorders", 450, "# Hyperthyroid Disorders"),
    (11, "Hypothyroidism and Thyroiditis", 503, "# Hypothyroidism and Thyroiditis"),
    (12, "Nontoxic Diffuse Goiter, Nodular Thyroid Disorders, and Thyroid Malignancies", 541, "# Nontoxic Diffuse Goiter, Nodular Thyroid Disorders, and Thyroid Malignancies"),
    (13, "The Adrenal Cortex", 596, "# The Adrenal Cortex"),
    (14, "Endocrine Hypertension", 672, "# Endocrine Hypertension"),
    (15, "Physiology and Pathology of the Female Reproductive Axis", 711, "# Physiology and Pathology of the Female Reproductive Axis"),
    (16, "Hormonal Contraception", 791, "# Hormonal Contraception"),
    (17, "Testicular Disorders", 826, "# Testicular Disorders"),
    (18, "Sexual Function and Dysfunction", 935, "# Sexual Function and Dysfunction"),
    (19, "Endocrine Changes in Pregnancy", 981, "# Endocrine Changes in Pregnancy"),
    (20, "Endocrinology of Fetal Development", 1004, "# Endocrinology of Fetal Development"),
    (21, "Differences of Sex Development", 1062, "# Differences of Sex Development"),
    (22, "Normal and Aberrant Growth in Children", 1147, "# Normal and Aberrant Growth in Children"),
    (23, "Physiology and Disorders of Puberty", 1273, "# Physiology and Disorders of Puberty"),
    (24, "Transgender Endocrinology", 1424, "# Transgender Endocrinology"),
    (25, "Hormones and Athletic Performance", 1441, "# Hormones and Athletic Performance"),
    (26, "Endocrine Function and Aging", 1460, "# Endocrine Function and Aging"),
    (27, "Hormones and Disorders of Mineral Metabolism", 1492, "# Hormones and Disorders of Mineral Metabolism"),
    (28, "Endocrine Functions of Bone", 1569, "# Endocrine Functions of Bone"),
    (29, "Osteoporosis: Basic and Clinical Aspects", 1576, "# Osteoporosis: Basic and Clinical Aspects"),
    (30, "Rickets and Osteomalacia", 1631, "# Rickets and Osteomalacia"),
    (31, "Kidney Stones", 1657, "# Kidney Stones"),
    (32, "Physiology of Insulin Secretion", 1680, "# Physiology of Insulin Secretion"),
    (33, "Pathophysiology of Type 2 Diabetes Mellitus", 1696, "# Pathophysiology of Type 2 Diabetes Mellitus"),
    (34, "Therapeutics of Type 2 Diabetes Mellitus", 1729, "# Therapeutics of Type 2 Diabetes Mellitus"),
    (35, "Type 1 Diabetes Mellitus", 1776, "# Type 1 Diabetes Mellitus"),
    (36, "Digitized Approaches to Diabetes Diagnostics and Therapeutics", 1830, "# Digitized Approaches to Diabetes Diagnostics and Therapeutics"),
    (37, "Monogenic Diabetes", 1872, "# Monogenic Diabetes"),
    (38, "Complications of Diabetes Mellitus", 1888, "# Complications of Diabetes Mellitus"),
    (39, "Hypoglycemia", 2027, "# ANA MARÍA ARBELÁEZ AND MICHAEL R. RICKELS"),
    (40, "Obesity and Neuroendocrine Control of Energy Stores", 2066, "# Obesity and Neuroendocrine Control of Energy Stores"),
    (41, "Disorders of Lipoprotein Metabolism", 2092, "# Disorders of Lipoprotein Metabolism"),
    (42, "Endocrine Neoplasia Syndromes", 2152, "# Endocrine Neoplasia Syndromes"),
    (43, "Neuroendocrine Tumors and Disorders", 2206, "# Neuroendocrine Tumors and Disorders"),
    (44, "The Immunoendocrinopathy Syndromes", 2226, "# The Immunoendocrinopathy Syndromes"),
    (45, "Endocrinology of Cancer Management and Survivorship", 2244, "# Endocrinology of Cancer Management and Survivorship"),
    (46, "Endocrinology of HIVAIDS", 2270, "# Endocrinology of HIV/AIDS"),
    (47, "Acute and Chronic COVID19 and the Endocrine System", 2296, "# Acute and Chronic COVID-19 and the Endocrine System"),
    (48, "Endocrine Disorders of Critical Illness", 2309, "# Endocrine Disorders of Critical Illness"),
]

# --- Endo 2021 Config ---
endo_json_path = "/Users/dr.ajayshukla/endo_masterapp/noupload/endo2021/endo2021.pdf_by_PaddleOCR-VL-1.6.json"
endo_md_path = "/Users/dr.ajayshukla/endo_masterapp/noupload/endo2021/endo2021.pdf_by_PaddleOCR-VL-1.6.md"

# --- Endo 2015 Config ---
endo2015_json_path = "/Users/dr.ajayshukla/endo_masterapp/noupload/endo2015/endo2015.pdf_by_PaddleOCR-VL-1.6.json"
endo2015_md_path = "/Users/dr.ajayshukla/endo_masterapp/noupload/endo2015/endo2015.pdf_by_PaddleOCR-VL-1.6.md"
endo2015_chapter_configs = [
    (1, "Front Matter", 0, None),
    (2, "Laboratory Reference Ranges", 6, "# Laboratory Reference Ranges"),
    (3, "Questions", 10, "## ENDOCRINE SELF-ASSESSMENT PROGRAM 2015"),
    (4, "Answers", 81, "# ANSWERS")
]


def clean_label(label):
    name = label
    if name.startswith("#"):
        name = name.lstrip("#").strip()
    if ":" in name:
        name = name.split(":", 1)[1].strip()
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9__]", "", name)
    name = re.sub(r"_+", "_", name)
    return name.strip('_')

def download_image(url, dest_path):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    retries = 3
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                with open(dest_path, "wb") as f:
                    f.write(response.read())
            return True
        except Exception as e:
            if attempt == retries - 1:
                print(f"Failed download {url} to {dest_path}: {e}")
                return False
            time.sleep(1.5 * (attempt + 1))
    return False

def split_williams2024(pages, md_lines, global_imgs_dir, download_queue, unique_urls):
    print("\n--- Slicing Williams 2024 ---")
    chapter_line_starts = []
    curr_idx = 0
    for i, config in enumerate(williams_chapter_configs):
        prefix, label, json_start, heading = config
        if heading is None:
            chapter_line_starts.append(0)
        else:
            found = False
            for line_idx in range(curr_idx, len(md_lines)):
                if md_lines[line_idx].strip() == heading:
                    chapter_line_starts.append(line_idx)
                    curr_idx = line_idx + 1
                    found = True
                    break
            if not found:
                raise ValueError(f"Could not find heading {heading} in Williams starting from line {curr_idx}")

    for i, config in enumerate(williams_chapter_configs):
        prefix, label, json_start, heading = config
        file_base = f"williams2024_chapter_{prefix:02d}_{clean_label(label)}"
        
        # MD Slicing
        start_line = chapter_line_starts[i]
        if i + 1 < len(williams_chapter_configs):
            end_line = chapter_line_starts[i+1]
            sliced_md_lines = md_lines[start_line:end_line]
        else:
            sliced_md_lines = md_lines[start_line:]
            
        md_text = "".join(sliced_md_lines)
        if prefix == 39:
            md_text = "# Hypoglycemia\n\n" + md_text
            
        # JSON Slicing
        start_page = json_start
        if i + 1 < len(williams_chapter_configs):
            end_page = williams_chapter_configs[i+1][2]
            chapter_pages = pages[start_page:end_page]
        else:
            chapter_pages = pages[start_page:]
            
        # Collect images for this chapter
        for p in chapter_pages:
            images = p['markdown'].get('images', {})
            for local_path, remote_url in images.items():
                basename = os.path.basename(local_path)
                dest_path = os.path.join(global_imgs_dir, basename)
                if remote_url not in unique_urls:
                    unique_urls.add(remote_url)
                    download_queue.append((remote_url, dest_path))
            
        # Localize remote image URLs in markdown text
        pattern = r'https://[a-zA-Z0-9.-]+\.bcebos\.com/[^"\s>]+?/imgs/([^"\s>?]+)(?:\?[^"\s>]*)?'
        localized_md_text = re.sub(pattern, r'imgs/\1', md_text)
        
        # Write flat chapter files
        with open(os.path.join(dest_root, f"{file_base}.md"), "w", encoding="utf-8") as f:
            f.write(localized_md_text)
            
        with open(os.path.join(dest_root, f"{file_base}.json"), "w", encoding="utf-8") as f:
            json.dump(chapter_pages, f, indent=2, ensure_ascii=False)
            
        print(f"Created Williams split: {file_base} ({len(chapter_pages)} pages)")

def split_endo2021(pages, md_lines, global_imgs_dir, download_queue, unique_urls):
    print("\n--- Slicing Endo 2021 ---")
    
    # 1. Match H1 lines to split MD file
    h1s = []
    for idx, line in enumerate(md_lines):
        if line.startswith("# ") and not line.startswith("#   ") and not line.startswith("##"):
            h1s.append((idx, line.strip()))
            
    # 2. Map H1s to page indices in JSON, keeping order
    mappings = []
    seen_pages = set()
    for line_idx, heading in h1s:
        clean_heading = heading[2:].strip()
        found_page = -1
        # Search JSON
        for page_idx, p in enumerate(pages):
            p_text = p['markdown']['text']
            if clean_heading in p_text:
                found_page = page_idx
                break
        if found_page == -1:
            short_heading = clean_heading[:20]
            for page_idx, p in enumerate(pages):
                p_text = p['markdown']['text']
                if short_heading in p_text:
                    found_page = page_idx
                    break
        if found_page != -1:
            if found_page in seen_pages:
                # Duplicate page match, ignore to maintain strict order
                continue
            seen_pages.add(found_page)
            mappings.append((heading, line_idx, found_page))
            
    # Ensure mappings are sorted by page index
    mappings.sort(key=lambda x: x[2])
    
    for i, (heading, line_idx, page_idx) in enumerate(mappings):
        prefix_num = i + 1
        file_base = f"endo2021_chapter_{prefix_num:02d}_{clean_label(heading)}"
        
        # MD Slicing
        start_line = line_idx
        if i + 1 < len(mappings):
            end_line = mappings[i+1][1]
            sliced_md_lines = md_lines[start_line:end_line]
        else:
            sliced_md_lines = md_lines[start_line:]
            
        md_text = "".join(sliced_md_lines)
        
        # JSON Slicing
        start_page = page_idx
        if i + 1 < len(mappings):
            end_page = mappings[i+1][2]
            chapter_pages = pages[start_page:end_page]
        else:
            chapter_pages = pages[start_page:]
            
        # Collect images for this chapter
        for p in chapter_pages:
            images = p['markdown'].get('images', {})
            for local_path, remote_url in images.items():
                basename = os.path.basename(local_path)
                dest_path = os.path.join(global_imgs_dir, basename)
                if remote_url not in unique_urls:
                    unique_urls.add(remote_url)
                    download_queue.append((remote_url, dest_path))
                    
        # Localize remote image URLs in markdown text
        pattern = r'https://[a-zA-Z0-9.-]+\.bcebos\.com/[^"\s>]+?/imgs/([^"\s>?]+)(?:\?[^"\s>]*)?'
        localized_md_text = re.sub(pattern, r'imgs/\1', md_text)
        
        # Write flat chapter files
        with open(os.path.join(dest_root, f"{file_base}.md"), "w", encoding="utf-8") as f:
            f.write(localized_md_text)
            
        with open(os.path.join(dest_root, f"{file_base}.json"), "w", encoding="utf-8") as f:
            json.dump(chapter_pages, f, indent=2, ensure_ascii=False)
            
        print(f"Created Endo2021 split: {file_base} ({len(chapter_pages)} pages)")

def split_endo2015(pages, md_lines, global_imgs_dir, download_queue, unique_urls):
    print("\n--- Slicing Endo 2015 ---")
    chapter_line_starts = []
    curr_idx = 0
    for i, config in enumerate(endo2015_chapter_configs):
        prefix, label, json_start, heading = config
        if heading is None:
            chapter_line_starts.append(0)
        else:
            found = False
            for line_idx in range(curr_idx, len(md_lines)):
                if md_lines[line_idx].strip() == heading:
                    chapter_line_starts.append(line_idx)
                    curr_idx = line_idx + 1
                    found = True
                    break
            if not found:
                raise ValueError(f"Could not find heading {heading} in Endo 2015 starting from line {curr_idx}")

    for i, config in enumerate(endo2015_chapter_configs):
        prefix, label, json_start, heading = config
        file_base = f"endo2015_chapter_{prefix:02d}_{clean_label(label)}"
        
        # MD Slicing
        start_line = chapter_line_starts[i]
        if i + 1 < len(endo2015_chapter_configs):
            end_line = chapter_line_starts[i+1]
            sliced_md_lines = md_lines[start_line:end_line]
        else:
            sliced_md_lines = md_lines[start_line:]
            
        md_text = "".join(sliced_md_lines)
            
        # JSON Slicing
        start_page = json_start
        if i + 1 < len(endo2015_chapter_configs):
            end_page = endo2015_chapter_configs[i+1][2]
            chapter_pages = pages[start_page:end_page]
        else:
            chapter_pages = pages[start_page:]
            
        # Collect images for this chapter
        for p in chapter_pages:
            images = p['markdown'].get('images', {})
            for local_path, remote_url in images.items():
                basename = os.path.basename(local_path)
                dest_path = os.path.join(global_imgs_dir, basename)
                if remote_url not in unique_urls:
                    unique_urls.add(remote_url)
                    download_queue.append((remote_url, dest_path))
            
        # Localize remote image URLs in markdown text
        pattern = r'https://[a-zA-Z0-9.-]+\.bcebos\.com/[^"\s>]+?/imgs/([^"\s>?]+)(?:\?[^"\s>]*)?'
        localized_md_text = re.sub(pattern, r'imgs/\1', md_text)
        
        # Write flat chapter files
        with open(os.path.join(dest_root, f"{file_base}.md"), "w", encoding="utf-8") as f:
            f.write(localized_md_text)
            
        with open(os.path.join(dest_root, f"{file_base}.json"), "w", encoding="utf-8") as f:
            json.dump(chapter_pages, f, indent=2, ensure_ascii=False)
            
        print(f"Created Endo2015 split: {file_base} ({len(chapter_pages)} pages)")

def main():
    print("Loading source materials...")
    
    # Williams 2024
    with open(williams_json_path, "r", encoding="utf-8") as f:
        williams_pages = json.load(f)
    with open(williams_md_path, "r", encoding="utf-8") as f:
        williams_md_lines = f.readlines()
        
    # Endo 2021
    with open(endo_json_path, "r", encoding="utf-8") as f:
        endo_pages = json.load(f)
    with open(endo_md_path, "r", encoding="utf-8") as f:
        endo_md_lines = f.readlines()

    # Endo 2015
    with open(endo2015_json_path, "r", encoding="utf-8") as f:
        endo2015_pages = json.load(f)
    with open(endo2015_md_path, "r", encoding="utf-8") as f:
        endo2015_md_lines = f.readlines()

    # Clean up the output directory
    print("Cleaning up target directory...")
    if os.path.exists(dest_root):
        shutil.rmtree(dest_root)
    os.makedirs(dest_root, exist_ok=True)
    
    # Global images directory
    global_imgs_dir = os.path.join(dest_root, "imgs")
    os.makedirs(global_imgs_dir, exist_ok=True)
    
    download_queue = []
    unique_urls = set()
    
    # Run splitters
    split_williams2024(williams_pages, williams_md_lines, global_imgs_dir, download_queue, unique_urls)
    split_endo2021(endo_pages, endo_md_lines, global_imgs_dir, download_queue, unique_urls)
    split_endo2015(endo2015_pages, endo2015_md_lines, global_imgs_dir, download_queue, unique_urls)
    
    print(f"\nCollected {len(download_queue)} total unique image download tasks.")
    
    # Parallel downloading of images
    if download_queue:
        print("Starting image downloads in parallel...")
        start_time = time.time()
        success_count = 0
        with ThreadPoolExecutor(max_workers=25) as executor:
            future_to_task = {
                executor.submit(download_image, url, path): (url, path)
                for url, path in download_queue
            }
            for future in as_completed(future_to_task):
                url, path = future_to_task[future]
                try:
                    res = future.result()
                    if res:
                        success_count += 1
                except Exception as e:
                    print(f"Task exception on {url}: {e}")
        elapsed = time.time() - start_time
        print(f"\nDownload completed: {success_count}/{len(download_queue)} succeeded in {elapsed:.2f} seconds.")
    else:
        print("No images to download.")

if __name__ == "__main__":
    main()
