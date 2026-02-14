"""Test the Polymarket LoL odds fetcher."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Minimal Streamlit stub so we can run outside Streamlit
import types
st_stub = types.ModuleType("streamlit")
st_stub.cache_data = lambda **kw: (lambda f: f)  # no-op decorator
sys.modules["streamlit"] = st_stub

from src.polymarket import fetch_polymarket_odds, get_team_odds, format_trend

print("=" * 60)
print("  POLYMARKET LOL ODDS FETCHER TEST")
print("=" * 60)

# 1. Fetch all odds
print("\n📡 Fetching Polymarket LoL events...")
odds = fetch_polymarket_odds()
print(f"✅ Found odds for {len(odds)} teams\n")

if not odds:
    print("⚠️  No data returned — API may be down or no active events.")
    sys.exit(1)

# 2. Print all team odds
print(f"{'Team':<30s} {'League':<6s} {'Odds':>8s} {'1w Chg':>8s} {'Volume':>12s} {'Bid/Ask':>12s}")
print("-" * 80)

for team, data in sorted(odds.items(), key=lambda x: -x[1]["odds"]):
    print(f"{team:<30s} {data['league']:<6s} {data['odds']:>7.1%} {data['change_1w']:>+7.1%}"
          f" ${data['volume']:>10,.0f} {data['best_bid']:.2f}/{data['best_ask']:.2f}")

# 3. Test get_team_odds helper
print("\n\n🔍 Testing get_team_odds('Gen.G', 'T1')...")
result = get_team_odds("Gen.G", "T1")
if result:
    print(f"  League: {result['league']}")
    if result["team_a"]:
        print(f"  Gen.G odds: {result['team_a']['odds']:.1%}")
    if result["team_b"]:
        print(f"  T1 odds:    {result['team_b']['odds']:.1%}")
else:
    print("  ⚠️  No data for Gen.G vs T1")

# 4. Test missing team
print("\n🔍 Testing get_team_odds('FakeTeam', 'AnotherFake')...")
result2 = get_team_odds("FakeTeam", "AnotherFake")
assert result2 is None, "Expected None for unknown teams"
print("  ✅ Correctly returned None for unknown teams")

# 5. Test format_trend
print("\n🔍 Testing format_trend...")
assert "🟢" in format_trend(0.05)
assert "🔴" in format_trend(-0.03)
assert "➖" in format_trend(0)
print("  ✅ format_trend works correctly")

print(f"\n{'=' * 60}")
print("  POLYMARKET TEST COMPLETE ✅")
print(f"{'=' * 60}")
