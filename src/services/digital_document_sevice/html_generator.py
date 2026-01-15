import os
import json

class HtmlGenerator:
    def __init__(self, output_folder):
        self.output_folder = output_folder
        self.questions_path = os.path.join(output_folder, "questions.json")
        self.math_folder = os.path.join(output_folder, "maths")
        self.viewer_path = os.path.join(output_folder, "viewer.html")

    def load_data(self):
        # Load Questions
        if not os.path.exists(self.questions_path):
            return [], {}
            
        with open(self.questions_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
            
        # Load Math Data
        math_data = {}
        if os.path.exists(self.math_folder):
            for filename in os.listdir(self.math_folder):
                file_path = os.path.join(self.math_folder, filename)
                if os.path.isfile(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        math_data[filename] = f.read()
                        
        return questions, math_data

    def generate_html(self, questions, math_data):
        # Embed data as JSON strings
        questions_json = json.dumps(questions, ensure_ascii=False)
        math_json = json.dumps(math_data, ensure_ascii=False)
        
        html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preview Đề Thi Azota Style</title>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary-color: #0056b3; 
            --bg-body: #f4f7f6;
            --card-bg: #ffffff;
            --text-color: #333333;
            --border-color: #e0e0e0;
        }}

        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-body);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}

        .header {{
            background-color: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .header h1 {{ margin: 0; color: var(--primary-color); font-size: 1.5rem; }}
        .header p {{ margin: 5px 0 0; color: #666; font-size: 0.9rem; }}

        .loading {{ text-align: center; font-size: 1.2rem; color: #6b7280; margin-top: 50px; }}

        .section-header {{
            background-color: #e0f2fe;
            color: #0c4a6e;
            padding: 15px;
            margin: 30px 0 20px 0;
            border-radius: 8px;
            border-left: 5px solid #0284c7;
        }}
        .section-header h2 {{ margin: 0; font-size: 1.25rem; }}

        .question-card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.02);
        }}

        .question-card:hover {{ box-shadow: 0 5px 15px rgba(0,0,0,0.08); }}

        .question-header {{ display: flex; align-items: baseline; margin-bottom: 15px; }}

        .question-number {{
            font-weight: 700;
            color: var(--primary-color);
            font-size: 1.1rem;
            margin-right: 10px;
            min-width: 60px;
        }}

        .question-content {{
            font-size: 1rem;
            line-height: 1.6;
            color: #2c3e50;
            width: 100%;
        }}

        .question-content img {{
            max-width: 100%;
            border-radius: 8px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .options-list {{
            margin-top: 20px;
            list-style: none;
            padding: 0;
            display: grid;
            grid-template-columns: 1fr;
            gap: 12px;
        }}
        @media(min-width: 700px) {{ .options-list {{ grid-template-columns: 1fr 1fr; }} }}

        .option-item {{
            display: flex;
            align-items: flex-start;
            padding: 12px 16px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            background: #fafafa;
        }}
        .option-item:hover {{ background-color: #e3f2fd; border-color: var(--primary-color); }}

        .option-key {{ font-weight: 700; color: var(--primary-color); margin-right: 12px; user-select: none; }}
        .option-content-wrapper {{ flex: 1; display: flex; align-items: start; flex-direction: column; }}
        .option-value {{ display: block; }}
        
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; margin-bottom: 4px; }}
        .badge-true {{ background-color: #dcfce7; color: #15803d; border: 1px solid #86efac; }}
        .badge-false {{ background-color: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }}

        .correct-answer {{ background-color: #f0fdf4 !important; border-color: #86efac !important; }}

        mjx-container {{ font-size: 110% !important; }}
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <h1>Đề Thi (Preview)</h1>
        <p>File này hoạt động Offline (Không cần Server)</p>
    </div>

    <div id="content-area"></div>
</div>

<script>
    // --- EMBEDDED DATA START ---
    const QUESTIONS_DATA = {questions_json};
    const MATH_DATA = {math_json};
    const MEDIA_PATH = 'media/';
    // --- EMBEDDED DATA END ---

    function init() {{
        const contentArea = document.getElementById('content-area');
        if (!QUESTIONS_DATA || QUESTIONS_DATA.length === 0) {{
            contentArea.innerHTML = '<div class="loading">Không có dữ liệu câu hỏi.</div>';
            return;
        }}
        renderQuestions(QUESTIONS_DATA, contentArea);
    }}

    function renderQuestions(sections, container) {{
        container.innerHTML = '';
        let htmlBuffer = '';

        if (Array.isArray(sections) && sections.length > 0 && sections[0].questions) {{
            // New Section Format found
            for (const section of sections) {{
                htmlBuffer += `<div class="section-header"><h2>${{section.name}}</h2></div>`;
                
                for (const q of section.questions) {{
                    htmlBuffer += renderSingleQuestion(q);
                }}
            }}
        }} else {{
            // Fallback for flat list
            const flatList = sections;
            for (const q of flatList) {{
                htmlBuffer += renderSingleQuestion(q);
            }}
        }}

        container.innerHTML = htmlBuffer;
        
        if (window.MathJax) {{
            // Only typeset the container, not the whole document (prevents format issues)
            MathJax.typesetPromise([container]).catch(function (err) {{
                console.error('MathJax typeset error:', err);
            }});
        }}
    }}

    function renderSingleQuestion(q) {{
        // Use q.question instead of q.content
        const contentHtml = parseContent(q.question || q.content);
        
        let optionsHtml = '';
        // Use q.answers instead of q.options. Support both for backward compatibility or transition.
        const answers = q.answers || q.options;
        
        if (answers && answers.length) {{
            optionsHtml = '<div class="options-list">';
            for (const opt of answers) {{
                // Use opt.content instead of opt.value
                const optContent = parseContent(opt.content || opt.value);
                
                // Logic to determine status based on q.correct_answer
                let isTrue = false;
                let isFalse = false;
                
                if (q.correct_answer) {{
                    if (typeof q.correct_answer === 'string') {{
                        // MCQ style: "A" - chỉ hiển thị "Đúng" cho đáp án đúng
                        if (q.correct_answer === opt.key) isTrue = true;
                    }} else if (typeof q.correct_answer === 'object') {{
                        // Map style: {{ "A": true, "B": false }}
                        // Kiểm tra xem có đáp án đúng nào không
                        const hasTrueAnswer = Object.values(q.correct_answer).some(v => v === true);
                        
                        if (q.correct_answer[opt.key] === true) {{
                            isTrue = true;
                        }} else if (q.correct_answer[opt.key] === false && hasTrueAnswer) {{
                            // Chỉ hiển thị "Sai" nếu có ít nhất một đáp án đúng
                            // Điều này phân biệt câu hỏi Đúng/Sai (có đáp án đúng) với MCQ không xác định được đáp án đúng
                            // Với MCQ chuẩn nếu tất cả đều false (không xác định được đáp án đúng), không hiển thị badge "Sai"
                            isFalse = true;
                        }}
                        // Nếu tất cả đều false (hasTrueAnswer = false), không hiển thị badge nào
                    }}
                }}
                
                // Badge logic
                let badge = '';
                if (isTrue) {{
                    badge = '<span class="badge badge-true">Đúng</span>';
                }} else if (isFalse) {{
                    badge = '<span class="badge badge-false">Sai</span>';
                }}
                // Với MCQ không xác định được đáp án đúng (tất cả false), không hiển thị badge

                optionsHtml += `
                    <div class="option-item ${{isTrue ? 'correct-answer' : ''}}">
                        <span class="option-key">${{opt.key}}.</span>
                        <div class="option-content-wrapper">
                            ${{badge}}
                            <span class="option-value">${{optContent}}</span>
                        </div>
                    </div>
                `;
            }}
            optionsHtml += '</div>';
        }}

        return `
            <div class="question-card">
                <div class="question-header">
                    <div class="question-number">Câu ${{q.id}}</div>
                    <div class="question-content">${{contentHtml}}</div>
                </div>
                ${{optionsHtml}}
            </div>
        `;
    }}

    function parseContent(text) {{
        if (!text) return '';

        // Images
        // Remove pandocbounded wrapper
        text = text.replace(/\\\\pandocbounded\\{{([^}}]+)\\}}/g, '$1');
        
        // Handle \\includegraphics[options]{{path}} - improved pattern to match correctly
        // Pattern: \\includegraphics[optional options]{{media/path or path}}
        text = text.replace(/\\\\includegraphics(?:\\[[^\\]]*\\])?\\{{([^}}]+)\\}}/g, (m, path) => {{
            // Remove 'media/' prefix if present, we'll add it via MEDIA_PATH
            let filename = path.replace(/^media[\\\\\\/]/, '');
            // Clean up any escaped slashes
            filename = filename.replace(/\\\\\\//g, '/');
            // Return HTML img tag with proper styling
            // Use string concatenation to avoid f-string variable interpolation
            return '<img src="' + MEDIA_PATH + filename + '" loading="lazy" style="max-width: 100%; height: auto; display: block; margin: 10px auto;" />';
        }});

        // Math Placeholders [:$mathname$]
        const regex = /\\[:\\$([^$]+)\\$\\]/g;
        
        text = text.replace(regex, (m, name) => {{
            const latex = MATH_DATA[name];
            if (latex) {{
                // If the content looks like HTML (starts with <), do NOT wrap in math delimiters
                if (latex.trim().startsWith('<') || latex.includes('<b>') || latex.includes('<i>')) {{
                    return latex;
                }}
                 // If it already has delimiters, return as is
                if (latex.trim().startsWith('$') || latex.trim().startsWith('\\\\(')) {{
                    return latex;
                }}
                // Output `\(` and `\)` for MathJax
                // In Python: need 4 backslashes \\\\( to output 2 backslashes \\( in JS string
                // In JS: \\( becomes \( in HTML output, which MathJax recognizes as math inline
                // In JS: \( becomes ( in HTML (no escape), MathJax won't recognize it as math
                // Use string concatenation to avoid f-string template literal escaping issues
                return '\\\\( ' + latex + ' \\\\)';
            }}
            return `[Missing: ${{name}}]`;
        }});

        // Remove newlines/BR immediately after table (user request: "sau table ko cần xuống dòng nữa")
        // Use [\\r\\n]+ to match newlines in regex (escaped for JavaScript)
        text = text.replace(/<\/table>[\s\\r\\n]*/g, '</table>');
        text = text.replace(/<\/table>\s*<br\s*\/?>/gi, '</table>');
        
        // Newlines to BR
        text = text.replace(/\\n/g, '<br>');

        return text;
    }}

    window.addEventListener('DOMContentLoaded', init);
</script>

</body>
</html>
"""
        with open(self.viewer_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return self.viewer_path

    def run(self):
        questions, math_data = self.load_data()
        return self.generate_html(questions, math_data)
