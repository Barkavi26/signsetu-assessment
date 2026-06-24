print("🔥 FILE STARTED EXECUTION")
import requests
import time
import uuid

BASE_URL = "https://qa-testing-navy.vercel.app"

CANDIDATE_ID = f"barkavi_{int(time.time())}"
headers = {"X-Candidate-ID": CANDIDATE_ID}


# ─── HELPERS ───────────────────────────────────────────

def authenticate():
    response = requests.post(f"{BASE_URL}/api/auth", headers=headers)
    print("\n[AUTH]")
    print("STATUS:", response.status_code)
    print("BODY:", response.text)
    if response.status_code != 201:
        print("Auth failed"); return None
    return response.json().get("token")


def auth_headers(token):
    """Always include both X-Candidate-ID and Bearer token."""
    return {
        "X-Candidate-ID": CANDIDATE_ID,
        "Authorization": f"Bearer {token}"
    }


def create_video(token, title="New Video"):
    response = requests.post(
        f"{BASE_URL}/api/videos",
        json={"title": title, "url": "https://example.com/video.mp4"},
        headers=auth_headers(token)   # ✅ use token here
    )
    print("\n[CREATE VIDEO]")
    print("STATUS:", response.status_code)
    print("BODY:", response.text)
    if response.status_code != 201:
        print("Video creation failed"); return None
    return response.json().get("id")


def delete_video(token, video_id):
    return requests.delete(
        f"{BASE_URL}/api/videos/{video_id}",
        headers=auth_headers(token)
    )


# ─── TEST 1: Invalid Video ID ──────────────────────────

def test_invalid_video_id(token):
    """Fetching a garbage ID should return 404, not 500."""
    response = requests.get(
        f"{BASE_URL}/api/videos/invalid_12345",
        headers=auth_headers(token)
    )
    print("\n[TEST 1] Invalid Video ID")
    print("STATUS:", response.status_code)
    result = "✅ PASS" if response.status_code == 404 else f"🐛 BUG — expected 404, got {response.status_code}"
    print(result)


# ─── TEST 2: Missing Auth Header ──────────────────────

def test_missing_auth(token):
    """Request without Authorization should be rejected."""
    video_id = create_video(token)
    if not video_id: return

    # Call without any auth
    response = requests.get(
        f"{BASE_URL}/api/videos/{video_id}",
        headers={"X-Candidate-ID": CANDIDATE_ID}  # no Bearer token
    )
    print("\n[TEST 2] Missing Auth Token")
    print("STATUS:", response.status_code)
    result = "✅ PASS" if response.status_code in [401, 403] else f"🐛 BUG — expected 401/403, got {response.status_code}"
    print(result)

    delete_video(token, video_id)  # cleanup


# ─── TEST 3: Captions Before Processing ───────────────

def test_captions_before_processing(token):
    """Fetching captions before triggering should return 404 or 400."""
    video_id = create_video(token)
    if not video_id: return

    response = requests.get(
        f"{BASE_URL}/api/captions",
        params={"videoId": video_id},
        headers=auth_headers(token)
    )
    print("\n[TEST 3] Captions Before Processing")
    print("STATUS:", response.status_code)
    result = "✅ PASS" if response.status_code in [400, 404] else f"🐛 BUG — got {response.status_code}: {response.text}"
    print(result)

    delete_video(token, video_id)  # cleanup


# ─── TEST 4: Duplicate Processing ────────────────────

def test_duplicate_process(token):
    """Triggering captions twice should not cause 500."""
    video_id = create_video(token)
    if not video_id: return

    r1 = requests.post(
        f"{BASE_URL}/api/videos/{video_id}/process-captions",
        headers=auth_headers(token)
    )
    r2 = requests.post(
        f"{BASE_URL}/api/videos/{video_id}/process-captions",
        headers=auth_headers(token)
    )

    print("\n[TEST 4] Duplicate Process")
    print("1st:", r1.status_code, r1.text)
    print("2nd:", r2.status_code, r2.text)

    if r2.status_code == 500:
        print("🐛 BUG — double trigger caused 500 server error")
    elif r2.status_code in [409, 400]:
        print("✅ PASS — second trigger correctly rejected")
    else:
        print(f"⚠️  NOTED — second trigger returned {r2.status_code} (check if idempotent)")

    delete_video(token, video_id)  # cleanup


# ─── TEST 5: Delete Twice ────────────────────────────

def test_delete_twice(token):
    """Second delete should return 404, not 204."""
    video_id = create_video(token)
    if not video_id: return

    r1 = delete_video(token, video_id)
    r2 = delete_video(token, video_id)

    print("\n[TEST 5] Delete Twice")
    print("1st:", r1.status_code)
    print("2nd:", r2.status_code)

    if r2.status_code == 204:
        print("🐛 BUG CONFIRMED — double delete returns 204, should be 404")
    elif r2.status_code == 404:
        print("✅ PASS — second delete correctly returns 404")


# ─── TEST 6: SQL Injection in Title ──────────────────

def test_sql_injection(token):
    """SQL injection in title should not crash the server."""
    payload = "'; DROP TABLE videos; --"
    video_id = create_video(token, title=payload)

    print("\n[TEST 6] SQL Injection in Title")
    if video_id:
        print("⚠️  Created with injection payload — checking if server is stable")
        check = requests.get(f"{BASE_URL}/api/videos", headers=auth_headers(token))
        if check.status_code == 500:
            print("🐛 BUG — SQL injection may have corrupted state")
        else:
            print("✅ Server stable after injection attempt")
        delete_video(token, video_id)
    else:
        print("✅ Server rejected injection payload at creation")


# ─── TEST 7: Missing X-Candidate-ID header ───────────

def test_missing_candidate_id():
    """Requests without X-Candidate-ID should be rejected per API rules."""
    response = requests.post(f"{BASE_URL}/api/auth")  # no headers at all
    print("\n[TEST 7] Missing X-Candidate-ID Header")
    print("STATUS:", response.status_code)
    result = "✅ PASS" if response.status_code in [400, 401, 403] else f"🐛 BUG — missing header accepted! Got {response.status_code}"
    print(result)


# ─── TEST 8: Process captions on deleted video ───────

def test_process_deleted_video(token):
    """Processing a deleted video should return 404."""
    video_id = create_video(token)
    if not video_id: return

    delete_video(token, video_id)

    response = requests.post(
        f"{BASE_URL}/api/videos/{video_id}/process-captions",
        headers=auth_headers(token)
    )
    print("\n[TEST 8] Process Captions on Deleted Video")
    print("STATUS:", response.status_code)
    result = "✅ PASS" if response.status_code == 404 else f"🐛 BUG — expected 404, got {response.status_code}"
    print(result)

# ─── TEST 9: Captions After Processing ───────────────

def test_captions_after_processing(token):
    """Captions should exist and be non-empty after processing completes."""
    video_id = create_video(token)
    if not video_id: return

    # Trigger processing
    requests.post(
        f"{BASE_URL}/api/videos/{video_id}/process-captions",
        headers=auth_headers(token)
    )

    # Poll until completed
    print("\n[TEST 9] Captions After Processing — polling...")
    for i in range(15):
        res = requests.get(
            f"{BASE_URL}/api/videos/{video_id}",
            headers=auth_headers(token)
        )
        status = res.json().get("status", "")
        print(f"  Attempt {i+1}: {status}")
        if status == "completed":
            break
        time.sleep(2)

    # Now fetch captions
    cap_res = requests.get(
        f"{BASE_URL}/api/captions",
        params={"videoId": video_id},
        headers=auth_headers(token)
    )
    print("STATUS:", cap_res.status_code)
    print("BODY:", cap_res.text)

    captions = cap_res.json()
    if isinstance(captions, list) and len(captions) > 0:
        print("✅ PASS — captions returned after processing")
    else:
        print("🐛 BUG — captions empty or missing even after processing")

    delete_video(token, video_id)




# ─── BONUS TEST 1: Token Expiry Not Enforced ─────────

def test_expired_token(token):
    """Old/fake token should be rejected after expiry."""
    fake_old_token = "MTc4MDAwMDAwMDAwMA=="  # fake base64 token
    
    response = requests.get(
        f"{BASE_URL}/api/videos",
        headers={
            "X-Candidate-ID": CANDIDATE_ID,
            "Authorization": f"Bearer {fake_old_token}"
        }
    )
    print("\n[BONUS 1] Expired/Fake Token")
    print("STATUS:", response.status_code)
    print("BODY:", response.text)
    
    if response.status_code == 200:
        print("🐛 BONUS BUG — fake/expired token was accepted!")
    elif response.status_code in [401, 403]:
        print("✅ PASS — fake token correctly rejected")


# ─── BONUS TEST 2: Negative Limit ────────────────────

def test_negative_limit(token):
    """Negative limit should be rejected, not return data or crash."""
    response = requests.get(
        f"{BASE_URL}/api/videos?limit=-1",
        headers=auth_headers(token)
    )
    print("\n[BONUS 2] Negative Limit")
    print("STATUS:", response.status_code)
    print("BODY:", response.text)

    if response.status_code == 500:
        print("🐛 BONUS BUG — negative limit caused server crash!")
    elif response.status_code == 200:
        data = response.json()
        videos = data if isinstance(data, list) else data.get("videos", [])
        if len(videos) > 100:
            print(f"🐛 BONUS BUG — negative limit returned {len(videos)} records (data leak!)")
        else:
            print(f"⚠️  NOTED — returned {len(videos)} videos with limit=-1")
    elif response.status_code in [400, 422]:
        print("✅ PASS — negative limit correctly rejected")


# ─── BONUS TEST 3: Zero Limit ─────────────────────────

def test_zero_limit(token):
    """limit=0 should return empty or be rejected, not crash."""
    response = requests.get(
        f"{BASE_URL}/api/videos?limit=0",
        headers=auth_headers(token)
    )
    print("\n[BONUS 3] Zero Limit")
    print("STATUS:", response.status_code)
    print("BODY:", response.text)

    if response.status_code == 500:
        print("🐛 BONUS BUG — limit=0 caused server crash!")
    elif response.status_code == 200:
        print("⚠️  NOTED — limit=0 accepted, check if result makes sense")
    else:
        print("✅ PASS — limit=0 correctly handled")


# ─── BONUS TEST 4: Huge Limit ─────────────────────────

def test_huge_limit(token):
    """Huge limit should be capped, not dump entire database."""
    response = requests.get(
        f"{BASE_URL}/api/videos?limit=999999",
        headers=auth_headers(token)
    )
    print("\n[BONUS 4] Huge Limit (999999)")
    print("STATUS:", response.status_code)

    if response.status_code == 500:
        print("🐛 BONUS BUG — huge limit caused server crash!")
    elif response.status_code == 200:
        data = response.json()
        videos = data if isinstance(data, list) else data.get("videos", [])
        print(f"Returned {len(videos)} videos")
        if len(videos) > 100:
            print("🐛 BONUS BUG — no cap on limit, possible data dump!")
        else:
            print("✅ PASS — limit capped correctly")
    else:
        print(f"✅ PASS — rejected with {response.status_code}")


# ─── BONUS TEST 5: String as Limit ───────────────────

def test_string_limit(token):
    """Non-numeric limit should return 400, not crash."""
    response = requests.get(
        f"{BASE_URL}/api/videos?limit=abc",
        headers=auth_headers(token)
    )
    print("\n[BONUS 5] String as Limit Value")
    print("STATUS:", response.status_code)
    print("BODY:", response.text)

    if response.status_code == 500:
        print("🐛 BONUS BUG — string limit caused server crash!")
    elif response.status_code in [400, 422]:
        print("✅ PASS — string limit correctly rejected")
    else:
        print(f"⚠️  NOTED — returned {response.status_code}")


# ─── BONUS TEST 6: No Candidate ID on Video Endpoints ─

def test_no_candidate_id_on_videos(token):
    """Video endpoints should also reject missing X-Candidate-ID."""
    response = requests.get(
        f"{BASE_URL}/api/videos",
        headers={"Authorization": f"Bearer {token}"}  # no X-Candidate-ID
    )
    print("\n[BONUS 6] No X-Candidate-ID on Video Endpoint")
    print("STATUS:", response.status_code)
    print("BODY:", response.text)

    if response.status_code == 200:
        print("🐛 BONUS BUG — missing X-Candidate-ID accepted on video endpoint!")
    elif response.status_code in [400, 401, 403]:
        print("✅ PASS — missing header correctly rejected")

# ─── BONUS TEST 7: IDOR Check ────────────────────────

def test_idor_access(token):
    """Can we access videos created by other candidates?"""
    # Create a video with our candidate ID
    video_id = create_video(token)
    if not video_id: return

    # Try accessing with a different candidate ID
    other_headers = {
        "X-Candidate-ID": "some_other_candidate_123",
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(
        f"{BASE_URL}/api/videos/{video_id}",
        headers=other_headers
    )
    print("\n[BONUS 7] IDOR — Access Other Candidate's Video")
    print("STATUS:", response.status_code)
    print("BODY:", response.text)

    if response.status_code == 200:
        print("🐛 BONUS BUG — accessed another candidate's video! IDOR vulnerability")
    else:
        print("✅ PASS — cross-candidate access blocked")

    delete_video(token, video_id)


# ─── RUN ALL ─────────────────────────────────────────

if __name__ == "__main__":
    print("STARTING VULNERABILITY TEST SUITE...\n")

    token = authenticate()
    if not token:
        print("Cannot proceed without token"); exit()

    test_invalid_video_id(token)
    test_missing_auth(token)
    test_captions_before_processing(token)
    test_duplicate_process(token)
    test_delete_twice(token)
    test_sql_injection(token)
    test_missing_candidate_id()
    test_process_deleted_video(token)
    test_captions_after_processing(token)

    print("\n--- BONUS TESTS ---")
    test_expired_token(token)
    test_negative_limit(token)
    test_zero_limit(token)
    test_huge_limit(token)
    test_string_limit(token)
    test_no_candidate_id_on_videos(token)
    test_idor_access(token)

    print("\n" + "="*40)
    print("TEST SUITE COMPLETED")
    print("="*40)