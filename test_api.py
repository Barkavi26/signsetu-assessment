import requests
import time

BASE_URL = "https://qa-testing-navy.vercel.app"

# Generate unique candidate ID for every run
headers = {
    "X-Candidate-ID": f"barkavi_{int(time.time())}"
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
    "X-Candidate-ID": headers["X-Candidate-ID"],
    "Authorization": f"Bearer {token}"
}

# -------------------------
# CREATE VIDEO
# -------------------------
video_response = requests.post(
    f"{BASE_URL}/api/videos",
    headers=headers
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
    headers=headers
)

print("\nPROCESS:")
print(process_response.status_code)
print(process_response.text)

# -------------------------
# POLL STATUS
# -------------------------
print("\nWAITING FOR COMPLETION...")

for i in range(10):

    status_response = requests.get(
        f"{BASE_URL}/api/videos/{video_id}",
        headers=auth_headers
    )

    print(f"\nAttempt {i+1}")
    print(status_response.status_code)
    print(status_response.text)

    data = status_response.json()

    if data.get("status") == "completed":
        print("\nPROCESSING COMPLETED!")
        break

    time.sleep(1)

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

print("\nTEST FLOW COMPLETED")