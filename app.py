from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__)
CORS(app) 

def fetch_nesco_balance(meter_number):
    url = "https://customer.nesco.gov.bd/pre/panel"
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = session.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        token = soup.find('input', {'name': '_token'})['value']
        
        # মিটার নম্বর ফিল্ড খুঁজে বের করা
        input_name = "customer_no"
        for inp in soup.find('form').find_all('input'):
            if inp.get('type') in ['text', 'number']:
                input_name = inp.get('name')
                break

        payload = {'_token': token, input_name: meter_number, 'submit': 'রিচার্জ হিস্ট্রি'}
        post_resp = session.post(url, data=payload, headers=headers)
        res_soup = BeautifulSoup(post_resp.text, 'html.parser')

        # ব্যালেন্স বের করার নতুন পদ্ধতি
        balance = None
        # 'অবশিষ্ট ব্যালেন্স (টাকা)' লেখাটি খুঁজবে
        label = res_soup.find(string=re.compile("অবশিষ্ট ব্যালেন্স"))
        if label:
            # ওই লেখাটির প্যারেন্ট কন্টেইনারে গিয়ে মানটি খুঁজে বের করবে
            container = label.find_parent(['div', 'tr'])
            # ইনপুট বক্স অথবা সাধারণ টেক্সট থেকে মানটি নেবে
            val_element = container.find('input') or container.find(string=re.compile(r'\d+\.\d+'))
            
            if val_element:
                text_val = val_element.get('value', '').strip() if val_element.name == 'input' else val_element.strip()
                # নিশ্চিত করবে এটি শুধু একটি নাম্বার
                if re.match(r'^\d+\.?\d*$', text_val):
                    balance = text_val

        if balance:
            return {"success": True, "meter_number": meter_number, "balance": balance, "details": "সফলভাবে ব্যালেন্স আপডেট হয়েছে!"}
        return {"success": False, "error": "ব্যালেন্স পাওয়া যায়নি।"}

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route('/api/get-balance')
def get_balance():
    return jsonify(fetch_nesco_balance(request.args.get('meter')))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
