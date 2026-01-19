import feedparser
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
import os
from pathlib import Path

# Configuration
CONFIG = {
    'feeds': [
        {'name': 'BBC News', 'url': 'http://feeds.bbci.co.uk/news/rss.xml', 'max_articles': 5},
        {'name': 'The Telegraph', 'url': 'https://www.telegraph.co.uk/rss.xml', 'max_articles': 5},
        {'name': 'Sky News', 'url': 'https://feeds.skynews.com/feeds/rss/home.xml', 'max_articles': 5},
        {'name': 'TechRadar', 'url': 'https://www.techradar.com/rss', 'max_articles': 5},
        {'name': 'MacRumors', 'url': 'https://www.macrumors.com/feed/', 'max_articles': 5},
        {'name': 'The Verge', 'url': 'https://www.theverge.com/rss/index.xml', 'max_articles': 5},
    ],
    # Email settings - FILL THESE IN
    'kindle_email': 'your_kindle@kindle.com',  # Your Kindle email address
    'sender_email': 'your_email@gmail.com',     # Your Gmail address
    'sender_password': 'your_app_password',     # Gmail app password (NOT your regular password)
}

def fetch_articles(feed_url, max_articles=5):
    """Fetch articles from an RSS feed"""
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        
        for entry in feed.entries[:max_articles]:
            article = {
                'title': entry.get('title', 'No title'),
                'link': entry.get('link', ''),
                'summary': entry.get('summary', entry.get('description', 'No summary available')),
                'published': entry.get('published', 'Unknown date')
            }
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
            }}
            h2 {{
                color: #555;
                margin-top: 30px;
                border-bottom: 2px solid #ddd;
                padding-bottom: 5px;
            }}
            .article {{
                margin-bottom: 25px;
                padding-bottom: 15px;
                border-bottom: 1px solid #eee;
            }}
            .article-title {{
                font-size: 18px;
                font-weight: bold;
                color: #000;
                margin-bottom: 5px;
            }}
            .article-meta {{
                color: #666;
                font-size: 14px;
                margin-bottom: 10px;
            }}
            .article-summary {{
                color: #333;
                margin-bottom: 10px;
            }}
            .article-link {{
                color: #0066cc;
                text-decoration: none;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <h1>Daily News Digest</h1>
        <p style="color: #666; font-style: italic;">{today}</p>
    """
    
    for feed_data in all_feeds_articles:
        feed_name = feed_data['name']
        articles = feed_data['articles']
        
        if articles:
            html += f"\n<h2>{feed_name}</h2>\n"
            
            for article in articles:
                # Clean up summary (remove HTML tags if present)
                summary = article['summary']
                # Basic HTML tag removal
                import re
                summary = re.sub('<[^<]+?>', '', summary)
                summary = summary[:500] + '...' if len(summary) > 500 else summary
                
                html += f"""
                <div class="article">
                    <div class="article-title">{article['title']}</div>
                    <div class="article-meta">{article['published']}</div>
                    <div class="article-summary">{summary}</div>
                    <a href="{article['link']}" class="article-link">Read full article →</a>
                </div>
                """
    
    html += """
    </body>
    </html>
    """
    
    return html

def send_to_kindle(html_content, config):
    """Send the digest to Kindle via email"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = config['sender_email']
        msg['To'] = config['kindle_email']
        msg['Subject'] = f"Daily News Digest - {datetime.now().strftime('%B %d, %Y')}"
        
        # Attach HTML
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
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
        print(f"  ✓ Found {len(articles)} articles\n")
    
    # Create HTML digest
    print("Creating digest...")
    html_content = create_html_digest(all_feeds_articles)
    
    # Optionally save to file for testing
    with open('digest_preview.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("✓ Preview saved to digest_preview.html\n")
    
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
