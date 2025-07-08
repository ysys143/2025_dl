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
    """일반 URL을 하이퍼링크로 변환 (YouTube 제외), 이미지 URL은 이미지로 삽입"""
    # URL 패턴 (http://, https://, www.)
    url_pattern = r'(?:https?://|www\.)(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s<>]*)?'
    
    def replace_url(match):
        url = match.group(0)
        
        # YouTube URL인지 확인
        if any(domain in url for domain in ['youtube.com', 'youtu.be']):
            return url  # YouTube는 이미 처리됨
        
        # 이미지 URL인지 확인 (이미 처리되었지만 혹시 남아있는 것들)
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.avif']
        if any(url.lower().find(ext) != -1 for ext in image_extensions):
            return url  # 이미지는 이미 처리됨
        
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
    # 이미 <a> 태그, <img> 태그, <div> 태그로 감싸져 있는 경우 제외
    results = []
    last_end = 0
    
    # HTML 태그들을 찾아서 그 내부는 건너뛰기
    for tag_match in re.finditer(r'<(?:a[^>]*>.*?</a>|img[^>]*>|iframe[^>]*>.*?</iframe>|div[^>]*class="(?:video|image)-container"[^>]*>.*?</div>)', text, re.DOTALL):
        # 태그 이전 텍스트에서 URL 변환
        before_text = text[last_end:tag_match.start()]
        converted = re.sub(url_pattern, replace_url, before_text)
        results.append(converted)
        
        # 태그는 그대로 추가
        results.append(tag_match.group(0))
        last_end = tag_match.end()
    
    # 마지막 태그 이후 텍스트 처리
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
    
    # 3. 이미지 URL을 플레이스홀더로 저장
    image_embeds = []
    def save_image_url(match):
        url = match.group(0)
        full_url = url  # 새 패턴은 이미 http/https로 시작
        
        # 이미지 확장자 확인 (패턴에서 이미 확인했지만 한번 더)
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.avif']
        if any(full_url.lower().find(ext) != -1 for ext in image_extensions):
            # 현재 텍스트에서 URL 위치를 찾아서 같은 줄에 :=big이 있는지 확인
            url_index = text.find(url)
            if url_index != -1:
                # URL 이후부터 줄 끝까지의 텍스트 확인
                line_end = text.find('\n', url_index)
                if line_end == -1:
                    line_end = len(text)
                line_after_url = text[url_index:line_end]
                
                is_big = ':=big' in line_after_url
                container_class = "image-container-big" if is_big else "image-container"
            else:
                container_class = "image-container"
            
            idx = len(image_embeds)
            embed_html = f'''
<div class="{container_class}">
    <img src="{full_url}" alt="이미지" loading="lazy" />
</div>'''
            image_embeds.append(embed_html)
            return f'%%%IMAGE{idx}%%%'
        
        return url  # 이미지가 아니면 원본 반환
    
    # 1) 마크다운 이미지 문법 처리 추가
    def save_markdown_image(match):
        alt_text = match.group(1)  # 이미지 설명
        url = match.group(2)       # 이미지 URL
        
        # :=big 옵션 확인
        is_big = False
        if ':=big' in url:
            url = url.replace(':=big', '')
            is_big = True
        
        idx = len(image_embeds)
        container_class = "image-container-big" if is_big else "image-container"
        embed_html = f'''
<div class="{container_class}">
    <img src="{url}" alt="{alt_text}" loading="lazy" />
</div>'''
        image_embeds.append(embed_html)
        return f'%%%IMAGE{idx}%%%'
    
    # 마크다운 이미지 패턴: ![alt text](url)
    markdown_image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    text = re.sub(markdown_image_pattern, save_markdown_image, text)
    
    # 2) 마크다운 링크 형식의 YouTube URL 처리
    markdown_youtube_pattern = r'\[([^\]]+)\]\((https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)[\w-]+(?:\?[\w=]*)*)\)'
    text = re.sub(markdown_youtube_pattern, save_youtube_markdown_link, text)
    
    # 3) 직접 YouTube URL 패턴으로 치환
    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+(?:&[\w=]*)*',
        r'https?://(?:www\.)?youtu\.be/[\w-]+(?:\?[\w=]*)*',
        r'https?://(?:www\.)?youtube\.com/embed/[\w-]+'
    ]
    
    for pattern in youtube_patterns:
        text = re.sub(pattern, save_youtube_embed, text)
    
    # 4) 이미지 URL 패턴으로 치환 (더 포괄적인 패턴 사용)
    image_url_pattern = r'https?://[^\s<>\[\]()]+\.(?:jpg|jpeg|png|gif|webp|svg|bmp|avif)(?:\?[^\s<>\[\]()]*)?'
    text = re.sub(image_url_pattern, save_image_url, text)
    
    # 5) :=big 태그 제거 (이미지 처리 후에 남아있는 것들)
    text = re.sub(r'\s*:=big\s*', ' ', text)
    
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
    
    # 9. 이미지 embeds 복원
    for idx, embed in enumerate(image_embeds):
        html = html.replace(f'%%%IMAGE{idx}%%%', embed)
    
    # 10. 일반 URL을 링크로 변환 (YouTube, 이미지 제외)
    html = convert_urls_to_links(html)
    
    # 11. YouTube embed와 이미지를 p 태그에서 분리하여 레이아웃 수정
    html = fix_youtube_embed_layout(html)
    
    return html

def fix_youtube_embed_layout(html):
    """YouTube embed와 이미지가 p 태그 안에 있으면 밖으로 빼내어 레이아웃 수정"""
    # p 태그 안에 있는 video-container div를 찾아서 p 태그를 분리
    video_pattern = r'<p>(.*?)<div class="video-container">(.*?)</div>(.*?)</p>'
    
    # p 태그 안에 있는 image-container div를 찾아서 p 태그를 분리
    image_pattern = r'<p>(.*?)<div class="image-container">(.*?)</div>(.*?)</p>'
    
    def replace_embed(match):
        before_text = match.group(1).strip()
        embed_html = match.group(2)
        after_text = match.group(3).strip()
        
        # 비디오인지 이미지인지 확인
        if 'iframe' in embed_html:
            container_class = "video-container"
        else:
            container_class = "image-container"
        
        result = ""
        
        # 앞쪽 텍스트가 있으면 p 태그로 감싸기
        if before_text:
            # HTML 태그 제거 (br 등)
            clean_before = re.sub(r'<br\s*/?>|</?strong>|</?em>', '', before_text).strip()
            if clean_before:
                result += f"<p>{before_text}</p>\n\n"
        
        # container를 독립적으로 배치
        result += f'<div class="{container_class}">{embed_html}</div>'
        
        # 뒤쪽 텍스트가 있으면 p 태그로 감싸기
        if after_text:
            # HTML 태그 제거 (br 등)
            clean_after = re.sub(r'<br\s*/?>|</?strong>|</?em>', '', after_text).strip()
            if clean_after:
                result += f"\n\n<p>{after_text}</p>"
        
        return result
    
    # 비디오와 이미지 패턴 모두 처리
    html = re.sub(video_pattern, replace_embed, html, flags=re.DOTALL)
    html = re.sub(image_pattern, replace_embed, html, flags=re.DOTALL)
    
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
        
        /* 이미지 컨테이너 */
        .image-container {
            margin: 24px auto;
            text-align: center;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            background: #fff;
            width: 50%;
            max-width: 512px;
        }
        
        .image-container img {
            width: 100%;
            height: auto;
            display: block;
            margin: 0 auto;
            border-radius: 8px;
            transition: transform 0.3s ease;
        }
        
        .image-container:hover img {
            transform: scale(1.02);
        }
        
        /* 큰 이미지 컨테이너 (:=big 옵션) */
        .image-container-big {
            margin: 24px auto;
            text-align: center;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            background: #fff;
            width: 100%;
            max-width: 800px;
        }
        
        .image-container-big img {
            width: 100%;
            height: auto;
            display: block;
            margin: 0 auto;
            border-radius: 8px;
            transition: transform 0.3s ease;
        }
        
        .image-container-big:hover img {
            transform: scale(1.02);
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

def generate_html_template(title, phase, background_text=""):
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
            top: 33px;
            bottom: 33px;
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
            content: 'AI의 진화: 기계는 생각할 수 있는가?';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            font-size: 120px;
            font-weight: 100;
            color: rgba(255, 255, 255, 0.08);
            word-wrap: break-word;
            overflow: hidden;
            line-height: 1.4;
            letter-spacing: 0.1em;
            filter: blur(2px);
            pointer-events: none;
            animation: text-flow 50s linear infinite;
            z-index: 1;
        }}
        
        @keyframes text-flow {{
            0% {{ transform: translateY(0%) rotate(0deg); }}
            100% {{ transform: translateY(-30%) rotate(1deg); }}
        }}
        
        .lead-slide h1, .lead-slide h3, .lead-slide p, .lead-slide strong, .lead-slide code, .lead-slide ul, .lead-slide li {{
            color: #fff !important;
            text-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            position: relative;
            z-index: 10;
        }}
        
        .lead-slide h1 {{
            font-size: 18px !important;
            font-weight: 400 !important;
            color: #000 !important;
            opacity: 0.7;
            letter-spacing: 0.02em;
            margin-bottom: 16px !important;
            text-shadow: none !important;
            position: relative;
            z-index: 10;
        }}
        
        /* 가장 강력한 CSS 선택자로 h2 스타일 강제 적용 */
        body .main-container .content-wrapper .lead-slide h2,
        html body .main-container .content-wrapper .lead-slide h2,
        .lead-slide h2,
        .lead-slide h2 *,
        div.lead-slide h2,
        .slide-card.lead-slide h2 {{
            font-size: 64px !important;
            font-weight: 900 !important;
            color: #000000 !important;
            opacity: 1.0 !important;
            letter-spacing: -0.02em !important;
            margin: 24px 0 48px 0 !important;
            text-shadow: 0 0 1px rgba(0,0,0,0.8) !important;
            line-height: 1.2 !important;
            background: none !important;
            background-color: transparent !important;
            -webkit-text-fill-color: #000000 !important;
            -webkit-background-clip: unset !important;
            background-clip: unset !important;
            filter: none !important;
            position: relative !important;
            z-index: 10 !important;
        }}
        
        .lead-slide p {{
            font-size: 24px !important;
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
            font-size: 64px;
            font-weight: 800;
            margin-bottom: 48px;
            line-height: 1.1;
            color: #0064FF;
            opacity: 0.8;
        }}
        
        .slide-card h2, .content-wrapper h2:not(.lead-slide h2) {{
            font-size: 48px;
            font-weight: 700;
            margin: 24px 0 36px 0;
            color: #0064FF;
            opacity: 0.8;
        }}
        
        h3 {{
            font-size: 32px;
            font-weight: 600;
            margin: 16px 0 28px 0;
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

def generate_html_footer(prev_file_link=None, next_file_link=None):
    """HTML 푸터 생성"""
    # 버튼 제거 - nav_html 변수 삭제
    
    # 스크롤 이벤트로 이전/다음 페이지 이동을 위한 스크립트 추가
    scroll_navigation_script = ""
    if prev_file_link or next_file_link:
        scroll_navigation_script = f'''
        <script>
        // 스크롤로 이전/다음 파트 이동
        (function() {{
            let hasTriggeredNext = false;
            let hasTriggeredPrev = false;
            let isAtBottom = false;
            let isAtTop = false;
            
            function checkScrollPosition() {{
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                const scrollHeight = document.documentElement.scrollHeight;
                const clientHeight = window.innerHeight;
                const scrolledToBottom = Math.ceil(scrollTop + clientHeight) >= scrollHeight - 5;
                const scrolledToTop = scrollTop <= 5;
                
                // 페이지 끝에 도달
                if (scrolledToBottom && !hasTriggeredNext && '{next_file_link}' && '{next_file_link}' !== 'None') {{
                    isAtBottom = true;
                    // 페이지 끝에 도달했을 때 안내 메시지 표시
                    if (!document.getElementById('scrollHintBottom')) {{
                        const hint = document.createElement('div');
                        hint.id = 'scrollHintBottom';
                        hint.style.cssText = 'position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: rgba(0, 100, 255, 0.9); color: white; padding: 16px 32px; border-radius: 50px; font-weight: 600; z-index: 1000; transition: opacity 0.3s ease;';
                        hint.textContent = '계속 스크롤하여 다음 파트로 이동';
                        document.body.appendChild(hint);
                        
                        setTimeout(() => {{
                            hint.style.opacity = '0';
                            setTimeout(() => hint.remove(), 300);
                        }}, 3000);
                    }}
                }} else if (!scrolledToBottom) {{
                    isAtBottom = false;
                    hasTriggeredNext = false;
                }}
                
                // 페이지 맨 위에 도달
                if (scrolledToTop && !hasTriggeredPrev && '{prev_file_link}' && '{prev_file_link}' !== 'None') {{
                    isAtTop = true;
                    // 페이지 맨 위에 도달했을 때 안내 메시지 표시
                    if (!document.getElementById('scrollHintTop')) {{
                        const hint = document.createElement('div');
                        hint.id = 'scrollHintTop';
                        hint.style.cssText = 'position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: rgba(108, 117, 125, 0.9); color: white; padding: 16px 32px; border-radius: 50px; font-weight: 600; z-index: 1000; transition: opacity 0.3s ease;';
                        hint.textContent = '계속 스크롤하여 이전 파트로 이동';
                        document.body.appendChild(hint);
                        
                        setTimeout(() => {{
                            hint.style.opacity = '0';
                            setTimeout(() => hint.remove(), 300);
                        }}, 3000);
                    }}
                }} else if (!scrolledToTop) {{
                    isAtTop = false;
                    hasTriggeredPrev = false;
                }}
            }}
            
            // 휠 이벤트로 페이지 끝/시작에서 추가 스크롤 감지
            window.addEventListener('wheel', function(e) {{
                // 아래로 스크롤 - 다음 파트로 이동
                if (isAtBottom && e.deltaY > 0 && !hasTriggeredNext && '{next_file_link}' && '{next_file_link}' !== 'None') {{
                    hasTriggeredNext = true;
                    setTimeout(() => {{
                        window.location.href = '{next_file_link}';
                    }}, 300);
                }}
                
                // 위로 스크롤 - 이전 파트로 이동
                if (isAtTop && e.deltaY < 0 && !hasTriggeredPrev && '{prev_file_link}' && '{prev_file_link}' !== 'None') {{
                    hasTriggeredPrev = true;
                    setTimeout(() => {{
                        // 이전 페이지의 맨 아래로 이동
                        window.location.href = '{prev_file_link}#scroll-to-bottom';
                    }}, 300);
                }}
            }});
            
            window.addEventListener('scroll', checkScrollPosition);
            
            // URL에 #scroll-to-bottom이 있으면 페이지 맨 아래로 스크롤
            if (window.location.hash === '#scroll-to-bottom') {{
                setTimeout(() => {{
                    window.scrollTo({{ top: document.body.scrollHeight, behavior: 'smooth' }});
                    // 해시 제거
                    history.replaceState(null, null, window.location.pathname);
                }}, 100);
            }}
            
            // 초기 체크
            checkScrollPosition();
        }})();
        </script>
        '''
    
    return f"""
        <!-- Footer -->
        <footer class="footer">
            <div class="footer-title">AI의 진화: 기계는 생각할 수 있는가?</div>
            <div class="footer-subtitle">위데이터랩 인공지능 트렌드 강연</div>
        </footer>
        </div>
    </div>
    {scroll_navigation_script}

    <script>
        function scrollToTop() {{
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}
        
        function scrollToBottom() {{
            window.scrollTo({{ top: document.body.scrollHeight, behavior: 'smooth' }});
        }}
        
        // 스크롤 진행률 표시
        window.addEventListener('scroll', function() {{
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
            const scrollPercent = (scrollTop / scrollHeight) * 100;
            document.getElementById('progressBar').style.width = scrollPercent + '%';
        }});
        
        // Intersection Observer for slide animations
        const observerOptions = {{
            root: null,
            rootMargin: '0px',
            threshold: 0.1
        }};
        
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.classList.add('animate-slide-in');
                }}
            }});
        }}, observerOptions);
        
        // Observe all slides
        document.addEventListener('DOMContentLoaded', function() {{
            const slides = document.querySelectorAll('.slide-card, .lead-slide');
            slides.forEach(slide => {{
                observer.observe(slide);
            }});
            
            // Initialize scroll spy
            initScrollSpy();
        }});
        
        // Scroll spy functionality
        function initScrollSpy() {{
            const slides = document.querySelectorAll('[id^="slide-"]');
            const scrollSpyList = document.getElementById('scrollSpyList');
            const scrollSpy = document.getElementById('scrollSpy');
            
            function calculateDynamicSizes() {{
                const containerHeight = window.innerHeight;
                const slideCount = slides.length;
                const padding = 66; // top (33px) and bottom (33px) padding to match nav buttons
                const availableHeight = containerHeight - padding;
                
                // Calculate optimal item height (minimum 16px, maximum 30px)
                let itemHeight = Math.max(Math.min(availableHeight / slideCount, 30), 16);
                
                // Calculate font size based on item height
                let fontSize = Math.max(Math.min(itemHeight * 0.6, 12), 8);
                
                // Calculate line height
                let lineHeight = itemHeight * 0.8;
                
                // If items still don't fit, reduce further
                const totalRequiredHeight = itemHeight * slideCount;
                if (totalRequiredHeight > availableHeight) {{
                    const scaleFactor = availableHeight / totalRequiredHeight;
                    itemHeight *= scaleFactor;
                    fontSize *= scaleFactor;
                    lineHeight *= scaleFactor;
                }}
                
                return {{
                    itemHeight: Math.max(itemHeight, 12), // absolute minimum
                    fontSize: Math.max(fontSize, 7), // absolute minimum
                    lineHeight: Math.max(lineHeight, 10) // absolute minimum
                }};
            }}
            
            function updateScrollSpySizes() {{
                const sizes = calculateDynamicSizes();
                document.querySelectorAll('.scroll-spy-item').forEach((item, index) => {{
                    item.style.height = sizes.itemHeight + 'px';
                    item.style.fontSize = sizes.fontSize + 'px';
                    item.style.lineHeight = sizes.lineHeight + 'px';
                    
                    // Update title text for screen size
                    const slide = slides[index];
                    if (slide) {{
                        const slideTitle = getSlideTitle(slide);
                        const span = item.querySelector('span');
                        if (span) {{
                            span.textContent = slideTitle;
                        }}
                    }}
                }});
            }}
            
            // Generate scroll spy items
            const initialSizes = calculateDynamicSizes();
            slides.forEach((slide, index) => {{
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
                    <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${{slideTitle}}</span>
                `;
                
                spyItem.addEventListener('click', () => {{
                    document.getElementById(slide.id).scrollIntoView({{ behavior: 'smooth' }});
                }});
                
                scrollSpyList.appendChild(spyItem);
            }});
            
            // Update active item on scroll
            const spyObserver = new IntersectionObserver((entries) => {{
                entries.forEach(entry => {{
                    if (entry.isIntersecting) {{
                        // Update active spy item
                        document.querySelectorAll('.scroll-spy-item').forEach(item => {{
                            item.classList.remove('active');
                        }});
                        
                        const activeItem = document.querySelector(`[data-slide="${{entry.target.id}}"]`);
                        if (activeItem) {{
                            activeItem.classList.add('active');
                        }}
                    }}
                }});
            }}, {{
                rootMargin: '-40% 0px -40% 0px',
                threshold: 0
            }});
            
            slides.forEach(slide => {{
                spyObserver.observe(slide);
            }});
            
            // Handle window resize with debouncing
            let resizeTimeout;
            window.addEventListener('resize', () => {{
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(() => {{
                    updateScrollSpySizes();
                }}, 100);
            }});
        }}
        
        function getSlideTitle(slide) {{
            // Calculate max title length based on screen size
            const screenWidth = window.innerWidth;
            let maxLength = 35;
            
            if (screenWidth < 1200) maxLength = 25;
            if (screenWidth < 1000) maxLength = 20;
            if (screenWidth < 800) maxLength = 15;
            
            // Try to get the first heading or first few words of content
            const heading = slide.querySelector('h1, h2, h3');
            if (heading) {{
                const text = heading.textContent.trim();
                return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
            }}
            
            // If no heading, get first paragraph
            const firstPara = slide.querySelector('p');
            if (firstPara) {{
                const text = firstPara.textContent.trim();
                return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
            }}
            
            return 'Slide';
        }}
        
    </script>
</body>
</html>"""

def extract_background_text(slides):
    """슬라이드 콘텐츠에서 배경 텍스트 추출"""
    import re
    
    all_text = ""
    for slide in slides:
        # 마크다운에서 텍스트만 추출 (코드 블록, URL 등 제외하지만 헤더는 포함)
        text = slide['content']
        
        # 헤더 마크다운 제거하되 텍스트는 유지 (# ## ### 제거)
        text = re.sub(r'^#+\s+(.*)$', r'\1', text, flags=re.MULTILINE)
        
        # 코드 블록 제거
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`[^`]+`', '', text)
        
        # 링크 제거하되 텍스트는 유지 ([텍스트](URL) → 텍스트)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # URL 제거
        text = re.sub(r'https?://[^\s]+', '', text)
        
        # 특수 문자 정리 (** __ 등)
        text = re.sub(r'[*_~\[\](){}]', '', text)
        text = re.sub(r'\s+', ' ', text)
        
        # 빈 문자열이 아닌 경우에만 추가
        clean_text = text.strip()
        if clean_text:
            all_text += clean_text + " "
    
    # 배경용 텍스트를 적당한 길이로 반복
    background_words = all_text.split()[:60]  # 60개 단어로 증가
    background_text = " ".join(background_words)
    
    # 텍스트가 너무 짧으면 반복
    while len(background_text) < 300:
        background_text += " " + " ".join(background_words[:30])
    
    return background_text[:600]  # 최대 600자로 증가

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
    
    # 파일명에서 제목과 phase 추출, 이전/다음 파일 링크 결정
    filename = Path(input_file).stem
    prev_file_link = None
    next_file_link = None
    
    if 'part1' in filename:
        title = "AI의 진화: 기계는 생각할 수 있는가? - Phase I"
        phase = "Phase I: AI의 기원과 진화"
        prev_file_link = None  # 첫 번째 파트는 이전 링크 없음
        next_file_link = "slides_part2_continuous.html"
    elif 'part2' in filename:
        title = "AI의 진화: 기계는 생각할 수 있는가? - Phase II"
        phase = "Phase II: 현대 AI와 도전과제"
        prev_file_link = "slides_part1_continuous.html"
        next_file_link = "slides_part3_continuous.html"
    elif 'part3' in filename:
        title = "AI의 진화: 기계는 생각할 수 있는가? - Phase III"
        phase = "Phase III: 실무와 미래 비전"
        prev_file_link = "slides_part2_continuous.html"
        next_file_link = None  # 마지막 파트는 다음 링크 없음
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
    
    # 배경 텍스트 추출
    background_text = extract_background_text(slides)
    
    # HTML 생성
    html_content = generate_html_template(title, phase, background_text)
    
    for i, slide in enumerate(slides):
        if slide['is_lead']:
            slide_class = "lead-slide"
            slide_id = f"slide-{slide['number']}"
            
            # 표지 슬라이드는 커스텀 HTML 구조 사용
            next_slide_link = ""
            if i + 1 < len(slides):
                next_slide_id = f"slide-{slides[i + 1]['number']}"
                next_slide_link = f'<a href="#{next_slide_id}" style="color: inherit; text-decoration: none;">스크롤하여 계속 읽기 ↓</a>'
            else:
                next_slide_link = '스크롤하여 계속 읽기 ↓'
            
            html_content += f'''
        <!-- Lead Slide {slide['number']} -->
        <div class="{slide_class}" id="{slide_id}">
            <h1>위데이터랩 인공지능 트렌드 강연</h1>
            <h2>{phase}</h2>
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
    
    html_content += generate_html_footer(prev_file_link, next_file_link)
    
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