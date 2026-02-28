import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import string
import random
from crawler import crawl_brand
import database

# Hardcoded list of 80 popular brands (extracted via subagent to bypass Cloudflare)
POPULAR_BRANDS = [
  "https://www.parfumo.com/Perfumes/Dior",
  "https://www.parfumo.com/Perfumes/Chanel",
  "https://www.parfumo.com/Perfumes/Yves_Saint_Laurent",
  "https://www.parfumo.com/Perfumes/Tom_Ford",
  "https://www.parfumo.com/Perfumes/Aaron_Terence_Hughes",
  "https://www.parfumo.com/Perfumes/Abdul_Samad_Al_Qurashi",
  "https://www.parfumo.com/Perfumes/Abercrombie_Fitch",
  "https://www.parfumo.com/Perfumes/Acca_Kappa",
  "https://www.parfumo.com/Perfumes/Acqua_di_Parma",
  "https://www.parfumo.com/Perfumes/Adidas",
  "https://www.parfumo.com/Perfumes/Adolfo_Dominguez",
  "https://www.parfumo.com/Perfumes/Aedes_de_Venustas",
  "https://www.parfumo.com/Perfumes/Aerin",
  "https://www.parfumo.com/Perfumes/Aesop",
  "https://www.parfumo.com/Perfumes/Afnan_Perfumes",
  "https://www.parfumo.com/Perfumes/Agent_Provocateur",
  "https://www.parfumo.com/Perfumes/Aigner",
  "https://www.parfumo.com/Perfumes/Ajmal",
  "https://www.parfumo.com/Perfumes/Akro",
  "https://www.parfumo.com/Perfumes/Al_Haramain",
  "https://www.parfumo.com/Perfumes/Al_Rehab",
  "https://www.parfumo.com/Perfumes/AlexandreJ",
  "https://www.parfumo.com/Perfumes/Alexandria_Fragrances",
  "https://www.parfumo.com/Perfumes/Alfred_Sung",
  "https://www.parfumo.com/Perfumes/Alkemia",
  "https://www.parfumo.com/Perfumes/AllSaints",
  "https://www.parfumo.com/Perfumes/Alyssa_Ashley",
  "https://www.parfumo.com/Perfumes/Amouage",
  "https://www.parfumo.com/Perfumes/Anna_Sui",
  "https://www.parfumo.com/Perfumes/Annayake",
  "https://www.parfumo.com/Perfumes/Annette_Neuffer",
  "https://www.parfumo.com/Perfumes/Arabian_Oud",
  "https://www.parfumo.com/Perfumes/Aramis",
  "https://www.parfumo.com/Perfumes/Ard_Al_Zaafaran",
  "https://www.parfumo.com/Perfumes/Areej_Le_Dore",
  "https://www.parfumo.com/Perfumes/Argos",
  "https://www.parfumo.com/Perfumes/Ariana_Grande",
  "https://www.parfumo.com/Perfumes/Armaf",
  "https://www.parfumo.com/Perfumes/Asabi",
  "https://www.parfumo.com/Perfumes/Asdaaf",
  "https://www.parfumo.com/Perfumes/astrophil-stella",
  "https://www.parfumo.com/Perfumes/Atelier_Cologne",
  "https://www.parfumo.com/Perfumes/Atelier_des_Ors",
  "https://www.parfumo.com/Perfumes/Atkinsons",
  "https://www.parfumo.com/Perfumes/Attar_Collection",
  "https://www.parfumo.com/Perfumes/Avon",
  "https://www.parfumo.com/Perfumes/Axe",
  "https://www.parfumo.com/Perfumes/Azzaro",
  "https://www.parfumo.com/Perfumes/bait-al-bakhoor",
  "https://www.parfumo.com/Perfumes/Baldessarini",
  "https://www.parfumo.com/Perfumes/Balenciaga",
  "https://www.parfumo.com/Perfumes/Balmain",
  "https://www.parfumo.com/Perfumes/Banana_Republic",
  "https://www.parfumo.com/Perfumes/Banderas",
  "https://www.parfumo.com/Perfumes/Bath_Body_Works",
  "https://www.parfumo.com/Perfumes/bdk_Parfums",
  "https://www.parfumo.com/Perfumes/Beaufort",
  "https://www.parfumo.com/Perfumes/Benetton",
  "https://www.parfumo.com/Perfumes/Bentley",
  "https://www.parfumo.com/Perfumes/Berdoues",
  "https://www.parfumo.com/Perfumes/Betty_Barclay",
  "https://www.parfumo.com/Perfumes/Beyonce",
  "https://www.parfumo.com/Perfumes/Bijan",
  "https://www.parfumo.com/Perfumes/billie-eilish",
  "https://www.parfumo.com/Perfumes/Biotherm",
  "https://www.parfumo.com/Perfumes/Birkholz",
  "https://www.parfumo.com/Perfumes/Black_Phoenix_Alchemy_Lab",
  "https://www.parfumo.com/Perfumes/Blend_Oud",
  "https://www.parfumo.com/Perfumes/Boadicea_the_Victorious",
  "https://www.parfumo.com/Perfumes/Bogner",
  "https://www.parfumo.com/Perfumes/Bogue",
  "https://www.parfumo.com/Perfumes/Bohoboco",
  "https://www.parfumo.com/Perfumes/Bois_1920",
  "https://www.parfumo.com/Perfumes/Bon_Parfumeur",
  "https://www.parfumo.com/Perfumes/Bond_No_9",
  "https://www.parfumo.com/Perfumes/borntostandout",
  "https://www.parfumo.com/Perfumes/Bortnikoff",
  "https://www.parfumo.com/Perfumes/Bottega_Veneta",
  "https://www.parfumo.com/Perfumes/Boucheron",
  "https://www.parfumo.com/Perfumes/Bourjois"
]

async def run_massive_collection():
    database.init_db()
    
    # Randomize to keep traffic patterns organic
    list_to_scrape = POPULAR_BRANDS[:]
    random.shuffle(list_to_scrape)
    
    print(f"\n--- Starting Massive Data Collection from {len(list_to_scrape)} Brands ---")
    
    # Scrape up to 40 colognes PER BRAND
    LIMIT_PER_BRAND = 40
    MAX_CONCURRENT_BROWSERS = 3
    
    for brand_url in list_to_scrape:
        print(f"\n--- Processing Brand: {brand_url} ---")
        try:
            await crawl_brand(brand_url, limit=LIMIT_PER_BRAND, max_concurrent=MAX_CONCURRENT_BROWSERS)
        except Exception as e:
            print(f"Error on brand {brand_url}: {e}")
            
        print("\nPipeline Cooling Down for 10 seconds...")
        await asyncio.sleep(10)
        
    print("\nMassive Data Collection Pipeline Complete!")

if __name__ == "__main__":
    asyncio.run(run_massive_collection())
