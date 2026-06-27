import os
import sys
import json
import asyncio
import logging
import argparse
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError

# Load environment variables
load_dotenv()

# Setup Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/scraper.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("scraper")

# Default Target Channels
DEFAULT_CHANNELS = ["CheMed1", "lobelia4cosmetics", "tikvahpharma"]

def generate_mock_data(limit=20):
    """Generates realistic mock data for Ethiopian medical/cosmetic channels."""
    logger.info("Generating mock data...")
    
    mock_messages = {
        "CheMed1": [
            ("Medical supplies, Glucometers, and BP monitors available in stock. Order now!", True),
            ("New shipment of surgical masks, gloves, and thermometers. Quality guaranteed.", True),
            ("Urgent: Amoxicillin 500mg and basic antibiotics available for clinics.", False),
            ("Defibrillator training session scheduled for next week. Registrations open.", True),
            ("High-quality wheelchairs and crutches imported from Germany. Contact for price.", True),
        ],
        "lobelia4cosmetics": [
            ("Lobelia Vitamin C Serum for glowing skin. Best price in Addis!", True),
            ("Hydrating moisturizers and sunscreens back in stock. Perfect for summer.", True),
            ("Organic hair growth oil with essential nutrients. 100% natural ingredients.", True),
            ("Matte lipsticks and foundations available in all shades.", True),
            ("Anti-aging night creams. dermatologically tested and approved.", False),
        ],
        "tikvahpharma": [
            ("Tikvah Pharma: Paracetamol 500mg tablets available for wholesale distribution.", False),
            ("Insulin glargine injection pens in stock. Cold-chain storage maintained.", True),
            ("Metformin 850mg for diabetes management. Available in all branches.", False),
            ("Atorvastatin 20mg tablets for cholesterol regulation. Prescription required.", True),
            ("Multi-vitamins and immune booster capsules. Stay healthy this winter.", True),
        ]
    }

    scraped_at = datetime.now(timezone.utc)
    date_str = scraped_at.strftime("%Y-%m-%d")
    
    # Base raw directories
    messages_dir = os.path.join("data", "raw", "telegram_messages", date_str)
    images_dir = os.path.join("data", "raw", "images")
    os.makedirs(messages_dir, exist_ok=True)
    
    for channel in DEFAULT_CHANNELS:
        channel_msgs = mock_messages.get(channel, [("General medical item description.", True)])
        records = []
        
        # Build image directories
        channel_img_dir = os.path.join(images_dir, channel)
        os.makedirs(channel_img_dir, exist_ok=True)
        
        for idx in range(min(limit, len(channel_msgs))):
            msg_text, has_media = channel_msgs[idx]
            msg_id = 1000 + idx
            
            img_path = None
            if has_media:
                # Create a simple mock image (blank text/color placeholder file)
                img_filename = f"{msg_id}.jpg"
                img_path = os.path.join(channel_img_dir, img_filename)
                
                # Write a dummy byte array representing a minimal valid JPEG/PNG placeholder
                # We'll use a tiny 1x1 pixel JPEG or PNG format for YOLO tests
                # 1x1 black pixel PNG:
                png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc` \x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
                with open(img_path, "wb") as f:
                    f.write(png_bytes)
            
            # Message timestamp spread out over the last few days
            msg_date = scraped_at - timedelta(hours=idx * 2)
            
            record = {
                "message_id": str(msg_id),
                "channel_name": channel,
                "message_date": msg_date.isoformat(),
                "message_text": msg_text,
                "has_media": has_media,
                "image_path": img_path.replace("\\", "/") if img_path else None,
                "views": idx * 150 + 20,
                "forwards": idx * 12 + 1
            }
            records.append(record)
            
        # Write channel json
        output_file = os.path.join(messages_dir, f"{channel}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=4)
            
        logger.info(f"Successfully wrote {len(records)} mock messages to {output_file}")
        
    logger.info("Mock data generation completed successfully.")

async def scrape_channel(client, channel_name, limit=50):
    """Scrapes data from a single Telegram channel using Telethon."""
    logger.info(f"Starting to scrape channel: {channel_name}")
    records = []
    
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    messages_dir = os.path.join("data", "raw", "telegram_messages", date_str)
    images_dir = os.path.join("data", "raw", "images", channel_name)
    
    os.makedirs(messages_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    
    try:
        # Get channel entity
        entity = await client.get_entity(channel_name)
        async for message in client.iter_messages(entity, limit=limit):
            # We filter out messages with no text and no media
            if not message.text and not message.media:
                continue
                
            has_media = message.media is not None
            img_path = None
            
            # Download image if it is a photo
            if has_media and getattr(message, 'photo', None):
                img_filename = f"{message.id}.jpg"
                dest_path = os.path.join(images_dir, img_filename)
                
                try:
                    img_path = await client.download_media(message, file=dest_path)
                    if img_path:
                        img_path = img_path.replace("\\", "/")
                except Exception as e:
                    logger.error(f"Failed to download media for msg {message.id} in {channel_name}: {e}")
            
            # Convert date to timezone-aware ISO string
            msg_date = message.date.astimezone(timezone.utc).isoformat()
            
            record = {
                "message_id": str(message.id),
                "channel_name": channel_name,
                "message_date": msg_date,
                "message_text": message.text or "",
                "has_media": has_media,
                "image_path": img_path,
                "views": message.views or 0,
                "forwards": message.forwards or 0
            }
            records.append(record)
            
        # Save records to JSON data lake
        output_file = os.path.join(messages_dir, f"{channel_name}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=4)
            
        logger.info(f"Successfully scraped {len(records)} messages from {channel_name} -> {output_file}")
        
    except FloodWaitError as e:
        logger.warning(f"Rate limited by Telegram. FloodWait for {e.seconds} seconds. Sleeping...")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        logger.error(f"Error scraping channel {channel_name}: {e}", exc_info=True)

async def main():
    parser = argparse.ArgumentParser(description="Telegram Channel Scraper")
    parser.add_argument("--mock", action="store_true", help="Generate mock data instead of scraping Telegram")
    parser.add_argument("--limit", type=int, default=50, help="Limit of messages to scrape per channel")
    args = parser.parse_args()
    
    # Read config
    api_id_str = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    phone = os.getenv("TELEGRAM_PHONE")
    
    # Determine if we run in mock mode
    run_mock = args.mock
    if not run_mock:
        if not api_id_str or not api_hash:
            logger.warning("TELEGRAM_API_ID or TELEGRAM_API_HASH not set. Falling back to mock mode!")
            run_mock = True

    if run_mock:
        generate_mock_data(limit=args.limit)
        return

    # Real scrape mode
    api_id = int(api_id_str)
    session_name = "session_medical_scraper"
    
    logger.info(f"Connecting to Telegram API as {phone or 'anonymous'}...")
    client = TelegramClient(session_name, api_id, api_hash)
    
    await client.connect()
    
    # Handle Login flow
    if not await client.is_user_authorized():
        if not phone:
            logger.error("User is not authorized and TELEGRAM_PHONE is not set in .env. Cannot complete authorization!")
            sys.exit(1)
            
        logger.info(f"Sending code request for {phone}...")
        await client.send_code_request(phone)
        
        # In a real pipeline context, we prompt on command line.
        # Since this runs asynchronously and might be non-interactive:
        code = input(f"Enter the code you received on Telegram for {phone}: ")
        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = input("2-Step Verification password is required: ")
            await client.sign_in(password=password)
            
    logger.info("Telegram client authorized successfully.")
    
    # Run scraping for all channels
    for channel in DEFAULT_CHANNELS:
        await scrape_channel(client, channel, limit=args.limit)
        
    await client.disconnect()
    logger.info("Scraper execution finished successfully.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        # Apply standard selector event loop for Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
