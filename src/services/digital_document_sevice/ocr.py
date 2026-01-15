import os
import re
import concurrent.futures
import subprocess
import time
import hashlib
from .utils import encode_image, get_hash, clean_latex_response
from .llm_client import client, AI_AVAILABLE
from .cache import LATEX_CACHE, save_cache
from .config import MAX_WORKERS

def call_openai_latex(image_path, retries=2):
    img_hash = get_hash(image_path if isinstance(image_path, str) and len(image_path) < 200 else "content")
    if os.path.exists(image_path):
        with open(image_path, "rb") as f: img_content = f.read()
        img_hash = hashlib.md5(img_content).hexdigest()
    
    if img_hash in LATEX_CACHE: 
         return clean_latex_response(LATEX_CACHE[img_hash])

    if not AI_AVAILABLE or not client: return None

    for attempt in range(retries + 1):
        try:
            base64_image = encode_image(image_path)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[ {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Convert this image to LaTeX. If it contains text, output valid LaTeX text. If it contains math, use LaTeX math mode ($...$). Preserve formatting like bolding (\\textbf). Do NOT use document delimiters. Return clean content."}, 
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "low"
                            }
                        },
                    ]
                } ],
                max_tokens=300, temperature=0.0
            )
            result = response.choices[0].message.content.strip()
            result = clean_latex_response(result)
            LATEX_CACHE[img_hash] = result
            return result
        except Exception as e:
            if attempt < retries: 
                print(f"     [!] API Error (Retrying {attempt+1}/{retries}): {e}")
                time.sleep(2)
            else: 
                print(f"     [!] API Failed Final: {e}")
                return None

def convert_wmf_to_png_standard(input_path, output_path):
    # Get the script path relative to this file's location
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up from services/digital_document_sevice to src, then to scripts
    # current_dir = src/services/digital_document_sevice
    # Need to go up 3 levels: .. -> services, .. -> src, .. -> project root
    # Actually, we want src/scripts, so go up 2 levels to src
    src_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    # Now go to src/scripts
    script_path = os.path.join(src_dir, "src", "scripts", "convert_ocr.ps1")
    # Ensure script exists (or rely on it being present, but safer to write it)
    if not os.path.exists(script_path):
        with open(script_path, 'w') as f:
            f.write(r"""
param ([string]$inputPath, [string]$outputPath)
try {
    Add-Type -AssemblyName System.Drawing
    if (-not (Test-Path $inputPath)) { exit 1 }
    $img = [System.Drawing.Image]::FromFile($inputPath)
    
    # Target clearer resolution (approx 1024px width for better OCR)
    # User requested clarity, so we prefer upscaling or maintaining high/300 DPI
    
    $scale = 1.0
    if ($img.Width -lt 1024) { $scale = 1024 / $img.Width }
    if ($img.Width -gt 2048) { $scale = 2048 / $img.Width } # Cap at 2048 to avoid huge tokens
    
    $newW = [int]($img.Width * $scale)
    $newH = [int]($img.Height * $scale)
    
    if ($newW -lt 1) { $newW = 1 }
    $bmp = New-Object System.Drawing.Bitmap($newW, $newH)
    $bmp.SetResolution(300, 300) # Increase DPI for clarity
    
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.Clear([System.Drawing.Color]::White)
    $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    
    $g.DrawImage($img, 0, 0, $newW, $newH)
    $bmp.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose(); $img.Dispose()
    Write-Host "Success"
} catch { exit 1 }
""")
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_path, "-inputPath", os.path.abspath(input_path), "-outputPath", os.path.abspath(output_path)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return "Success" in res.stdout
    except: return False

def process_single_wmf(task_info):
    filename_orig, abs_orig_path, output_folder = task_info
    
    # Fallback: Check for PNG if WMF matches are missing
    if not os.path.exists(abs_orig_path):
        alt_png = os.path.splitext(abs_orig_path)[0] + ".png"
        if os.path.exists(alt_png):
            abs_orig_path = alt_png
            filename_orig = os.path.splitext(filename_orig)[0] + ".png"
        else:
             print(f"     [!] Missing file: {abs_orig_path}")
             return None
             
    base_name = os.path.basename(filename_orig).rsplit('.', 1)[0]
    filename_temp = f"{base_name}_gpt_temp.png"
    abs_temp_path = os.path.abspath(os.path.join(output_folder, "media", filename_temp))
    
    ext = os.path.splitext(filename_orig)[1].lower()
    if ext in ['.png', '.jpg', '.jpeg']:
         abs_temp_path = abs_orig_path
    else:
        if not os.path.exists(abs_temp_path):
            if not convert_wmf_to_png_standard(abs_orig_path, abs_temp_path): return None 
            
    core_latex = call_openai_latex(abs_temp_path)
    
    if ext not in ['.png', '.jpg', '.jpeg']:
        try: os.remove(abs_temp_path)
        except: pass
        
    if core_latex: 
        print(f"     [+] OCR Success: {filename_orig}")
        return (filename_orig, f"${core_latex}$")
    else: 
        print(f"     [-] OCR Failed: {filename_orig}")
        return None

def process_latex_images(latex_text, output_folder):
    if not AI_AVAILABLE: return latex_text
    print(f"   > Pre-scanning images & analyzing dimensions...")
    all_matches = re.finditer(r'\{([^}]+?)\.(wmf|emf|jpeg|jpg|png)\}', latex_text, re.IGNORECASE)
    ocr_tasks = []      
    seen_files = set()
    replacements_by_filename = {}   
    for match in all_matches:
        rel_path = match.group(1)
        ext = match.group(2).lower()
        base_name = os.path.basename(rel_path)
        filename_orig = f"{base_name}.{ext}"
        abs_orig_path = os.path.abspath(os.path.join(output_folder, "media", filename_orig))
        if not os.path.exists(abs_orig_path): continue
        if ext in ['wmf', 'emf']:
            if filename_orig not in seen_files:
                ocr_tasks.append((filename_orig, abs_orig_path, output_folder))
                seen_files.add(filename_orig)
        else:
             replacements_by_filename[filename_orig] = f"\n\\begin{{center}}\n\\includegraphics[max width=\\linewidth,keepaspectratio]{{media/{filename_orig}}}\n\\end{{center}}\n"
    print(f"   > Identified {len(ocr_tasks)} formulas to OCR (WMF only)...")
    ocr_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_wmf, task): task for task in ocr_tasks}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                fname, code = res
                ocr_results[fname] = code
    save_cache(LATEX_CACHE)
    print("   > Injecting LaTeX codes...")
    def replacer(match):
        full_command = match.group(0)
        path_match = re.search(r'\{([^}]+?)\.(wmf|emf|jpeg|jpg|png)\}', full_command, re.IGNORECASE)
        if not path_match: return full_command
        base_name = os.path.basename(path_match.group(1))
        ext = path_match.group(2).lower()
        fname = f"{base_name}.{ext}"
        if fname in ocr_results: return ocr_results[fname]
        if fname in replacements_by_filename: return replacements_by_filename[fname]
        return full_command
    new_text = re.sub(r'(?:\\pandocbounded\{)?\s*\\includegraphics(?:\[[^\]]*\])?\{[^}]+\.(?:wmf|emf|jpeg|jpg|png)\}(?:\})?', replacer, latex_text, flags=re.IGNORECASE)
    return new_text

