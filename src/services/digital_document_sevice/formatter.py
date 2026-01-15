import re

def apply_ultimate_rules(text):
    # 1. Clean Delimiters (Fix \( ... \) issues) --
    # Handle cases where pandoc escapes backslashes
    text = text.replace(r'\\(', '$').replace(r'\\)', '$')
    text = text.replace(r'\(', '$').replace(r'\)', '$')
    text = text.replace(r'\[', '$').replace(r'\]', '$')
    text = text.replace('$$', '$').replace(r'\\)', '$')
    text = text.replace(r'\(', '$').replace(r'\)', '$')
    text = text.replace(r'\[', '$').replace(r'\]', '$')
    text = text.replace('$$', '$')
    
    # 2. Physics & Math cleanup --
    text = text.replace('\uf02d', '-') 
    text = re.sub(r'ν\s*([xy])', r'v_{\1}', text) 
    text = re.sub(r'\\nu(?=[_]?[xy])', 'v', text)
    
    # Fix common LaTeX formatting issues from Pandoc
    # PRIORITY 1: Fix \\ ^{\\circ} or \ ^{\circ} or \^{\circ} -> ^{\circ} (remove backslash before caret in degree symbol)
    # Fix double escape: \\ ^{\\circ} -> ^{\circ}
    text = re.sub(r'\\\\\s+\^\\circ', r'^{\\circ}', text)
    text = re.sub(r'\\\\\s*\^\\circ', r'^{\\circ}', text)
    # Fix single escape: \ ^{\circ} or \^{\circ} -> ^{\circ}
    text = re.sub(r'\\\s+\^\\circ', r'^{\\circ}', text)
    text = re.sub(r'\\\s*\^\\circ', r'^{\\circ}', text)
    text = re.sub(r'\\\^\\circ', r'^{\\circ}', text)
    
    # PRIORITY 2: Fix \text{ } (space in text command) -> regular space (not \, for better compatibility)
    text = re.sub(r'\$([^$]*?)\\text\{\s+\}([^$]*?)\$', r'$\1 \2$', text)
    
    # PRIORITY 3: Replace \, with regular space for better compatibility
    text = re.sub(r'\$([^$]*?)\\\,([^$]*?)\$', r'$\1 \2$', text) 
    
    # Auto-add degree symbol for trig functions
    # Pattern: sin(90 - a) -> sin(90^\circ - a)
    text = re.sub(r'\\(sin|cos|tan|cot)\s*\(\s*(90|180|270|360)\s*(-)', r'\\\1(\2^\\circ \3', text)
    
    greek_map = {
        'α': r'\alpha', 'β': r'\beta', 'γ': r'\gamma', 'δ': r'\delta', 
        'ε': r'\varepsilon', 'θ': r'\theta', 'λ': r'\lambda', 'μ': r'\mu', 
        'π': r'\pi', 'ρ': r'\rho', 'σ': r'\sigma', 
        'τ': r'\tau', 'φ': r'\varphi', 'ω': r'\omega', 'Δ': r'\Delta'
    }
    for char, latex in greek_map.items():
        text = text.replace(char, latex)
    
    text = text.replace('Góc tạo bởi vận tốc', 'Góc tạo bởi vectơ vận tốc')
    
    parts = text.split('$')
    new_parts = []
    
    for i, part in enumerate(parts):
        if i % 2 == 0: 
            # Text Mode
            part = re.sub(r'\b(Ox|Oy|Oz)\b', r'$\1$', part)
            part = re.sub(r'\\tan\s+\\alpha', r'$\\tan \\alpha$', part)
            part = re.sub(r'\\tan\s+\\beta', r'$\\tan \\beta$', part)
            part = part.replace('ν', 'v') 
            eq_pattern = r'\b([vV](?:_?\{?[xy]\}?)|F|a|d)\s*=\s*(\d+(?:,\d+)?)\s*([cmk]?m/[s^2]+|[cmk]?m|kg|s|Hz|J|N|W)\b'
            part = re.sub(eq_pattern, r'$\1 = \2\,\\text{\3}$', part)
            part = re.sub(r'(?<!\$)\\alpha(?!\$)', r'$\\alpha$', part)
        else: 
            # Math Mode
            # PRIORITY 1: Fix \\ ^{\\circ} or \ ^{\circ} (backslash space before degree) -> ^{\circ}
            # Fix double escape: \\ ^{\\circ} -> ^{\circ}
            part = re.sub(r'\\\\\s+\^\\circ', r'^{\\circ}', part)
            part = re.sub(r'\\\\\s*\^\\circ', r'^{\\circ}', part)
            # Fix single escape: \ ^{\circ} or \^{\circ} -> ^{\circ}
            part = re.sub(r'\\\s+\^\\circ', r'^{\\circ}', part)
            part = re.sub(r'\\\s*\^\\circ', r'^{\\circ}', part)
            part = re.sub(r'\\\^\\circ', r'^{\\circ}', part)
            
            # PRIORITY 2: Fix \text{ } (with space) -> regular space (not \, for better compatibility)
            part = re.sub(r'\\text\{\s+\}', r' ', part)  # \text{ } -> space (better than \, which only works in math mode)
            
            # PRIORITY 3: Replace \, with regular space for better compatibility outside math rendering
            part = re.sub(r'\\,', r' ', part)
            
            # Don't add \, here - use regular space for better compatibility
            part = re.sub(r'(\d+(?:,\d+)?)\s*([cmk]?m/[s^2]+|[cmk]?m|kg|s|Hz|J|N|W)\b', r'\1 \\text{\2}', part)
            part = re.sub(r'\\nu(?=[_]?[xy])', 'v', part) 
        new_parts.append(part)
        
    text = '$'.join(new_parts)
    text = text.replace('$$', '$') 
    return text

def format_latex_content(latex_text):
    # Pre-processing: Fix common Pandoc LaTeX formatting issues
    # PRIORITY 1: Fix \\ ^{\\circ} or \ ^{\circ} or \^{\circ} -> ^{\circ} (remove backslash/space before caret)
    # Fix double escape: \\ ^{\\circ} -> ^{\circ}
    text = re.sub(r'\\\\\s+\^\\circ', r'^{\\circ}', latex_text)
    text = re.sub(r'\\\\\s*\^\\circ', r'^{\\circ}', text)
    # Fix single escape: \ ^{\circ} or \^{\circ} -> ^{\circ}
    text = re.sub(r'\\\s+\^\\circ', r'^{\\circ}', text)
    text = re.sub(r'\\\s*\^\\circ', r'^{\\circ}', text)
    text = re.sub(r'\\\^\\circ', r'^{\\circ}', text)
    
    # PRIORITY 2: Fix \text{ } (space in text command) -> regular space (not \, for better compatibility)
    text = re.sub(r'\\text\{\s+\}', r' ', text)
    
    # PRIORITY 3: Replace \, with regular space for better compatibility
    text = re.sub(r'\\,', r' ', text)
    
    text = apply_ultimate_rules(text)
    
    # 3. Angle Notation Fix: \angle ABC -> \overline{ABC} (User request visual match)
    text = re.sub(r'\\angle\s+([A-Z]{3})', r'\\overline{\1}', text)
    text = re.sub(r'\\angle\s+([A-Z]{1})', r'\\overline{\1}', text)
    text = re.sub(r'\\angle\{([A-Z]{3})\}', r'\\overline{\1}', text)
    
    # 4. Fix Scalar-Vector Order: \vec{a}k -> k\vec{a}
    # User feedback: "k cannot be on the right of vector"
    def move_scalar_left(match):
        vec_part = match.group(1)
        scalar = match.group(2)
        return f"{scalar}{vec_part}"

    # Pattern: \overrightarrow{...} followed by k or number
    text = re.sub(r'((?:\\overrightarrow|\\vec|\\overline|\\widehat)\{[^}]+\})\s*([kK])\b', move_scalar_left, text)
    
    # Pattern: ( \vec{a} + \vec{b} ) k
    text = re.sub(r'(\([^\)]*(?:\\overrightarrow|\\vec|\\overline|\\widehat)[^\)]*\))\s*([kK])\b', move_scalar_left, text)
    
    text = re.sub(r'\\textbf\{\\ul\{([A-Da-d])\}\.\}', r'\\textbf{\1.}', text)
    label_pattern = r'(\\textbf\{[A-Da-d][\.\)]\})'
    pattern_inline = r'([^\n])(\s*)' + label_pattern
    formatted_text = re.sub(pattern_inline, r'\1\n\n\3', text)
    # Collapse multiple newlines to max 2
    formatted_text = re.sub(r'\n{3,}', '\n\n', formatted_text)
    return formatted_text

def write_full_latex_file(content, output_path):
    header = r"""\PassOptionsToPackage{final}{graphicx}
\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[vietnamese]{babel}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{left=2cm, right=2cm, top=2cm, bottom=2cm}
\usepackage[export]{adjustbox}
\usepackage{float}
\usepackage{soul}
\usepackage{soul}
\usepackage{ulem}
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{array}
\usepackage{calc}
\usepackage{multirow}
\newcolumntype{Y}{>{\centering\arraybackslash}X}
\newcommand{\vv}[1]{\overrightarrow{#1}}
\newcommand{\pandocbounded}[1]{#1}
\newcommand{\real}[1]{#1}
\setlength{\parindent}{0pt}
\setlength{\parskip}{1.0em}
\begin{document}
"""
    footer = r"\end{document}"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(header + content + footer)

