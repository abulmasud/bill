from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright
import os
import re

app = FastAPI(title="NESCO Live Scraper API")

# গ্লোবাল CORS কনফিগারেশন
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/balance/{meter_no}")
def get_nesco_balance(meter_no: str, response: Response):
    # ব্রাউজার ব্লকিং এড়াতে সরাসরি রেসপন্সে হেডার পিন করা হলো
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"

    if not meter_no.isdigit():
        raise HTTPException(status_code=400, detail="Invalid meter number format")

    url = "https://customer.nesco.gov.bd/pre/panel"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(url, timeout=30000)
            page.fill("input[name='meter_no']", meter_no)
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")
            
            page_text = page.locator("body").inner_text()
            browser.close()

            if "Server Error" in page_text or "500" in page_text:
                raise HTTPException(status_code=502, detail="NESCO Server Error")

            balance = "--"
            units = "--"
            
            balance_match = re.search(r'(?:Balance|ব্যালেন্স|টাকা|৳|Current)[\s\:\=]*([0-9.,]+)', page_text, re.IGNORECASE)
            if balance_match:
                balance = "৳ " + balance_match[1]
            else:
                fallback_match = re.search(r'([0-9]{1,5}\.[0-9]{2})', page_text)
                if fallback_match:
                    balance = "৳ " + fallback_match[1]

            unit_match = re.search(r'(?:Unit|ইউনিট|kWh)[\s\:\=]*([0-9.,]+)', page_text, re.IGNORECASE)
            if unit_match:
                units = unit_match[1] + " kWh"
            else:
                units = "Active"

            return {
                "status": "success",
                "meter_no": meter_no,
                "balance": balance,
                "units_used": units
            }

        except Exception as e:
            browser.close()
            raise HTTPException(status_code=500, detail=str(e))
