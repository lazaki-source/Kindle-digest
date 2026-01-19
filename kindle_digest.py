import feedparser
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup
import time
import re

# Configuration
CONFIG = {
    'feeds': [
        {'name': 'BBC News', 'url': 'http://feeds.bbci.co.uk/news/rss.xml', 'max_articles': 5},
        {'name': 'The Economist', 'url': 'https://www.economist.com/rss', 'max_articles': 5},
        {'name': 'The Verge', 'url': 'https://www.theverge.com/rss/partner/subscriber-only-full-feed/rss.xml', 'max_articles': 5},
    ],
    # Get credentials from environment variables (GitHub Secrets)
    'kindle_email': os.environ.get('KINDLE_EMAIL'),
    'sender_email': os.environ.get('SENDER_EMAIL'),
    'sender_password': os.environ.get('SENDER_PASSWORD'),
}

def fetch_full_article(url):
    """Fetch the full article content from a URL"""
    try:
        print(f"    Fetching full article from {url[:50]}...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
            element.decompose()
        
        # Try common article selectors
        article_content = None
        selectors = [
            'article',
            '[role="article"]',
            '.article-body',
            '.article-content',
            '.story-body',
            '.post-content',
            '.entry-content',
            'main',
        ]
        
        for selector in selectors:
            article_content = soup.select_one(selector)
            if article_content:
                break
        
        if not article_content:
            # Fallback: get main content area
            article_content = soup.find('body')
        
        if article_content:
            # Extract paragraphs
            paragraphs = article_content.find_all('p')
            text_content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
            
            # Basic cleanup
            text_content = text_content.replace('\n\n\n', '\n\n')
            
            if len(text_content) > 200:  # Only return if we got substantial content
                return text_content
        
        return None
        
    except Exception as e:
        print(f"    ✗ Error fetching article: {e}")
        return None

def fetch_articles(feed_url, max_articles=5):
    """Fetch articles from an RSS feed and get full content"""
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        
        for entry in feed.entries[:max_articles]:
            article = {
                'title': entry.get('title', 'No title'),
                'link': entry.get('link', ''),
                'summary': entry.get('summary', entry.get('description', '')),
                'published': entry.get('published', 'Unknown date'),
                'full_content': None
            }
            
            # Fetch full article content
            if article['link']:
                full_content = fetch_full_article(article['link'])
                if full_content:
                    article['full_content'] = full_content
                    print(f"    ✓ Got full article ({len(full_content)} chars)")
                else:
                    print(f"    ⚠ Using summary instead")
                
                # Be nice to servers - small delay between requests
                time.sleep(1)
            
            articles.append(article)
        
        return articles
    except Exception as e:
        print(f"Error fetching feed {feed_url}: {e}")
        return []

def create_html_digest(all_feeds_articles):
    """Create an HTML document with all articles"""
    today = datetime.now().strftime("%B %d, %Y")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="author" content="Claude AI">
        <title>Daily News Digest - {today}</title>
        <style>
            body {{
                font-family: Georgia, serif;
                line-height: 1.6;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1 {{
                color: #333;
                border-bottom: 3px solid #333;
                padding-bottom: 10px;
                page-break-after: avoid;
            }}
            h2 {{
                color: #555;
                margin-top: 40px;
                border-bottom: 2px solid #ddd;
                padding-bottom: 5px;
                page-break-after: avoid;
            }}
            .article {{
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 2px solid #ddd;
                page-break-inside: avoid;
            }}
            .article-title {{
                font-size: 20px;
                font-weight: bold;
                color: #000;
                margin-bottom: 8px;
                page-break-after: avoid;
            }}
            .article-meta {{
                color: #666;
                font-size: 14px;
                margin-bottom: 15px;
                font-style: italic;
            }}
            .article-content {{
                color: #333;
                text-align: justify;
                margin-bottom: 15px;
            }}
            .article-link {{
                color: #0066cc;
                text-decoration: none;
                font-size: 14px;
                display: block;
                margin-top: 10px;
            }}
            .source-divider {{
                margin: 50px 0 30px 0;
                page-break-before: always;
            }}
            .toc {{
                margin: 30px 0;
                padding: 20px;
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                page-break-after: always;
            }}
            .toc h3 {{
                color: #333;
                margin-top: 20px;
                margin-bottom: 10px;
                font-size: 18px;
            }}
            .toc-item {{
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 1px solid #e0e0e0;
            }}
            .toc-title {{
                font-weight: bold;
                color: #0066cc;
                text-decoration: none;
                display: block;
                margin-bottom: 5px;
            }}
            .toc-title:hover {{
                text-decoration: underline;
            }}
            .toc-summary {{
                font-size: 14px;
                color: #666;
                line-height: 1.4;
            }}
        </style>
    </head>
    <body>
        <h1>Daily News Digest</h1>
        <p style="color: #666; font-style: italic;">{today}</p>
    """
    
    # Build table of contents
    html += '\n<div class="toc">\n<h2>Table of Contents</h2>\n'
    
    article_counter = 0
    for feed_data in all_feeds_articles:
        feed_name = feed_data['name']
        articles = feed_data['articles']
        
        if articles:
            html += f'<h3>{feed_name}</h3>\n'
            
            for article in articles:
                article_counter += 1
                article_id = f"article-{article_counter}"
                
                # Create short summary (first 150 chars of content)
                content = article.get('full_content') or article.get('summary', '')
                content = re.sub('<[^<]+?>', '', content).strip()
                short_summary = content[:150] + '...' if len(content) > 150 else content
                
                html += f"""
                <div class="toc-item">
                    <a href="#{article_id}" class="toc-title">{article['title']}</a>
                    <div class="toc-summary">{short_summary}</div>
                </div>
                """
    
    html += '</div>\n'
    
    # Reset counter for article content
    article_counter = 0
    
    for idx, feed_data in enumerate(all_feeds_articles):
        feed_name = feed_data['name']
        articles = feed_data['articles']
        
        if articles:
            divider_class = 'source-divider' if idx > 0 else ''
            html += f'\n<h2 class="{divider_class}">{feed_name}</h2>\n'
            
            for article in articles:
                article_counter += 1
                article_id = f"article-{article_counter}"
                
                # Use full content if available, otherwise use summary
                content = article.get('full_content') or article.get('summary', 'Content not available')
                
                # Clean up content
                content = re.sub('<[^<]+?>', '', content)
                content = content.strip()
                
                # Format paragraphs
                paragraphs = content.split('\n\n')
                formatted_content = ''.join([f'<p>{p.strip()}</p>' for p in paragraphs if p.strip()])
                
                html += f"""
                <div class="article" id="{article_id}">
                    <div class="article-title">{article['title']}</div>
                    <div class="article-meta">{article['published']}</div>
                    <div class="article-content">
                        {formatted_content}
                    </div>
                    <a href="{article['link']}" class="article-link">Original article: {article['link']}</a>
                </div>
                """
    
    html += """
    </body>
    </html>
    """
    
    return html

def send_to_kindle(html_content, config):
    """Send the digest to Kindle via email with HTML attachment"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = config['sender_email']
        msg['To'] = config['kindle_email']
        msg['Subject'] = f"Daily News Digest - {datetime.now().strftime('%B %d, %Y')}"
        
        # Add a simple text body
        body = "Your daily news digest is attached."
        msg.attach(MIMEText(body, 'plain'))
        
        # Create HTML file attachment
        filename = f"Daily News Digest {datetime.now().strftime('%d-%m-%Y')}.html"
        
        # Attach the HTML file
        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(html_content.encode('utf-8'))
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', f'attachment; filename={filename}')
        msg.attach(attachment)
        
        # Connect to Gmail SMTP
        print("Connecting to email server...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(config['sender_email'], config['sender_password'])
        
        # Send email
        print(f"Sending to {config['kindle_email']}...")
        server.send_message(msg)
        server.quit()
        
        print("✓ Digest sent successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error sending email: {e}")
        return False

def main():
    """Main function to orchestrate the digest creation and sending"""
    print(f"\n{'='*50}")
    print(f"RSS to Kindle Digest Generator")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")
    
    all_feeds_articles = []
    
    # Fetch articles from each feed
    for feed in CONFIG['feeds']:
        print(f"Fetching {feed['name']}...")
        articles = fetch_articles(feed['url'], feed['max_articles'])
        all_feeds_articles.append({
            'name': feed['name'],
            'articles': articles
        })
        print(f"  ✓ Processed {len(articles)} articles\n")
    
    # Create HTML digest
    print("Creating digest...")
    html_content = create_html_digest(all_feeds_articles)
    
    # Optionally save to file for testing
    try:
        with open('digest_preview.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("✓ Preview saved to digest_preview.html\n")
    except:
        print("(Preview file not saved - this is normal on GitHub Actions)\n")
    
    # Send to Kindle
    print("Sending to Kindle...")
    success = send_to_kindle(html_content, CONFIG)
    
    if success:
        print(f"\n{'='*50}")
        print("All done! Check your Kindle in a few minutes.")
        print(f"{'='*50}\n")
    else:
        print("\nFailed to send. Please check your email settings.")

if __name__ == "__main__":
    main()
