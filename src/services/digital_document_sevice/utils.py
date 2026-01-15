import hashlib
import base64
import re

def get_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def clean_latex_response(code):
    if not code: return ""
    code = code.replace("```latex", "").replace("```", "").strip()
    match = re.search(r'\\begin\{document\}(.*?)\\end\{document\}', code, re.DOTALL)
    if match: code = match.group(1).strip()
    code = code.replace(r'\[', '').replace(r'\]', '')
    code = code.replace(r'\(', '').replace(r'\)', '')
    code = code.replace(r'$', '') 
    
    math_envs = ['equation', 'align', 'gather', 'split', 'multline']
    for env in math_envs:
        pattern = r'\\begin\{' + env + r'\*?\}(.*?)\\end\{' + env + r'\*?\}'
        while re.search(pattern, code, re.DOTALL):
            code = re.sub(pattern, r'\1', code, flags=re.DOTALL)
            
    code = re.sub(r'\\documentclass\[.*?\]\{.*?\}', '', code)
    code = re.sub(r'\\usepackage\{.*?\}', '', code)
    
    size_commands = [r'\\Huge', r'\\huge', r'\\LARGE', r'\\Large', r'\\large', r'\\normalsize', r'\\small', r'\\footnotesize', r'\\scriptsize', r'\\tiny']
    for cmd in size_commands:
        code = re.sub(cmd + r'\s*', '', code) 
        code = re.sub(cmd + r'\b', '', code)
    return code.strip()

