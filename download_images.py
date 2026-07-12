"""
Download product images for the clothing store - using placeholder images
"""
import urllib.request
import os
import sys

# Use more reliable image sources
images = {
    "men_grey_linen": "https://images.pexels.com/photos/769749/pexels-photo-769749.jpeg?w=400",
    "men_black_polo": "https://images.pexels.com/photos/428340/pexels-photo-428340.jpeg?w=400",
    "men_blue_denim": "https://images.pexels.com/photos/297933/pexels-photo-297933.jpeg?w=400",
    "men_white_classic": "https://images.pexels.com/photos/874158/pexels-photo-874158.jpeg?w=400",
    "men_brown_shoes": "https://images.pexels.com/photos/267301/pexels-photo-267301.jpeg?w=400",
    "men_white_sneakers": "https://images.pexels.com/photos/2529148/pexels-photo-2529148.jpeg?w=400",
    "women_red_dress": "https://images.pexels.com/photos/794062/pexels-photo-794062.jpeg?w=400",
    "women_white_wedding": "https://images.pexels.com/photos/2888687/pexels-photo-2888687.jpeg?w=400",
    "women_blue_evening": "https://images.pexels.com/photos/761963/pexels-photo-761963.jpeg?w=400",
    "women_floral_summer": "https://images.pexels.com/photos/980514/pexels-photo-980514.jpeg?w=400",
    "women_black_office": "https://images.pexels.com/photos/3755706/pexels-photo-3755706.jpeg?w=400",
    "women_red_boots": "https://images.pexels.com/photos/19090/pexels-photo.jpg?w=400",
    "women_white_sandals": "https://images.pexels.com/photos/2820886/pexels-photo-2820886.jpeg?w=400",
    "women_black_heels": "https://images.pexels.com/photos/931881/pexels-photo-931881.jpeg?w=400",
}

output_dir = "static/images"
os.makedirs(output_dir, exist_ok=True)

for name, url in images.items():
    filepath = os.path.join(output_dir, f"{name}.jpg")
    if os.path.exists(filepath):
        print(f"[OK] {name}.jpg already exists, skipping")
        continue
    try:
        print(f"Downloading {name}...")
        urllib.request.urlretrieve(url, filepath)
        print(f"  OK - Saved {name}.jpg")
    except Exception as e:
        print(f"  FAILED {name}: {e}")
        sys.stdout.flush()

print("\nDone! Now generating placeholder for any missing images...")

# For any missing images, create a simple colored placeholder
for name in images:
    filepath = os.path.join(output_dir, f"{name}.jpg")
    if not os.path.exists(filepath):
        # Create a simple text file as placeholder
        with open(filepath.replace('.jpg', '.txt'), 'w') as f:
            f.write(f"Placeholder for {name}")
        print(f"  Created placeholder for {name}")

print("\nAll done!")