import os
import json
import requests
import time
from openai import OpenAI
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --- CONFIGURATION & SETUP ---

# 1. Load Environment Variables (API Key)
# We force Python to look in the current folder for .env
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError(f"No API Key found! Checked path: {env_path}")

# 2. Setup Clients and Paths
client = OpenAI(api_key=API_KEY)
AFFILIATE_TAG = "your-tag-20"
OUTPUT_DIR = "public/content"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- FUNCTIONS ---

def get_book_recommendation(exclude_list):
    """
    Asks AI for a book using the "Smart Friend" persona.
    Separates 'Buzz' (Fame) from 'Matters' (Vibe).
    """
    exclusions = ", ".join(exclude_list)
    
    system_instruction = """
    You are a smart, 30-year-old book lover recommending a book to a close friend over coffee. You are excited about the recommendation.
    
    TONE GUIDELINES:
    1. Casual & Grounded: Use contractions (it's, can't). 
    2. No Fluff: No "masterpiece," "breathtaking," "seminal," or "essential." 
    3. Specifics: Don't be vague.
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
    
    - plot: String (Minimum 400 words. Max 500 words.  The "elevator pitch". Focus on the conflict. What actually happens?)
    
    - buzz: String (Minimum 100 words. Max 150 words. SOCIAL PROOF & FAME. Mention specific awards (Booker, Pulitzer, Nobel), if it was a bestseller, if it was banned, movie adaptations, or cultural impact.)
    
    - matters: String (Minimum 100 words. Max 150 words. THE VIBE. Why read it *today*? Does it feel modern? Is it hilarious? Is it disturbing? Ignore the awards here—focus on the feeling of reading it.)
    
    - taste: String (CRITICAL: A direct EXCERPT from the book's text. Preferably the opening lines or a famous passage. Do NOT write a summary. Do NOT write a review. Only provide the actual words written by the author.Minimum 100 words, max 300.)
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=1.0 # High creativity for better tone
    )

    return json.loads(response.choices[0].message.content)

def get_cover_url(title, author):
    """
    Searches Google Books for the cover by Title + Author.
    """
    try:
        query = f"{title} {author}".replace(" ", "+")
        url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=1"
        
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if "items" in data and len(data["items"]) > 0:
            volume = data["items"][0]["volumeInfo"]
            if "imageLinks" in volume:
                images = volume["imageLinks"]
                # Try to get the biggest image available
                cover_link = images.get("extraLarge") or images.get("large") or images.get("medium") or images.get("thumbnail")
                
                if cover_link:
                    # Upgrade http to https to prevent browser warnings
                    return cover_link.replace("http://", "https://")
                    
    except Exception as e:
        print(f"   ⚠️ Cover fetch warning: {e}")

    # Fallback placeholder
    return "https://placehold.co/600x900/EEE/31343C?text=Classic+Literature"

def generate_affiliate_link(title, author):
    query = f"{title} {author}".replace(" ", "+")
    return f"https://www.amazon.com/s?k={query}&tag={AFFILIATE_TAG}"

def run_batch_job(days_to_generate=2):
    """
    Generates content for the next X days.
    """
    start_date = datetime.now()
    generated_titles = []

    print(f"🚀 Starting batch generation for {days_to_generate} days...")

    for i in range(days_to_generate):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d") # Filename
        display_date = current_date.strftime("%B %d, %Y") # UI Display

        print(f"[{i+1}/{days_to_generate}] Generating for {date_str}...")

        try:
            # 1. Get AI Content
            book = get_book_recommendation(generated_titles)
            generated_titles.append(book['title']) 
            
            # 2. Get Metadata
            book['cover_url'] = get_cover_url(book['title'], book['author'])
            book['buy_link'] = generate_affiliate_link(book['title'], book['author'])
            book['date_display'] = display_date
            book['date_id'] = date_str

            # 3. Save JSON File
            json_filename = os.path.join(OUTPUT_DIR, f"{date_str}.json")
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(book, f, indent=4, ensure_ascii=False)

            print(f"   ✅ Saved {book['title']}")
            
            # Sleep to be polite to APIs
            time.sleep(1)

        except Exception as e:
            print(f"   ❌ Error on {date_str}: {e}")

    print("\n🎉 Batch Complete! Don't forget to 'git push'.")

if __name__ == "__main__":
    # Change the number below to generate more days
    run_batch_job(days_to_generate=2)