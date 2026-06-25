import requests
import time

BASE_URL = "https://qa-testing-navy.vercel.app"

# Dynamic candidate ID — required by API (fixed ID causes StateCollision bug)
CANDIDATE_ID = f"barkavi_{int(time.time())}"

headers = {
    "X-Candidate-ID": CANDIDATE_ID
}

# -------------------------
# AUTHENTICATE
# -------------------------
auth_response = requests.post(
    f"{BASE_URL}/api/auth",
    headers=headers
)

print("AUTH:")
print(auth_response.status_code)
print(auth_response.text)

if auth_response.status_code != 201:
    print("Authentication failed")
    exit()

token = auth_response.json()["token"]

print("\nTOKEN:")
print(token)

# Auth headers
auth_headers = {
    "X-Candidate-ID": CANDIDATE_ID,
    "Authorization": f"Bearer {token}"
}

# -------------------------
# CREATE VIDEO
# -------------------------
video_response = requests.post(
    f"{BASE_URL}/api/videos",
    headers=auth_headers
)

print("\nCREATE VIDEO:")
print(video_response.status_code)
print(video_response.text)

if video_response.status_code != 201:
    print("Video creation failed")
    exit()

video_data = video_response.json()
video_id = video_data["id"]

print("\nVIDEO ID:")
print(video_id)

# -------------------------
# PROCESS CAPTIONS
# -------------------------
process_response = requests.post(
    f"{BASE_URL}/api/videos/{video_id}/process-captions",
    headers=auth_headers
)

print("\nPROCESS:")
print(process_response.status_code)
print(process_response.text)

# -------------------------
# POLL STATUS
# -------------------------
print("\nWAITING FOR COMPLETION...")
print("NOTE: Token expires in 5 seconds — re-authenticating each poll (Bug #4)")

for i in range(20):

    # Re-authenticate every poll due to 5-second token expiry bug
    reauth = requests.post(f"{BASE_URL}/api/auth", headers=headers)
    if reauth.status_code == 201:
        new_token = reauth.json()["token"]
        auth_headers["Authorization"] = f"Bearer {new_token}"
        print(f"  Re-authenticated at attempt {i+1}")
    elif reauth.status_code == 409:
        print(f"  BUG: StateCollision at attempt {i+1} — cannot re-auth with same ID")
        print(f"  This proves Bug B4: no session cleanup endpoint exists")
        break
    else:
        print(f"  Re-auth failed at attempt {i+1}: {reauth.text}")

    status_response = requests.get(
        f"{BASE_URL}/api/videos/{video_id}",
        headers=auth_headers
    )

    print(f"\nAttempt {i+1}")
    print(status_response.status_code)
    print(status_response.text)

    if status_response.status_code == 401:
        print("BUG CONFIRMED: Token expired during async polling — 5s too short")
        break

    data = status_response.json()

    if data.get("status") == "completed":
        print("\nPROCESSING COMPLETED!")
        break

    time.sleep(3)

# -------------------------
# GET CAPTIONS
# -------------------------
print("\nGET CAPTIONS:")

captions_response = requests.get(
    f"{BASE_URL}/api/captions",
    params={"videoId": video_id},
    headers=auth_headers
)

print(captions_response.status_code)
print(captions_response.text)

if captions_response.status_code == 200:
    data = captions_response.json()
    if isinstance(data, list) and len(data) == 0:
        print("BUG CONFIRMED: Captions empty even after processing (Bug #5)")
    else:
        print("Captions returned successfully")

# -------------------------
# DELETE VIDEO
# -------------------------
print("\nDELETE VIDEO:")

delete_response = requests.delete(
    f"{BASE_URL}/api/videos/{video_id}",
    headers=auth_headers
)

print(delete_response.status_code)
print(delete_response.text)

# -------------------------
# DOUBLE DELETE TEST
# -------------------------
print("\nDOUBLE DELETE TEST:")

delete_response2 = requests.delete(
    f"{BASE_URL}/api/videos/{video_id}",
    headers=auth_headers
)

print(delete_response2.status_code)
print(delete_response2.text)

if delete_response2.status_code == 204:
    print("BUG CONFIRMED: Double delete returns 204 — should be 404 (Bug #2)")
elif delete_response2.status_code == 404:
    print("PASS: Second delete correctly returns 404")

print("\nTEST FLOW COMPLETED")