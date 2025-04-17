import asyncio
import json
from playwright.async_api import async_playwright
from db_operations import update_hackathon_data


async def scrape_hackathons():
    url = "https://hackscrapped.vercel.app/"
    
    async with async_playwright() as p:
        # Launch browser with a larger viewport to ensure all elements are visible
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        print("Navigating to the website...")
        await page.goto(url, wait_until="networkidle")
        
        # Wait for initial content to load
        await asyncio.sleep(5)
        
        print("Starting to scroll for lazy loading...")
        # Scroll to load all hackathon cards
        previous_height = 0
        scroll_attempts = 0
        max_scroll_attempts = 20  # Limit scrolling attempts
        
        while scroll_attempts < max_scroll_attempts:
            current_height = await page.evaluate("document.body.scrollHeight")
            if previous_height >= current_height and scroll_attempts > 3:
                # If height hasn't changed after several attempts, we're probably done
                break
                
            previous_height = current_height
            # Scroll down
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)  # Wait for content to load
            scroll_attempts += 1
            print(f"Scroll attempt {scroll_attempts}/{max_scroll_attempts}...")
        
        print("Scrolling complete. Now collecting hackathon data...")
        
        # Get all hackathon cards - using the correct class selector
        # Based on the HTML provided, we need to select the cards with the proper class
        card_selector = "div.relative.group.border-2.border-black"
        cards = await page.query_selector_all(card_selector)
        
        print(f"Found {len(cards)} hackathon cards")
        
        data = []
        
        # Process each card
        for i, card in enumerate(cards):
            print(f"Processing card {i+1}/{len(cards)}...")
            card_data = {}
            
            try:
                # Get the headline and URL from the anchor tag
                headline_anchor = await card.query_selector("h2.text-lg")
                if headline_anchor:
                    headline_text = await headline_anchor.inner_text()
                    card_data["headline"] = headline_text.strip()
                
                # Get the URL
                url_anchor = await card.query_selector("a[href^='https://']")
                if url_anchor:
                    href = await url_anchor.get_attribute("href")
                    card_data["url"] = href
                
                # Get the sub-headline
                sub_headline = await card.query_selector("span.text-xs.font-sans.font-semibold")
                if sub_headline:
                    sub_headline_text = await sub_headline.inner_text()
                    card_data["sub_headline"] = sub_headline_text.strip()
                
                # Get the mode of the hackathon
                mode_element = await card.query_selector("span.font-bold:has-text('Mode:')")
                if mode_element:
                    parent_p = await mode_element.evaluate_handle("node => node.parentElement")
                    mode_text = await parent_p.inner_text()
                    mode = mode_text.replace("Mode:", "").strip()
                    card_data["mode"] = mode
                
                # Get location and no_of_participant;
                location_indicator = await card.query_selector("div.flex.items-center:has(svg)")
                if location_indicator:
                    location_text = await location_indicator.inner_text()
                    if location_text:
                        temp = location_text.strip()
                        parts = temp.split("\n\n")  
                        loc = parts[0].strip() if len(parts) > 0 else ""
                        nop = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip().isdigit() else 0

                        card_data["location"] = loc
                        card_data["no_of_participant"] = nop

                
                # Get tags
                tags = await card.query_selector_all("span.border-2.text-gray-600.dark\\:text-green-500")
                if tags:
                    tag_list = []
                    for tag in tags:
                        tag_text = await tag.inner_text()
                        tag_list.append(tag_text.strip())
                    card_data["tags"] = tag_list
                
                # Get status (Live, Open, Upcoming)
                status_button = await card.query_selector("button.text-green-600, button.text-white")
                if status_button:
                    status_text = await status_button.inner_text()
                    card_data["status"] = status_text.strip()
                
                # Get organization logo and link
                logo_anchor = await card.query_selector("a:has(img)")
                if logo_anchor:
                    logo_link = await logo_anchor.get_attribute("href")
                    card_data["organization_link"] = logo_link
                    
                    logo_img = await logo_anchor.query_selector("img")
                    if logo_img:
                        logo_src = await logo_img.get_attribute("src")
                        card_data["organization_logo"] = logo_src
                        
                        logo_alt = await logo_img.get_attribute("alt")
                        if logo_alt:
                            card_data["organization_name"] = logo_alt
                
                # Get dates if available
                date_element = await card.query_selector("span.atcb-text, span[part='atcb-button-text']")
                if date_element:
                    date_text = await date_element.inner_text()
                    card_data["dates"] = date_text.strip()
                
                data.append(card_data)
                
            except Exception as e:
                print(f"Error processing card {i+1}: {str(e)}")
                continue
        
        # Take a screenshot for debugging
        await page.screenshot(path="hackathon_page.png", full_page=True)
        
        # Save the results to a JSON file
        with open("hackathon_data.json", "w", encoding="utf-8") as f:
            json.dump(data, indent=2, fp=f)
        
        # Print summary
        print(json.dumps(data[:2], indent=2, ensure_ascii=False))  # Print first 2 items as sample
        print(f"\nSuccessfully scraped {len(data)} hackathons!")
        
        
        
        await browser.close()
        return data

if __name__ == "__main__":
    async def main():
        await scrape_hackathons()
        
        #update the database (using the async function)
        results = await update_hackathon_data()
        print(results["message"])
    
    # Run the main async function
    asyncio.run(main())