import os
import subprocess

def convert_docx_to_latex(docx_path, output_folder):
    if not os.path.exists(docx_path): return ""
    output_filename = os.path.join(output_folder, "temp_pandoc.tex")
    try:
        cmd = [
            'pandoc', os.path.abspath(docx_path), '-f', 'docx', '-t', 'latex', 
            '--wrap=none', f'--extract-media={os.path.abspath(output_folder)}', 
            '-o', os.path.abspath(output_filename)
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if os.path.exists(output_filename):
            with open(output_filename, 'r', encoding='utf-8') as f:
                content = f.read()
            # Xóa file temp_pandoc.tex sau khi đọc xong
            try:
                os.remove(output_filename)
            except:
                pass
            return content
        return ""
    except: return ""

