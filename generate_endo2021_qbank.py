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

# Find all endo2021 markdown files
all_files = os.listdir(source_dir)
endo_md_files = sorted([f for f in all_files if f.startswith("endo2021_") and f.endswith(".md")])

print(f"Found {len(endo_md_files)} Endo 2021 markdown files.")

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

def query_ollama(prompt, text_content):
    url = "http://localhost:11434/api/generate"
    
    # Strip references section to save context space
    for marker in ["## References", "##### References", "## REFERENCES", "##### REFERENCES", "## Reference", "##### Reference", "## REFERENCE", "##### REFERENCE"]:
        if marker in text_content:
            text_content = text_content.split(marker)[0]
            
    full_prompt = f"{prompt}\n\nHere is the chapter markdown text:\n{text_content}"
    
    data = {
        "model": "phi4:latest",
        "prompt": full_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
            "num_ctx": 8192
        }
    }
    
    # 3 attempts with 600s timeout
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=600) as response:
                res = json.loads(response.read().decode('utf-8'))
                raw_response = res['response'].strip()
                # Parse to ensure it is valid JSON
                return json.loads(raw_response)
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            time.sleep(10)
    return None

prompt_template = """You are an expert endocrinologist and clinical study aid developer. 
Your task is to convert the following raw OCR markdown text for a textbook chapter into a structured study Q-Bank JSON file in the target schema.

Target JSON Schema:
{
  "id": "e21-XX",
  "volume": 2021,
  "chapterNo": "XX",
  "title": "<Chapter Title>",
  "section": "Endocrine Self-Assessment Program 2021 (Endo 2021)",
  "authors": "<Author Name(s) extracted from text>",
  "sourceFile": "williams_2024_chapters/endo2021_chapter_XX_<Slug>.md",
  "items": [
    // Array of items
  ]
}

Items can be of types: mcq, why, how.
To satisfy the requirement that >60% of items are Why/How questions, you must output exactly:
- 1 MCQ (based on Case 1 / Case 2 vignette and question)
- 2 Why/How questions (based on the explanations and main conclusions)
Total items: 3. This yields 2 Why/How items out of 3 items (66.7% Why/How ratio, which is >60%).

Item schemas:
1. MCQ:
{
  "id": "e21-XX-q1",
  "type": "mcq",
  "subtopic": "<Topic>",
  "question": "<Vignette stem ending in a question>",
  "options": ["A", "B", "C", "D"],
  "correctOption": <0-indexed integer 0-3>,
  "explanation": "<High-quality medical explanation>",
  "reference": "<VERBATIM QUOTE FROM TEXT PREFIXED BY HEADING>"
}

2. Why / How:
{
  "id": "e21-XX-why1", // or e21-XX-how1, e21-XX-why2, etc.
  "type": "why", // or "how"
  "subtopic": "<Topic>",
  "question": "Why ...?", // or "How ...?"
  "answer": "Because ...", // or explanation of how
  "keyPoints": ["Point 1", "Point 2", ...],
  "reference": "<VERBATIM QUOTE FROM TEXT PREFIXED BY HEADING>"
}

Rules for References:
- Every item's `reference` MUST contain a verbatim quote from the text wrapped in double quotes, prefixed by the section heading (e.g. `MAIN CONCLUSIONS: "quote..."`). NEVER invent quotes.

Format:
- Output a single, clean JSON object ONLY. Do not include markdown code blocks, reasoning, thinking, or extra text. Start directly with '{' and end with '}'."""

# Keep track of changes
modified_index = False

for idx, f in enumerate(endo_md_files):
    # Match chapter number
    match = re.match(r"endo2021_chapter_(\d+)_(.*)\.md", f)
    if not match:
        continue
    
    ch_num = int(match.group(1))
    slug = match.group(2)
    
    # Skip Chapter 1 since it's already done
    if ch_num == 1:
        continue
        
    print(f"[{idx+1}/{len(endo_md_files)}] Processing Chapter {ch_num}: {slug}...")
    
    # Target file paths
    json_filename = f.replace(".md", ".json")
    target_json_path = os.path.join(target_dir, json_filename)
    
    # Skip if already exists and is valid
    if os.path.exists(target_json_path) and os.path.getsize(target_json_path) > 100:
        print("  JSON file already exists. Skipping.")
        # Make sure it's in index.json
        ch_idx = get_index_chapter(ch_num)
        if ch_idx and (ch_idx['status'] != 'ready' or ch_idx['file'] != json_filename):
            ch_idx['file'] = json_filename
            ch_idx['status'] = 'ready'
            modified_index = True
        continue
        
    # Read md content
    with open(os.path.join(source_dir, f), "r", encoding="utf-8") as file:
        md_text = file.read()
        
    # Query LLM
    start_time = time.time()
    result_json = query_ollama(prompt_template, md_text)
    
    if result_json:
        # Post-validation checks
        try:
            # Overwrite id/volume/chapterNo to be absolutely safe
            result_json['id'] = f"e21-{ch_num:02d}"
            result_json['volume'] = 2021
            result_json['chapterNo'] = str(ch_num)
            result_json['sourceFile'] = f"williams_2024_chapters/{f}"
            
            # Reformat item IDs to match chapter prefix
            items = result_json.get('items', [])
            mcqs = 0
            why_how = 0
            
            for it_idx, item in enumerate(items):
                it_type = item.get('type')
                if it_type == 'mcq':
                    item['id'] = f"e21-{ch_num:02d}-q{mcqs+1}"
                    mcqs += 1
                elif it_type in ['why', 'how']:
                    item['id'] = f"e21-{ch_num:02d}-{it_type}{why_how+1}"
                    why_how += 1
                else:
                    item['id'] = f"e21-{ch_num:02d}-item{it_idx+1}"
            
            # Save Qbank JSON file
            with open(target_json_path, "w", encoding="utf-8") as out_f:
                json.dump(result_json, out_f, indent=2, ensure_ascii=False)
                
            print(f"  Successfully wrote {json_filename} in {time.time() - start_time:.2f}s (items: {len(items)}, why/how: {why_how})")
            
            # Register in index.json
            ch_idx = get_index_chapter(ch_num)
            if ch_idx:
                ch_idx['file'] = json_filename
                ch_idx['status'] = 'ready'
                modified_index = True
                
            # Write index.json immediately to save progress
            if modified_index:
                with open(index_path, "w", encoding="utf-8") as ind_f:
                    json.dump(index_data, ind_f, indent=2, ensure_ascii=False)
                modified_index = False
                
        except Exception as parse_e:
            print(f"  Error post-processing output: {parse_e}")
    else:
        print(f"  Failed to generate chapter {ch_num} from Ollama.")
        
# Write final check index.json
if modified_index:
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
    print("Updated data/index.json catalog successfully!")
