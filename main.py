from fasthtml.common import *
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

# Create FastHTML app with PicoCSS
app, rt = fast_app()

# Create SQLite database and tables
db = database("social_poster.db")

# Define data models
@dataclass
class Account:
    id: int = None
    network: str = None  # "bluesky", "twitter", "mastodon"
    username: str = None
    credentials: str = None  # JSON string
    created_at: str = None
    updated_at: str = None

# Create table if it doesn't exist
accounts = db.create(Account, pk="id")

# Mastodon OAuth configuration
MASTODON_REDIRECT_URI = "http://localhost:5001/login/mastodon/callback"
# We'll store client credentials per instance in the database

# Main route
@rt("/")
def get():
    """Main page showing credentials and post form"""
    active_accounts = list(accounts())
    
    return Titled("Social Media Poster",
        Div(
            H1("Social Media Poster"),
            Div(
                H2("Your Connected Accounts"),
                render_connected_accounts(active_accounts),
                H2("Connect a New Account"),
                render_connection_forms(),
                id="accounts-section"
            ),
            Div(
                H2("Post a Message"),
                render_post_form(active_accounts) if active_accounts else 
                    P("Please connect at least one social media account to post messages."),
                id="post-section"
            )
        )
    )

def render_connected_accounts(active_accounts):
    """Render list of connected accounts with logout buttons"""
    if not active_accounts:
        return P("No connected accounts yet.")
    
    account_divs = []
    for account in active_accounts:
        account_divs.append(
            Card(
                Div(
                    H3(f"{account.network.capitalize()}: {account.username}"),
                    Button("Logout", 
                        hx_post=f"/logout/{account.id}", 
                        hx_target="#accounts-section",
                        hx_swap="outerHTML",
                        cls="outline"
                    )
                )
            )
        )
    
    return Grid(*account_divs)

def render_connection_forms():
    """Render forms for connecting to social networks"""
    # Check which networks the user is already connected to
    active_accounts = list(accounts())
    connected_networks = [account.network for account in active_accounts]
    
    connection_cards = []
    
    # Bluesky connection form
    if "bluesky" not in connected_networks:
        connection_cards.append(
            Card(
                H3("Bluesky"),
                P("Connect using your handle and an app password."),
                P(A("Create an App Password", href="https://bsky.app/settings/app-passwords", target="_blank"), 
                " before logging in."),
                Form(
                    Input(id="bsky-handle", name="handle", placeholder="Your Bluesky handle"),
                    Input(id="bsky-password", name="password", type="password", placeholder="App Password"),
                    Button("Connect", type="submit"),
                    hx_post="/login/bluesky",
                    hx_target="#accounts-section",
                    hx_swap="outerHTML"
                )
            )
        )
    
    # Twitter/X connection form
    if "twitter" not in connected_networks:
        connection_cards.append(
            Card(
                H3("Twitter/X"),
                P("Connect using browser login."),
                P("This will open a browser window. Please login and then wait for the browser to close automatically."),
                Button("Connect with Twitter", 
                    hx_post="/login/twitter",
                    hx_target="#accounts-section",
                    hx_swap="outerHTML"
                )
            )
        )
    
    # Mastodon connection form
    if "mastodon" not in connected_networks:
        connection_cards.append(
            Card(
                H3("Mastodon"),
                P("Connect to your Mastodon instance."),
                Form(
                    Input(id="mastodon-instance", name="instance", placeholder="yourdomain.social"),
                    Button("Connect", type="submit"),
                    action="/login/mastodon",
                    method="post"
                ),
                footer=P("Enter your instance domain without https://")
            )
        )
    
    # If no connection forms to show, display a message
    if not connection_cards:
        return P("You're connected to all available social networks.")
    
    return Grid(*connection_cards)

def render_post_form(active_accounts):
    """Render form for posting to selected networks"""
    account_checkboxes = []
    for account in active_accounts:
        account_checkboxes.append(
            CheckboxX(
                id=f"account_id", 
                name="account_id",
                value=str(account.id),
                checked=True, 
                label=f"{account.network.capitalize()}: {account.username}"
            )
        )
    
    return Form(
        Group(*account_checkboxes) if account_checkboxes else None,
        Textarea(id="post-content", name="content", placeholder="What's on your mind?", rows=5),
        Button("Post", type="submit"),
        Div(id="post-result"),
        hx_post="/post",
        hx_target="#post-result",
        hx_swap="innerHTML"
    )

# Login handlers for each platform
@rt("/login/bluesky")
def post(handle: str, password: str):
    """Handle Bluesky login with atproto library"""
    try:
        # Login to Bluesky to verify credentials
        client = AtprotoClient()
        profile = client.login(handle, password)
        
        # Store credentials (just username and password)
        credentials = {
            "handle": handle,
            "password": password
        }
        
        # Save to database
        accounts.insert(Account(
            network="bluesky",
            username=handle,
            credentials=json.dumps(credentials),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        ))
        
        # Return updated accounts section
        return render_updated_accounts_section()
    except Exception as e:
        return Div(
            H2("Your Connected Accounts"),
            render_connected_accounts(list(accounts())),
            H2("Connect a New Account"),
            render_connection_forms(),
            P(f"Error connecting to Bluesky: {str(e)}", cls="error"),
            id="accounts-section"
        )


@rt("/login/twitter")
def post():
    """Handle Twitter login with Selenium"""
    try:
        # Launch browser for Twitter login
        driver = webdriver.Chrome()
        driver.get("https://twitter.com/i/flow/login")
        
        # Wait for user to complete login (up to 5 minutes)
        WebDriverWait(driver, 300).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='primaryColumn']"))
        )
        
        # Get cookies and user info
        cookies = driver.get_cookies()
        
        # Try to extract username
        try:
            # Attempt to navigate to profile page
            driver.get("https://twitter.com/home")
            time.sleep(2)  # Wait for navigation
            
            # Click on profile icon to see username
            profile_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='AppTabBar_Profile_Link']"))
            )
            profile_button.click()
            
            # Extract username from URL
            time.sleep(2)  # Wait for navigation
            current_url = driver.current_url
            username = current_url.split("/")[-1]
        except:
            # Fallback username if extraction fails
            username = "twitter_user"
        
        # Close browser
        driver.quit()
        
        # Save to database
        accounts.insert(Account(
            network="twitter",
            username=username,
            credentials=json.dumps({"cookies": cookies}),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        ))
        
        # Return updated accounts section
        return render_updated_accounts_section()
    except Exception as e:
        return Div(
            H2("Your Connected Accounts"),
            render_connected_accounts(list(accounts())),
            H2("Connect a New Account"),
            render_connection_forms(),
            P(f"Error connecting to Twitter: {str(e)}", cls="error"),
            id="accounts-section"
        )

@rt("/login/mastodon")
def post(instance: str, sess):
    """Initiate Mastodon OAuth flow"""
    try:
        # Save instance to session for callback
        sess["mastodon_instance"] = instance
        
        # First, register the application with the Mastodon instance
        app_url = f"https://{instance}/api/v1/apps"
        app_data = {
            "client_name": "Open Social Poster",
            "redirect_uris": MASTODON_REDIRECT_URI,
            "scopes": "write:statuses read",
            "website": "https://github.com/andreasthinks/open-social-poster"
        }
        
        app_response = requests.post(app_url, data=app_data)
        if app_response.status_code != 200:
            raise Exception(f"Failed to register app: {app_response.text}")
        
        app_info = app_response.json()
        
        # Store client credentials in session for the callback
        sess["mastodon_client_id"] = app_info["client_id"]
        sess["mastodon_client_secret"] = app_info["client_secret"]
        
        # Redirect to authorization page
        auth_url = qp(f"https://{instance}/oauth/authorize", 
            redirect_uri=MASTODON_REDIRECT_URI,
            client_id=app_info["client_id"],
            scope="write:statuses read",
            response_type="code"
        )
        
        # Simple redirect to the authorization page
        # The user will be redirected back to our callback URL after authorization
        return RedirectResponse(auth_url, status_code=303)
    except Exception as e:
        return Div(
            H2("Your Connected Accounts"),
            render_connected_accounts(list(accounts())),
            H2("Connect a New Account"),
            render_connection_forms(),
            P(f"Error connecting to Mastodon: {str(e)}", cls="error"),
            id="accounts-section"
        )

@rt("/login/mastodon/callback")
def get(code: str, sess):
    """Handle Mastodon OAuth callback"""
    # This route is called when the user is redirected back from the Mastodon authorization page
    try:
        # Process the authorization code and save credentials
        process_mastodon_code(code, sess)
        
        # Redirect to the main page
        return RedirectResponse("/", status_code=303)
    except Exception as e:
        return Titled("Error", 
                     Container(
                         H1("Mastodon Login Error"),
                         P(f"Failed to authenticate with Mastodon: {str(e)}"),
                         A("Return to Home", href="/")
                     ))

# Helper function to process Mastodon authorization code
def process_mastodon_code(code: str, sess):
    """Process Mastodon authorization code and save credentials"""
    try:
        instance = sess.get("mastodon_instance")
        client_id = sess.get("mastodon_client_id")
        client_secret = sess.get("mastodon_client_secret")
        
        if not instance or not client_id or not client_secret:
            raise ValueError("Mastodon credentials not found in session")
        
        # Exchange code for access token
        token_url = f"https://{instance}/oauth/token"
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": MASTODON_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_info = token_response.json()
        
        # Get user information
        headers = {"Authorization": f"Bearer {token_info['access_token']}"}
        user_url = f"https://{instance}/api/v1/accounts/verify_credentials"
        user_response = requests.get(user_url, headers=headers)
        user_info = user_response.json()
        
        # Save credentials
        credentials = {
            "instance": instance,
            "access_token": token_info["access_token"],
            "token_type": token_info.get("token_type"),
            "scope": token_info.get("scope"),
            "created_at": token_info.get("created_at"),
            "expires_in": token_info.get("expires_in"),
            "refresh_token": token_info.get("refresh_token")
        }
        
        # Save to database
        accounts.insert(Account(
            network="mastodon",
            username=f"{user_info['username']}@{instance}",
            credentials=json.dumps(credentials),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        ))
        
        # Return updated accounts section
        return render_updated_accounts_section()
    except Exception as e:
        return Div(
            H2("Your Connected Accounts"),
            render_connected_accounts(list(accounts())),
            H2("Connect a New Account"),
            render_connection_forms(),
            P(f"Error connecting to Mastodon: {str(e)}", cls="error"),
            id="accounts-section"
        )

# Logout handler
@rt("/logout/{id}")
def post(id: int):
    """Handle logout for a social network account"""
    try:
        # Remove account from database
        accounts.delete(id)
        
        # Return updated accounts section
        return render_updated_accounts_section()
    except Exception as e:
        return Div(
            H2("Your Connected Accounts"),
            render_connected_accounts(list(accounts())),
            H2("Connect a New Account"),
            render_connection_forms(),
            P(f"Error logging out: {str(e)}", cls="error"),
            id="accounts-section"
        )

def render_updated_accounts_section():
    """Helper to render the updated accounts section after changes"""
    active_accounts = list(accounts())
    return Div(
        H2("Your Connected Accounts"),
        render_connected_accounts(active_accounts),
        H2("Connect a New Account"),
        render_connection_forms(),
        id="accounts-section"
    )

# Posting handler
@rt("/post")
def post(content: str, account_id: list[str] = None):
    """Post message to selected platforms"""
    print(account_id)
    print(type(account_id))
    if not content.strip():
        return Div(
            P("Please enter some content to post.", cls="error")
        )

    if account_id is None:
        account_id = []
    
    # Convert valid account IDs to integers
    selected_account_ids = []
    for id_str in account_id:
        try:
            selected_account_ids.append(int(id_str))
        except (ValueError, TypeError):
            # Skip invalid IDs
            continue
    
    # Get account objects
    selected_accounts = []
    for account_id in selected_account_ids:
        try:
            account = accounts[account_id]
            selected_accounts.append(account)
        except:
            pass
    
    if not selected_accounts:
        return Div(
            P("Please select at least one account to post to.", cls="error")
        )
    
    # Post to each selected platform
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
    
    # Display results
    result_items = []
    for account, success, message in results:
        result_items.append(
            Card(
                H4(f"{account.network.capitalize()}: {account.username}"),
                P(message if not success else "Posted successfully!"),
                cls=f"{'success' if success else 'error'}"
            )
        )
    
    return Div(
        H3("Post Results"),
        Grid(*result_items),
        Button("Clear", 
               hx_post="/clear-results", 
               hx_target="#post-result", 
               hx_swap="innerHTML")
    )

@rt("/clear-results")
def post():
    """Clear post results"""
    return ""

# Platform-specific posting functions
def post_to_bluesky(account, content):
    """Post content to Bluesky"""
    credentials = json.loads(account.credentials)
    
    # Get handle and password from credentials
    handle = credentials.get("handle")
    password = credentials.get("password")
    
    # Create client and login with handle and password
    client = AtprotoClient()
    client.login(handle, password)
    
    # Send post
    post = client.send_post(text=content)
    return f"Posted to Bluesky: {post.uri}"

def post_to_twitter(account, content):
    """Post content to Twitter/X using Selenium"""
    credentials = json.loads(account.credentials)
    cookies = credentials.get("cookies", [])
    
    # Set up Selenium
    driver = webdriver.Chrome()
    driver.get("https://twitter.com")
    
    # Add saved cookies
    for cookie in cookies:
        if 'expiry' in cookie:
            del cookie['expiry']
        driver.add_cookie(cookie)
    
    # Navigate to home page and refresh to apply cookies
    driver.get("https://twitter.com/home")
    
    # Find and click the tweet button
    try:
        # Look for the tweet compose area
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tweetTextarea_0']"))
        )
        
        # Enter tweet text
        post_area = driver.find_element(By.CSS_SELECTOR, "[data-testid='tweetTextarea_0']")
        post_area.send_keys(content)
        
        # Find and click the tweet button
        tweet_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='tweetButton']"))
        )
        tweet_button.click()
        
        # Wait for the tweet to be posted
        time.sleep(5)  # Simple wait for tweet to post
        
    finally:
        # Always close the browser
        driver.quit()
    
    return "Posted to Twitter successfully"

def post_to_mastodon(account, content):
    """Post content to Mastodon"""
    credentials = json.loads(account.credentials)
    
    instance = credentials.get("instance")
    access_token = credentials.get("access_token")
    
    # Create post
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "status": content,
        "visibility": "public"  # or "unlisted", "private", "direct"
    }
    
    response = requests.post(
        f"https://{instance}/api/v1/statuses",
        headers=headers,
        json=data
    )
    
    if response.status_code not in (200, 201, 202):
        raise Exception(f"Failed to post to Mastodon: {response.text}")
    
    return f"Posted to Mastodon: {response.json().get('url', 'Success!')}"

# Start the server
if __name__ == "__main__":
    serve()
