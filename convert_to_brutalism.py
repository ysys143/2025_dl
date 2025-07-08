#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Marp Markdown to Brutalism Style HTML Converter
마크다운 슬라이드를 브루탈리즘 스타일 HTML로 변환하는 스크립트
"""

import re
import os
import sys
from pathlib import Path

def parse_marp_markdown(content):
    """마크다운 내용을 파싱하여 슬라이드들을 추출"""
    slides = []
    
    # 줄 단위로 분할
    lines = content.split('\n')
    
    current_slide = []
    slide_number = 1
    yaml_section = True
    
    for line in lines:
        # YAML front matter 건너뛰기
        if yaml_section:
            if line.strip() == '---' and len(current_slide) > 0:
                yaml_section = False
                current_slide = []
                continue
            elif line.strip() == '---':
                current_slide.append(line)
                continue
            else:
                current_slide.append(line)
                continue
        
        # 슬라이드 구분자 찾기
        if line.strip() == '---':
            # 현재 슬라이드 저장
            if current_slide:
                slide_content = '\n'.join(current_slide).strip()
                if slide_content:
                    is_lead = slide_number == 1
                    slides.append({
                        'number': slide_number,
                        'content': slide_content,
                        'is_lead': is_lead
                    })
                    slide_number += 1
            current_slide = []
        else:
            current_slide.append(line)
    
    # 마지막 슬라이드 처리
    if current_slide:
        slide_content = '\n'.join(current_slide).strip()
        if slide_content:
            is_lead = slide_number == 1
            slides.append({
                'number': slide_number,
                'content': slide_content,
                'is_lead': is_lead
            })
    
    return slides

def markdown_to_html(text):
    """마크다운을 HTML로 변환 (Brutalism 스타일)"""
    # 제목 변환
    text = re.sub(r'^# (.+)$', r'<h1 class="brutal-title">\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2 class="brutal-subtitle">\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'<h3 class="brutal-heading">\1</h3>', text, flags=re.MULTILINE)
    
    # 굵은 글씨
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong class="brutal-bold">\1</strong>', text)
    
    # 코드 블록
    text = re.sub(r'```\n(.*?)\n```', r'<pre class="brutal-code-block"><code>\1</code></pre>', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'<code class="brutal-code">\1</code>', text)
    
    # 리스트 처리
    lines = text.split('\n')
    result_lines = []
    in_list = False
    list_type = None
    
    for line in lines:
        line = line.strip()
        if line.startswith('- '):
            if not in_list:
                result_lines.append('<ul class="brutal-list">')
                in_list = True
                list_type = 'ul'
            elif list_type == 'ol':
                result_lines.append('</ol>')
                result_lines.append('<ul class="brutal-list">')
                list_type = 'ul'
            result_lines.append(f'<li class="brutal-list-item">{line[2:]}</li>')
        elif line.startswith('1. ') or re.match(r'^\d+\. ', line):
            if not in_list:
                result_lines.append('<ol class="brutal-list brutal-numbered">')
                in_list = True
                list_type = 'ol'
            elif list_type == 'ul':
                result_lines.append('</ul>')
                result_lines.append('<ol class="brutal-list brutal-numbered">')
                list_type = 'ol'
            content = re.sub(r'^\d+\. ', '', line)
            result_lines.append(f'<li class="brutal-list-item">{content}</li>')
        else:
            if in_list:
                if line.startswith('- ') or re.match(r'^\d+\. ', line):
                    pass  # 이미 처리됨
                else:
                    result_lines.append(f'</{list_type}>')
                    in_list = False
                    list_type = None
                    if line:
                        result_lines.append(f'<p class="brutal-text">{line}</p>')
            else:
                if line:
                    result_lines.append(f'<p class="brutal-text">{line}</p>')
                else:
                    result_lines.append('')
    
    if in_list:
        result_lines.append(f'</{list_type}>')
    
    return '\n'.join(result_lines)

def generate_html_template(title, phase):
    """HTML 템플릿 생성 (Brutalism 스타일)"""
    return f"""<!DOCTYPE html>
<html lang="ko-KR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=Inter:wght@400;700;900&display=swap');
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Inter', monospace;
            font-weight: 400;
            line-height: 1.4;
            color: #000;
            background: #fff;
            overflow-x: hidden;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0;
        }}
        
        /* BRUTALIST TYPOGRAPHY */
        .brutal-title {{
            font-family: 'Inter', sans-serif;
            font-weight: 900;
            font-size: clamp(2rem, 8vw, 4rem);
            line-height: 0.9;
            color: #000;
            text-transform: uppercase;
            letter-spacing: -0.05em;
            margin: 0 0 1rem 0;
            text-shadow: 4px 4px 0px #ff0000;
            transform: rotate(-1deg);
        }}
        
        .brutal-subtitle {{
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: clamp(1.5rem, 5vw, 2.5rem);
            line-height: 1.1;
            color: #000;
            text-transform: uppercase;
            letter-spacing: -0.02em;
            margin: 2rem 0 1rem 0;
            border-left: 8px solid #ff0000;
            padding-left: 1rem;
            transform: rotate(0.5deg);
        }}
        
        .brutal-heading {{
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: clamp(1.2rem, 4vw, 1.8rem);
            line-height: 1.2;
            color: #fff;
            text-transform: uppercase;
            margin: 1.5rem 0 0.5rem 0;
            background: #000;
            padding: 0.5rem;
            border: 3px solid #000;
            display: inline-block;
            transform: rotate(-0.5deg);
        }}
        
        .brutal-text {{
            font-family: 'Inter', sans-serif;
            font-weight: 400;
            font-size: clamp(1rem, 3vw, 1.2rem);
            line-height: 1.4;
            color: #000;
            margin: 1rem 0;
            text-align: left;
        }}
        
        .brutal-bold {{
            font-weight: 700;
            background: #ff0000;
            color: #fff;
            padding: 0.2rem 0.4rem;
            border: 2px solid #000;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-radius: 0;
        }}
        
        .brutal-code {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 400;
            background: #000;
            color: #00ff00;
            padding: 0.2rem 0.4rem;
            border: 2px solid #00ff00;
            font-size: 0.9em;
            border-radius: 0;
        }}
        
        .brutal-code-block {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 400;
            background: #000;
            color: #00ff00;
            padding: 2rem;
            border: 4px solid #00ff00;
            margin: 2rem 0;
            overflow-x: auto;
            font-size: 0.9rem;
            line-height: 1.4;
            border-radius: 0;
        }}
        
        .brutal-list {{
            margin: 1.5rem 0;
            padding-left: 0;
            list-style: none;
        }}
        
        .brutal-list-item {{
            background: #f0f0f0;
            border: 3px solid #000;
            margin: 0.5rem 0;
            padding: 1rem;
            position: relative;
            transform: rotate(0.2deg);
            transition: transform 0.1s ease;
        }}
        
        .brutal-list-item:nth-child(odd) {{
            transform: rotate(-0.2deg);
        }}
        
        .brutal-list-item:hover {{
            transform: rotate(0deg) scale(1.02);
            background: #000;
            color: #fff;
        }}
        
        .brutal-list-item::before {{
            content: "▶";
            position: absolute;
            left: -1.5rem;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1.5rem;
            color: #ff0000;
        }}
        
        .brutal-numbered .brutal-list-item {{
            counter-increment: brutal-counter;
        }}
        
        .brutal-numbered .brutal-list-item::before {{
            content: counter(brutal-counter, decimal-leading-zero);
            left: -2rem;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 1.2rem;
            background: #000;
            color: #fff;
            padding: 0.2rem 0.5rem;
            border: 2px solid #000;
        }}
        
        .brutal-numbered {{
            counter-reset: brutal-counter;
        }}
        
        /* SLIDE STYLES */
        .slide-container {{
            border: 8px solid #000;
            background: #fff;
            margin: 3rem 0;
            padding: 3rem;
            position: relative;
            transform: rotate(0.5deg);
            box-shadow: 16px 16px 0px #000;
        }}
        
        .slide-container:nth-child(even) {{
            transform: rotate(-0.5deg);
            background: #f0f0f0;
            box-shadow: -16px 16px 0px #000;
        }}
        
        .slide-container:nth-child(3n) {{
            background: #000;
            color: #fff;
        }}
        
        .slide-container:nth-child(3n) .brutal-title {{
            color: #ffff00;
            text-shadow: 4px 4px 0px #ff0000;
        }}
        
        .slide-container:nth-child(3n) .brutal-subtitle {{
            color: #fff;
            border-left-color: #ffff00;
        }}
        
        .slide-container:nth-child(3n) .brutal-heading {{
            background: #ffff00;
            color: #000;
        }}
        
        .slide-container:nth-child(3n) .brutal-text {{
            color: #fff;
        }}
        
        .slide-container:nth-child(3n) .brutal-bold {{
            background: #ffff00;
            color: #000;
            border-color: #ffff00;
        }}
        
        .slide-container:nth-child(3n) .brutal-list-item {{
            background: #222;
            color: #fff;
            border-color: #ffff00;
        }}
        
        .slide-container:nth-child(3n) .brutal-list-item:hover {{
            background: #ffff00;
            color: #000;
        }}
        
        .lead-slide {{
            border: 12px solid #000;
            background: #ff0000;
            color: #fff;
            margin: 0 0 4rem 0;
            padding: 4rem;
            text-align: center;
            position: relative;
            transform: none;
            box-shadow: 24px 24px 0px #000;
        }}
        
        .lead-slide::before {{
            content: "BRUTAL";
            position: absolute;
            top: -20px;
            left: 50%;
            transform: translateX(-50%);
            background: #000;
            color: #fff;
            padding: 0.5rem 2rem;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 1.5rem;
            letter-spacing: 0.1em;
        }}
        
        .lead-slide .brutal-title {{
            color: #fff;
            text-shadow: 4px 4px 0px #000;
            transform: none;
            margin-bottom: 2rem;
        }}
        
        .slide-number {{
            position: absolute;
            top: -2rem;
            right: 0;
            background: #000;
            color: #fff;
            padding: 0.5rem 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 1.2rem;
            border: 3px solid #000;
        }}
        
        .divider {{
            height: 20px;
            background: repeating-linear-gradient(
                45deg,
                #000,
                #000 10px,
                #fff 10px,
                #fff 20px
            );
            margin: 4rem 0;
            border: 4px solid #000;
        }}
        
        .navigation {{
            position: fixed;
            top: 2rem;
            right: 2rem;
            z-index: 1000;
        }}
        
        .nav-button {{
            background: #ff0000;
            color: #fff;
            border: 4px solid #000;
            padding: 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 1rem;
            text-transform: uppercase;
            cursor: pointer;
            display: block;
            margin: 0.5rem 0;
            transition: all 0.1s ease;
            box-shadow: 4px 4px 0px #000;
        }}
        
        .nav-button:hover {{
            background: #000;
            color: #ff0000;
            transform: translate(-2px, -2px);
            box-shadow: 8px 8px 0px #ff0000;
        }}
        
        .nav-button:active {{
            transform: translate(0, 0);
            box-shadow: 2px 2px 0px #000;
        }}
        
        .progress-bar {{
            position: fixed;
            top: 0;
            left: 0;
            width: 0%;
            height: 8px;
            background: repeating-linear-gradient(
                90deg,
                #ff0000,
                #ff0000 10px,
                #000 10px,
                #000 20px
            );
            z-index: 1001;
            transition: width 0.3s ease;
            border-bottom: 4px solid #000;
        }}
        
        .footer {{
            background: #000;
            color: #fff;
            padding: 3rem;
            text-align: center;
            margin-top: 4rem;
            border: 8px solid #000;
            position: relative;
        }}
        
        .footer::before {{
            content: "END";
            position: absolute;
            top: -20px;
            left: 50%;
            transform: translateX(-50%);
            background: #ff0000;
            color: #fff;
            padding: 0.5rem 2rem;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 1.5rem;
            letter-spacing: 0.1em;
            border: 3px solid #000;
        }}
        
        .footer-title {{
            font-family: 'Inter', sans-serif;
            font-weight: 900;
            font-size: 2rem;
            text-transform: uppercase;
            margin-bottom: 1rem;
            letter-spacing: -0.02em;
        }}
        
        .footer-subtitle {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 400;
            font-size: 1rem;
            letter-spacing: 0.05em;
        }}
        
        /* RESPONSIVE */
        @media (max-width: 768px) {{
            .slide-container {{
                margin: 2rem 1rem;
                padding: 2rem;
                transform: none;
                box-shadow: 8px 8px 0px #000;
            }}
            
            .lead-slide {{
                margin: 0 1rem 3rem 1rem;
                padding: 2rem;
                box-shadow: 12px 12px 0px #000;
            }}
            
            .navigation {{
                top: 1rem;
                right: 1rem;
            }}
            
            .nav-button {{
                padding: 0.8rem;
                font-size: 0.9rem;
            }}
        }}
        
        /* ANIMATIONS */
        @keyframes brutal-shake {{
            0%, 100% {{ transform: translateX(0); }}
            25% {{ transform: translateX(-2px); }}
            75% {{ transform: translateX(2px); }}
        }}
        
        .slide-container:hover {{
            animation: brutal-shake 0.5s ease-in-out;
        }}
        
        /* GLITCH EFFECT */
        .glitch {{
            position: relative;
        }}
        
        .glitch::before,
        .glitch::after {{
            content: attr(data-text);
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: inherit;
        }}
        
        .glitch::before {{
            animation: glitch-anim 0.3s infinite;
            color: #ff0000;
            z-index: -1;
        }}
        
        .glitch::after {{
            animation: glitch-anim2 0.3s infinite;
            color: #00ff00;
            z-index: -2;
        }}
        
        @keyframes glitch-anim {{
            0% {{ transform: translate(0); }}
            20% {{ transform: translate(-2px, 2px); }}
            40% {{ transform: translate(-2px, -2px); }}
            60% {{ transform: translate(2px, 2px); }}
            80% {{ transform: translate(2px, -2px); }}
            100% {{ transform: translate(0); }}
        }}
        
        @keyframes glitch-anim2 {{
            0% {{ transform: translate(0); }}
            20% {{ transform: translate(2px, 2px); }}
            40% {{ transform: translate(2px, -2px); }}
            60% {{ transform: translate(-2px, 2px); }}
            80% {{ transform: translate(-2px, -2px); }}
            100% {{ transform: translate(0); }}
        }}
    </style>
</head>
<body>
    <!-- Progress Bar -->
    <div class="progress-bar" id="progressBar"></div>
    
    <!-- Navigation -->
    <div class="navigation">
        <button class="nav-button" onclick="scrollToTop()">↑ TOP</button>
        <button class="nav-button" onclick="scrollToBottom()">↓ BOTTOM</button>
    </div>

    <div class="container">
"""

def generate_html_footer():
    """HTML 푸터 생성 (Brutalism 스타일)"""
    return """
        <!-- Footer -->
        <footer class="footer">
            <div class="footer-title">AI의 진화: 기계는 생각할 수 있는가?</div>
            <div class="footer-subtitle">위데이터랩 인공지능 트렌드 강연</div>
        </footer>
    </div>

    <script>
        function scrollToTop() {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
        
        function scrollToBottom() {
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        }
        
        // 스크롤 진행률 표시
        window.addEventListener('scroll', function() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
            const scrollPercent = (scrollTop / scrollHeight) * 100;
            document.getElementById('progressBar').style.width = scrollPercent + '%';
        });
        
        // 글리치 효과를 위한 데이터 속성 추가
        document.addEventListener('DOMContentLoaded', function() {
            const titles = document.querySelectorAll('.brutal-title');
            titles.forEach(title => {
                title.setAttribute('data-text', title.textContent);
                title.classList.add('glitch');
            });
        });
        
        // 랜덤 색상 변경 - 가독성을 고려한 조합만 사용
        function randomizeColors() {
            const colorCombos = [
                { bg: '#000', text: '#fff' },
                { bg: '#fff', text: '#000' },
                { bg: '#ff0000', text: '#fff' },
                { bg: '#000080', text: '#fff' },
                { bg: '#f0f0f0', text: '#000' }
            ];
            
            const elements = document.querySelectorAll('.slide-container');
            
            elements.forEach(element => {
                if (Math.random() > 0.8) {
                    const combo = colorCombos[Math.floor(Math.random() * colorCombos.length)];
                    element.style.backgroundColor = combo.bg;
                    element.style.color = combo.text;
                }
            });
        }
        
        // 5초마다 색상 변경
        setInterval(randomizeColors, 5000);
    </script>
</body>
</html>"""

def convert_markdown_to_html(input_file, output_file):
    """마크다운 파일을 HTML로 변환"""
    
    # 입력 파일 읽기
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"오류: 파일 '{input_file}'을 찾을 수 없습니다.")
        return False
    except Exception as e:
        print(f"오류: 파일 읽기 실패 - {e}")
        return False
    
    # 파일명에서 제목과 phase 추출
    filename = Path(input_file).stem
    if 'part1' in filename:
        title = "AI의 진화: 기계는 생각할 수 있는가? - Phase I [BRUTAL]"
        phase = "Phase I: AI의 기원과 진화 (1-28장)"
    elif 'part2' in filename:
        title = "AI의 진화: 기계는 생각할 수 있는가? - Phase II [BRUTAL]"
        phase = "Phase II: 현대 AI와 도전과제 (29-73장)"
    elif 'part3' in filename:
        title = "AI의 진화: 기계는 생각할 수 있는가? - Phase III [BRUTAL]"
        phase = "Phase III: 실무와 미래 비전 (74-93장)"
    else:
        title = "AI의 진화: 기계는 생각할 수 있는가? [BRUTAL]"
        phase = "AI 트렌드 강연"
    
    # 슬라이드 파싱
    slides = parse_marp_markdown(content)
    
    if not slides:
        print("오류: 슬라이드를 찾을 수 없습니다.")
        return False
    
    print(f"총 {len(slides)}개의 슬라이드를 발견했습니다.")
    
    # HTML 생성
    html_content = generate_html_template(title, phase)
    
    for i, slide in enumerate(slides):
        if slide['is_lead']:
            slide_class = "lead-slide"
            slide_id = f"slide-{slide['number']}"
            
            # 마크다운을 HTML로 변환
            slide_html = markdown_to_html(slide['content'])
            
            html_content += f'''
        <!-- Lead Slide {slide['number']} -->
        <div class="{slide_class}" id="{slide_id}">
            {slide_html}
        </div>
        '''
        else:
            slide_class = "slide-container"
            slide_id = f"slide-{slide['number']}"
            
            # 마크다운을 HTML로 변환
            slide_html = markdown_to_html(slide['content'])
            
            html_content += f'''
        <!-- Slide {slide['number']} -->
        <div class="{slide_class}" id="{slide_id}">
            <div class="slide-number">{slide["number"]}/{len(slides)}</div>
            {slide_html}
        </div>
        '''
        
        # 구분선 추가 (마지막 슬라이드 제외)
        if i < len(slides) - 1:
            html_content += '\n        <div class="divider"></div>\n'
    
    html_content += generate_html_footer()
    
    # 출력 파일 쓰기
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"변환 완료: {output_file}")
        return True
    except Exception as e:
        print(f"오류: 파일 쓰기 실패 - {e}")
        return False

def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python convert_to_brutalism.py <input_markdown_file> [output_html_file]")
        print("예시: python convert_to_brutalism.py slides_part1_reorganized.md")
        return
    
    input_file = sys.argv[1]
    
    # 출력 파일명 생성
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        input_path = Path(input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_brutalism.html")
    
    print(f"입력 파일: {input_file}")
    print(f"출력 파일: {output_file}")
    
    success = convert_markdown_to_html(input_file, output_file)
    
    if success:
        print("✅ BRUTALISM 변환이 성공적으로 완료되었습니다!")
        print(f"브라우저에서 {output_file}을 열어보세요.")
        print("⚠️  주의: 깜빡이는 효과가 있으니 광과민성 발작 주의!")
    else:
        print("❌ 변환에 실패했습니다.")

if __name__ == "__main__":
    main()