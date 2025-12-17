import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gemini():
    print("\n--- Testing Gemini ---")
    api_key = os.getenv('GEMINI_API_KEY')
    model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not found in environment variables.")
        return

    print(f"[INFO] GEMINI_API_KEY found (starts with: {api_key[:4]}...)")
    print(f"[INFO] Model: {model}")

    try:
        from google import genai
        print("[INFO] google.genai package imported.")
        
        client = genai.Client(api_key=api_key)
        print("[INFO] Gemini client initialized.")
        
        print("[INFO] Sending request to Gemini...")
        response = client.models.generate_content(
            model=model,
            contents=[{'parts': [{'text': 'Hello, say "Gemini is working" in JSON format: {"status": "Gemini is working"}'}]}]
        )
        
        print(f"[INFO] Response received type: {type(response)}")
        if hasattr(response, 'text'):
            print(f"[INFO] Response text: {response.text}")
        else:
            print(f"[WARN] Response has no text attribute. Response: {response}")

    except ImportError:
        print("[ERROR] google.genai package not installed.")
    except Exception as e:
        print(f"[ERROR] Gemini test failed: {e}")

def test_openai():
    print("\n--- Testing OpenAI ---")
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not found in environment variables.")
        return

    print(f"[INFO] OPENAI_API_KEY found (starts with: {api_key[:4]}...)")
    print(f"[INFO] Base URL: {base_url}")
    print(f"[INFO] Model: {model}")

    try:
        import openai
        print("[INFO] openai package imported.")
        
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        print("[INFO] OpenAI client initialized.")
        
        print("[INFO] Sending request to OpenAI...")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'OpenAI is working'"}
            ]
        )
        
        print(f"[INFO] Response received.")
        print(f"[INFO] Content: {response.choices[0].message.content}")

    except Exception as e:
        print(f"[ERROR] OpenAI test failed: {e}")

if __name__ == "__main__":
    # Force UTF-8 for stdout/stderr if possible, though print usually handles it
    if sys.platform.startswith('win'):
        # Just use standard print, avoid fancy characters
        pass
    test_gemini()
    test_openai()
