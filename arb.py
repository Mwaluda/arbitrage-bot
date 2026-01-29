from flask import Flask
from threading import Thread
import time
import requests
from datetime import datetime

# Flask app to keep Replit alive
app = Flask('')

@app.route('/')
def home():
    return "🚀 Arbitrage Bot is Running! Bot is active and monitoring for opportunities."

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ================================================================================
# ARBITRAGE BOT CONFIGURATION
# ================================================================================

TELEGRAM_BOT_TOKEN = "8550504870:AAHNvImIK6NDqTbEK5R-iEjfUeObNjpQxZU"
TELEGRAM_CHAT_ID = "1899667197"
ODDS_API_KEY = "YOUR_ODDS_API_KEY"  # ⚠️ REPLACE THIS with your actual API key from the-odds-api.com

STAKE = 1000  # KES
MIN_PROFIT_PERCENT = 2.0
CHECK_INTERVAL = 300  # seconds (5 minutes)
SPORTS = ['soccer_kenya_premier_league', 'basketball_nba', 'tennis_atp']

# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

def send_telegram_message(message):
    """Send message to Telegram with better error handling"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.Timeout:
        print("⚠️  Telegram timeout - message not sent")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Telegram error: {e}")
        return False

def get_odds(sport, retries=3):
    """Fetch odds with retry logic"""
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'uk',
        'markets': 'h2h',
        'oddsFormat': 'decimal'
    }
    
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print(f"   ⚠️  Timeout attempt {attempt + 1}/{retries}")
            if attempt < retries - 1:
                time.sleep(2)
        except requests.exceptions.RequestException as e:
            print(f"   ❌ API Error: {e}")
            return None
    
    print(f"   ❌ Failed after {retries} attempts")
    return None

def calculate_arbitrage(odds_data):
    """Calculate arbitrage opportunities"""
    opportunities = []
    
    if not odds_data:
        return opportunities
    
    for game in odds_data:
        if 'bookmakers' not in game or len(game['bookmakers']) < 2:
            continue
            
        best_odds = {}
        
        for bookmaker in game['bookmakers']:
            if 'markets' not in bookmaker:
                continue
                
            for market in bookmaker['markets']:
                if market['key'] != 'h2h':
                    continue
                    
                for outcome in market['outcomes']:
                    outcome_name = outcome['name']
                    odds = outcome['price']
                    
                    if outcome_name not in best_odds or odds > best_odds[outcome_name]['odds']:
                        best_odds[outcome_name] = {
                            'odds': odds,
                            'bookmaker': bookmaker['title']
                        }
        
        if len(best_odds) < 2:
            continue
        
        # Calculate arbitrage
        total_inverse = sum(1/odds['odds'] for odds in best_odds.values())
        
        if total_inverse < 1:
            profit_percent = ((1/total_inverse - 1) * 100)
            
            if profit_percent >= MIN_PROFIT_PERCENT:
                stakes = {}
                for outcome, data in best_odds.items():
                    stakes[outcome] = STAKE / (data['odds'] * total_inverse)
                
                opportunities.append({
                    'game': f"{game['home_team']} vs {game['away_team']}",
                    'sport': game['sport_title'],
                    'profit_percent': profit_percent,
                    'bets': best_odds,
                    'stakes': stakes,
                    'total_stake': STAKE,
                    'guaranteed_profit': STAKE * (1/total_inverse - 1)
                })
    
    return opportunities

# ================================================================================
# MAIN FUNCTION
# ================================================================================

def main():
    """Main monitoring loop"""
    print("=" * 80)
    print("🚀 SEMI-AUTOMATED ARBITRAGE MONITOR - REAL-TIME")
    print("=" * 80)
    print(f"⚡ Checking every {CHECK_INTERVAL} seconds")
    print(f"💰 Stake: KES {STAKE}")
    print(f"📊 Min Profit: {MIN_PROFIT_PERCENT}%")
    print(f"⏰ Active: 06:00 - 23:00")
    print("=" * 80)
    print("✅ Telegram alerts enabled!")
    print("📱 You'll get instant notifications!")
    print("🔄 Starting real-time monitoring...")
    print("⚠️  Keep this window open!")
    print("📱 Press Ctrl+C to stop")
    
    # Start Flask server to keep Replit alive
    print("\n🌐 Starting web server to keep bot alive...")
    keep_alive()
    print("✅ Web server started! Bot will stay alive 24/7")
    
    # Send startup notification
    send_telegram_message("🚀 <b>Arbitrage Bot Started!</b>\n\nMonitoring for opportunities every 5 minutes.")
    
    check_count = 0
    total_api_calls = 0
    opportunities_today = 0
    
    while True:
        try:
            check_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"\n🔍 [{current_time}] Searching {len(SPORTS)} sports... (Check #{check_count})")
            
            all_opportunities = []
            
            for sport in SPORTS:
                print(f"   📊 Checking {sport}...")
                odds_data = get_odds(sport)
                total_api_calls += 1
                
                if odds_data:
                    opportunities = calculate_arbitrage(odds_data)
                    all_opportunities.extend(opportunities)
            
            if all_opportunities:
                opportunities_today += len(all_opportunities)
                print(f"   🎯 Found {len(all_opportunities)} opportunities!")
                
                for opp in all_opportunities:
                    message = f"""
🎯 <b>ARBITRAGE OPPORTUNITY!</b>

🏆 {opp['game']}
📊 Sport: {opp['sport']}
💰 Profit: {opp['profit_percent']:.2f}%
💵 Guaranteed: KES {opp['guaranteed_profit']:.2f}

<b>Bets to Place:</b>
"""
                    for outcome, data in opp['bets'].items():
                        stake = opp['stakes'][outcome]
                        message += f"\n📌 {outcome}: KES {stake:.2f} @ {data['odds']} ({data['bookmaker']})"
                    
                    send_telegram_message(message)
                    print(f"   📤 Alert sent to Telegram!")
            else:
                print(f"   ✅ No opportunities | API: {total_api_calls} calls | Found today: {opportunities_today}")
            
            # Wait before next check
            print(f"   ⏳ Waiting {CHECK_INTERVAL} seconds until next check...")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n👋 Stopping monitor...")
            print(f"📊 Final Stats:")
            print(f"   Checks performed: {check_count}")
            print(f"   API calls made: {total_api_calls}")
            print(f"   Opportunities found: {opportunities_today}")
            send_telegram_message("🛑 <b>Bot Stopped</b>\n\nArbitrage monitoring has been stopped.")
            break
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            print(f"   🔄 Retrying in 30 seconds...")
            time.sleep(30)  # Wait 30 seconds before retry

if __name__ == "__main__":
    main()
