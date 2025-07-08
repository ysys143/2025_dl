#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Marp Markdown to Continuous Scroll HTML Converter (v4)
마크다운 슬라이드를 연속 스크롤 HTML로 변환하는 스크립트

markdown2와 pygments를 사용하여 코드 하이라이팅을 포함한 
고품질 마크다운 렌더링을 제공하며, YouTube 임베딩과 링크 자동 변환을 지원합니다.

필요한 라이브러리 설치:
    pip install markdown2 pygments

사용법:
    단일 파일 변환:
        python convert_to_continuous_v4.py <input_markdown_file> [output_html_file]
        
    폴더 일괄 변환:
        python convert_to_continuous_v4.py <input_directory> [output_directory]

기능:
    - YouTube 링크 자동 임베딩
    - URL 자동 하이퍼링크 변환
    - 마크다운 링크 문법 지원
    - 코드 하이라이팅 (Pygments)
    - 반응형 디자인
"""

import re
import os
import sys
from pathlib import Path
import glob
from urllib.parse import urlparse, parse_qs

try:
    import markdown2
except ImportError:
    print("Error: markdown2 library is required. Please install it using:")
    print("pip install markdown2")
    sys.exit(1)

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
    from pygments.formatters import HtmlFormatter
    from pygments.styles import get_style_by_name
    PYGMENTS_AVAILABLE = True
except ImportError:
    print("Warning: pygments library not found. Code highlighting will be disabled.")
    print("Install it using: pip install pygments")
    PYGMENTS_AVAILABLE = False

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

def extract_youtube_id(url):
    """YouTube URL에서 비디오 ID 추출"""
    parsed_url = urlparse(url)
    
    # youtu.be 형식
    if parsed_url.hostname in ['youtu.be', 'www.youtu.be']:
        return parsed_url.path[1:]
    
    # youtube.com 형식
    if parsed_url.hostname in ['youtube.com', 'www.youtube.com']:
        if parsed_url.path == '/watch':
            query_params = parse_qs(parsed_url.query)
            return query_params.get('v', [None])[0]
        elif parsed_url.path.startswith('/embed/'):
            return parsed_url.path.split('/')[2]
    
    return None

def convert_youtube_links(text):
    """YouTube 링크를 임베드로 변환"""
    # YouTube URL 패턴
    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+(?:&[\w=]*)*',
        r'https?://(?:www\.)?youtu\.be/[\w-]+(?:\?[\w=]*)*',
        r'https?://(?:www\.)?youtube\.com/embed/[\w-]+'
    ]
    
    for pattern in youtube_patterns:
        matches = re.finditer(pattern, text)
        for match in reversed(list(matches)):
            url = match.group(0)
            video_id = extract_youtube_id(url)
            
            if video_id:
                # YouTube 임베드 HTML
                embed_html = f'''
<div class="video-container">
    <iframe 
        src="https://www.youtube.com/embed/{video_id}" 
        title="YouTube video player" 
        frameborder="0" 
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
        allowfullscreen>
    </iframe>
</div>'''
                text = text[:match.start()] + embed_html + text[match.end():]
    
    return text

def convert_urls_to_links(text):
    """일반 URL을 하이퍼링크로 변환 (YouTube 제외)"""
    # URL 패턴 (http://, https://, www.)
    url_pattern = r'(?:https?://|www\.)(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s<>]*)?'
    
    def replace_url(match):
        url = match.group(0)
        
        # YouTube URL인지 확인
        if any(domain in url for domain in ['youtube.com', 'youtu.be']):
            return url  # YouTube는 이미 처리됨
        
        # www.로 시작하면 http:// 추가
        if url.startswith('www.'):
            full_url = 'http://' + url
        else:
            full_url = url
        
        # 도메인 추출 (표시용)
        parsed = urlparse(full_url)
        display_text = parsed.netloc or url
        
        return f'<a href="{full_url}" target="_blank" rel="noopener noreferrer">{display_text}</a>'
    
    # HTML 태그 내부가 아닌 URL만 변환
    # 이미 <a> 태그로 감싸져 있거나 href 속성 값인 경우 제외
    results = []
    last_end = 0
    
    # <a> 태그를 찾아서 그 내부는 건너뛰기
    for a_match in re.finditer(r'<a[^>]*>.*?</a>', text, re.DOTALL):
        # <a> 태그 이전 텍스트에서 URL 변환
        before_text = text[last_end:a_match.start()]
        converted = re.sub(url_pattern, replace_url, before_text)
        results.append(converted)
        
        # <a> 태그는 그대로 추가
        results.append(a_match.group(0))
        last_end = a_match.end()
    
    # 마지막 <a> 태그 이후 텍스트 처리
    remaining = text[last_end:]
    converted = re.sub(url_pattern, replace_url, remaining)
    results.append(converted)
    
    return ''.join(results)

def highlight_code_block(match):
    """코드 블록을 Pygments로 하이라이팅"""
    if not PYGMENTS_AVAILABLE:
        # Pygments가 없으면 기본 처리
        code = match.group(2)
        return f'<pre><code>{code}</code></pre>'
    
    language = match.group(1) or 'text'
    code = match.group(2)
    
    try:
        # 언어별 렉서 가져오기
        if language:
            lexer = get_lexer_by_name(language, stripall=True)
        else:
            lexer = guess_lexer(code)
    except:
        lexer = TextLexer()
    
    # Monokai 스타일의 HTML 포매터 사용
    formatter = HtmlFormatter(
        style='monokai',
        noclasses=True,  # 인라인 스타일 사용
        linenos=False,   # 라인 번호 표시 안함
    )
    
    # 하이라이팅된 HTML 생성
    highlighted = highlight(code, lexer, formatter)
    
    # 언어 라벨 추가
    language_label = f'<span class="code-language">{language.upper()}</span>' if language != 'text' else ''
    
    return f'<div class="code-block-wrapper">{language_label}{highlighted}</div>'

def markdown_to_html(text):
    """markdown2를 사용하여 마크다운을 HTML로 변환"""
    
    # 1. 먼저 코드 블록을 플레이스홀더로 보호
    code_blocks = []
    code_block_pattern = r'```[\s\S]*?```'
    
    def save_code_block_temp(match):
        idx = len(code_blocks)
        code_blocks.append(match.group(0))
        return f'%%%TEMPCODE{idx}%%%'
    
    # 코드 블록을 임시로 치환
    text = re.sub(code_block_pattern, save_code_block_temp, text)
    
    # 2. YouTube 링크를 플레이스홀더로 저장 (코드 블록 외부만)
    youtube_embeds = []
    def save_youtube_embed(match):
        url = match.group(0)
        video_id = extract_youtube_id(url)
        
        if video_id:
            idx = len(youtube_embeds)
            embed_html = f'''
<div class="video-container">
    <iframe 
        src="https://www.youtube.com/embed/{video_id}" 
        title="YouTube video player" 
        frameborder="0" 
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
        allowfullscreen>
    </iframe>
</div>'''
            youtube_embeds.append(embed_html)
            return f'%%%YOUTUBE{idx}%%%'
        return url
    
    def save_youtube_markdown_link(match):
        link_text = match.group(1)  # 링크 텍스트
        url = match.group(2)       # URL
        video_id = extract_youtube_id(url)
        
        if video_id:
            idx = len(youtube_embeds)
            embed_html = f'''
<div class="video-container">
    <iframe 
        src="https://www.youtube.com/embed/{video_id}" 
        title="{link_text}" 
        frameborder="0" 
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
        allowfullscreen>
    </iframe>
</div>'''
            youtube_embeds.append(embed_html)
            return f'%%%YOUTUBE{idx}%%%'
        return match.group(0)  # 원본 마크다운 링크 반환
    
    # 1) 마크다운 링크 형식의 YouTube URL 먼저 처리
    markdown_youtube_pattern = r'\[([^\]]+)\]\((https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)[\w-]+(?:\?[\w=]*)*)\)'
    text = re.sub(markdown_youtube_pattern, save_youtube_markdown_link, text)
    
    # 2) 직접 YouTube URL 패턴으로 치환
    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+(?:&[\w=]*)*',
        r'https?://(?:www\.)?youtu\.be/[\w-]+(?:\?[\w=]*)*',
        r'https?://(?:www\.)?youtube\.com/embed/[\w-]+'
    ]
    
    for pattern in youtube_patterns:
        text = re.sub(pattern, save_youtube_embed, text)
    
    # 3. 코드 블록 복원
    for idx, code_block in enumerate(code_blocks):
        text = text.replace(f'%%%TEMPCODE{idx}%%%', code_block)
    
    # 4. Pygments 사용 시 코드 블록 처리
    if PYGMENTS_AVAILABLE:
        # 코드 블록을 임시 플레이스홀더로 치환
        code_blocks = []
        def save_code_block(match):
            idx = len(code_blocks)
            code_blocks.append(highlight_code_block(match))
            return f'%%%CODEBLOCK{idx}%%%'
        
        # 코드 블록 찾아서 치환
        text = re.sub(r'```(\w+)?\n(.*?)```', save_code_block, text, flags=re.DOTALL)
    
    # 5. markdown2 설정
    extras = [
        'fenced-code-blocks',  # ```로 둘러싸인 코드 블록 지원
        'code-friendly',       # 코드 친화적 설정
        'tables',              # 테이블 지원
        'break-on-newline',    # 줄바꿈을 <br>로 변환
        'header-ids',          # 헤더에 ID 자동 생성
        'link-patterns',       # 링크 패턴 지원
    ]
    
    # 링크 패턴 설정 (자동 링크 변환)
    link_patterns = [
        (re.compile(r'(?<!\()https?://[^\s<]+[^\s<\.\)\]]', re.I), r'\g<0>'),
    ]
    
    # 6. 마크다운을 HTML로 변환
    html = markdown2.markdown(text, extras=extras, link_patterns=link_patterns)
    
    # 7. 저장된 코드 블록 복원
    if PYGMENTS_AVAILABLE:
        for idx, code_block in enumerate(code_blocks):
            html = html.replace(f'%%%CODEBLOCK{idx}%%%', code_block)
    
    # 8. YouTube embeds 복원
    for idx, embed in enumerate(youtube_embeds):
        html = html.replace(f'%%%YOUTUBE{idx}%%%', embed)
    
    # 9. 일반 URL을 링크로 변환 (YouTube 제외)
    html = convert_urls_to_links(html)
    
    # 10. YouTube embed를 p 태그에서 분리하여 레이아웃 수정
    html = fix_youtube_embed_layout(html)
    
    return html

def fix_youtube_embed_layout(html):
    """YouTube embed가 p 태그 안에 있으면 밖으로 빼내어 레이아웃 수정"""
    # p 태그 안에 있는 video-container div를 찾아서 p 태그를 분리
    pattern = r'<p>(.*?)<div class="video-container">(.*?)</div>(.*?)</p>'
    
    def replace_embed(match):
        before_text = match.group(1).strip()
        video_html = match.group(2)
        after_text = match.group(3).strip()
        
        result = ""
        
        # 앞쪽 텍스트가 있으면 p 태그로 감싸기
        if before_text:
            # HTML 태그 제거 (br 등)
            clean_before = re.sub(r'<br\s*/?>|</?strong>|</?em>', '', before_text).strip()
            if clean_before:
                result += f"<p>{before_text}</p>\n\n"
        
        # video-container를 독립적으로 배치
        result += f'<div class="video-container">{video_html}</div>'
        
        # 뒤쪽 텍스트가 있으면 p 태그로 감싸기
        if after_text:
            # HTML 태그 제거 (br 등)
            clean_after = re.sub(r'<br\s*/?>|</?strong>|</?em>', '', after_text).strip()
            if clean_after:
                result += f"\n\n<p>{after_text}</p>"
        
        return result
    
    # 한 번만 실행하여 모든 패턴 교체 (무한 루프 방지)
    html = re.sub(pattern, replace_embed, html, flags=re.DOTALL)
    
    return html

def generate_pygments_css():
    """Pygments 스타일 CSS 생성"""
    if not PYGMENTS_AVAILABLE:
        return ""
    
    # Monokai 스타일의 CSS 생성
    formatter = HtmlFormatter(style='monokai')
    css = formatter.get_style_defs()
    
    # 추가 스타일
    additional_css = """
        /* 코드 블록 래퍼 스타일 */
        .code-block-wrapper {
            position: relative;
            margin: 24px 0;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .code-block-wrapper .highlight {
            margin: 0 !important;
            border-radius: 0 !important;
        }
        
        .code-block-wrapper pre {
            margin: 0 !important;
            padding: 24px !important;
            border-radius: 0 !important;
            border: none !important;
            box-shadow: none !important;
        }
        
        /* 언어 라벨 */
        .code-language {
            position: absolute;
            top: 8px;
            right: 8px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 600;
            color: #fff;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            backdrop-filter: blur(10px);
            z-index: 10;
            font-family: 'JetBrains Mono', monospace;
        }
        
        /* 코드 하이라이팅 개선 */
        .highlight {
            line-height: 1.6 !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 14px !important;
        }
        
        /* 다크 테마에서 코드 블록 스타일 */
        .lead-slide .code-block-wrapper {
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        }
        
        .lead-slide .code-language {
            background: rgba(255, 255, 255, 0.2);
        }
        
        /* 비디오 컨테이너 */
        .video-container {
            position: relative;
            width: 100%;
            padding-bottom: 56.25%; /* 16:9 비율 */
            margin: 24px 0;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        }
        
        .video-container iframe {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }
        
        /* 링크 스타일 */
        a {
            color: #0064FF;
            text-decoration: none;
            border-bottom: 1px solid transparent;
            transition: all 0.2s;
        }
        
        a:hover {
            border-bottom-color: #0064FF;
        }
        
        .lead-slide a {
            color: #0064FF;
        }
        
        .lead-slide a:hover {
            border-bottom-color: #0064FF;
            transform: translateY(2px);
        }
    """
    
    return css + additional_css

def generate_html_template(title, phase):
    """HTML 템플릿 생성"""
    pygments_css = generate_pygments_css() if PYGMENTS_AVAILABLE else ""
    
    return f"""<!DOCTYPE html>
<html lang="ko-KR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', system-ui, sans-serif;
            line-height: 1.6;
            color: #1d1d1f;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            overflow-x: hidden;
        }}
        
        /* Layout */
        .main-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            width: 100%;
            padding-left: 192px; /* 스크롤 스파이 공간 */
        }}
        
        .content-wrapper {{
            max-width: 1024px;
            width: 100%;
            padding: 32px;
            margin: 0 auto;
            position: relative;
            left: 40px; /* 살짝 오른쪽으로 이동하여 실제 중앙에 배치 */
        }}
        
        /* Navigation */
        .nav-container {{
            position: fixed;
            top: 33px;
            right: 24px;
            z-index: 40;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        
        .nav-button {{
            background: transparent;
            color: #000;
            border: 1px solid #000;
            border-radius: 0.125rem;
            padding: 12px 20px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            display: block;
            width: auto;
            box-shadow: none;
            opacity: 0.6;
        }}
        
        .nav-button:hover {{
            transform: translateY(-2px);
            background: rgba(0, 0, 0, 0.05);
            opacity: 1.0;
        }}
        
        /* Progress Bar */
        .progress-bar {{
            position: fixed;
            top: 0;
            left: 0;
            height: 3px;
            background: linear-gradient(90deg, #495057 0%, #6c757d 100%);
            z-index: 50;
            transition: width 0.3s;
            box-shadow: 0 2px 8px rgba(108, 117, 125, 0.5);
        }}
        
        /* Scroll Spy */
        .scroll-spy {{
            position: fixed;
            left: 0;
            top: 0;
            bottom: 0;
            width: 192px;
            z-index: 40;
            display: flex;
            align-items: center;
            padding: 0 16px;
        }}
        
        .scroll-spy-item {{
            padding: 2px 8px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 10px;
            line-height: 1.3;
            border-left: 2px solid transparent;
            color: #666;
            box-sizing: border-box;
            overflow: hidden;
            font-style: italic;
            opacity: 0.5;
        }}
        
        .scroll-spy-item:hover {{
            background: #f5f5f5;
            border-left-color: #ddd;
            color: #333;
            opacity: 0.7;
        }}
        
        .scroll-spy-item.active {{
            background: #f0f0f0;
            border-left-color: #000;
            color: #000;
            font-weight: 500;
            opacity: 1.0;
        }}
        
        /* 번호 스타일 제거됨
        .scroll-spy-number {{
            display: inline-block;
            width: 24px;
            font-weight: 500;
            color: #999;
            font-size: 10px;
        }}
        
        .scroll-spy-item.active .scroll-spy-number {{
            color: #000;
        }} */
        
        /* Slides */
        .lead-slide {{
            background: 
                radial-gradient(circle at 20% 80%, rgba(120, 120, 120, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(160, 160, 160, 0.2) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(200, 200, 200, 0.1) 0%, transparent 50%),
                linear-gradient(135deg, #f0f0f2 0%, #e8e8ea 25%, #d8d8da 50%, #c8c8ca 75%, #b8b8ba 100%);
            color: #fff;
            text-align: center;
            padding: 180px 48px;
            margin-bottom: 64px;
            position: relative;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            box-shadow: 
                0 32px 64px rgba(0, 0, 0, 0.08),
                0 16px 32px rgba(0, 0, 0, 0.04),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
            overflow: hidden;
        }}
        
        .lead-slide::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 30% 70%, rgba(255, 255, 255, 0.05) 0%, transparent 70%),
                radial-gradient(circle at 70% 30%, rgba(255, 255, 255, 0.03) 0%, transparent 70%);
            pointer-events: none;
        }}
        
        .lead-slide::after {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: repeating-linear-gradient(
                45deg,
                transparent,
                transparent 200px,
                rgba(255, 255, 255, 0.01) 200px,
                rgba(255, 255, 255, 0.01) 201px
            );
            pointer-events: none;
            animation: subtle-move 20s ease-in-out infinite;
        }}
        
        @keyframes subtle-move {{
            0%, 100% {{ transform: translateX(0) translateY(0); }}
            50% {{ transform: translateX(-20px) translateY(-20px); }}
        }}
        
        .lead-slide h1, .lead-slide h2, .lead-slide h3, .lead-slide p, .lead-slide strong, .lead-slide code, .lead-slide ul, .lead-slide li {{
            color: #fff !important;
            text-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            position: relative;
            z-index: 10;
        }}
        
        .lead-slide h1 {{
            font-size: 64px !important;
            font-weight: 900 !important;
            letter-spacing: -0.02em;
            margin-bottom: 32px !important;
            background: linear-gradient(135deg, #fff 0%, #f0f0f0 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.1));
        }}
        
        .lead-slide h2 {{
            font-size: 28px !important;
            font-weight: 400 !important;
            opacity: 0.9;
            letter-spacing: 0.02em;
            margin-bottom: 48px !important;
        }}
        
        .lead-slide p {{
            font-size: 18px !important;
            font-weight: 300 !important;
            opacity: 0.8;
            letter-spacing: 0.01em;
            line-height: 1.8;
        }}
        
        /* strong 태그의 배경색 제거 */
        .lead-slide strong {{
            background: none !important;
            padding: 0 !important;
            font-weight: 600 !important;
        }}
        
        .slide-card {{
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 48px;
            margin-bottom: 32px;
            border-left: 4px solid #6c757d;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}
        
        .slide-card p, .slide-card strong, .slide-card code, .slide-card ul, .slide-card li {{
            color: #424245;
        }}
        
        .slide-card:hover {{
            box-shadow: 0 16px 48px rgba(0, 0, 0, 0.15);
            transform: translateY(-4px);
            transition: all 0.3s ease;
        }}
        
        /* Typography */
        h1 {{
            font-size: 56px;
            font-weight: 800;
            margin-bottom: 56px;
            line-height: 1.1;
            color: #0064FF;
            opacity: 0.8;
        }}
        
        h2 {{
            font-size: 40px;
            font-weight: 700;
            margin: 24px 0 40px 0;
            color: #0064FF;
            opacity: 0.8;
        }}
        
        h3 {{
            font-size: 28px;
            font-weight: 600;
            margin: 16px 0 32px 0;
            color: #0064FF;
            opacity: 0.8;
        }}
        
        p {{
            margin-bottom: 16px;
            color: #424245;
        }}
        
        strong {{
            font-weight: 700;
            background: #f0f0f0;
            padding: 2px 8px;
        }}
        
        code {{
            font-family: 'JetBrains Mono', monospace;
            background: #f5f5f5;
            color: #333;
            padding: 2px 6px;
            font-size: 14px;
            border-radius: 3px;
        }}
        
        pre {{
            background: #1a1a1a;
            color: #f1f1f1;
            padding: 32px;
            overflow-x: auto;
            margin: 24px 0;
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            line-height: 1.6;
            border-left: 4px solid #6c757d;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
            border: 1px solid #333;
            border-radius: 8px;
        }}
        
        pre code {{
            background: transparent !important;
            color: #f1f1f1 !important;
            padding: 0;
            font-size: inherit;
        }}
        
        /* Pygments 코드 하이라이팅 스타일 */
        {pygments_css}
        
        ul, ol {{
            margin: 24px 0;
            padding-left: 24px;
        }}
        
        li {{
            margin-bottom: 8px;
            color: #424245;
        }}
        
        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 24px 0;
            background: white;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        }}
        
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #e5e5e5;
        }}
        
        th {{
            background: #f5f5f5;
            font-weight: 600;
            color: #333;
        }}
        
        tr:hover {{
            background: #f9f9f9;
        }}
        
        /* Utilities */
        .page-info {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 32px;
            padding-top: 24px;
            border-top: 1px solid #e5e5e5;
        }}
        
        .page-number {{
            font-size: 14px;
            font-weight: 600;
            color: #666;
        }}
        
        .page-label {{
            font-size: 12px;
            color: #999;
            background: #f5f5f5;
            padding: 4px 12px;
        }}
        
        .divider {{
            height: 1px;
            background: #e5e5e5;
            margin: 48px auto;
            max-width: 600px;
        }}
        
        .footer {{
            background: #f5f5f5;
            padding: 32px;
            margin-top: 64px;
            text-align: center;
            border-top: 1px solid #e5e5e5;
        }}
        
        .footer-title {{
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        
        .footer-subtitle {{
            font-size: 14px;
            color: #666;
        }}
        
        /* Hide on small screens */
        @media (max-width: 1024px) {{
            .scroll-spy {{
                display: none;
            }}
            
            .main-container {{
                padding-left: 0; /* 모바일에서는 왼쪽 패딩 제거 */
            }}
            
            .content-wrapper {{
                left: 0; /* 모바일에서는 중앙 보정 제거 */
            }}
            
            .nav-container {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <!-- Progress Bar -->
    <div class="progress-bar" id="progressBar"></div>
    
    <!-- Navigation -->
    <div class="nav-container">
        <button onclick="scrollToTop()" class="nav-button">↑ Top</button>
        <button onclick="scrollToBottom()" class="nav-button">↓ End</button>
    </div>
    
    <!-- Scroll Spy -->
    <div class="scroll-spy" id="scrollSpy">
        <div id="scrollSpyList">
            <!-- Scroll spy items will be generated dynamically -->
        </div>
    </div>

    <div class="main-container">
        <div class="content-wrapper">
"""

def generate_html_footer():
    """HTML 푸터 생성"""
    return """
        <!-- Footer -->
        <footer class="footer">
            <div class="footer-title">AI의 진화: 기계는 생각할 수 있는가?</div>
            <div class="footer-subtitle">위데이터랩 인공지능 트렌드 강연</div>
        </footer>
        </div>
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
        
        // Intersection Observer for slide animations
        const observerOptions = {
            root: null,
            rootMargin: '0px',
            threshold: 0.1
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-slide-in');
                }
            });
        }, observerOptions);
        
        // Observe all slides
        document.addEventListener('DOMContentLoaded', function() {
            const slides = document.querySelectorAll('.slide-card, .lead-slide');
            slides.forEach(slide => {
                observer.observe(slide);
            });
            
            // Initialize scroll spy
            initScrollSpy();
        });
        
        // Scroll spy functionality
        function initScrollSpy() {
            const slides = document.querySelectorAll('[id^="slide-"]');
            const scrollSpyList = document.getElementById('scrollSpyList');
            const scrollSpy = document.getElementById('scrollSpy');
            
            function calculateDynamicSizes() {
                const containerHeight = window.innerHeight;
                const slideCount = slides.length;
                const padding = 32; // top and bottom padding
                const availableHeight = containerHeight - padding;
                
                // Calculate optimal item height (minimum 16px, maximum 30px)
                let itemHeight = Math.max(Math.min(availableHeight / slideCount, 30), 16);
                
                // Calculate font size based on item height
                let fontSize = Math.max(Math.min(itemHeight * 0.6, 12), 8);
                
                // Calculate line height
                let lineHeight = itemHeight * 0.8;
                
                // If items still don't fit, reduce further
                const totalRequiredHeight = itemHeight * slideCount;
                if (totalRequiredHeight > availableHeight) {
                    const scaleFactor = availableHeight / totalRequiredHeight;
                    itemHeight *= scaleFactor;
                    fontSize *= scaleFactor;
                    lineHeight *= scaleFactor;
                }
                
                return {
                    itemHeight: Math.max(itemHeight, 12), // absolute minimum
                    fontSize: Math.max(fontSize, 7), // absolute minimum
                    lineHeight: Math.max(lineHeight, 10) // absolute minimum
                };
            }
            
            function updateScrollSpySizes() {
                const sizes = calculateDynamicSizes();
                document.querySelectorAll('.scroll-spy-item').forEach((item, index) => {
                    item.style.height = sizes.itemHeight + 'px';
                    item.style.fontSize = sizes.fontSize + 'px';
                    item.style.lineHeight = sizes.lineHeight + 'px';
                    
                    // Update title text for screen size
                    const slide = slides[index];
                    if (slide) {
                        const slideTitle = getSlideTitle(slide);
                        const span = item.querySelector('span');
                        if (span) {
                            span.textContent = slideTitle;
                        }
                    }
                });
            }
            
            // Generate scroll spy items
            const initialSizes = calculateDynamicSizes();
            slides.forEach((slide, index) => {
                const slideNumber = slide.id.replace('slide-', '');
                const slideTitle = getSlideTitle(slide);
                
                const spyItem = document.createElement('div');
                spyItem.className = 'scroll-spy-item';
                spyItem.setAttribute('data-slide', slide.id);
                spyItem.style.height = initialSizes.itemHeight + 'px';
                spyItem.style.fontSize = initialSizes.fontSize + 'px';
                spyItem.style.lineHeight = initialSizes.lineHeight + 'px';
                spyItem.style.display = 'flex';
                spyItem.style.alignItems = 'center';
                spyItem.innerHTML = `
                    <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${slideTitle}</span>
                `;
                
                spyItem.addEventListener('click', () => {
                    document.getElementById(slide.id).scrollIntoView({ behavior: 'smooth' });
                });
                
                scrollSpyList.appendChild(spyItem);
            });
            
            // Update active item on scroll
            const spyObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        // Update active spy item
                        document.querySelectorAll('.scroll-spy-item').forEach(item => {
                            item.classList.remove('active');
                        });
                        
                        const activeItem = document.querySelector(`[data-slide="${entry.target.id}"]`);
                        if (activeItem) {
                            activeItem.classList.add('active');
                        }
                    }
                });
            }, {
                rootMargin: '-40% 0px -40% 0px',
                threshold: 0
            });
            
            slides.forEach(slide => {
                spyObserver.observe(slide);
            });
            
            // Handle window resize with debouncing
            let resizeTimeout;
            window.addEventListener('resize', () => {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(() => {
                    updateScrollSpySizes();
                }, 100);
            });
        }
        
        function getSlideTitle(slide) {
            // Calculate max title length based on screen size
            const screenWidth = window.innerWidth;
            let maxLength = 35;
            
            if (screenWidth < 1200) maxLength = 25;
            if (screenWidth < 1000) maxLength = 20;
            if (screenWidth < 800) maxLength = 15;
            
            // Try to get the first heading or first few words of content
            const heading = slide.querySelector('h1, h2, h3');
            if (heading) {
                const text = heading.textContent.trim();
                return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
            }
            
            // If no heading, get first paragraph
            const firstPara = slide.querySelector('p');
            if (firstPara) {
                const text = firstPara.textContent.trim();
                return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
            }
            
            return 'Slide';
        }
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
        title = "AI의 진화: 기계는 생각할 수 있는가? - Phase I"
        phase = "Phase I: AI의 기원과 진화 (1-28장)"
    elif 'part2' in filename:
        title = "AI의 진화: 기계는 생각할 수 있는가? - Phase II"
        phase = "Phase II: 현대 AI와 도전과제 (29-73장)"
    elif 'part3' in filename:
        title = "AI의 진화: 기계는 생각할 수 있는가? - Phase III"
        phase = "Phase III: 실무와 미래 비전 (74-93장)"
    else:
        title = "AI의 진화: 기계는 생각할 수 있는가?"
        phase = "AI 트렌드 강연"
    
    # 슬라이드 파싱
    slides = parse_marp_markdown(content)
    
    if not slides:
        print("오류: 슬라이드를 찾을 수 없습니다.")
        return False
    
    print(f"총 {len(slides)}개의 슬라이드를 발견했습니다.")
    if PYGMENTS_AVAILABLE:
        print("Pygments를 사용하여 코드 하이라이팅을 적용합니다.")
    
    # HTML 생성
    html_content = generate_html_template(title, phase)
    
    for i, slide in enumerate(slides):
        if slide['is_lead']:
            slide_class = "lead-slide"
            slide_id = f"slide-{slide['number']}"
            
            # 마크다운을 HTML로 변환
            slide_html = markdown_to_html(slide['content'])
            
            # 다음 슬라이드가 있으면 링크 추가
            next_slide_link = ""
            if i + 1 < len(slides):
                next_slide_id = f"slide-{slides[i + 1]['number']}"
                next_slide_link = f'<a href="#{next_slide_id}" style="color: inherit; text-decoration: none;">스크롤하여 계속 읽기 ↓</a>'
            else:
                next_slide_link = '스크롤하여 계속 읽기 ↓'
            
            html_content += f'''
        <!-- Lead Slide {slide['number']} -->
        <div class="{slide_class}" id="{slide_id}">
            {slide_html}
            <p style="margin-top: 32px; opacity: 0.8;">{next_slide_link}</p>
        </div>
        '''
        else:
            slide_class = "slide-card"
            slide_id = f"slide-{slide['number']}"
            
            # 마크다운을 HTML로 변환
            slide_html = markdown_to_html(slide['content'])
            
            # 페이지 번호 추가
            page_number = f'''
            <div class="page-info">
                <div class="page-number">{slide["number"]} / {len(slides)}</div>
                <div class="page-label">Slide {slide["number"]}</div>
            </div>
            '''
            
            html_content += f'''
        <!-- Slide {slide['number']} -->
        <div class="{slide_class}" id="{slide_id}">
            {slide_html}
            {page_number}
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

def process_single_file(input_file, output_file=None):
    """단일 파일 처리"""
    # 출력 파일명 생성
    if output_file is None:
        input_path = Path(input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_continuous.html")
    
    print(f"입력 파일: {input_file}")
    print(f"출력 파일: {output_file}")
    
    success = convert_markdown_to_html(input_file, output_file)
    
    if success:
        print(f"✅ 변환 완료: {output_file}")
        return True
    else:
        print(f"❌ 변환 실패: {input_file}")
        return False

def process_directory(input_dir, output_dir=None):
    """디렉토리 내 모든 마크다운 파일 처리"""
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"오류: 디렉토리 '{input_dir}'를 찾을 수 없습니다.")
        return False
    
    if not input_path.is_dir():
        print(f"오류: '{input_dir}'는 디렉토리가 아닙니다.")
        return False
    
    # 출력 디렉토리 설정
    if output_dir is None:
        output_path = input_path / "html_output"
    else:
        output_path = Path(output_dir)
    
    # 출력 디렉토리 생성
    output_path.mkdir(exist_ok=True)
    
    # 마크다운 파일 찾기
    md_files = list(input_path.glob("*.md"))
    
    if not md_files:
        print(f"디렉토리 '{input_dir}'에서 마크다운 파일을 찾을 수 없습니다.")
        return False
    
    print(f"디렉토리 '{input_dir}'에서 {len(md_files)}개의 마크다운 파일을 발견했습니다.")
    print(f"출력 디렉토리: {output_path}")
    print()
    
    success_count = 0
    total_count = len(md_files)
    
    for md_file in md_files:
        output_file = output_path / f"{md_file.stem}_continuous.html"
        
        if process_single_file(str(md_file), str(output_file)):
            success_count += 1
        print()  # 빈 줄 추가
    
    print(f"처리 완료: {success_count}/{total_count}개 파일 변환 성공")
    
    if success_count > 0:
        print(f"출력 디렉토리에서 HTML 파일들을 확인하세요: {output_path}")
        return True
    else:
        print("모든 파일 변환에 실패했습니다.")
        return False

def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법:")
        print("  단일 파일: python convert_to_continuous_v4.py <input_markdown_file> [output_html_file]")
        print("  폴더 처리: python convert_to_continuous_v4.py <input_directory> [output_directory]")
        print()
        print("예시:")
        print("  python convert_to_continuous_v4.py slides_part1_reorganized.md")
        print("  python convert_to_continuous_v4.py marp_md/")
        print("  python convert_to_continuous_v4.py marp_md/ html/")
        return
    
    input_path = Path(sys.argv[1])
    
    # 파일인지 디렉토리인지 확인
    if input_path.is_file():
        # 단일 파일 처리
        output_file = sys.argv[2] if len(sys.argv) >= 3 else None
        success = process_single_file(str(input_path), output_file)
        
        if success:
            print("\n✅ 변환이 성공적으로 완료되었습니다!")
        else:
            print("\n❌ 변환에 실패했습니다.")
            
    elif input_path.is_dir():
        # 디렉토리 처리
        output_dir = sys.argv[2] if len(sys.argv) >= 3 else None
        success = process_directory(str(input_path), output_dir)
        
        if success:
            print("\n✅ 모든 파일 변환이 완료되었습니다!")
        else:
            print("\n❌ 일부 또는 모든 파일 변환에 실패했습니다.")
    else:
        print(f"오류: '{input_path}'는 존재하지 않는 파일 또는 디렉토리입니다.")
        return

if __name__ == "__main__":
    main()