import json
import os

import requests
from dotenv import load_dotenv


def test_oauth2_flow(client_id, client_secret):
    """
    Test 1: OAuth2 Flow
    Faire un appel POST sur https://api.insee.fr/token (Basic Auth) pour récupérer l'access token
    """
    token_url = "https://api.insee.fr/token"
    print(f"\n[Flow 1: OAuth2] Requesting token from {token_url}...")
    
    data = {"grant_type": "client_credentials"}
    
    try:
        # requests.post automatically encodes client_id & client_secret as Basic Auth
        response = requests.post(token_url, auth=(client_id, client_secret), data=data)
        response.raise_for_status()
        
        token_info = response.json()
        access_token = token_info.get("access_token")
        if not access_token:
            print("❌ Authentication succeeded but 'access_token' is missing.")
            print("Response:", token_info)
            return None
            
        print("✅ Success! Access token retrieved.")
        print(f"Token (preview): {access_token[:10]}... (expires in {token_info.get('expires_in', 'unknown')}s)")
        return access_token
    except Exception as e:
        print("❌ OAuth2 flow failed.")
        print(f"Error details: {e}")
        if 'response' in locals() and response is not None:
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
        return None

def test_api_key_flow(api_key):
    """
    Test 2: Direct API Key Flow
    Uses the new API Key authentication recommended by the new Gravitee-based INSEE portal.
    """
    print("\n[Flow 2: Direct API Key] Testing authentication using X-INSEE-Api-Key...")
    # The new gateway accepts headers: X-INSEE-Api-Key-Production (for api.insee.fr production gateway)
    # or X-INSEE-Api-Key-Integration (for test environments)
    # We will test with X-INSEE-Api-Key-Production as we are targeting api.insee.fr
    headers = {
        "X-INSEE-Api-Key-Production": api_key,
        "Accept": "application/json"
    }
    return headers

def call_donnees_locales(auth_headers):
    """
    Call the new Melodi API (public, no authentication needed)
    and try to call the legacy Données Locales API (which requires authentication).
    """
    # 1. New Melodi API call (public and free, no auth headers needed!)
    melodi_url = "https://api.insee.fr/melodi/data/DS_RP_POPULATION_PRINC?GEO=COM-69001"
    print(f"\n[API Test 1] Calling new Melodi API (public, no headers): {melodi_url}...")
    
    try:
        # We perform a direct GET request without any auth headers
        response = requests.get(melodi_url)
        response.raise_for_status()
        data = response.json()
        print("✅ Success! Data successfully retrieved from Melodi API without authentication!")
        print(f"Response status: {response.status_code}")
        print("\nResponse Preview (First 1000 characters):")
        formatted = json.dumps(data, indent=2)
        print(formatted[:1000])
        if len(formatted) > 1000:
            print("\n... (truncated)")
    except Exception as e:
        print("❌ Melodi API call failed.")
        print(f"Error details: {e}")
        if 'response' in locals() and response is not None:
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")

    # 2. Historical Données Locales API call (requires OAuth2 token)
    if auth_headers:
        legacy_url = "https://api.insee.fr/donnees-locales/v1/donnees/geo-COMM+POP/DEP-69"
        print(f"\n[API Test 2] Calling legacy Données Locales API (requires token): {legacy_url}...")
        
        try:
            response = requests.get(legacy_url, headers=auth_headers)
            response.raise_for_status()
            data = response.json()
            print("✅ Success! Data retrieved from legacy Données Locales API.")
            print(f"Response status: {response.status_code}")
            print("\nResponse Preview (First 1000 characters):")
            formatted = json.dumps(data, indent=2)
            print(formatted[:1000])
            if len(formatted) > 1000:
                print("\n... (truncated)")
        except Exception as e:
            print("❌ Legacy Données Locales API call failed.")
            print(f"Error details: {e}")
            if 'response' in locals() and response is not None:
                print(f"Status Code: {response.status_code}")
                print(f"Response: {response.text}")
    else:
        print("\n[API Test 2] Skipped legacy Données Locales API call (no OAuth2 token generated).")

def main():
    load_dotenv()
    
    client_id = os.getenv("INSEE_CLIENT_ID")
    client_secret = os.getenv("INSEE_CLIENT_SECRET")
    api_key = os.getenv("INSEE_API_KEY")

    # Clean potential quotes
    client_id = client_id.strip('"').strip("'") if client_id else None
    client_secret = client_secret.strip('"').strip("'") if client_secret else None
    api_key = api_key.strip('"').strip("'") if api_key else None

    # Check if we have at least one authentication method
    if not (client_id and client_secret) and not api_key:
        print("❌ Error: No authentication credentials found in .env.")
        print("Please define either (INSEE_CLIENT_ID and INSEE_CLIENT_SECRET) or (INSEE_API_KEY).")
        return

    # Method 1: Try OAuth2 flow if credentials are present
    auth_headers = None
    if client_id and client_secret:
        print(f"Loaded credentials: Client ID = {client_id[:6]}..., Client Secret = {client_secret[:4]}...")
        access_token = test_oauth2_flow(client_id, client_secret)
        if access_token:
            auth_headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
        else:
            print("\nℹ️ OAuth2 token acquisition failed (possibly due to connection reset by the INSEE gateway).")

    # Method 2: Fallback or try API Key flow if present
    if not auth_headers and api_key:
        print(f"Loaded Direct API Key: {api_key[:6]}...")
        auth_headers = test_api_key_flow(api_key)
    elif api_key and auth_headers:
        print(f"\nDirect API Key is also available in .env ({api_key[:6]}...).")
        choice = input("Do you want to run the API call with the API Key instead of the OAuth2 token? (y/N): ").strip().lower()
        if choice == 'y':
            auth_headers = test_api_key_flow(api_key)

    # Execute the actual calls (Melodi API will run without auth headers, legacy API will be skipped)
    call_donnees_locales(auth_headers)

if __name__ == "__main__":
    main()
