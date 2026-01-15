import json
import re
import os

# JSON_PATH will be set by process_file() function parameter

def split_content_to_answers(text, existing_answers=None):
    """
    Splits text that might contain options in various formats:
    - '<b>X.</b>' or '<b>X)</b>' (dot/parenthesis INSIDE the <b> tag)
    - '<b>X</b>)' (parenthesis OUTSIDE the <b> tag)
    Returns: (cleaned_text, new_answers_list)
    """
    if not text:
        return text, []
    
    # Pattern 1: Dot/parenthesis INSIDE the <b> tag: <b>A.</b> or <b>A)</b>
    pattern1 = r'(?:<br\s*/?>|\n|^)\s*<b>([a-dA-D])[\.\)]</b>\s*'
    
    # Pattern 2: Parenthesis OUTSIDE the <b> tag: <b>c</b>)
    pattern2 = r'(?:<br\s*/?>|\n|^)\s*<b>([a-dA-D])</b>\s*[\)]\s*'
    
    # Find all matches with both patterns
    matches1 = list(re.finditer(pattern1, text, re.MULTILINE))
    matches2 = list(re.finditer(pattern2, text, re.MULTILINE))
    
    # Combine and sort by position
    all_matches = []
    for m in matches1:
        all_matches.append(('inside', m))
    for m in matches2:
        all_matches.append(('outside', m))
    
    # Sort by start position
    all_matches.sort(key=lambda x: x[1].start())
    
    # Remove duplicates (same position)
    matches = []
    seen_positions = set()
    for match_type, m in all_matches:
        if m.start() not in seen_positions:
            matches.append(m)
            seen_positions.add(m.start())
    
    if not matches:
        return text, []
    
    # Extract the first part (before first option) as cleaned text
    first_match = matches[0]
    cleaned_text = text[:first_match.start()].strip()
    
    new_answers = []
    
    # Process each match
    for i, match in enumerate(matches):
        key = match.group(1).upper()
        
        # Find the end position of this option's content
        # It's either before the next option or end of text
        start_pos = match.end()
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(text)
        
        content = text[start_pos:end_pos].strip()
        
        # Remove trailing newlines and clean up
        content = re.sub(r'\n+$', '', content)
        content = content.strip()
        
        # Stop at next option if found (look for pattern in content)
        # Check both patterns: inside and outside
        next_option_match1 = re.search(r'(?:<br\s*/?>|\n)\s*<b>([a-dA-D])[\.\)]</b>', content, re.MULTILINE)
        next_option_match2 = re.search(r'(?:<br\s*/?>|\n)\s*<b>([a-dA-D])</b>\s*[\)]', content, re.MULTILINE)
        
        next_option_match = None
        if next_option_match1 and next_option_match2:
            # Take the one that appears first
            next_option_match = next_option_match1 if next_option_match1.start() < next_option_match2.start() else next_option_match2
        elif next_option_match1:
            next_option_match = next_option_match1
        elif next_option_match2:
            next_option_match = next_option_match2
        
        if next_option_match:
            content = content[:next_option_match.start()].strip()
        
        if content:  # Only add if there's content
            new_answers.append({
                "key": key,
                "content": content
            })
        
    return cleaned_text, new_answers

def process_file(json_path=None):
    if json_path is None:
        # Default path
        json_path = os.path.join(os.getcwd(), "output_data", "questions.json")
    
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Data is list of sections
    for section in data:
        for q in section.get("questions", []):
            # 1. Check if 'question' text contains hidden options
            # IMPORTANT: Do this BEFORE clean_string_content to preserve format
            q_text, extracted_answers = split_content_to_answers(q["question"])
            
            if extracted_answers:
                print(f"Extracted {len(extracted_answers)} answers from Question {q['id']}")
                q["question"] = q_text
                
                # Initialize answers if not exists
                if "answers" not in q:
                    q["answers"] = []
                
                # Check for duplicates?
                existing_keys = {a["key"] for a in q["answers"]}
                for ans in extracted_answers:
                    if ans["key"] not in existing_keys:
                        q["answers"].append(ans)
                        existing_keys.add(ans["key"])
            
            # 2. Check if existing 'answers' contain hidden options (merged answers)
            original_answers = list(q["answers"])
            q["answers"] = [] # Rebuild
            
            for ans in original_answers:
                # Split this answer content
                ans_text, extra_answers = split_content_to_answers(ans["content"])
                
                # The first part is the content of THIS answer
                ans["content"] = ans_text
                q["answers"].append(ans)
                
                # The rest are new answers found inside this one
                if extra_answers:
                    print(f"Found {len(extra_answers)} nested options in Answer {ans['key']} of Question {q['id']}")
                    for extra in extra_answers:
                         q["answers"].append(extra)
            
            # Sort answers by key just in case
            q["answers"].sort(key=lambda x: x["key"])
            
            # --- FINAL CLEANUP: COMPACT SPACING ---
            # IMPORTANT: Clean AFTER extracting options to preserve format
            def clean_string_content(text):
                if not text: return ""
                # 1. Minify HTML Tables: Remove newlines and indentation between tags
                def minify_table(match):
                    tbl = match.group(0)
                    # Remove whitespace between tags: >  <  -> ><
                    tbl = re.sub(r'>\s+<', '><', tbl)
                    return tbl
                
                text = re.sub(r'<table[\s\S]*?</table>', minify_table, text)
                
                # 1b. Remove all whitespace/newlines and stray `}` immediately after </table>
                text = re.sub(r'</table>\s*\}+', '</table>', text, flags=re.IGNORECASE)
                text = re.sub(r'</table>(<br\s*/?>\s*)+', '</table>', text, flags=re.IGNORECASE)
                text = re.sub(r'</table>([^<]*?)\}', r'</table>\1', text, flags=re.IGNORECASE | re.DOTALL)
                
                # 2. General LaTeX/Pandoc cleanup
                # Convert textsuperscript to HTML superscript tag
                text = re.sub(r'\\textsuperscript\{([^}]+)\}', r'<sup>\1</sup>', text)
                
                # Convert LaTeX commands to HTML
                # \emph{} -> <em> (emphasis)
                text = re.sub(r'\\emph\{([^}]+)\}', r'<em>\1</em>', text) 
                text = re.sub(r'\\textbf\{([^}]+)\}', r'\1', text)
                text = re.sub(r'\\textit\{([^}]+)\}', r'\1', text)
                text = re.sub(r'\\text\{([^}]+)\}', r'\1', text)

                # Remove stray braces that specifically wrap parenthesized text: {(...)} -> (...)
                text = re.sub(r'\{\s*(\([^}]+\))\s*\}', r'\1', text)

                # Protect \includegraphics commands before cleanup (temporary replacement)
                includegraphics_placeholders = {}
                def protect_includegraphics(match):
                    placeholder = f"__INCLUDE_GRAPHICS_{len(includegraphics_placeholders)}__"
                    includegraphics_placeholders[placeholder] = match.group(0)
                    return placeholder
                
                # Protect complete \includegraphics commands
                text = re.sub(r'\\includegraphics(?:\[[^\]]*\])?\{[^}]+\}', protect_includegraphics, text)
                # Also protect incomplete ones (missing closing brace) - fix them first
                text = re.sub(r'\\includegraphics(?:\[[^\]]*\])?\{([^}\n]+)(?<!})$', r'\\includegraphics{\1}', text, flags=re.MULTILINE)
                # Now protect the fixed ones
                text = re.sub(r'\\includegraphics(?:\[[^\]]*\])?\{[^}]+\}', protect_includegraphics, text)

                # Remove `}` immediately after </table> tag
                text = re.sub(r'</table>\s*\}', '</table>', text, flags=re.IGNORECASE)
                
                # Remove standalone `}` at the end of text
                text = re.sub(r'([^\}])\s*\}\s*$', r'\1', text, flags=re.MULTILINE)
                
                # Remove `}` at the start of a line
                text = re.sub(r'^\s*\}\s*$', '', text, flags=re.MULTILINE)
                
                # Restore protected \includegraphics commands
                for placeholder, original in includegraphics_placeholders.items():
                    text = text.replace(placeholder, original)
                
                # 3. Collapse multiple spaces
                text = re.sub(r'[ \t]+', ' ', text)

                # 4. Collapse newlines to exactly 1
                text = re.sub(r'\n+', '\n', text)
                
                # 5. Trim lines
                text = text.strip()
                
                return text

            q["question"] = clean_string_content(q["question"])
            for ans in q["answers"]:
                ans["content"] = clean_string_content(ans["content"])

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("Post-processing complete.")

if __name__ == "__main__":
    process_file()
