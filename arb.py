#!/usr/bin/env python3
"""
SEMI-AUTOMATED Arbitrage Finder - Real-Time Edition (Replit Version)
- Checks odds every 5 minutes
- Instant Telegram alerts with direct links
- Pre-calculated stakes
- YOU place bets manually (safe & legal!)
- Optimized for 1,000 KES stake
- Flask keep-alive for 24/7 operation on Replit
"""

from flask import Flask
from threading import Thread
import requests
import time
from datetime import datetime
from typing import List, Dict, Optional
import json

# ============================================================================
# FLASK KEEP-ALIVE (for Replit)
# ============================================================================

app = Flask('')

@app.route('/')
def home():
    uptime = datetime.now() - stats.get('started_at', datetime.now())
    hours = uptime.total_seconds() / 3600
    
    return f"""
    <html>
    <head><title>Arbitrage Bot</title></head>
    <body style="font-family: Arial; padding: 20px; background: #1a1a1a; color: #00ff00;">
        <h1>🚀 Arbitrage Bot is Running!</h1>
        <p>✅ Bot is active and monitoring for opportunities</p>
        <p>⏱️ Uptime: {hours:.1f} hours</p>
        <p>🔍 Searches performed: {stats.get('searches', 0)}</p>
        <p>🎯 Opportunities found: {stats.get('opportunities_found', 0)}</p>
        <p>📡 API calls made: {stats.get('api_calls', 0)}</p>
        <hr>
        <p style="color: #888;">Keep this URL alive with UptimeRobot for 24/7 monitoring</p>
    </body>
    </html>
    """

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ============================================================================
# CONFIGURATION
# ============================================================================

ODDS_API_KEY = "cca2b86b41ea4ff7d47cba7247f1dcde"
TELEGRAM_BOT_TOKEN = "8550504870:AAHNvImIK6NDqTbEK5R-iEjfUeObNjpQxZU"
TELEGRAM_CHAT_ID = "1899667197"

# Check odds every 5 minutes (real-time!)
CHECK_INTERVAL = 300  # seconds

# Settings
MIN_PROFIT_PERCENT = 2.0
MAX_STAKE_KES = 1000

# Active hours (Kenya time - 24hr format)
ACTIVE_START_HOUR = 6   # 6 AM
ACTIVE_END_HOUR = 23    # 11 PM
# Set both to 0 to run 24/7

# Smart daily sports schedule
DAILY_SPORTS = {
    0: ["basketball_nba", "icehockey_nhl"],  # Monday
    1: ["soccer_uefa_champs_league", "basketball_nba", "icehockey_nhl"],  # Tuesday
    2: ["soccer_uefa_champs_league", "soccer_epl", "basketball_nba"],  # Wednesday
    3: ["soccer_uefa_europa_league", "basketball_nba", "icehockey_nhl"],  # Thursday
    4: ["soccer_epl", "soccer_spain_la_liga", "basketball_nba"],  # Friday
    5: ["soccer_epl", "soccer_spain_la_liga", "soccer_germany_bundesliga", 
        "soccer_italy_serie_a", "basketball_nba"],  # Saturday
    6: ["soccer_epl", "soccer_spain_la_liga", "soccer_germany_bundesliga",
        "soccer_italy_serie_a", "basketball_nba"]  # Sunday
}

KENYAN_BOOKMAKERS = [
    'betway', 'betin', 'sportpesa', '22bet', '1xbet',
    'bet254', 'mozzartbet', 'betika', 'odibets', 'shabiki'
]

# Bookmaker URLs (for quick links)
BOOKMAKER_URLS = {
    'betway': 'https://betway.co.ke',
    'sportpesa': 'https://www.sportpesa.com',
    '22bet': 'https://22bet.co.ke',
    '1xbet': 'https://1xbet.co.ke',
    'betin': 'https://betin.co.ke',
    'bet254': 'https://www.bet254.com',
    'mozzartbet': 'https://www.mozzartbet.co.ke',
    'betika': 'https://www.betika.com',
    'odibets': 'https://odibets.com',
}

# Track found opportunities (avoid duplicate alerts)
seen_opportunities = set()

# Statistics
stats = {
    'searches': 0,
    'opportunities_found': 0,
    'api_calls': 0,
    'started_at': datetime.now()
}

# ============================================================================

class ArbitrageFinder:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        
    def is_3_way_sport(self, sport_key: str) -> bool:
        return 'soccer' in sport_key.lower() or 'football' in sport_key.lower()
    
    def get_odds(self, sport: str) -> Dict:
        is_3_way = self.is_3_way_sport(sport)
        url = f"{self.base_url}/sports/{sport}/odds"
        params = {
            'apiKey': self.api_key,
            'regions': 'uk,eu',
            'markets': 'h2h',
            'oddsFormat': 'decimal'
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            stats['api_calls'] += 1
            
            # Filter for Kenyan bookmakers
            filtered_data = []
            for event in data:
                kenyan_bms = [
                    bm for bm in event.get('bookmakers', [])
                    if any(kb.lower() in bm.get('key', '').lower() or 
                          kb.lower() in bm.get('title', '').lower() 
                          for kb in KENYAN_BOOKMAKERS)
                ]
                
                if kenyan_bms:
                    event['bookmakers'] = kenyan_bms
                    filtered_data.append(event)
            
            return {
                'data': filtered_data,
                'remaining': response.headers.get('x-requests-remaining'),
                'used': response.headers.get('x-requests-used'),
                'is_3_way': is_3_way
            }
        except requests.exceptions.Timeout:
            print(f"⚠️  {sport}: Connection timeout (retrying next cycle)")
            return {'data': [], 'remaining': None, 'used': None, 'is_3_way': is_3_way}
        except Exception as e:
            print(f"⚠️  {sport}: {e}")
            return {'data': [], 'remaining': None, 'used': None, 'is_3_way': is_3_way}
    
    def calculate_arbitrage(self, odds_list: List[float]) -> Dict:
        if not odds_list or any(o <= 1 for o in odds_list):
            return {'exists': False}
        
        implied_prob_sum = sum(1/odd for odd in odds_list)
        
        if implied_prob_sum < 1:
            profit_percent = ((1 / implied_prob_sum) - 1) * 100
            return {
                'exists': True,
                'profit_percent': profit_percent,
                'implied_prob_sum': implied_prob_sum
            }
        return {'exists': False}
    
    def calculate_stakes(self, total_stake: float, odds_list: List[float]) -> List[float]:
        implied_prob_sum = sum(1/odd for odd in odds_list)
        return [(total_stake / implied_prob_sum) / odd for odd in odds_list]
    
    def find_arbitrage_opportunities(self, sport: str, total_stake: float = 1000) -> List[Dict]:
        result = self.get_odds(sport)
        events = result['data']
        is_3_way = result['is_3_way']
        
        if not events:
            return []
        
        opportunities = []
        
        for event in events:
            try:
                home_team = event['home_team']
                away_team = event['away_team']
                commence_time = event['commence_time']
                event_id = event.get('id', f"{home_team}_{away_team}")
                
                best_odds = {}
                bookmaker_info = {}
                bookmaker_keys = {}
                
                for bookmaker in event['bookmakers']:
                    bookmaker_name = bookmaker['title']
                    bookmaker_key = bookmaker['key']
                    
                    for market in bookmaker['markets']:
                        if market['key'] == 'h2h':
                            for outcome in market['outcomes']:
                                outcome_name = outcome['name']
                                odds = outcome['price']
                                
                                if outcome_name not in best_odds or odds > best_odds[outcome_name]:
                                    best_odds[outcome_name] = odds
                                    bookmaker_info[outcome_name] = bookmaker_name
                                    bookmaker_keys[outcome_name] = bookmaker_key
                
                required_outcomes = 3 if is_3_way else 2
                
                if len(best_odds) >= required_outcomes:
                    odds_values = list(best_odds.values())
                    arb_result = self.calculate_arbitrage(odds_values)
                    
                    if arb_result['exists'] and arb_result['profit_percent'] >= MIN_PROFIT_PERCENT:
                        # Create unique ID to avoid duplicate alerts
                        opp_id = f"{event_id}_{arb_result['profit_percent']:.1f}"
                        
                        if opp_id in seen_opportunities:
                            continue  # Already alerted about this
                        
                        seen_opportunities.add(opp_id)
                        stats['opportunities_found'] += 1
                        
                        stakes = self.calculate_stakes(total_stake, odds_values)
                        guaranteed_return = stakes[0] * odds_values[0]
                        profit = guaranteed_return - total_stake
                        
                        opportunity = {
                            'sport': sport,
                            'sport_name': self.get_sport_display_name(sport),
                            'home_team': home_team,
                            'away_team': away_team,
                            'commence_time': commence_time,
                            'profit_percent': round(arb_result['profit_percent'], 2),
                            'profit_amount': round(profit, 2),
                            'total_stake': total_stake,
                            'guaranteed_return': round(guaranteed_return, 2),
                            'is_3_way': is_3_way,
                            'bets': []
                        }
                        
                        for i, (outcome, odds) in enumerate(best_odds.items()):
                            bet_type = self.get_bet_type_display(outcome, home_team, away_team, is_3_way)
                            bookmaker_key = bookmaker_keys[outcome]
                            bookmaker_url = BOOKMAKER_URLS.get(bookmaker_key, '#')
                            
                            opportunity['bets'].append({
                                'outcome': outcome,
                                'bet_type': bet_type,
                                'bookmaker': bookmaker_info[outcome],
                                'bookmaker_url': bookmaker_url,
                                'odds': round(odds, 2),
                                'stake': round(stakes[i], 2),
                                'return': round(stakes[i] * odds, 2)
                            })
                        
                        opportunities.append(opportunity)
                        
            except (KeyError, IndexError):
                continue
        
        return opportunities
    
    def get_sport_display_name(self, sport_key: str) -> str:
        names = {
            'soccer_epl': '⚽ EPL',
            'soccer_spain_la_liga': '⚽ La Liga',
            'soccer_germany_bundesliga': '⚽ Bundesliga',
            'soccer_italy_serie_a': '⚽ Serie A',
            'soccer_uefa_champs_league': '⚽ Champions League',
            'soccer_uefa_europa_league': '⚽ Europa League',
            'basketball_nba': '🏀 NBA',
            'icehockey_nhl': '🏒 NHL',
        }
        return names.get(sport_key, sport_key.upper())
    
    def get_bet_type_display(self, outcome: str, home: str, away: str, is_3_way: bool) -> str:
        if not is_3_way:
            if outcome == home:
                return f"{home} Win"
            elif outcome == away:
                return f"{away} Win"
            return outcome
        else:
            if outcome == home:
                return f"{home} Win (1)"
            elif outcome == away:
                return f"{away} Win (2)"
            elif outcome.lower() in ['draw', 'tie']:
                return "Draw (X)"
            return outcome


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, text: str, disable_preview: bool = True) -> bool:
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': disable_preview
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except requests.exceptions.Timeout:
            print("⚠️  Telegram timeout - message not sent")
            return False
        except Exception as e:
            print(f"Telegram error: {e}")
            return False
    
    def format_opportunity(self, opp: Dict) -> str:
        bet_type = "3-WAY" if opp['is_3_way'] else "2-WAY"
        
        msg = f"🚨 <b>ARBITRAGE ALERT!</b> 🚨\n"
        msg += f"⚡ <b>{bet_type}</b> | {opp['sport_name']}\n\n"
        
        msg += f"⚽ <b>{opp['home_team']} vs {opp['away_team']}</b>\n\n"
        
        msg += f"💰 <b>PROFIT: KES {opp['profit_amount']} ({opp['profit_percent']}%)</b>\n"
        msg += f"📊 Stake: KES {opp['total_stake']}\n"
        msg += f"✅ Return: KES {opp['guaranteed_return']}\n\n"
        
        msg += "🎯 <b>QUICK ACTION REQUIRED!</b>\n"
        msg += "⏱️ <i>Odds may change in 2-5 minutes</i>\n\n"
        
        msg += "=" * 30 + "\n"
        msg += "📋 <b>PLACE THESE BETS:</b>\n"
        msg += "=" * 30 + "\n\n"
        
        for i, bet in enumerate(opp['bets'], 1):
            msg += f"<b>BET {i}: {bet['bet_type']}</b>\n"
            msg += f"🏪 Bookmaker: {bet['bookmaker']}\n"
            msg += f"📊 Odds: {bet['odds']}\n"
            msg += f"💵 <b>Stake: KES {bet['stake']}</b>\n"
            msg += f"↩️ Return: KES {bet['return']}\n"
            
            if bet['bookmaker_url'] != '#':
                msg += f"🔗 <a href='{bet['bookmaker_url']}'>Open {bet['bookmaker']}</a>\n"
            
            msg += "\n"
        
        try:
            commence_dt = datetime.fromisoformat(opp['commence_time'].replace('Z', '+00:00'))
            msg += f"⏰ Match: {commence_dt.strftime('%d %b, %I:%M %p')}\n"
        except:
            pass
        
        msg += "\n⚡ <b>ACT NOW!</b> Open bookmaker apps and place bets!"
        
        return msg
    
    def send_daily_summary(self):
        """Send summary at end of day"""
        runtime = datetime.now() - stats['started_at']
        hours = runtime.total_seconds() / 3600
        
        msg = f"📊 <b>DAILY SUMMARY</b>\n\n"
        msg += f"⏱️ Runtime: {hours:.1f} hours\n"
        msg += f"🔍 Searches: {stats['searches']}\n"
        msg += f"🎯 Opportunities: {stats['opportunities_found']}\n"
        msg += f"📡 API Calls: {stats['api_calls']}\n"
        
        if stats['opportunities_found'] > 0:
            msg += f"\n🎉 Great day! {stats['opportunities_found']} opportunities found!"
        else:
            msg += f"\n😔 No opportunities today. Keep running!"
        
        return self.send_message(msg)


def is_active_hours() -> bool:
    """Check if currently in active hours"""
    if ACTIVE_START_HOUR == 0 and ACTIVE_END_HOUR == 0:
        return True  # 24/7 mode
    
    current_hour = datetime.now().hour
    return ACTIVE_START_HOUR <= current_hour < ACTIVE_END_HOUR


def get_todays_sports() -> List[str]:
    """Get sports based on day of week"""
    today = datetime.now().weekday()
    return DAILY_SPORTS.get(today, ["basketball_nba", "icehockey_nhl"])


def monitor_arbitrage(finder: ArbitrageFinder, notifier: Optional[TelegramNotifier]):
    """Main monitoring loop"""
    
    print("\n" + "="*80)
    print("🚀 SEMI-AUTOMATED ARBITRAGE MONITOR - REAL-TIME")
    print("="*80)
    print(f"\n⚡ Checking every {CHECK_INTERVAL} seconds")
    print(f"💰 Stake: KES {MAX_STAKE_KES}")
    print(f"📊 Min Profit: {MIN_PROFIT_PERCENT}%")
    
    if ACTIVE_START_HOUR != 0 or ACTIVE_END_HOUR != 0:
        print(f"⏰ Active: {ACTIVE_START_HOUR:02d}:00 - {ACTIVE_END_HOUR:02d}:00")
    else:
        print(f"⏰ Active: 24/7")
    
    print("="*80)
    
    if notifier:
        print("\n✅ Telegram alerts enabled!")
        print("📱 You'll get instant notifications!\n")
    else:
        print("\n⚠️  WARNING: Telegram not configured!")
        print("Opportunities will only show in console.\n")
    
    print("🔄 Starting real-time monitoring...")
    print("⚠️  Keep this window open!")
    print("📱 Press Ctrl+C to stop\n")
    
    last_summary_day = datetime.now().day
    
    while True:
        try:
            # Check if in active hours
            if not is_active_hours():
                current_hour = datetime.now().hour
                print(f"😴 [{datetime.now().strftime('%H:%M:%S')}] Outside active hours (currently {current_hour:02d}:00). Sleeping...")
                time.sleep(300)  # Check every 5 min
                continue
            
            # Get today's sports
            sports_to_search = get_todays_sports()
            
            stats['searches'] += 1
            now = datetime.now().strftime('%H:%M:%S')
            
            print(f"\n🔍 [{now}] Searching {len(sports_to_search)} sports... (Check #{stats['searches']})")
            
            # Search all sports
            all_opportunities = []
            for sport in sports_to_search:
                opportunities = finder.find_arbitrage_opportunities(sport, MAX_STAKE_KES)
                if opportunities:
                    all_opportunities.extend(opportunities)
            
            # Report results
            if all_opportunities:
                print(f"🎉 FOUND {len(all_opportunities)} OPPORTUNITY(IES)!")
                
                # Send Telegram alerts
                if notifier:
                    for opp in all_opportunities:
                        message = notifier.format_opportunity(opp)
                        if notifier.send_message(message):
                            print(f"📱 Alert sent: {opp['home_team']} vs {opp['away_team']} (KES {opp['profit_amount']})")
                        else:
                            print(f"❌ Failed to send alert")
                        time.sleep(1)  # Avoid Telegram rate limit
                else:
                    # Just print to console
                    for opp in all_opportunities:
                        print(f"\n💰 {opp['home_team']} vs {opp['away_team']}")
                        print(f"   Profit: KES {opp['profit_amount']} ({opp['profit_percent']}%)")
                        for bet in opp['bets']:
                            print(f"   - {bet['bet_type']}: KES {bet['stake']} @ {bet['bookmaker']}")
            else:
                print(f"   No opportunities | API: {stats['api_calls']} calls | Found today: {stats['opportunities_found']}")
            
            # Send daily summary
            current_day = datetime.now().day
            if current_day != last_summary_day and notifier:
                notifier.send_daily_summary()
                last_summary_day = current_day
                # Reset daily stats
                stats['searches'] = 0
                stats['opportunities_found'] = 0
                stats['started_at'] = datetime.now()
            
            # Wait before next check
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Stopping monitor...")
            if notifier:
                notifier.send_message("🛑 Arbitrage monitor stopped.")
            print("\n📊 Final Stats:")
            print(f"   Searches: {stats['searches']}")
            print(f"   Opportunities: {stats['opportunities_found']}")
            print(f"   API Calls: {stats['api_calls']}")
            print("\nGoodbye! 👋\n")
            break
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Continuing in 60 seconds...")
            time.sleep(60)


def main():
    # Start Flask server to keep Replit alive
    print("🌐 Starting Flask server for 24/7 uptime...")
    keep_alive()
    print("✅ Flask server running on port 8080")
    print("🔗 Bot will stay alive as long as UptimeRobot pings it!\n")
    
    finder = ArbitrageFinder(ODDS_API_KEY)
    
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        notifier = None
    else:
        notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        # Send startup message
        notifier.send_message(
            f"🚀 <b>Arbitrage Monitor Started!</b>\n\n"
            f"⚡ Checking every {CHECK_INTERVAL} seconds\n"
            f"💰 Stake: KES {MAX_STAKE_KES}\n"
            f"📊 Min Profit: {MIN_PROFIT_PERCENT}%\n\n"
            f"You'll get instant alerts! 📱"
        )
    
    # Start monitoring
    monitor_arbitrage(finder, notifier)


if __name__ == "__main__":
    main()
