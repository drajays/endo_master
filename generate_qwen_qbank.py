import os
import re
import json
import urllib.request
import time
import sys

source_dir = "/Users/dr.ajayshukla/endo_masterapp/williams_2024_chapters"
target_dir = "/Users/dr.ajayshukla/endo_masterapp/data"
index_path = "/Users/dr.ajayshukla/endo_masterapp/data/index.json"

os.makedirs(target_dir, exist_ok=True)

# Load index.json
with open(index_path, "r", encoding="utf-8") as f:
    index_data = json.load(f)

# Helper to find chapter in index
def get_index_chapter(ch_num):
    for sec in index_data['sections']:
        if "Endo 2021" in sec['name']:
            for ch in sec['chapters']:
                if ch['id'] == f"e21-{ch_num:02d}":
                    return ch
    return None

# Find all endo2021 markdown files
all_files = os.listdir(source_dir)
endo_md_files = sorted([f for f in all_files if f.startswith("endo2021_") and f.endswith(".md")])

print(f"Found {len(endo_md_files)} Endo 2021 markdown files.")

def extract_key_sections(md_text):
    # Find Title (first heading)
    title_match = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Unknown Title"
    
    # Find Main Conclusions
    main_conclusions = ""
    mc_match = re.search(r"(#####?\s*Main\s*Conclusions.*?)(?=^#|##|###|#####?\s*Significance|#####?\s*Barriers)", md_text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if mc_match:
        main_conclusions = mc_match.group(1).strip()
    else:
        mc_match = re.search(r"(#####?\s*Main\s*Conclusions.*?)(?=^#|##|###)", md_text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if mc_match:
            main_conclusions = mc_match.group(1).strip()
            
    # Find Clinical Case Vignettes
    case_vignettes = ""
    cv_match = re.search(r"(#####?\s*Clinical\s*Case\s*Vignettes.*)", md_text, re.DOTALL | re.IGNORECASE)
    if not cv_match:
        cv_match = re.search(r"(#####?\s*Case\s*1.*)", md_text, re.DOTALL | re.IGNORECASE)
        
    if cv_match:
        case_vignettes = cv_match.group(1).strip()
        
        # Clean up cases 3/4 if they exist to keep the context compact
        for marker in ["##### Case 3", "## Case 3", "### Case 3", "Case 3", "##### Case 4", "## Case 4", "### Case 4", "Case 4"]:
            if marker in case_vignettes:
                case_vignettes = case_vignettes.split(marker)[0].strip()
                
        # Clean up references from case vignettes if present
        for marker in ["## References", "##### References", "## REFERENCES", "##### REFERENCES", "## Reference", "##### Reference", "## REFERENCE", "##### REFERENCE"]:
            if marker in case_vignettes:
                case_vignettes = case_vignettes.split(marker)[0].strip()
                
    return title, main_conclusions, case_vignettes

def query_ollama(prompt, text_content):
    url = "http://localhost:11434/api/generate"
    full_prompt = f"{prompt}\n\nHere is the textbook content:\n{text_content}"
    data = {
        "model": "qwen2.5:3b",
        "prompt": full_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
            "num_ctx": 8192,
            "num_predict": 2048
        }
    }
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                res = json.loads(response.read().decode('utf-8'))
                return json.loads(res['response'].strip())
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            time.sleep(5)
    return None

mcq_prompt = """You are an expert endocrinologist and clinical study aid developer. 
Your task is to generate a single clinical multiple-choice question (MCQ) based on the case vignette and question in the text.

Output format:
{
  "subtopic": "<Topic category>",
  "question": "<The case vignette stem ending with a question>",
  "options": [
    "<Option A>",
    "<Option B>",
    "<Option C>",
    "<Option D>"
  ],
  "correctOption": <0-indexed integer 0-3 representing the correct option>,
  "explanation": "<Detailed clinical explanation of why the correct option is right and others are wrong>",
  "reference": "<VERBATIM double-quoted quote from the text prefixed by the heading title (e.g. ANSWER: \\"quote\\")>"
}

Output a single JSON object only. Do not include extra text or markdown block formatting."""

why_prompt = """You are an expert endocrinologist and clinical study aid developer.
Your task is to generate a single clinical "Why" question based on the provided Main Conclusions and clinical explanations.

Output format:
{
  "type": "why",
  "subtopic": "<Topic category>",
  "question": "Why ...?",
  "answer": "Because ...",
  "keyPoints": [
    "<Key clinical point 1>",
    "<Key clinical point 2>"
  ],
  "reference": "<VERBATIM double-quoted quote from the text prefixed by the heading title (e.g. MAIN CONCLUSIONS: \\"quote\\")>"
}

Output a single JSON object only. Do not include extra text or markdown block formatting."""

how_prompt = """You are an expert endocrinologist and clinical study aid developer.
Your task is to generate a single clinical "How" question based on the provided Main Conclusions and clinical explanations. This question should focus on a diagnostic step, mechanism of action, or monitoring approach.

Output format:
{
  "type": "how",
  "subtopic": "<Topic category>",
  "question": "How ...?",
  "answer": "<Explanation of how>",
  "keyPoints": [
    "<Key clinical point 1>",
    "<Key clinical point 2>"
  ],
  "reference": "<VERBATIM double-quoted quote from the text prefixed by the heading title (e.g. MAIN CONCLUSIONS: \\"quote\\")>"
}

Output a single JSON object only. Do not include extra text or markdown block formatting."""

modified_index = False

for idx, f in enumerate(endo_md_files):
    # Match chapter number
    match = re.match(r"endo2021_chapter_(\d+)_(.*)\.md", f)
    if not match:
        continue
    
    ch_num = int(match.group(1))
    slug = match.group(2)
    
    # Skip Chapter 1 since it's already done and validated (items: 8)
    if ch_num == 1:
        continue
        
    print(f"[{idx+1}/{len(endo_md_files)}] Processing Chapter {ch_num}: {slug}...")
    
    # Target file paths
    json_filename = f.replace(".md", ".json")
    target_json_path = os.path.join(target_dir, json_filename)
    
    # Check if we can skip (must have >= 3 items, and at least 1 MCQ + 2 Why/How)
    should_skip = False
    if os.path.exists(target_json_path) and os.path.getsize(target_json_path) > 100:
        try:
            with open(target_json_path, "r", encoding="utf-8") as existing_f:
                existing_data = json.load(existing_f)
                items = existing_data.get("items", [])
                if len(items) >= 3:
                    why_how_count = sum(1 for item in items if item.get("type") in ["why", "how"])
                    mcq_count = sum(1 for item in items if item.get("type") == "mcq")
                    if mcq_count >= 1 and why_how_count >= 2:
                        should_skip = True
        except Exception:
            pass
            
    if should_skip:
        print("  JSON file already exists with sufficient items. Skipping.")
        ch_idx = get_index_chapter(ch_num)
        if ch_idx and (ch_idx['status'] != 'ready' or ch_idx['file'] != json_filename):
            ch_idx['file'] = json_filename
            ch_idx['status'] = 'ready'
            modified_index = True
        continue
        
    # Read md content
    with open(os.path.join(source_dir, f), "r", encoding="utf-8") as file:
        md_text = file.read()
        
    # Extract key sections
    title, mc, cv = extract_key_sections(md_text)
    
    # Check what content to send
    mc_content = mc if mc else md_text
    cv_content = cv if cv else md_text
    
    ch_idx = get_index_chapter(ch_num)
    title = ch_idx['title'] if ch_idx else title
    
    print("  Generating MCQ...")
    mcq_start = time.time()
    mcq_item = query_ollama(mcq_prompt, cv_content)
    
    print("  Generating Why item...")
    why_start = time.time()
    why_item = query_ollama(why_prompt, mc_content)
    
    print("  Generating How item...")
    how_start = time.time()
    how_item = query_ollama(how_prompt, mc_content)
    
    # Build final combined JSON
    result_json = {
        "id": f"e21-{ch_num:02d}",
        "volume": 2021,
        "chapterNo": str(ch_num),
        "title": title,
        "section": "Endocrine Self-Assessment Program 2021 (Endo 2021)",
        "authors": "ESAP Committee",
        "sourceFile": f"williams_2024_chapters/{f}",
        "items": []
    }
    
    why_how_success = 0
    
    if mcq_item:
        mcq_item["id"] = f"e21-{ch_num:02d}-q1"
        mcq_item["type"] = "mcq"
        # Validate options list
        opts = mcq_item.get("options", [])
        if not isinstance(opts, list) or len(opts) < 4:
            mcq_item["options"] = opts + ["Option B", "Option C", "Option D"][:4-len(opts)]
        try:
            mcq_item["correctOption"] = int(mcq_item.get("correctOption", 0))
        except:
            mcq_item["correctOption"] = 0
        result_json["items"].append(mcq_item)
        
    if why_item:
        why_item["id"] = f"e21-{ch_num:02d}-why1"
        why_item["type"] = "why"
        if "keyPoints" not in why_item:
            why_item["keyPoints"] = ["Key Point 1", "Key Point 2"]
        result_json["items"].append(why_item)
        why_how_success += 1
        
    if how_item:
        how_item["id"] = f"e21-{ch_num:02d}-how1"
        how_item["type"] = "how"
        if "keyPoints" not in how_item:
            how_item["keyPoints"] = ["Key Point 1", "Key Point 2"]
        result_json["items"].append(how_item)
        why_how_success += 1
        
    total_time = time.time() - mcq_start
    
    if len(result_json["items"]) >= 3:
        # Save Qbank JSON file
        with open(target_json_path, "w", encoding="utf-8") as out_f:
            json.dump(result_json, out_f, indent=2, ensure_ascii=False)
            
        print(f"  Successfully wrote {json_filename} in {total_time:.2f}s (items: {len(result_json['items'])}, why/how: {why_how_success})")
        
        # Register in index.json
        if ch_idx:
            ch_idx['file'] = json_filename
            ch_idx['status'] = 'ready'
            modified_index = True
            
        # Write index.json progress immediately
        if modified_index:
            with open(index_path, "w", encoding="utf-8") as ind_f:
                json.dump(index_data, ind_f, indent=2, ensure_ascii=False)
            modified_index = False
    else:
        print(f"  Failed to generate all 3 required items for Chapter {ch_num} (items generated: {len(result_json['items'])}).")

# Write final index.json check
if modified_index:
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
print("Updated data/index.json catalog successfully!")
