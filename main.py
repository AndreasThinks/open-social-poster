from fasthtml.common import *
from monsterui.all import *  # Import MonsterUI components
import os
import json
import time
from datetime import datetime
from atproto import Client as AtprotoClient
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

# Setup FastHTML app with MonsterUI's blue theme and DaisyUI
app, rt = fast_app(hdrs=Theme.blue.headers(daisy=True))

# SQLite database setup
db = database("social_poster.db")
@dataclass
class Account:
    id: int = None
    network: str = None
    username: str = None
    credentials: str = None
    created_at: str = None
    updated_at: str = None
accounts = db.create(Account, pk="id")

# Mastodon OAuth configuration
MASTODON_REDIRECT_URI = "http://localhost:5001/login/mastodon/callback"

# Main route
@rt("/")
def get():
    active_accounts = list(accounts())
    return (
        Title("Social Media Poster"),
        Container(
            Section(H1("Social Media Poster"), id="header"),
            Section(
                H2("Your Connected Accounts"),
                render_connected_accounts(active_accounts),
                id="accounts-section"
            ),
            Section(
                H2("Connect a New Account"),
                render_connection_forms(),
                id="connection-section"
            ),
            Section(
                H2("Post a Message"),
                render_post_form(active_accounts) if active_accounts else P("Please connect at least one social media account to post messages."),
                id="post-section"
            ),
            cls="p-6 space-y-6 bg-white dark:bg-gray-800 rounded-lg shadow-md max-w-2xl mx-auto"
        )
    )

# Render connected accounts
def render_connected_accounts(active_accounts):
    if not active_accounts:
        return P("No connected accounts yet.", cls="text-muted")
    account_divs = [
        Card(
            CardHeader(DivLAligned(UkIcon(account.network), H3(f"{account.network.capitalize()}: {account.username}"))),
            CardFooter(
                Button(UkIcon('log-out'), "Logout", hx_post=f"/logout/{account.id}", hx_target="#accounts-section", hx_swap="outerHTML", cls=ButtonT.secondary)
            ),
            cls=CardT.hover
        ) for account in active_accounts
    ]
    return Grid(*account_divs, cls="grid-cols-1 md:grid-cols-2 gap-4")

# Render connection forms
def render_connection_forms():
    active_accounts = list(accounts())
    connected_networks = [account.network for account in active_accounts]
    connection_cards = []
    
    if "bluesky" not in connected_networks:
        connection_cards.append(
            Card(
                CardHeader(DivLAligned(UkIcon('bluesky'), H3("Bluesky"))),
                CardBody(
                    P("Connect using your handle and an app password."),
                    P(A("Create an App Password", href="https://bsky.app/settings/app-passwords", target="_blank"), " before logging in."),
                    Form(
                        FormLabel("Handle"),
                        Input(id="bsky-handle", name="handle", placeholder="Your Bluesky handle", cls="w-full"),
                        FormLabel("App Password"),
                        Input(id="bsky-password", name="password", type="password", placeholder="App Password", cls="w-full"),
                        Button("Connect", type="submit", cls=ButtonT.primary),
                        hx_post="/login/bluesky",
                        hx_target="#accounts-section",
                        hx_swap="outerHTML",
                        cls="space-y-2"
                    )
                ),
                cls=CardT.default
            )
        )
    
    if "twitter" not in connected_networks:
        connection_cards.append(
            Card(
                CardHeader(DivLAligned(UkIcon('twitter'), H3("Twitter/X"))),
                CardBody(
                    P("Connect using browser login."),
                    P("This will open a browser window. Please login and then wait for the browser to close."),
                    Button("Connect with Twitter", hx_post="/login/twitter", hx_target="#accounts-section", hx_swap="outerHTML", cls=ButtonT.primary)
                ),
                cls=CardT.default
            )
        )
    
    if "mastodon" not in connected_networks:
        connection_cards.append(
            Card(
                CardHeader(DivLAligned(UkIcon('mastodon'), H3("Mastodon"))),
                CardBody(
                    P("Connect to your Mastodon instance."),
                    Form(
                        FormLabel("Instance"),
                        Input(id="mastodon-instance", name="instance", placeholder="yourdomain.social", cls="w-full"),
                        Button("Connect", type="submit", cls=ButtonT.primary),
                        action="/login/mastodon",
                        method="post",
                        cls="space-y-2"
                    ),
                    P("Enter your instance domain without https://", cls="text-muted")
                ),
                cls=CardT.default
            )
        )
    
    return Grid(*connection_cards, cls="grid-cols-1 md:grid-cols-3 gap-4") if connection_cards else P("You're connected to all available networks.", cls="text-muted")

def render_post_form(active_accounts):
    # Generate checkboxes for each active account
    account_checkboxes = [
        LabelCheckboxX(
            id=f"account_{account.id}",
            name="account_id",
            value=str(account.id),
            checked=True,
            label=f"{account.network.capitalize()}: {account.username}"
        ) for account in active_accounts
    ]
    
    # Create the form with improved layout and styling
    form = Form(
        # Checkbox section with a clear header
        Div(
            P("Select accounts to post to:", cls="text-white mb-2"),
            Group(*account_checkboxes, cls="flex flex-wrap gap-4"),
            cls="mb-4"
        ),
        # Label for the textarea
        FormLabel("Post Content", fr="post-content", cls="text-white mt-4"),
        # Improved textarea styling
        Textarea(
            id="post-content",
            name="content",
            placeholder="What's on your mind?",
            rows=8,  # Increased from 5 to 8 for more space
            cls="w-full p-4 border border-gray-500 rounded-lg bg-gray-700 text-white placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-400",
            hx_trigger="keyup changed delay:500ms",
            hx_get="/check_length",
            hx_target="#char-warning"
        ),
        # Character limit warning area
        Div(id="char-warning", cls="text-sm text-red-500 mt-2"),
        # Submit button
        Button(
            UkIcon('send', cls="mr-2"),
            "Post",
            type="submit",
            cls="mt-4 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-500 transition-colors"
        ),
        # Result display area
        Div(id="post-result", cls="mt-4"),
        hx_post="/post",
        hx_target="#post-result",
        hx_swap="innerHTML",
        cls="space-y-4"
    )
    
    # Wrap everything in a styled card
    return Card(
        CardBody(form),
        cls="bg-gray-800 border border-gray-700 rounded-lg shadow-md"
    )

CHAR_LIMITS = {
    "twitter": 280,
    "mastodon": 500,
    "bluesky": 300
}

@rt("/check_length")
def get(content: str, account_id: list[str] = None):
    if not content.strip():
        return ""  # No content to check yet
    
    # If no account_ids are provided, use all active accounts as a fallback
    if not account_id:
        active_accounts = list(accounts())
        if not active_accounts:
            return "Warning: No accounts connected to check length against."
    else:
        # Fetch selected accounts from the database based on provided IDs
        active_accounts = [accounts[int(id)] for id in account_id if id.isdigit() and int(id) in accounts]
        if not active_accounts:
            return "Warning: No valid accounts selected to check length against."
    
    # Determine the strictest character limit among selected networks
    selected_networks = [account.network for account in active_accounts if account.network in CHAR_LIMITS]
    if not selected_networks:
        return ""  # No valid networks to check against
    
    max_len = min(CHAR_LIMITS[network] for network in selected_networks)
    
    # Check if the content exceeds the minimum limit
    if len(content) > max_len:
        return f"Warning: Your message ({len(content)} characters) exceeds the {max_len}-character limit for selected networks."
    
    return ""  # Content is within limits

# Login handlers
@rt("/login/bluesky")
def post(handle: str, password: str):
    try:
        client = AtprotoClient()
        profile = client.login(handle, password)
        credentials = {"handle": handle, "password": password}
        accounts.insert(Account(network="bluesky", username=handle, credentials=json.dumps(credentials), created_at=datetime.now().isoformat(), updated_at=datetime.now().isoformat()))
        return render_updated_accounts_section()
    except Exception as e:
        return render_updated_accounts_section_with_error(f"Error connecting to Bluesky: {str(e)}")

@rt("/login/twitter")
def post():
    try:
        driver = webdriver.Chrome()
        driver.get("https://twitter.com/i/flow/login")
        WebDriverWait(driver, 300).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='primaryColumn']")))
        cookies = driver.get_cookies()
        try:
            driver.get("https://twitter.com/home")
            time.sleep(2)
            profile_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='AppTabBar_Profile_Link']")))
            profile_button.click()
            time.sleep(2)
            username = driver.current_url.split("/")[-1]
        except:
            username = "twitter_user"
        driver.quit()
        accounts.insert(Account(network="twitter", username=username, credentials=json.dumps({"cookies": cookies}), created_at=datetime.now().isoformat(), updated_at=datetime.now().isoformat()))
        return render_updated_accounts_section()
    except Exception as e:
        return render_updated_accounts_section_with_error(f"Error connecting to Twitter: {str(e)}")

@rt("/login/mastodon")
def post(instance: str, sess):
    try:
        sess["mastodon_instance"] = instance
        app_url = f"https://{instance}/api/v1/apps"
        app_data = {"client_name": "Social Media Poster", "redirect_uris": MASTODON_REDIRECT_URI, "scopes": "write:statuses read"}
        app_response = requests.post(app_url, data=app_data)
        if app_response.status_code != 200:
            raise Exception(f"Failed to register app: {app_response.text}")
        app_info = app_response.json()
        sess["mastodon_client_id"] = app_info["client_id"]
        sess["mastodon_client_secret"] = app_info["client_secret"]
        auth_url = qp(f"https://{instance}/oauth/authorize", redirect_uri=MASTODON_REDIRECT_URI, client_id=app_info["client_id"], scope="write:statuses read", response_type="code")
        return RedirectResponse(auth_url, status_code=303)
    except Exception as e:
        return render_updated_accounts_section_with_error(f"Error connecting to Mastodon: {str(e)}")

@rt("/login/mastodon/callback")
def get(code: str, sess):
    try:
        process_mastodon_code(code, sess)
        return RedirectResponse("/", status_code=303)
    except Exception as e:
        return Titled("Error", Container(H1("Mastodon Login Error"), P(f"Failed to authenticate: {str(e)}"), A("Return to Home", href="/"), cls="p-6"))

def process_mastodon_code(code: str, sess):
    instance = sess.get("mastodon_instance")
    client_id = sess.get("mastodon_client_id")
    client_secret = sess.get("mastodon_client_secret")
    token_url = f"https://{instance}/oauth/token"
    token_data = {"client_id": client_id, "client_secret": client_secret, "code": code, "redirect_uri": MASTODON_REDIRECT_URI, "grant_type": "authorization_code"}
    token_response = requests.post(token_url, data=token_data)
    token_info = token_response.json()
    headers = {"Authorization": f"Bearer {token_info['access_token']}"}
    user_url = f"https://{instance}/api/v1/accounts/verify_credentials"
    user_response = requests.get(user_url, headers=headers)
    user_info = user_response.json()
    credentials = {"instance": instance, "access_token": token_info["access_token"]}
    accounts.insert(Account(network="mastodon", username=f"{user_info['username']}@{instance}", credentials=json.dumps(credentials), created_at=datetime.now().isoformat(), updated_at=datetime.now().isoformat()))

# Logout handler
@rt("/logout/{id}")
def post(id: int):
    accounts.delete(id)
    return render_updated_accounts_section()

# Helper to render accounts section with error
def render_updated_accounts_section():
    active_accounts = list(accounts())
    return Div(H2("Your Connected Accounts"), render_connected_accounts(active_accounts), H2("Connect a New Account"), render_connection_forms(), id="accounts-section")

def render_updated_accounts_section_with_error(error_msg):
    active_accounts = list(accounts())
    return Div(H2("Your Connected Accounts"), render_connected_accounts(active_accounts), H2("Connect a New Account"), render_connection_forms(), Alert(error_msg, cls=AlertT.error), id="accounts-section")

# Post handler
@rt("/post")
def post(content: str, account_id: list[str] = None):
    if not content.strip():
        return Alert("Please enter some content to post.", cls=AlertT.error)
    if not account_id:
        return Alert("Please select at least one account to post to.", cls=AlertT.error)
    
    selected_accounts = [accounts[int(id)] for id in account_id if id.isdigit() and int(id) in accounts]
    for account in selected_accounts:
        max_len = CHAR_LIMITS.get(account.network, 500)
        if len(content) > max_len:
            return Alert(
                f"Message too long for {account.network.capitalize()} ({len(content)} characters exceeds {max_len}-character limit).",
                cls=AlertT.error
            )
    
    # Proceed with posting if all checks pass
    results = []
    for account in selected_accounts:
        try:
            if account.network == "bluesky":
                result = post_to_bluesky(account, content)
                success = True
            elif account.network == "twitter":
                result = post_to_twitter(account, content)
                success = True
            elif account.network == "mastodon":
                result = post_to_mastodon(account, content)
                success = True
            else:
                result = f"Unknown network: {account.network}"
                success = False
            results.append((account, success, result))
        except Exception as e:
            results.append((account, False, str(e)))
    
    result_items = [
        Alert(
            H4(f"{account.network.capitalize()}: {account.username}"),
            P(message if not success else "Posted successfully!"),
            cls=AlertT.success if success else AlertT.error
        ) for account, success, message in results
    ]
    return Div(
        H3("Post Results"),
        *result_items,
        Button("Clear", hx_post="/clear-results", hx_target="#post-result", hx_swap="innerHTML"),
        cls="space-y-2"
    )
@rt("/clear-results")
def post():
    return ""

# Platform-specific posting functions (unchanged)
def post_to_bluesky(account, content):
    credentials = json.loads(account.credentials)
    client = AtprotoClient()
    client.login(credentials["handle"], credentials["password"])
    post = client.send_post(text=content)
    return f"Posted to Bluesky: {post.uri}"

def post_to_twitter(account, content):
    credentials = json.loads(account.credentials)
    cookies = credentials.get("cookies", [])
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get("https://twitter.com")
    for cookie in cookies:
        if 'expiry' in cookie:
            del cookie['expiry']
        driver.add_cookie(cookie)
    driver.get("https://twitter.com/home")
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tweetTextarea_0']")))
        post_area = driver.find_element(By.CSS_SELECTOR, "[data-testid='tweetTextarea_0']")
        post_area.send_keys(content)
        tweet_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Post']/ancestor::button")))
        tweet_button.click()
        time.sleep(5)
    finally:
        driver.quit()
    return "Posted to Twitter successfully"

def post_to_mastodon(account, content):
    credentials = json.loads(account.credentials)
    headers = {"Authorization": f"Bearer {credentials['access_token']}", "Content-Type": "application/json"}
    data = {"status": content, "visibility": "public"}
    response = requests.post(f"https://{credentials['instance']}/api/v1/statuses", headers=headers, json=data)
    if response.status_code not in (200, 201, 202):
        raise Exception(f"Failed to post: {response.text}")
    return f"Posted to Mastodon: {response.json().get('url', 'Success!')}"

if __name__ == "__main__":
    serve()