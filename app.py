from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__)
# ফ্রন্টএন্ড থেকে কল করার জন্য CORS এনাবল করা হলো
CORS(app) 

def fetch_nesco_balance(meter_number):
    url = "https://customer.nesco.gov.bd/pre/panel"
    
    # কুকিজ এবং সেশন ধরে রাখার জন্য requests.Session()
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
            return {"success": False, "error": "Security token missing on the website!"}
        token = token_input['value']

        # ফর্ম থেকে মিটার নম্বরের ইনপুট ফিল্ডের আসল নাম বের করা
        input_name = "customer_no" 
        form = soup.find('form', id='customer-form')
        if form:
            for inp in form.find_all('input'):
                if inp.get('type') in ['text', 'number']:
                    input_name = inp.get('name')
                    break

        # ধাপ ২: টোকেন এবং মিটার নম্বর দিয়ে ফর্ম সাবমিট করা (POST Request)
        payload = {
            '_token': token,
            input_name: meter_number,
            'submit': 'রিচার্জ হিস্ট্রি' 
        }

        post_resp = session.post(url, data=payload, headers=headers)
        res_soup = BeautifulSoup(post_resp.text, 'html.parser')

        # ধাপ ৩: "অবশিষ্ট ব্যালেন্স" খুঁজে বের করা (মিনিমাম রিচার্জ ইগনোর করে)
        remaining_balance = None
        
        # পেজের যেখানে "অবশিষ্ট ব্যালেন্স" লেখাটি আছে, সেটি খুঁজবে
        balance_text_element = res_soup.find(string=re.compile("অবশিষ্ট ব্যালেন্স"))
        
        if balance_text_element:
            # "অবশিষ্ট ব্যালেন্স" লেখার ঠিক পরের এলিমেন্টগুলো এক এক করে চেক করবে
            for node in balance_text_element.find_all_next():
                
                # ১. যদি এটি একটি ইনপুট বক্স হয় (যেমনটা ওয়েবসাইটের বক্সে দেখা যাচ্ছে)
                if node.name == 'input':
                    val = node.get('value', '').strip()
                    # যদি ভ্যালুটি শুধু একটি নাম্বার হয় (যেমন: 189.33)
                    if re.fullmatch(r'-?\d{1,3}(,\d{3})*(\.\d+)?', val):
                        remaining_balance = val
                        break
                
                # ২. যদি সাধারণ টেক্সট হয় (div, span ইত্যাদি), তবে সরাসরি টেক্সট চেক করবে
                elif node.name in ['div', 'span', 'p', 'td']:
                    text_inside = node.find(string=True, recursive=False)
                    if text_inside:
                        val = text_inside.strip()
                        # সময় বা অন্য লেখা ইগনোর করে শুধু ব্যালেন্সের নাম্বার খুঁজবে
                        if re.fullmatch(r'-?\d{1,3}(,\d{3})*(\.\d+)?', val):
                            remaining_balance = val
                            break

        if remaining_balance:
            return {
                "success": True,
                "meter_number": meter_number,
                "balance": remaining_balance, 
                "details": "লাইভ অবশিষ্ট ব্যালেন্স সফলভাবে আনা হয়েছে!"
            }
        else:
            return {
                "success": False,
                "error": "আপনার মিটার নম্বরের জন্য কোনো অবশিষ্ট ব্যালেন্স পাওয়া যায়নি অথবা নম্বরটি ভুল।"
            }

    except Exception as e:
        return {
            "success": False,
            "error": "Scraping Error: " + str(e)
        }

# হোম রুট (API স্ট্যাটাস চেক করার জন্য)
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "success", 
        "message": "NESCO Real Balance API is running perfectly!"
    })

# ব্যালেন্স চেক করার মূল API রুট
@app.route('/api/get-balance', methods=['GET'])
def get_balance():
    meter_number = request.args.get('meter')
    if not meter_number:
        return jsonify({"success": False, "error": "Meter number is missing!"}), 400

    data = fetch_nesco_balance(meter_number)
    return jsonify(data)

if __name__ == '__main__':
    # Render-এর জন্য PORT ভেরিয়েবল সেটআপ
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
