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
        # Clean up references from case vignettes if present
        for marker in ["## References", "##### References", "## REFERENCES", "##### REFERENCES", "## Reference", "##### Reference", "## REFERENCE", "##### REFERENCE"]:
            if marker in case_vignettes:
                case_vignettes = case_vignettes.split(marker)[0].strip()
                
    return title, main_conclusions, case_vignettes

def query_ollama(prompt, input_text):
    url = "http://localhost:11434/api/generate"
    
    full_prompt = f"{prompt}\n\nHere is the chapter text (excerpt or full):\n{input_text}"
    
    data = {
        "model": "qwen2.5:3b",
        "prompt": full_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
            "num_ctx": 8192
        }
    }
    
    # 3 attempts with 90s timeout
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                res = json.loads(response.read().decode('utf-8'))
                raw_response = res['response'].strip()
                # Parse to ensure it is valid JSON
                return json.loads(raw_response)
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            time.sleep(5)
    return None

def make_prompt(ch_num, title, filename):
    prompt = f"""You are an expert endocrinologist and clinical study aid developer. 
Your task is to convert the raw textbook chapter text into a structured study Q-Bank JSON file.

You must output exactly:
- 1 MCQ item (type: "mcq", based on the patient case/vignette)
- 2 Why or How items (type: "why" or "how", based on the clinical explanations or mechanisms)
Total items in the "items" array: 3.

Target JSON format:
{{
  "id": "e21-{ch_num:02d}",
  "volume": 2021,
  "chapterNo": "{ch_num}",
  "title": "{title}",
  "section": "Endocrine Self-Assessment Program 2021 (Endo 2021)",
  "authors": "ESAP Committee",
  "sourceFile": "williams_2024_chapters/{filename}",
  "items": [
    {{
      "id": "e21-{ch_num:02d}-q1",
      "type": "mcq",
      "subtopic": "<Subtopic>",
      "question": "<Vignette stem ending in a question>",
      "options": [
        "<Option A>",
        "<Option B>",
        "<Option C>",
        "<Option D>"
      ],
      "correctOption": <0-indexed integer 0-3 representing correct option>,
      "explanation": "<High-quality medical explanation>",
      "reference": "<VERBATIM QUOTE FROM TEXT PREFIXED BY HEADING>"
    }},
    {{
      "id": "e21-{ch_num:02d}-why1",
      "type": "why",
      "subtopic": "<Subtopic>",
      "question": "Why ...?",
      "answer": "Because ...",
      "keyPoints": [
        "<Key Point 1>",
        "<Key Point 2>"
      ],
      "reference": "<VERBATIM QUOTE FROM TEXT PREFIXED BY HEADING>"
    }},
    {{
      "id": "e21-{ch_num:02d}-how1",
      "type": "how",
      "subtopic": "<Subtopic>",
      "question": "How ...?",
      "answer": "<Explanation of how>",
      "keyPoints": [
        "<Key Point 1>",
        "<Key Point 2>"
      ],
      "reference": "<VERBATIM QUOTE FROM TEXT PREFIXED BY HEADING>"
    }}
  ]
}}

Rules for references:
- The "reference" field must contain a verbatim double-quoted quote from the chapter text, prefixed by the heading title (e.g. MAIN CONCLUSIONS: "quote..."). Never invent quotes.

Format:
- Output a single, clean JSON object ONLY. Do not include markdown code blocks, reasoning, thinking, or extra text. Start directly with '{{' and end with '}}':"""
    return prompt

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
    
    # Choose input text
    if mc and cv:
        input_text = f"CHAPTER TITLE: {title}\n\n{mc}\n\n{cv}"
        print(f"  Extracted key sections: Main Conclusions ({len(mc)} chars) & Case Vignettes ({len(cv)} chars).")
    else:
        # Fallback: strip references section
        cleaned_text = md_text
        for marker in ["## References", "##### References", "## REFERENCES", "##### REFERENCES", "## Reference", "##### Reference", "## REFERENCE", "##### REFERENCE"]:
            if marker in cleaned_text:
                cleaned_text = cleaned_text.split(marker)[0]
        input_text = cleaned_text
        print("  Fallback: using full text (references stripped).")
        
    ch_idx = get_index_chapter(ch_num)
    title = ch_idx['title'] if ch_idx else title
    
    prompt = make_prompt(ch_num, title, f)
    
    start_time = time.time()
    result_json = query_ollama(prompt, input_text)
    
    if result_json:
        try:
            # Overwrite metadata to ensure correctness
            result_json['id'] = f"e21-{ch_num:02d}"
            result_json['volume'] = 2021
            result_json['chapterNo'] = str(ch_num)
            result_json['title'] = title
            result_json['section'] = "Endocrine Self-Assessment Program 2021 (Endo 2021)"
            result_json['authors'] = "ESAP Committee"
            result_json['sourceFile'] = f"williams_2024_chapters/{f}"
            
            # Reformat item IDs and validate
            items = result_json.get('items', [])
            
            # Flatten any nested structures
            flat_items = []
            def extract_items_recursive(it_list):
                for item in it_list:
                    nested = item.pop("items", None)
                    flat_items.append(item)
                    if isinstance(nested, list):
                        extract_items_recursive(nested)
            
            extract_items_recursive(items)
            
            mcqs = 0
            why_how = 0
            final_items = []
            
            for it_idx, item in enumerate(flat_items):
                it_type = item.get('type')
                if not it_type:
                    continue
                if it_type == 'mcq':
                    item['id'] = f"e21-{ch_num:02d}-q{mcqs+1}"
                    mcqs += 1
                    options = item.get("options", [])
                    if not isinstance(options, list) or len(options) < 4:
                        item["options"] = options + ["Option B", "Option C", "Option D"][:4-len(options)]
                    try:
                        item["correctOption"] = int(item.get("correctOption", 0))
                    except:
                        item["correctOption"] = 0
                elif it_type in ['why', 'how']:
                    item['id'] = f"e21-{ch_num:02d}-{it_type}{why_how+1}"
                    why_how += 1
                    if "keyPoints" not in item:
                        item["keyPoints"] = ["Key Point 1", "Key Point 2"]
                else:
                    item['type'] = 'why'
                    item['id'] = f"e21-{ch_num:02d}-why{why_how+1}"
                    why_how += 1
                
                final_items.append(item)
            
            result_json['items'] = final_items
            
            # Save Qbank JSON file
            with open(target_json_path, "w", encoding="utf-8") as out_f:
                json.dump(result_json, out_f, indent=2, ensure_ascii=False)
                
            print(f"  Successfully wrote {json_filename} in {time.time() - start_time:.2f}s (items: {len(final_items)}, why/how: {why_how})")
            
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
                
        except Exception as parse_e:
            print(f"  Error post-processing output: {parse_e}")
    else:
        print(f"  Failed to generate chapter {ch_num} from Ollama.")

# Write final index.json check
if modified_index:
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
print("Updated data/index.json catalog successfully!")
