from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app) 

def fetch_nesco_balance(meter_number):
    url = "https://customer.nesco.gov.bd/pre/panel"
    
    # requests.Session() ব্যবহার করা হচ্ছে যাতে কুকিজ এবং টোকেন সেভ থাকে
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    try:
        # ধাপ ১: পেজে ভিজিট করে _token (CSRF Token) বের করা
        response = session.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        token_input = soup.find('input', {'name': '_token'})
        if not token_input:
            return {"success": False, "error": "Security token missing on website!"}
        token = token_input['value']

        # ইনপুট ফিল্ডের নাম বের করা (মিটার নম্বর যেখানে বসবে)
        input_name = "customer_no" # ডিফল্ট নাম
        form = soup.find('form', id='customer-form')
        if form:
            for inp in form.find_all('input'):
                if inp.get('type') in ['text', 'number']:
                    input_name = inp.get('name')
                    break

        # ধাপ ২: টোকেন এবং মিটার নম্বর দিয়ে ফর্ম সাবমিট করা (POST)
        payload = {
            '_token': token,
            input_name: meter_number,
            'submit': 'রিচার্জ হিস্ট্রি' # বাটনের ভ্যালু
        }

        post_resp = session.post(url, data=payload, headers=headers)
        res_soup = BeautifulSoup(post_resp.text, 'html.parser')

        # ধাপ ৩: রেজাল্ট পেজ থেকে ডেটা টেবিল বের করা
        table = res_soup.find('table')
        if not table:
            return {"success": False, "error": "এই মিটারের কোনো ডেটা পাওয়া যায়নি অথবা নম্বরটি ভুল।"}

        # টেবিলের প্রথম ডেটা সারিটি (Latest Recharge) বের করা
        rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')[1:]
        
        if not rows:
             return {"success": False, "error": "রিচার্জের কোনো রেকর্ড নেই।"}

        first_row_cols = rows[0].find_all('td')
        row_data = [td.text.strip() for td in first_row_cols]

        # NESCO এর টেবিলে সাধারণত: [০] তারিখ, [১] ভেন্ডর, [২] রসিদ নম্বর, [৩] টাকার পরিমাণ থাকে।
        # আমরা পুরো সারিটাই পাঠিয়ে দিচ্ছি, যাতে কোনো ভুল না হয়।
        latest_recharge_amount = row_data[3] if len(row_data) > 3 else row_data[-1]
        recharge_date = row_data[0] if len(row_data) > 0 else "Unknown Date"

        return {
            "success": True,
            "meter_number": meter_number,
            "balance": f"৳ {latest_recharge_amount}",
            "details": f"সর্বশেষ রিচার্জের তারিখ: {recharge_date}",
            "raw_data": row_data # ডিবাগ করার সুবিধার জন্য
        }

    except Exception as e:
        return {
            "success": False,
            "error": "Scraping Error: " + str(e)
        }

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "success", "message": "NESCO Live Scraper API is running!"})

@app.route('/api/get-balance', methods=['GET'])
def get_balance():
    meter_number = request.args.get('meter')
    if not meter_number:
        return jsonify({"success": False, "error": "Meter number is missing!"}), 400

    data = fetch_nesco_balance(meter_number)
    return jsonify(data)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
