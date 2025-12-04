"""Insert 200 realistic primary school expense items into Neon DB.

Run from repo root in venv:
    python scripts\seed_expense_items.py

It reads DATABASE_URL from .env and inserts common school expense categories.
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load .env so DATABASE_URL is available
load_dotenv()


# 200 realistic primary school expense items
EXPENSE_ITEMS = [
    # Stationery & Office Supplies (20 items)
    "Notebooks (ruled A4)",
    "Pens (ballpoint, pack of 50)",
    "Pencils (HB, box of 100)",
    "Erasers (rubber)",
    "Sharpeners (pencil)",
    "Markers (permanent, assorted colors)",
    "Highlighters (pack of 6)",
    "Correction fluid (white-out)",
    "Stapler & staples",
    "Paper clips (box of 100)",
    "Sticky notes (pack of 100)",
    "Envelopes (pack of 500)",
    "Folders (A4, assorted)",
    "Binders (ring, assorted)",
    "Tape (masking & scotch)",
    "Glue stick (pack of 12)",
    "Scissors (metal, pack of 10)",
    "Rulers (30cm, pack of 20)",
    "Calculators (basic)",
    "Register books (class records)",
    
    # Cleaning Supplies (15 items)
    "Broom (large)",
    "Dustpan & brush set",
    "Mop & bucket",
    "Disinfectant (5L jerry can)",
    "Bleach (concentrated)",
    "Soap bars (pack of 50)",
    "Toilet paper rolls (case of 96)",
    "Paper towels (industrial roll)",
    "Trash bins (large)",
    "Trash bags (heavy-duty, roll)",
    "Sponges (scouring pad pack)",
    "Floor wax (5L)",
    "Duster cloth (pack of 10)",
    "Ventil fan cleaner spray",
    "Insecticide spray (aerosol)",
    
    # Maintenance & Repairs (20 items)
    "Paint (interior, white, 20L)",
    "Paint (interior, colored, 20L)",
    "Brushes (paint, assorted sizes)",
    "Rollers (paint, with handle)",
    "Nails (assorted sizes, 5kg box)",
    "Screws (assorted, 1kg box)",
    "Wood filler",
    "Sandpaper (assorted grits)",
    "Putty (fixing)",
    "Hinges (metal, assorted)",
    "Locks (padlock, assorted)",
    "Door handles (assorted)",
    "Light bulbs (LED, 9W, 60W, 100W)",
    "Electrical wire (coil)",
    "Electrical tape",
    "Soldering iron & solder",
    "Wrench set (10-piece)",
    "Screwdriver set (12-piece)",
    "Pliers (assorted)",
    "Hammer (2kg)",
    
    # Furniture & Fixtures (15 items)
    "Desk (wooden, teacher)",
    "Chair (plastic, classroom)",
    "Bench (wooden, student)",
    "Table (dining, 6-seater)",
    "Cabinet (filing, metal)",
    "Shelf unit (metal)",
    "Whiteboard (magnetic, 2m x 1m)",
    "Bulletin board (cork)",
    "Coat rack (wall-mounted)",
    "Shoe rack (metal, 4-tier)",
    "Water dispenser (cooler)",
    "Locker (metal student)",
    "Door (wooden, classroom)",
    "Window grille (metal)",
    "Door frame (with hinges)",
    
    # Educational Materials (25 items)
    "Textbook (English, Grade 1)",
    "Textbook (Math, Grade 1)",
    "Textbook (Science, Grade 1)",
    "Textbook (English, Grade 2)",
    "Textbook (Math, Grade 2)",
    "Textbook (Science, Grade 2)",
    "Textbook (English, Grade 3)",
    "Textbook (Math, Grade 3)",
    "Textbook (Science, Grade 3)",
    "Textbook (English, Grade 4)",
    "Textbook (Math, Grade 4)",
    "Textbook (Science, Grade 4)",
    "Textbook (English, Grade 5)",
    "Textbook (Math, Grade 5)",
    "Textbook (Science, Grade 5)",
    "Textbook (English, Grade 6)",
    "Textbook (Math, Grade 6)",
    "Textbook (Science, Grade 6)",
    "Exercise book (pack of 50)",
    "Teaching aids (charts, maps)",
    "Flashcards (alphabet & numbers)",
    "Posters (educational)",
    "Picture cards (vocabulary)",
    "Puzzle games (educational)",
    "Model set (3D shapes, skeleton)",
    
    # Sports & Recreation (15 items)
    "Football (size 5)",
    "Volleyball (official size)",
    "Basketball (size 6)",
    "Netball (official)",
    "Badminton racket (pack of 4)",
    "Badminton shuttlecock (dozen)",
    "Table tennis bat (pack of 6)",
    "Table tennis ball (dozen)",
    "Tennis racket (junior)",
    "Skipping rope (pack of 10)",
    "Hula hoop (pack of 5)",
    "Cones (training, pack of 12)",
    "Whistle (coach, pack of 5)",
    "First aid kit (sports)",
    "Sports mat (exercise)",
    
    # ICT & Technology (15 items)
    "Computer monitor (21 inch)",
    "Computer keyboard (mechanical)",
    "Computer mouse (optical, wireless)",
    "Printer cartridge (black)",
    "Printer cartridge (color)",
    "Printer paper (A4, ream of 500)",
    "USB cable (micro, type-c, HDMI)",
    "Power extension cable (10m)",
    "Power strip (6-socket)",
    "Network cable (CAT6, 100m)",
    "Router (WiFi 5G)",
    "Projector lamp (replacement)",
    "Screen protector (for devices)",
    "SSD external drive (1TB)",
    "Microphone & headset (quality)",
    
    # Furniture for Students (15 items)
    "Student desk (metal frame)",
    "Student chair (plastic seat)",
    "Student locker (small)",
    "Reading table (library)",
    "Library chair (padded)",
    "Storage rack (classroom)",
    "Shelf divider (book organizer)",
    "Cubby hole unit (personalized)",
    "Bag hook (wall-mounted)",
    "Name plate holder",
    "Magazine rack",
    "Picture frame (classroom display)",
    "Pencil holder (ceramic, per desk)",
    "Desk organizer (compartmented)",
    "Blotter pad (desk)",
    
    # Kitchen & Cafeteria (15 items)
    "Gas cooker (4-burner)",
    "Stainless steel pot (30L)",
    "Stainless steel pan (frying)",
    "Utensils (ladle, spatula, tongs set)",
    "Plates (dinner, 50 pieces)",
    "Cups (plastic, 50 pieces)",
    "Spoons (stainless, 50 pieces)",
    "Forks (stainless, 50 pieces)",
    "Knives (serving, pack of 6)",
    "Cutting board (wooden)",
    "Strainer (large, stainless)",
    "Waste bin (50L)",
    "Drying rack (stainless)",
    "Food storage container (20L)",
    "Apron (kitchen staff, pack of 5)",
    
    # Health & Hygiene (15 items)
    "Hand sanitizer (5L bottle)",
    "Facemask (medical, box of 50)",
    "Thermometer (infrared)",
    "First aid box (complete kit)",
    "Bandages (assorted sizes, 100 pack)",
    "Antiseptic wipes (pack of 100)",
    "Disposable gloves (latex-free, 100 pairs)",
    "Medical cotton wool (500g)",
    "Saline solution (1L)",
    "Antiseptic solution (1L)",
    "Pain relief tablets (pack of 100)",
    "Antacid tablets (pack of 100)",
    "Cough syrup (200ml bottle)",
    "Hydration salts (ORS, pack of 25)",
    "Health record book (student)",
    
    # Uniforms & Dress Code (10 items)
    "School uniform (shirt, size M)",
    "School uniform (trouser, size M)",
    "School uniform (skirt, size M)",
    "School sweater (cardigan)",
    "School tie (striped)",
    "School badge (emblem)",
    "Safety belt (reflective)",
    "Apron (lab, students)",
    "Socks (school colors, pack of 5)",
    "Shoes (formal, black)",
    
    # Security & Safety (10 items)
    "CCTV camera (HD, 2MP)",
    "Security gate (metal, sliding)",
    "Exit sign (illuminated)",
    "Fire extinguisher (6kg, ABC type)",
    "Fire escape ladder (rope)",
    "First aid signage",
    "No entry sign",
    "Caution sign (wet floor)",
    "Emergency whistle (pack of 5)",
    "Security lock (high security)",
    
    # Outdoor & Grounds (15 items)
    "Grass seeds (5kg bag)",
    "Garden hose (50m)",
    "Watering can (20L)",
    "Shovel (spade, long handle)",
    "Rake (garden, 10-tooth)",
    "Hoe (garden)",
    "Wheelbarrow (metal)",
    "Garden shears (pruning)",
    "Fertilizer (NPK, 50kg bag)",
    "Compost (organic, bulk)",
    "Flower pots (various sizes, dozen)",
    "Plant seedlings (assorted, 100)",
    "Benches (outdoor, wooden)",
    "Picnic table (metal frame)",
    "Trash bin (outdoor, large)",
    
    # Utilities & Infrastructure (10 items)
    "Water tank (5000L)",
    "Solar panel (200W)",
    "Battery backup (inverter, 5kVA)",
    "Generator (5kVA diesel)",
    "Electrical panel (breaker box)",
    "Door bell (wireless)",
    "Clock (wall-mounted, large)",
    "Notice board (wooden frame)",
    "Flag pole (metal, tall)",
    "Parking sign (reserved spot)",
]


def main():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print('ERROR: DATABASE_URL environment variable not set.')
        print('Set it in .env or environment and re-run.')
        sys.exit(1)

    engine = create_engine(database_url)
    
    print(f'Connecting to Neon database...')
    print(f'Inserting {len(EXPENSE_ITEMS)} expense items...\n')
    
    try:
        with engine.begin() as conn:
            # Insert items one by one using parameterized query
            for idx, item_name in enumerate(EXPENSE_ITEMS, 1):
                sql = text("""
                    INSERT INTO expense_items (name, description)
                    VALUES (:name, :desc)
                    ON CONFLICT (name) DO NOTHING;
                """)
                conn.execute(sql, {"name": item_name, "desc": f"Expense item: {item_name}"})
                
                # Print progress every 20 items
                if idx % 20 == 0:
                    print(f"  ✓ Inserted {idx}/{len(EXPENSE_ITEMS)} items...")
            
            print(f'\n✅ Successfully inserted {len(EXPENSE_ITEMS)} expense items.')
            print('These items are now available in the dropdown on /bursar/expenses/add')
            
    except Exception as e:
        print(f'❌ Error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
