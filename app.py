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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        response = session.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        token_input = soup.find('input', {'name': '_token'})
        if not token_input:
            return {"success": False, "error": "Security token missing!"}
        token = token_input['value']
        
        # মিটার নম্বর ফিল্ড খুঁজে বের করা
        input_name = "customer_no"
        form = soup.find('form')
        if form:
            for inp in form.find_all('input'):
                if inp.get('type') in ['text', 'number']:
                    input_name = inp.get('name')
                    break

        payload = {'_token': token, input_name: meter_number, 'submit': 'রিচার্জ হিস্ট্রি'}
        post_resp = session.post(url, data=payload, headers=headers)
        res_soup = BeautifulSoup(post_resp.text, 'html.parser')

        # ব্যালেন্স বের করার নতুন পদ্ধতি
        balance = None
        label = res_soup.find(string=re.compile("অবশিষ্ট ব্যালেন্স"))
        
        if label:
            # ওই লেখার আশপাশে থাকা বক্স বা টেক্সট খুঁজবে
            for node in label.find_all_next():
                if node.name == 'input':
                    val = node.get('value', '').strip()
                    if re.search(r'\d+\.\d+', val) or re.match(r'^\d+$', val):
                        balance = val
                        break
                elif node.name in ['div', 'td', 'span']:
                    text_inside = node.find(string=True, recursive=False)
                    if text_inside:
                        val = text_inside.strip()
                        if re.fullmatch(r'-?\d{1,7}(,\d{3})*(\.\d+)?', val):
                            balance = val
                            break

        if balance:
            return {"success": True, "meter_number": meter_number, "balance": balance, "details": "সফলভাবে ব্যালেন্স আপডেট হয়েছে!"}
        return {"success": False, "error": "এই মিটারের কোনো অবশিষ্ট ব্যালেন্স পাওয়া যায়নি।"}

    except Exception as e:
        return {"success": False, "error": str(e)}

# এই রুটটি আগেরবার বাদ পড়েছিল!
@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "success", "message": "NESCO Live API is running perfectly!"})

@app.route('/api/get-balance', methods=['GET'])
def get_balance():
    meter_number = request.args.get('meter')
    if not meter_number:
        return jsonify({"success": False, "error": "Meter number is missing!"}), 400
    
    return jsonify(fetch_nesco_balance(meter_number))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
