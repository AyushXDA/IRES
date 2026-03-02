"""Test script for Railway Reservation System — all endpoints."""
import httpx
import json
import pymysql
import sys

BASE = "http://localhost:8000"
passed = 0
failed = 0


def pp(data):
    """Pretty print JSON."""
    print(json.dumps(data, indent=2, default=str))


def check(label, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"   [PASS] {label}")
    else:
        failed += 1
        print(f"   [FAIL] {label}")


# ═══════════════════ CLEANUP ══════════════════════════
print("=" * 60)
print("CLEANUP: Truncating tables for a clean run")
conn = pymysql.connect(host="localhost", user="root", password="root", database="railway_db")
c = conn.cursor()
c.execute("SET FOREIGN_KEY_CHECKS=0")
for table in ["bookings", "trains", "users"]:
    c.execute(f"TRUNCATE TABLE {table}")
c.execute("SET FOREIGN_KEY_CHECKS=1")
conn.commit()
conn.close()
print("   Tables cleaned.")

# ═══════════════════ SETUP: Register + Promote Admin ══
print()
print("=" * 60)
print("SETUP: Register admin user")
r = httpx.post(f"{BASE}/auth/register", json={
    "username": "ayush",
    "email": "ayush@example.com",
    "password": "Secret123",
})
print(f"   Register: {r.status_code}")

# Promote to admin via direct DB update
conn = pymysql.connect(host="localhost", user="root", password="root", database="railway_db")
c = conn.cursor()
c.execute("UPDATE users SET role=%s WHERE email=%s", ("admin", "ayush@example.com"))
conn.commit()
conn.close()
print("   Promoted to admin")

# ═══════════════════ LOGIN AS ADMIN ═══════════════════
print()
print("=" * 55)
print("5. LOGIN AS ADMIN")
r = httpx.post(f"{BASE}/auth/login", json={"email": "ayush@example.com", "password": "Secret123"})
admin_token = r.json()["access_token"]
admin_h = {"Authorization": f"Bearer {admin_token}"}
print(f"   Status: {r.status_code}")

r = httpx.get(f"{BASE}/auth/me", headers=admin_h)
print(f"   Role: {r.json()['role']}")

# ═══════════════════ ADD TRAINS ═══════════════════════
print()
print("6. ADD TRAIN #1 (Rajdhani)")
r = httpx.post(f"{BASE}/admin/trains", headers=admin_h, json={
    "train_number": "12301",
    "train_name": "Rajdhani Express",
    "source": "New Delhi",
    "destination": "Mumbai Central",
    "total_seats": 5,
    "departure_time": "16:00",
    "arrival_time": "08:15",
})
print(f"   Status: {r.status_code}")
train1 = r.json()
print(f"   Train: {train1['train_name']} | Seats: {train1['available_seats']}/{train1['total_seats']}")

print()
print("7. ADD TRAIN #2 (Shatabdi)")
r = httpx.post(f"{BASE}/admin/trains", headers=admin_h, json={
    "train_number": "12002",
    "train_name": "Shatabdi Express",
    "source": "New Delhi",
    "destination": "Bhopal",
    "total_seats": 3,
    "departure_time": "06:15",
    "arrival_time": "14:30",
})
print(f"   Status: {r.status_code}")
train2 = r.json()
print(f"   Train: {train2['train_name']} | Seats: {train2['available_seats']}/{train2['total_seats']}")

# ═══════════════════ DUPLICATE TRAIN ══════════════════
print()
print("8. ADD DUPLICATE TRAIN (expect 409)")
r = httpx.post(f"{BASE}/admin/trains", headers=admin_h, json={
    "train_number": "12301",
    "train_name": "Dup",
    "source": "A",
    "destination": "B",
    "total_seats": 10,
})
print(f"   Status: {r.status_code} | {r.json()['detail']}")

# ═══════════════════ UPDATE TRAIN ═════════════════════
print()
print("9. UPDATE TRAIN (PATCH)")
r = httpx.patch(f"{BASE}/admin/trains/{train1['id']}", headers=admin_h, json={
    "train_name": "Rajdhani Super Express",
})
print(f"   Status: {r.status_code} | New name: {r.json()['train_name']}")

# ═══════════════════ LIST & SEARCH ════════════════════
print()
print("10. LIST ALL TRAINS")
r = httpx.get(f"{BASE}/trains")
print(f"   Status: {r.status_code} | Count: {len(r.json())}")
for t in r.json():
    print(f"   - {t['train_number']} {t['train_name']}: {t['source']} -> {t['destination']} ({t['available_seats']}/{t['total_seats']})")

print()
print("11. SEARCH: Delhi -> Mumbai")
r = httpx.get(f"{BASE}/trains/search", params={"source": "Delhi", "destination": "Mumbai"})
print(f"   Status: {r.status_code} | Results: {len(r.json())}")
check("Found Rajdhani for Delhi->Mumbai", r.status_code == 200 and len(r.json()) >= 1)

print()
print("12. SEARCH: source only (Delhi)")
r = httpx.get(f"{BASE}/trains/search", params={"source": "Delhi"})
print(f"   Status: {r.status_code} | Results: {len(r.json())}")
check("Source-only search returns trains from Delhi", r.status_code == 200 and len(r.json()) >= 2)

print()
print("13. SEARCH: destination only (Bhopal)")
r = httpx.get(f"{BASE}/trains/search", params={"destination": "Bhopal"})
print(f"   Status: {r.status_code} | Results: {len(r.json())}")
check("Dest-only search returns trains to Bhopal", r.status_code == 200 and len(r.json()) >= 1)

print()
print("14. SEARCH: no results (Delhi -> Chennai)")
r = httpx.get(f"{BASE}/trains/search", params={"source": "Delhi", "destination": "Chennai"})
print(f"   Status: {r.status_code} | Results: {len(r.json())}")
check("No trains for Delhi->Chennai", r.status_code == 200 and len(r.json()) == 0)

print()
print("15. STATIONS AUTOCOMPLETE")
r = httpx.get(f"{BASE}/trains/stations")
stations = r.json()
print(f"   Status: {r.status_code} | Stations: {stations}")
check("Stations endpoint returns list", r.status_code == 200 and isinstance(stations, list))
check("Contains 'New Delhi'", "New Delhi" in stations)
check("Contains 'Mumbai Central'", "Mumbai Central" in stations)
check("Contains 'Bhopal'", "Bhopal" in stations)

# ═══════════════════ BOOKING FLOW ═════════════════════
# Register a regular user for booking tests
print()
print("=" * 60)
print("16. REGISTER REGULAR USER")
r = httpx.post(f"{BASE}/auth/register", json={
    "username": "rider1",
    "email": "rider1@test.com",
    "password": "Pass1234",
})
print(f"   Status: {r.status_code}")

r = httpx.post(f"{BASE}/auth/login", json={"email": "rider1@test.com", "password": "Pass1234"})
user_token = r.json()["access_token"]
user_h = {"Authorization": f"Bearer {user_token}"}

print()
print("17. BOOK A SEAT on Rajdhani")
r = httpx.post(f"{BASE}/bookings", headers=user_h, json={"train_id": train1["id"]})
print(f"   Status: {r.status_code}")
booking1 = r.json()
print(f"   Booking ID: {booking1['id']} | Seat: {booking1['seat_number']} | Train: {booking1['train_name']}")
check("Booking created", r.status_code == 201 or r.status_code == 200)

print()
print("18. DUPLICATE BOOKING (expect 409)")
r = httpx.post(f"{BASE}/bookings", headers=user_h, json={"train_id": train1["id"]})
print(f"   Status: {r.status_code} | {r.json()['detail']}")
check("Duplicate blocked", r.status_code == 409)

print()
print("19. CHECK SEAT AVAILABILITY")
r = httpx.get(f"{BASE}/trains/{train1['id']}")
t = r.json()
print(f"   {t['train_name']}: {t['available_seats']}/{t['total_seats']} available")
check("Seat count decreased", t['available_seats'] == t['total_seats'] - 1)

print()
print("20. MY BOOKING HISTORY")
r = httpx.get(f"{BASE}/bookings/my", headers=user_h)
print(f"   Status: {r.status_code} | Bookings: {len(r.json())}")
for b in r.json():
    print(f"   - Booking #{b['id']}: Seat {b['seat_number']} on {b['train_name']} ({b['status']})")
check("Has bookings", len(r.json()) >= 1)

print()
print("21. CANCEL BOOKING")
r = httpx.delete(f"{BASE}/bookings/{booking1['id']}", headers=user_h)
print(f"   Status: {r.status_code} | New status: {r.json()['status']}")
check("Booking cancelled", r.json()['status'] == 'cancelled')

print()
print("22. VERIFY SEAT RESTORED")
r = httpx.get(f"{BASE}/trains/{train1['id']}")
t = r.json()
print(f"   {t['train_name']}: {t['available_seats']}/{t['total_seats']} available")
check("Seat restored after cancel", t['available_seats'] == t['total_seats'])

print()
print("23. BOOKING HISTORY (shows cancelled)")
r = httpx.get(f"{BASE}/bookings/my", headers=user_h)
for b in r.json():
    print(f"   - Booking #{b['id']}: Seat {b['seat_number']} on {b['train_name']} ({b['status']})")

# ═══════════════════ UNAUTHORIZED TEST ════════════════
print()
print("=" * 60)
print("24. REGULAR USER tries admin endpoint (expect 403)")
r = httpx.post(f"{BASE}/admin/trains", headers=user_h, json={
    "train_number": "99999",
    "train_name": "Hack Train",
    "source": "A",
    "destination": "B",
    "total_seats": 1,
})
print(f"   Status: {r.status_code} | {r.json()['detail']}")
check("Admin blocked for regular user", r.status_code == 403)

print()
print("25. NO TOKEN hits protected route (expect 401)")
r = httpx.get(f"{BASE}/auth/me")
print(f"   Status: {r.status_code} | {r.json()['detail']}")
check("Unauthorized without token", r.status_code == 401)

# ═══════════════════ DELETE TRAIN ═════════════════════
print()
print("26. DELETE TRAIN (admin)")
r = httpx.delete(f"{BASE}/admin/trains/{train2['id']}", headers=admin_h)
print(f"   Status: {r.status_code}")
check("Train deleted", r.status_code == 200)

print()
print("27. VERIFY STATIONS UPDATED AFTER DELETE")
r = httpx.get(f"{BASE}/trains/stations")
stations = r.json()
print(f"   Stations: {stations}")
check("Bhopal removed from stations", "Bhopal" not in stations)

# ═══════════════════ SUMMARY ═════════════════════════
print()
print("=" * 60)
total = passed + failed
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print("Some tests failed -- check output above")
print("=" * 60)
sys.exit(1 if failed else 0)
