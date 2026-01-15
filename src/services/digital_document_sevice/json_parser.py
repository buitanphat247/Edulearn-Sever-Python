import os
import re
import json

class LatexToJsonParser:
    def __init__(self, output_folder):
        self.output_folder = output_folder
        self.math_folder = os.path.join(output_folder, "maths")
        if not os.path.exists(self.math_folder):
            os.makedirs(self.math_folder)
        
    def save_math_var(self, content, var_name):
        """Saves math content to a separate file."""
        file_path = os.path.join(self.math_folder, var_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    def extract_math(self, text, unique_id):
        """
        Finds all $...$ blocks, saves them to files, and replaces them with [:$var_name$].
        unique_id should be unique for this question instance (e.g. 1, 2, 3...)
        """
        def replacer(match):
            nonlocal counter
            content = match.group(1).strip()
            
            # Clean up common LaTeX formatting issues before saving
            
            # PRIORITY 1: Fix \ ^{\circ} or \^{\circ} or \\ ^{\\circ} -> ^{\circ} (remove backslash/space before caret)
            # Pattern: \ (space) ^\circ or \^\circ or \\ ^{\\circ} -> ^{\circ}
            # Fix double escape: \\ ^{\\circ} -> ^{\circ}
            content = re.sub(r'\\\\\s+\^\\circ', r'^{\\circ}', content)
            content = re.sub(r'\\\\\s*\^\\circ', r'^{\\circ}', content)
            # Fix single escape: \ ^{\\circ} or \ ^{\circ} -> ^{\circ}
            content = re.sub(r'\\\s+\^\\circ', r'^{\\circ}', content)
            content = re.sub(r'\\\s*\^\\circ', r'^{\\circ}', content)
            content = re.sub(r'\\\^\\circ', r'^{\\circ}', content)
            
            # PRIORITY 2: Fix \text{ } (space in text command)
            # Option 1: Replace with regular space (for better compatibility outside math mode)
            # Option 2: Keep as \, (thin space in math mode)
            # We'll replace with regular space for better compatibility
            content = re.sub(r'\\text\{\s+\}', r' ', content)
            
            # PRIORITY 3: Fix \, (thin space) - replace with regular space for better compatibility
            # \, only works in math mode, if MathJax/KaTeX doesn't render, it shows as literal
            # Replace \, with regular space for better display
            content = re.sub(r'\\,', r' ', content)
            
            # PRIORITY 4: Wrap plain text units in \text{} for proper rendering
            # If content is simple text unit (no math operators, no backslashes, no $, ^, _, {, }, no numbers at start)
            # Examples: "mm", "kg", "m/s", "°C" should become "\text{mm}", "\text{kg}", etc.
            # Skip if it already contains math symbols, LaTeX commands, or starts with numbers (which indicates math expressions)
            # Pattern: content is 1-10 chars, only letters, /, °, spaces allowed, no math symbols
            if content and len(content) <= 15 and not re.search(r'[\\$^_{}\d]|\\[a-zA-Z]+', content) and re.match(r'^[a-zA-ZÀ-ÿ\s/°]+$', content):
                # Simple text unit, wrap in \text{}
                content = f'\\text{{{content}}}'
            
            counter += 1
            # Using unique_id ensures no collision even if Question Number repeats (Part I vs Part II)
            var_name = f"mathm{unique_id}_{counter}"
            self.save_math_var(content, var_name)
            return f"[:${var_name}$]"

        counter = 0
        new_text = re.sub(r'\$([^\$]+)\$', replacer, text)
        return new_text

    def normalize_latex(self, text):
        """
        Pre-processes text to standardize LaTeX before extraction.
        """
        # 1. Convert \( ... \) to $ ... $
        text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
        
        # 2. Convert \[ ... \] to $$ ... $$ (or single $ for simple inline)
        text = re.sub(r'\\\[(.*?)\\\]', r'$\1$', text, flags=re.DOTALL)
        
        # 3. Remove comments
        text = re.sub(r'(?<!\\)%.*', '', text)
        
        return text

    def clean_html_formatting(self, text):
        """
        Cleans up LaTeX formatting tags to HTML after math is extracted.
        """
        # Normalize simple tags (Pandoc uses strong/em)
        text = re.sub(r'<strong[^>]*>', '<b>', text)
        text = re.sub(r'</strong>', '</b>', text)
        text = re.sub(r'<em[^>]*>', '<i>', text)
        text = re.sub(r'</em>', '</i>', text)
        text = text.replace("<br>", "\n").replace("<br/>", "\n")

        # Remove \begin{center}, \end{center}
        text = re.sub(r'\\begin\{center\}', '', text)
        text = re.sub(r'\\end\{center\}', '', text)
        
        # --- Handle Option Keys (Bold/Underline) ---
        # Format: __OPT_TRUE_A__ or __OPT_FALSE_A__
        
        # 1. True Cases (Underlined)
        p1 = r'\\textbf\{\\ul\{([a-dA-D])\s*[\.\)]?\s*\}\}\s*[\.\)]?'
        text = re.sub(p1, r'__OPT_TRUE_\1__', text)
        p2 = r'\\ul\{\\textbf\{([a-dA-D])\s*[\.\)]?\s*\}\}\s*[\.\)]?'
        text = re.sub(p2, r'__OPT_TRUE_\1__', text)
        p3 = r'\\textbf\{\\ul\{([a-dA-D])\}\}\s*[\.\)]?'
        text = re.sub(p3, r'__OPT_TRUE_\1__', text)
        p4 = r'\\ul\{\s*([a-dA-D])\s*[\.\)]?\s*\}\s*[\.\)]?'
        text = re.sub(p4, r'__OPT_TRUE_\1__', text)

        # HTML Patterns
        h1 = r'<b>\s*<u>\s*([a-dA-D])\s*[\.\)]?\s*</u>\s*</b>\s*[\.\)]?'
        text = re.sub(h1, r'__OPT_TRUE_\1__', text)
        h2 = r'<u>\s*<b>\s*([a-dA-D])\s*[\.\)]?\s*</b>\s*</u>\s*[\.\)]?'
        text = re.sub(h2, r'__OPT_TRUE_\1__', text)
        
        # 2. False/Normal Cases (Bold only)
        text = re.sub(r'\\textbf\{\s*([a-dA-D])\s*[\.\)]\s*\}', r'__OPT_FALSE_\1__', text)
        text = re.sub(r'\\textbf\{\s*([a-dA-D])\s*\}\s*[\.\)]', r'__OPT_FALSE_\1__', text)
        text = re.sub(r'\\textbf\{\s*([a-dA-D])\s*\}', r'__OPT_FALSE_\1__', text)

        # HTML Patterns
        h3 = r'<b>\s*([a-dA-D])\s*</b>\s*[\.\)]'
        text = re.sub(h3, r'__OPT_FALSE_\1__', text)
        h4 = r'<b>\s*([a-dA-D])\s*[\.\)]\s*</b>'
        text = re.sub(h4, r'__OPT_FALSE_\1__', text)

        # --- General Formatting ---
        # \textsuperscript{...} -> <sup>...</sup>
        text = re.sub(r'\\textsuperscript\{([^\}]+)\}', r'<sup>\1</sup>', text)
        
        # \textbf{...} -> <b>...</b>
        text = re.sub(r'\\textbf\{([^\}]+)\}', r'<b>\1</b>', text)
        
        # \textit{...} -> <i>...</i>
        text = re.sub(r'\\textit\{([^\}]+)\}', r'<i>\1</i>', text)
        
        # \ul{...} -> ... (REMOVE UNDERLINE VISUALS)
        text = re.sub(r'\\ul\{([^\}]+)\}', r'\1', text)
        text = re.sub(r'<u>(.*?)</u>', r'\1', text)
        
        # Remove \noindent
        text = re.sub(r'\\noindent', '', text)
        
        # Clean multiple spaces/newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()

    def parse_group(self, group_text, global_q_counter_start):
        questions = []
        
        # Split by "Câu X"
        split_pattern = r'(?:\n|^)\s*(?:\\textbf\{)?(?:<b>)?Câu\s+(\d+)(?:[\.:])?(?:</b>)?(?:\})?[\.:]?'
        segments = re.split(split_pattern, group_text, flags=re.IGNORECASE)
        
        current_global = global_q_counter_start
        
        i = 1
        while i < len(segments):
            q_num_str = segments[i]
            if not q_num_str.isdigit():
                i+=1
                continue
                
            q_content = segments[i+1] if i+1 < len(segments) else ""
            
            current_global += 1
            
            # 1. Normalize LaTeX Math
            q_content = self.normalize_latex(q_content)
            
            # 2. Extract Math
            q_content = self.extract_math(q_content, current_global)
            
            # 3. Clean remaining text formatting
            q_content = self.clean_html_formatting(q_content)

            # Parse Options using the tokens
            option_pattern = r'(__OPT_(?:TRUE|FALSE)_[a-dA-D]__)'
            ops_split = re.split(option_pattern, q_content)

            parts = {
                "id": q_num_str,
                "question": ops_split[0].strip(),
                "answers": [],
                "correct_answer": None
            }
            
            current_answers = []
            truth_map = {}
            
            # ops_split[1] is Token1, [2] is Content1, [3] is Token2...
            for k in range(1, len(ops_split), 2):
                token = ops_split[k]
                val = ops_split[k+1].strip()
                
                # Parse Token
                match = re.search(r'__OPT_(TRUE|FALSE)_([a-dA-D])__', token)
                if match:
                    is_true = (match.group(1) == 'TRUE')
                    key = match.group(2).upper()
                    
                    current_answers.append({
                        "key": key,
                        "content": val
                    })
                    
                    truth_map[key] = is_true

            parts["answers"] = current_answers
            
            # Determine correct_answer format
            true_keys = [k for k, v in truth_map.items() if v]
            
            if len(true_keys) == 1 and len(truth_map) > 1 and len([k for k, v in truth_map.items() if not v]) >= 1:
                if "PHẦN II" in group_text.upper() or "ĐÚNG SAI" in group_text.upper():
                     parts["correct_answer"] = truth_map
                else:
                     if len(true_keys) == 1:
                         parts["correct_answer"] = true_keys[0]
                     else:
                         parts["correct_answer"] = truth_map
                         
            else:
                 parts["correct_answer"] = truth_map

            questions.append(parts)
            i += 2
            
        return questions, current_global

    def parse_questions(self, full_latex_text):
        temp_text = full_latex_text
        temp_text = re.sub(r'\\textbf\{([^\}]+)\}', r'<b>\1</b>', temp_text)
        
        split_pattern = r'(?:^|\n)\s*(?:<b>)?(PHẦN\s+[IVX0-9]+.*?)(?:</b>|$)'
        segments = re.split(split_pattern, temp_text, flags=re.IGNORECASE)
        
        sections = []
        global_counter = 0
        
        if len(segments) < 2:
            qs, global_counter = self.parse_group(full_latex_text, global_counter)
            sections.append({
                "name": "ĐỀ BÀI",
                "questions": qs
            })
            return sections

        i = 1
        while i < len(segments):
            header = segments[i].strip()
            body = segments[i+1] if i+1 < len(segments) else ""
            
            qs, global_counter = self.parse_group(body, global_counter)
            
            sections.append({
                "name": header,
                "questions": qs
            })
            i += 2
            
        return sections

    def run(self, latex_content):
        questions = self.parse_questions(latex_content)
        
        json_path = os.path.join(self.output_folder, "questions.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
            
        return json_path
