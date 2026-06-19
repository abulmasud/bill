from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
CORS(app) 

def fetch_nesco_balance(meter_number):
    url = "https://customer.nesco.gov.bd/pre/panel"
    
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    try:
        # ধাপ ১: পেজে ভিজিট করে _token বের করা
        response = session.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        token_input = soup.find('input', {'name': '_token'})
        if not token_input:
            return {"success": False, "error": "Security token missing!"}
        token = token_input['value']

        # ইনপুট ফিল্ডের নাম বের করা
        input_name = "customer_no" 
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
            'submit': 'রিচার্জ হিস্ট্রি' 
        }

        post_resp = session.post(url, data=payload, headers=headers)
        res_soup = BeautifulSoup(post_resp.text, 'html.parser')

        # ধাপ ৩: "অবশিষ্ট ব্যালেন্স" খুঁজে বের করা (ম্যাজিক ট্রিক)
        remaining_balance = None
        
        # 'অবশিষ্ট ব্যালেন্স' লেখাটি পেজের যেখানে আছে সেটি খুঁজবে
        balance_text_element = res_soup.find(string=re.compile("অবশিষ্ট ব্যালেন্স"))
        
        if balance_text_element:
            # লেখাটির মূল কন্টেইনার (div) ধরবে
            container = balance_text_element.find_parent(['div', 'div', 'tr'])
            if container:
                # কন্টেইনারের ভেতর কোনো input বক্সে ডেটা আছে কি না খুঁজবে
                inputs = container.find_all('input')
                for inp in inputs:
                    val = inp.get('value', '').strip()
                    if val and re.match(r'^[0-9\.]+$', val):
                        remaining_balance = val
                        break
                
                # যদি input বক্সে না থাকে, তবে সাধারণ টেক্সট থেকে নাম্বারটি খুঁজবে
                if not remaining_balance:
                    texts = container.stripped_strings
                    for t in texts:
                        # শুধু নাম্বার এবং দশমিক আছে এমন টেক্সট (যেমন: 189.33)
                        if re.match(r'^[0-9\.]+$', t):
                            remaining_balance = t
                            break

        if remaining_balance:
            return {
                "success": True,
                "meter_number": meter_number,
                "balance": f"{remaining_balance}", # একদম আসল ব্যালেন্স
                "details": "লাইভ অবশিষ্ট ব্যালেন্স সফলভাবে আনা হয়েছে!"
            }
        else:
            return {
                "success": False,
                "error": "আপনার মিটার নম্বরের জন্য কোনো অবশিষ্ট ব্যালেন্স পাওয়া যায়নি।"
            }

    except Exception as e:
        return {
            "success": False,
            "error": "Scraping Error: " + str(e)
        }

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "success", "message": "NESCO Real Balance API is running!"})

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
