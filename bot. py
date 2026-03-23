import telebot
import requests
import random
import time
import base64
import json

# ========== إعدادات PayPal (Sandbox) ==========
# سجل في https://developer.paypal.com عشان تاخذ هذه المفاتيح
PAYPAL_CLIENT_ID = "YOUR_PAYPAL_CLIENT_ID"
PAYPAL_SECRET = "YOUR_PAYPAL_SECRET"

# ========== توكن البوت ==========
BOT_TOKEN = "7662450317:AAHOQUXKWf4e4Zzs9oWhFkbguLBwS_QvM4Q"
bot = telebot.TeleBot(BOT_TOKEN)

try:
    bot.delete_webhook()
    print("Webhook deleted")
except:
    pass

# ========== جلب معلومات BIN ==========
def get_bin_info(bin_prefix):
    try:
        url = f"https://lookup.binlist.net/{bin_prefix[:6]}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            bank = data.get('bank', {}).get('name', 'غير معروف')
            country = data.get('country', {}).get('name', 'غير معروف')
            scheme = data.get('scheme', 'غير معروف')
            brand = data.get('brand', 'غير معروف')
            return {
                'bank': bank,
                'country': country,
                'scheme': scheme,
                'brand': brand
            }
        return None
    except:
        return None

# ========== توليد بطاقة ==========
def gen_card(bin_prefix):
    remaining = ''.join([str(random.randint(0,9)) for _ in range(9)])
    card = bin_prefix[:6] + remaining
    digits = [int(d) for d in card]
    for i in range(len(digits)-1, -1, -1):
        if i % 2 == 0:
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9
    check = (10 - (sum(digits) % 10)) % 10
    full = card + str(check)
    month = str(random.randint(1,12)).zfill(2)
    year = str(random.randint(2025,2029))
    cvv = str(random.randint(100,999))
    return f"{full}|{month}|{year}|{cvv}"

def generate_cards(bin_prefix, count):
    cards = []
    for _ in range(count):
        cards.append(gen_card(bin_prefix))
    return cards

# ========== الحصول على توكن PayPal ==========
def get_paypal_token():
    try:
        url = "https://api.sandbox.paypal.com/v1/oauth2/token"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US",
        }
        auth = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_SECRET}".encode()).decode()
        headers["Authorization"] = f"Basic {auth}"
        data = {"grant_type": "client_credentials"}
        r = requests.post(url, headers=headers, data=data, timeout=15)
        if r.status_code == 200:
            return r.json().get("access_token")
        return None
    except:
        return None

# ========== فحص بطاقة على PayPal ==========
def check_paypal(card_str):
    try:
        parts = card_str.split('|')
        card, month, year, cvv = parts
        
        token = get_paypal_token()
        if not token:
            return "DEAD"
        
        url = "https://api.sandbox.paypal.com/v1/payments/payment"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        card_clean = card.replace(" ", "")
        
        payload = {
            "intent": "sale",
            "payer": {
                "payment_method": "credit_card",
                "funding_instruments": [{
                    "credit_card": {
                        "number": card_clean,
                        "type": "visa",
                        "expire_month": month,
                        "expire_year": year,
                        "cvv2": cvv
                    }
                }]
            },
            "transactions": [{
                "amount": {
                    "total": "1.00",
                    "currency": "USD"
                },
                "description": "Test Payment"
            }]
        }
        
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if r.status_code == 201:
            return "LIVE_NO_OTP"
        else:
            return "DEAD"
    except:
        return "DEAD"

# ========== أوامر البوت ==========
@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, """
🌟 **بوت فحص PayPal** 🌟

/gen <BIN> → توليد 10 بطاقات
/otp رقم|شهر|سنة|رمز → فحص بطاقة واحدة
/otp20 <BIN> → فحص 20 بطاقة (مع معلومات البنك)

⚠️ يستخدم PayPal Sandbox للاختبار
    """)

@bot.message_handler(commands=['gen'])
def gen_cmd(msg):
    try:
        parts = msg.text.split()
        bin_prefix = parts[1] if len(parts) > 1 else "424242"
        cards = [gen_card(bin_prefix) for _ in range(10)]
        bot.reply_to(msg, "🎴 **10 بطاقات:**\n\n" + "\n".join(cards))
    except Exception as e:
        bot.reply_to(msg, f"خطأ: {e}")

@bot.message_handler(commands=['otp'])
def otp_cmd(msg):
    try:
        data = msg.text.replace('/otp', '').strip()
        if '|' not in data:
            bot.reply_to(msg, "❌ /otp رقم|شهر|سنة|رمز\nمثال: /otp 4242424242424242|12|2025|123")
            return
        parts = data.split('|')
        if len(parts) != 4:
            bot.reply_to(msg, "❌ 4 أجزاء: رقم|شهر|سنة|رمز")
            return
        card_str = data.strip()
        card_number = parts[0]
        bin_info = get_bin_info(card_number[:6])
        
        info_text = ""
        if bin_info:
            info_text = f"\n🏦 **{bin_info['bank']}**\n🌍 **{bin_info['country']}**\n💳 **{bin_info['scheme'].upper()}**\n"
        
        bot.reply_to(msg, f"⏳ جاري الفحص...\n{card_str}{info_text}")
        result = check_paypal(card_str)
        if result == "LIVE_NO_OTP":
            bot.reply_to(msg, f"✅ **LIVE - لا تطلب OTP**\n{card_str}{info_text}")
        else:
            bot.reply_to(msg, f"❌ **DEAD أو OTP**\n{card_str}{info_text}")
    except Exception as e:
        bot.reply_to(msg, f"خطأ: {e}")

@bot.message_handler(commands=['otp20'])
def otp20_cmd(msg):
    try:
        parts = msg.text.split()
        if len(parts) < 2:
            bot.reply_to(msg, "❌ /otp20 <BIN>\nمثال: /otp20 465901")
            return
        bin_prefix = parts[1][:6]
        
        bin_info = get_bin_info(bin_prefix)
        info_header = ""
        if bin_info:
            info_header = f"\n🏦 **البنك:** {bin_info['bank']}\n🌍 **الدولة:** {bin_info['country']}\n💳 **النوع:** {bin_info['scheme'].upper()} ({bin_info['brand']})\n"
        else:
            info_header = "\n❓ **معلومات البنك غير متوفرة**\n"
        
        bot.reply_to(msg, f"🔍 **فحص BIN {bin_prefix}**{info_header}\n⏳ جاري توليد وفحص 20 بطاقة... (قد يستغرق 30-60 ثانية)")
        
        cards = generate_cards(bin_prefix, 20)
        
        live_cards = []
        results_text = f"📊 **نتائج فحص BIN {bin_prefix}**\n{info_header}\n"
        results_text += "═" * 40 + "\n\n"
        
        for i, card in enumerate(cards, 1):
            result = check_paypal(card)
            if result == "LIVE_NO_OTP":
                live_cards.append(card)
                status = "✅ LIVE"
            else:
                status = "❌ DEAD"
            
            results_text += f"{i:2}. {card} → {status}\n"
            time.sleep(0.3)
        
        results_text += f"\n{'═' * 40}\n"
        results_text += f"📈 **الإحصائيات:**\n"
        results_text += f"🔴 LIVE بدون OTP: {len(live_cards)}\n"
        results_text += f"⚫ DEAD: {20 - len(live_cards)}\n"
        
        if live_cards:
            results_text += f"\n⚠️ **ثغرة مكتشفة!** {len(live_cards)} بطاقة صالحة بدون OTP.\n"
            results_text += f"💡 يمكن ربطها بـ PayPal مباشرة.\n"
        else:
            results_text += f"\n✅ **BIN آمن** - لا توجد بطاقات صالحة بدون OTP.\n"
        
        if len(results_text) > 4000:
            bot.reply_to(msg, results_text[:4000])
            if len(results_text) > 4000:
                bot.reply_to(msg, results_text[4000:8000])
        else:
            bot.reply_to(msg, results_text)
            
    except Exception as e:
        bot.reply_to(msg, f"خطأ: {e}")

print("🚀 بوت PayPal شغال...")
bot.infinity_polling()
