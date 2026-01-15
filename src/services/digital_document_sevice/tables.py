import re
import hashlib
from .llm_client import client, AI_AVAILABLE
from .cache import LATEX_CACHE, save_cache

def call_openai_table_reformat(latex_table_code):
    table_hash = "TABLE_TAILWIND_V3_" + hashlib.md5(latex_table_code.encode('utf-8')).hexdigest()
    if table_hash in LATEX_CACHE:
        return LATEX_CACHE[table_hash]
    
    if not AI_AVAILABLE or not client: return latex_table_code

    # Pre-cleanup: Fix common LaTeX formatting issues in table cells
    # Fix \text{ } (space in text command) -> \, (thin space)
    cleaned_table = re.sub(r'\\text\{\s+\}', r'\\,', latex_table_code)
    # Fix \ ^{\circ} or \^{\circ} -> ^{\circ} (remove backslash/space before caret)
    cleaned_table = re.sub(r'\\\s+\^\\circ', r'^{\\circ}', cleaned_table)
    cleaned_table = re.sub(r'\\\s*\^\\circ', r'^{\\circ}', cleaned_table)
    cleaned_table = re.sub(r'\\\^\\circ', r'^{\\circ}', cleaned_table)
    # Fix spaces in negative numbers: \(- 0,6\) -> \(-0,6\)
    cleaned_table = re.sub(r'\\([-+])\s+(\d)', r'\\\1\2', cleaned_table)
    # Fix degree symbol format: ^{\mathbf{0}} or ^{0} -> ^{\circ} (if it's meant to be degree)
    # Note: This is tricky, we'll leave it for now as it depends on context
    
    try:
        # Build prompt without backslashes in f-string
        math_delimiter = r'\( ... \)'
        prompt_text = f"""Convert this LaTeX table into a clean HTML table using Tailwind CSS for styling.
RULES:
1. Output ONLY the HTML code. No markdown block.
2. IMPORTANT: Use these exact Tailwind classes:
   - Table: <table class="w-full border-collapse border border-gray-400 my-4 text-base">
   - Header (th): class="border border-gray-400 bg-gray-100 px-2 py-2 font-bold text-center"
   - Cell (td): class="border border-gray-400 px-2 py-2 text-center"
3. Preserve all data accurately.
4. Convert LaTeX math inside cells to {math_delimiter} delimiters.
5. IMPORTANT: Remove extra spaces in math expressions (e.g., negative numbers should have no space: -0,6 not - 0,6).
6. IMPORTANT: Fix degree symbols: ensure ^circ is used correctly (no extra backslash or space before caret).
7. Use <thead> and <tbody>.
8. Handle colspan/rowspan correctly.
9. Ensure the table has a complete border grid.

Input:
{cleaned_table}
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": prompt_text
            }],
            max_tokens=2000, temperature=0.0
        )
        result = response.choices[0].message.content.strip()
        result = result.replace("```html", "").replace("```", "").strip()
        
        # Minify
        result = re.sub(r'>\s+<', '><', result)
        result = result.replace('\n', '')
        
        LATEX_CACHE[table_hash] = result
        return result
    except Exception as e:
        print(f"Table Reformat Error: {e}")
        return latex_table_code

def process_latex_tables(latex_text):
    if not AI_AVAILABLE: return latex_text
    print("   > Scanning and Converting Tables to HTML (AI)...")
    
    # Matches longtable blocks
    # Priority 1: Wrapped in {\def\LTcaptype{none} ... } (Pandoc default)
    # Priority 2: Standard \begin{longtable} ... \end{longtable}
    pattern = r'(?:\{\s*\\def\\LTcaptype\{none\}\s*(\\begin\{(?:longtable|table|tabular)\}.*?\\end\{(?:longtable|table|tabular)\})\s*\})|(\\begin\{(?:longtable|table|tabular)\}.*?\\end\{(?:longtable|table|tabular)\})'
    
    def table_replacer(match):
        # group(1) matches the inner table if wrapped
        # group(2) matches the table if NOT wrapped
        raw_table = match.group(1) or match.group(2)
        
        if not raw_table: return match.group(0)
        print("     [+] Found a table, asking OpenAI to convert to HTML...")
        clean_table = call_openai_table_reformat(raw_table)
        return clean_table
        
    new_text = re.sub(pattern, table_replacer, latex_text, flags=re.DOTALL)
    
    # Final cleanup for any missed singleton tags (just in case recursion or odd spacing caused misses)
    new_text = new_text.replace(r'{\def\LTcaptype{none}', '').replace(r'\def\LTcaptype{none}', '')
    
    save_cache(LATEX_CACHE)
    return new_text

