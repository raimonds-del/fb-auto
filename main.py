import os
import requests
import pandas as pd
from apify_client import ApifyClient
from dotenv import load_dotenv
from datetime import datetime

# Load the API token from the .env file
load_dotenv()
API_TOKEN = os.getenv("APIFY_API_TOKEN")

if not API_TOKEN:
    raise ValueError("❌ Error: APIFY_API_TOKEN not found in .env file.")

client = ApifyClient(API_TOKEN)

def download_file(url, folder, filename):
    """Helper to download a file from a URL."""
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            path = os.path.join(folder, filename)
            with open(path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return path
    except Exception as e:
        print(f"⚠️ Failed to download {url}: {e}")
    return None

def main():
    # --- CONFIGURATION ---
    COMPETITOR_NAME = "Shopify"  # Change this to your competitor
    COUNTRY_CODE = "US"          # Change to your target country
    MAX_ADS = 10                 # How many ads to download
    # ---------------------

    print(f"🚀 Starting scrape for: {COMPETITOR_NAME}...")

    # Configure the Actor (curious_coder/facebook-ads-library-scraper)
    # Note: We construct the startUrl manually to ensure it hits the right filters
    run_input = {
        "startUrls": [{
            "url": f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country={COUNTRY_CODE}&q={COMPETITOR_NAME}&search_type=keyword_unordered&media_type=all"
        }],
        "maxItems": MAX_ADS,
        "proxyConfiguration": {"useApifyProxy": True}
    }

    # Run the actor
    run = client.actor("curious_coder/facebook-ads-library-scraper").call(run_input=run_input)
    
    print("✅ Scrape complete. Fetching results...")

    # Get data from dataset
    dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items

    if not dataset_items:
        print("❌ No ads found. Check your competitor name or API limits.")
        return

    # Create directories for organization
    timestamp = datetime.now().strftime("%Y-%m-%d")
    base_folder = f"media/{COMPETITOR_NAME}_{timestamp}"
    os.makedirs(f"{base_folder}/images", exist_ok=True)
    os.makedirs(f"{base_folder}/videos", exist_ok=True)

    results_data = []

    print(f"📦 Downloading media for {len(dataset_items)} ads...")

    for i, ad in enumerate(dataset_items):
        ad_id = ad.get("id", f"unknown_{i}")
        text = ad.get("adBody", "")
        
        # Handle Images
        images = ad.get("images", [])
        local_image_path = "N/A"
        if images and images[0].get("originalImageUrl"):
            img_url = images[0].get("originalImageUrl")
            local_image_path = download_file(img_url, f"{base_folder}/images", f"{ad_id}.jpg")

        # Handle Videos
        videos = ad.get("videos", [])
        local_video_path = "N/A"
        if videos and videos[0].get("videoUrl"):
            vid_url = videos[0].get("videoUrl")
            local_video_path = download_file(vid_url, f"{base_folder}/videos", f"{ad_id}.mp4")

        # Save data for CSV
        results_data.append({
            "Ad ID": ad_id,
            "Text": text,
            "Advertiser": ad.get("pageName"),
            "Start Date": ad.get("startDate"),
            "Local Image": local_image_path,
            "Local Video": local_video_path,
            "Original URL": ad.get("adSnapshotUrl")
        })

    # Save summary CSV
    df = pd.DataFrame(results_data)
    csv_path = f"{base_folder}/summary_report.csv"
    df.to_csv(csv_path, index=False)
    
    print(f"\n🎉 DONE! Files saved in: {base_folder}")
    print(f"📄 Summary CSV created at: {csv_path}")

if __name__ == "__main__":
    main()
