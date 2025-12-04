import os
import json
import requests
import time
from openai import OpenAI
from datetime import datetime, timedelta
from dotenv import load_dotenv  # <--- Add this import

# Force Python to look for .env in the same folder as the script
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)

# Now try to get the key
API_KEY = os.getenv("OPENAI_API_KEY")

# Debugging print (it will print "None" if it fails, or "sk-..." if it works)
# print(f"DEBUG: Key loaded is: {API_KEY}") 

if not API_KEY:
    raise ValueError(f"No API Key found! Checked path: {env_path}")


AFFILIATE_TAG = "your-tag-20"
OUTPUT_DIR = "public/content"
# ---------------------


client = OpenAI(api_key=API_KEY)

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_book_recommendation(exclude_list):
    """
    Asks AI for a book with a specific "Smart Friend" persona.
    """
    exclusions = ", ".join(exclude_list)
    
    # We define the persona and constraints strictly here
    system_instruction = """
    You are a smart, 30-year-old book lover recommending a book to a close friend over coffee.
    
    TONE GUIDELINES:
    1.  **Casual & Grounded:** distinctively conversational. Use contractions (it's, can't). 
    2.  **No Fluff:** Do NOT use words like "masterpiece," "magnum opus," "breathtaking," "seminal," or "essential."
    3.  **No Moralizing:** Don't tell the user what they will learn or how they will become a better person.
    4.  **No Spoilers:** Just the hook.
    5.  **Specifics over Generalities:** Don't say "It explores the human condition." Say "It explores why we lie to our spouses."
    
    The goal is intrigue, not homework.
    """

    prompt = f"""
    Select a distinct "modern or ancient classic" from world literature.
    CRITICAL: Do NOT choose any of the following books: {exclusions}.
    
    Return ONLY a raw JSON object with these fields:
    - title: String
    - author: String
    - year: String
    - genre: String
    - country: String
    - isbn: String (Valid ISBN-13 for a popular edition)
    
    - plot: String (Max 300 words. The "elevator pitch". Focus on the conflict and the vibe. What actually happens?)
    
    - buzz: String (Max 100 words. What's the reputation? Is it a cult classic? A hate-read? A slow burn? Be honest about how people receive it.)
    
    - matters: String (Max 100 words. Why read it now? Not because it's "historically important," but because it feels real/funny/disturbing/beautiful today.)
    
    - taste: String (A very brief abstract or a specific, vivid, well-known section from the book that captures the style.)
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=1.0 # Slightly higher temperature for more "personality"
    )

    return json.loads(response.choices[0].message.content)

def get_cover_url(isbn):
    url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
    try:
        r = requests.head(url, timeout=5)
        if r.status_code == 200:
            return url
    except:
        pass
    return "https://placehold.co/600x900/EEE/31343C?text=Classic+Literature"

def generate_affiliate_link(title, author):
    query = f"{title} {author}".replace(" ", "+")
    return f"https://www.amazon.com/s?k={query}&tag={AFFILIATE_TAG}"

def load_template():
    # Assumes template.html is in the same folder
    with open('template.html', 'r', encoding='utf-8') as f:
        return f.read()

def run_batch_job(days_to_generate=1, start_date=None):
    if start_date is None:
        start_date = datetime.now()
        
    generated_titles = []
    html_template = load_template()

    print(f"🚀 Starting batch generation for {days_to_generate} days...")

    for i in range(days_to_generate):
        # Calculate date for this drop
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d") # Filename format
        display_date = current_date.strftime("%B %d, %Y") # UI format

        print(f"[{i+1}/{days_to_generate}] Generating for {date_str}...")

        # Get content from AI
        try:
            book = get_book_recommendation(generated_titles)
            generated_titles.append(book['title']) # Add to exclude list
            
            # Enhance data
            book['cover_url'] = get_cover_url(book.get('isbn', ''))
            book['buy_link'] = generate_affiliate_link(book['title'], book['author'])
            book['date_display'] = display_date
            book['date_id'] = date_str

            # 1. Save Raw JSON (The App uses this if native)
            json_filename = os.path.join(OUTPUT_DIR, f"{date_str}.json")
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(book, f, indent=4, ensure_ascii=False)

            # 2. Save Rendered HTML (The App uses this if WebView)
            final_html = html_template.replace('{{TITLE}}', book['title']) \
                                      .replace('{{AUTHOR}}', book['author']) \
                                      .replace('{{YEAR}}', book['year']) \
                                      .replace('{{GENRE}}', book['genre']) \
                                      .replace('{{COUNTRY}}', book['country']) \
                                      .replace('{{COVER_URL}}', book['cover_url']) \
                                      .replace('{{PLOT}}', book['plot']) \
                                      .replace('{{BUZZ}}', book['buzz']) \
                                      .replace('{{MATTERS}}', book['matters']) \
                                      .replace('{{TASTE}}', book['taste']) \
                                      .replace('{{BUY_LINK}}', book['buy_link']) \
                                      .replace('{{DATE}}', display_date)
            
            html_filename = os.path.join(OUTPUT_DIR, f"{date_str}.html")
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(final_html)

            print(f"   ✅ Saved {book['title']}")
            
            # Sleep briefly to be nice to APIs
            time.sleep(1)

        except Exception as e:
            print(f"   ❌ Error on {date_str}: {e}")

    print("\n🎉 Batch Complete! Upload the 'generated_content' folder to your cloud.")

if __name__ == "__main__":
    # Generate content for the next 7 days
    run_batch_job(days_to_generate=2)