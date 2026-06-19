from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

app = Flask(__name__)
# InfinityFree থেকে রিকোয়েস্ট অ্যাকসেপ্ট করার জন্য CORS এনাবল করা হলো
CORS(app) 

def fetch_nesco_balance(meter_number):
    """
    এই ফাংশনটি NESCO-এর সার্ভার থেকে ব্যালেন্স আনবে। 
    যেহেতু কোনো পাবলিক API নেই, আপনাকে ব্রাউজারের Inspect > Network tab ব্যবহার করে 
    NESCO কাস্টমার পোর্টালের আসল URL এবং Payload বের করে এখানে বসাতে হবে।
    """
    
    # এটি একটি ডামি/টেম্পলেট স্ট্রাকচার। আসল URL এবং হেডারের জন্য NESCO ওয়েবসাইট চেক করুন।
    nesco_login_url = "https://customer.nesco.gov.bd/api/login_or_balance_endpoint"
    
    # ধরি NESCO এই ফরম্যাটে ডেটা নেয়
    payload = {
        "meter_no": meter_number
        # যদি লগইন প্রয়োজন হয়, তবে username/password বা token এখানে দিতে হবে
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json"
    }

    try:
        # আসল রিকোয়েস্ট করার কোড:
        # response = requests.post(nesco_login_url, json=payload, headers=headers)
        # data = response.json()
        # balance = data.get("balance")

        # টেস্ট করার জন্য ডামি রেসপন্স (আসল API বসালে এটি মুছে দেবেন)
        simulated_balance = "540.25" 
        
        return {
            "success": True,
            "meter_number": meter_number,
            "balance": simulated_balance
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# --- নতুন যোগ করা হোম রুট ---
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "success",
        "message": "NESCO API is running perfectly!"
    })
# -----------------------------

@app.route('/api/get-balance', methods=['GET'])
def get_balance():
    meter_number = request.args.get('meter')
    
    if not meter_number:
        return jsonify({"success": False, "error": "Meter number is missing!"}), 400

    data = fetch_nesco_balance(meter_number)
    return jsonify(data)

if __name__ == '__main__':
    # Render সাধারণত PORT এনভায়রনমেন্ট ভেরিয়েবল ব্যবহার করে
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
