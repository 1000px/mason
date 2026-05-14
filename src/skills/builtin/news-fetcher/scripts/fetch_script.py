# src/skills/builtin/news_fetcher/fetch_script.py
import requests
import sys
import json

def fetch_news():
    try:
        count = sys.argv[1] if len(sys.argv) > 1 else 5
        
        # 使用 V2EX API (国内访问稳定)
        url = "https://www.v2ex.com/api/topics/hot.json"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        for i, item in enumerate(data[:int(count)]):
            title = item.get('title', 'No Title')
            url = item.get('url', '#')
            content = item.get('content', 'No Content')[:150] # 截取部分预览
            
            snippet = f"""
标题: {title}
链接: {url}
预览: {content}
"""
            results.append(snippet.strip())
        
        if not results:
            sys.stdout.write("未找到相关新闻。")
        else:
            sys.stdout.write("\n---\n".join(results))
            
    except Exception as e:
        sys.stdout.write(f"抓取新闻失败: {str(e)}")

if __name__ == "__main__":
    fetch_news()