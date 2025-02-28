# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "atproto",
#     "monsterui",
#     "python-fasthtml",
#     "requests",
#     "selenium",
# ]
# ///
import tempfile
import shutil
from fasthtml.common import *
from monsterui.all import *
import os
import json
import time
from datetime import datetime
from atproto import Client as AtprotoClient, models
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import re

# Setup FastHTML app with MonsterUI's blue theme and DaisyUI
app, rt = fast_app(hdrs=Theme.blue.headers(daisy=True))

db_dir = os.path.join(os.path.expanduser("~"), ".social_poster")
print(db_dir)
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, "social_poster.db")
db = database(db_path)

@dataclass
class Account:
    id: int = None
    network: str = None
    username: str = None
    credentials: str = None
    created_at: str = None
    updated_at: str = None
accounts = db.create(Account, pk="id")

@dataclass
class Upload:
    id: int = None
    filename: str = None
    content_type: str = None
    data: bytes = None
    created_at: str = None
uploads = db.create(Upload, pk="id")

# Mastodon OAuth configuration
MASTODON_REDIRECT_URI = "http://localhost:5001/login/mastodon/callback"

# Main route
@rt("/")
def get():
    active_accounts = list(accounts())
    has_accounts = bool(active_accounts)
    tabs = TabContainer(
        Li(A("Accounts"), cls='uk-active' if not has_accounts else ''),
        Li(A("Post"), cls='uk-active' if has_accounts else ''),
        uk_switcher='connect: #tab-content; animation: uk-animation-fade',
        alt=True
    )
    content = Ul(id="tab-content", cls="uk-switcher")(
        Li(render_accounts_tab(active_accounts)),
        Li(render_post_tab(active_accounts))
    )
    return (
        Title("Open Social Poster"),
        Container(
            Section(H1("Open Social Poster"), id="header"),
            tabs,
            content,
            cls="p-6 space-y-6 bg-white dark:bg-gray-800 rounded-lg shadow-md max-w-2xl mx-auto"
        )
    )

# Accounts tab rendering (unchanged except for function call)
def render_accounts_tab(active_accounts):
    return Div(
        render_connected_accounts(active_accounts),
        H2("Connect a New Account"),
        render_connection_forms(),
        id="accounts-content"
    )

# Post tab rendering with file upload
def render_post_tab(active_accounts):
    if not active_accounts:
        return Div(P("Please connect at least one social media account to post messages."), id="post-content")
    else:
        return Div(
            Details(
                Summary(
                    DivLAligned(
                        UkIcon('image', cls="mr-2"),
                        P("Add Media", cls=TextT.medium),
                        cls="flex items-center cursor-pointer hover:text-primary transition-colors"
                    ),
                    cls="py-2"
                ),
                Div(
                    Form(
                        DivLAligned(
                            Div(
                                Input(
                                    type="file", 
                                    multiple=True, 
                                    name="files", 
                                    cls="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                ),
                                UkIcon('upload', cls="mr-2"),
                                P("Select files", cls=TextT.sm),
                                cls="relative border border-gray-300 rounded p-2 hover:bg-gray-50 transition-colors"
                            ),
                            Button("Upload", 
                                   cls=(ButtonT.secondary, "text-sm px-3 py-1 ml-2"),
                                   hx_disable_elt="this"),
                            cls="w-full"
                        ),
                        hx_post="/upload",
                        hx_target="#uploaded-files",
                        hx_swap="outerHTML"
                    ),
                    cls="pt-1 pb-3"
                ),
                cls="border-b mb-4"
            ),
            Div(id="uploaded-files", cls="mb-4"),
            render_post_form(active_accounts),
            id="post-content"
        )

def render_uploaded_files():
    current_uploads = list(uploads())
    if not current_uploads:
        return Div(id="uploaded-files")
    
    file_items = [
        Div(
            DivLAligned(
                get_file_icon(upload.filename),
                P(truncate_filename(upload.filename), cls="ml-1 text-sm"),
                Button(
                    UkIcon('x', cls="h-4 w-4 text-red-500"),
                    hx_delete=f"/delete_upload/{upload.id}",
                    hx_target="#uploaded-files",
                    hx_swap="outerHTML",
                    cls="ml-2 p-0"
                ),
                cls="py-1 px-2 rounded-md mr-2 mb-2"
            )
        ) for upload in current_uploads
    ]
    
    return Div(
        Div(
            DivLAligned(
                P(f"{len(current_uploads)} file(s) attached", cls="text-sm text-primary font-medium"),
                cls="mt-1 mb-2"
            ),
            Div(cls="flex flex-wrap")(*file_items),
        ),
        id="uploaded-files",
    )

def truncate_filename(filename, max_length=20):
    """Truncate filename if it's too long"""
    if len(filename) <= max_length:
        return filename
    ext = filename.split('.')[-1] if '.' in filename else ''
    name = filename[:max_length-len(ext)-3] + '...' + ('.' + ext if ext else '')
    return name

# Helper function to determine appropriate icon based on file type
def get_file_icon(filename):
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    icon_name = 'file'
    
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        icon_name = 'image'
    elif ext in ['mp4', 'mov', 'avi', 'webm']:
        icon_name = 'video'
    elif ext in ['mp3', 'wav', 'ogg']:
        icon_name = 'music'
    elif ext in ['pdf']:
        icon_name = 'file-text'
    
    return UkIcon(icon_name, cls="text-gray-500")

# File upload route
@rt("/upload")
async def post(files: list[UploadFile]):
    for file in files:
        uploads.insert(Upload(
            filename=file.filename,
            content_type=file.content_type,
            data=await file.read(),
            created_at=datetime.now().isoformat()
        ))
    return render_uploaded_files()

# Delete upload route
@rt("/delete_upload/{id}")
def delete(id: int):
    uploads.delete(id)
    return render_uploaded_files()

# Connected accounts rendering (unchanged)
def render_connected_accounts(active_accounts):
    if not active_accounts:
        return P("No connected accounts yet.", cls="text-muted")
    account_divs = [
        Card(
            CardHeader(DivLAligned(UkIcon(account.network), H3(f"{account.network.capitalize()}: {account.username}"))),
            CardFooter(
                Button(UkIcon('log-out'), "Logout", hx_post=f"/logout/{account.id}", hx_target="#accounts-content", hx_swap="outerHTML", cls=ButtonT.secondary)
            ),
            cls=CardT.hover
        ) for account in active_accounts
    ]
    return (H2("Your Connected Accounts"), Grid(*account_divs, cols=1))

# Connection forms (unchanged)
def render_connection_forms():
    active_accounts = list(accounts())
    connected_networks = [account.network for account in active_accounts]
    connection_cards = []
    # Bluesky connection
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
                        hx_target="#accounts-content",
                        hx_swap="outerHTML",
                        cls="space-y-2"
                    )
                ),
                cls=CardT.default
            )
        )
    # Twitter connection
    if "twitter" not in connected_networks:
        connection_cards.append(
            Card(
                CardHeader(DivLAligned(UkIcon('twitter'), H3("Twitter/X"))),
                CardBody(
                    P("Connect using browser login."),
                    P("This will open a browser window. Please login and then wait for the browser to close."),
                    Button("Connect with Twitter", hx_post="/login/twitter", hx_target="#accounts-content", hx_swap="outerHTML", cls=ButtonT.primary)
                ),
                cls=CardT.default
            )
        )
    # Mastodon connection
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
    return Grid(*connection_cards, cols=1) if connection_cards else P("You're connected to all available networks.", cls="text-muted")

# Post form rendering (unchanged)
def render_post_form(active_accounts):
    account_checkboxes = [
        LabelCheckboxX(
            id=f"account_{account.id}",
            name="account_id",
            value=str(account.id),
            checked=True,
            label=f"{account.network.capitalize()}: {account.username}"
        ) for account in active_accounts
    ]
    loading = Loading(cls=LoadingT.spinner, htmx_indicator=True, id="post-loading")
    form = Form(
        Div(
            P("Select accounts to post to:", cls="text-white mb-2"),
            Group(*account_checkboxes, cls="flex flex-wrap gap-4"),
            cls="mb-4"
        ),
        FormLabel("Post Content", fr="post-content", cls="text-white mt-4"),
        Textarea(
            id="post-content",
            name="content",
            placeholder="What's on your mind?",
            rows=8,
            cls="w-full p-4 border border-gray-500 rounded-lg bg-gray-700 text-white placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-400",
            hx_trigger="keyup changed delay:500ms",
            hx_get="/check_length",
            hx_target="#char-warning"
        ),
        Div(id="char-warning", cls="text-sm text-red-500 mt-2"),
        Div(loading, cls="mt-2"),
        Button(
            UkIcon('send', cls="mr-2"),
            "Post",
            type="submit",
            cls="mt-4 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-500 transition-colors"
        ),
        Div(id="post-result", cls="mt-4"),
        hx_post="/post",
        hx_target="#post-result",
        hx_swap="innerHTML",
        hx_indicator="#post-loading",
        hx_disabled_elt="find button",
        cls="space-y-4"
    )
    return Card(CardBody(form), cls="bg-gray-800 border border-gray-700 rounded-lg shadow-md")

CHAR_LIMITS = {"twitter": 280, "mastodon": 500, "bluesky": 300}

@rt("/check_length")
def get(content: str, account_id: list[str] = None):
    if not content.strip():
        return ""
    if not account_id:
        active_accounts = list(accounts())
        if not active_accounts:
            return "Warning: No accounts connected to check length against."
    else:
        active_accounts = [accounts[int(id)] for id in account_id if id.isdigit() and int(id) in accounts]
        if not active_accounts:
            return "Warning: No valid accounts selected to check length against."
    selected_networks = [account.network for account in active_accounts if account.network in CHAR_LIMITS]
    if not selected_networks:
        return ""
    max_len = min(CHAR_LIMITS[network] for network in selected_networks)
    if len(content) > max_len:
        return f"Warning: Your message ({len(content)} characters) exceeds the {max_len}-character limit for selected networks."
    return ""

# Login handlers (unchanged)
@rt("/login/bluesky")
def post(handle: str, password: str):
    try:
        client = AtprotoClient()
        profile = client.login(handle, password)
        credentials = {"handle": handle, "password": password}
        accounts.insert(Account(network="bluesky", username=handle, credentials=json.dumps(credentials), created_at=datetime.now().isoformat(), updated_at=datetime.now().isoformat()))
        return render_updated_accounts_tab()
    except Exception as e:
        return render_updated_accounts_tab_with_error(f"Error connecting to Bluesky: {str(e)}")

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
        return render_updated_accounts_tab()
    except Exception as e:
        return render_updated_accounts_tab_with_error(f"Error connecting to Twitter: {str(e)}")

@rt("/login/mastodon")
def post(instance: str, sess):
    try:
        sess["mastodon_instance"] = instance
        app_url = f"https://{instance}/api/v1/apps"
        app_data = {"client_name": "Open Social Poster", "redirect_uris": MASTODON_REDIRECT_URI, "scopes": "write:statuses write:media read"}
        app_response = requests.post(app_url, data=app_data)
        if app_response.status_code != 200:
            raise Exception(f"Failed to register app: {app_response.text}")
        app_info = app_response.json()
        sess["mastodon_client_id"] = app_info["client_id"]
        sess["mastodon_client_secret"] = app_info["client_secret"]
        auth_url = qp(f"https://{instance}/oauth/authorize", redirect_uri=MASTODON_REDIRECT_URI, client_id=app_info["client_id"], scope="write:statuses write:media read", response_type="code")
        return RedirectResponse(auth_url, status_code=303)
    except Exception as e:
        return render_updated_accounts_tab_with_error(f"Error connecting to Mastodon: {str(e)}")

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

# Logout handler (unchanged)
@rt("/logout/{id}")
def post(id: int):
    accounts.delete(id)
    return render_updated_accounts_tab()

# Helper functions for accounts tab updates (unchanged)
def render_updated_accounts_tab():
    active_accounts = list(accounts())
    return Div(
        H2("Your Connected Accounts"),
        render_connected_accounts(active_accounts),
        H2("Connect a New Account"),
        render_connection_forms(),
        id="accounts-content"
    )

def render_updated_accounts_tab_with_error(error_msg):
    active_accounts = list(accounts())
    return Div(
        H2("Your Connected Accounts"),
        render_connected_accounts(active_accounts),
        H2("Connect a New Account"),
        render_connection_forms(),
        Alert(error_msg, cls=AlertT.error),
        id="accounts-content"
    )

# Post handler with media
@rt("/post")
def post(content: str, account_id: list[str] = None):
    if not content.strip():
        return Alert("Please enter some content to post.", cls=AlertT.error)
    if not account_id:
        return Alert("Please select at least one account to post to.", cls=AlertT.error)
    
    selected_accounts = [accounts[int(id)] for id in account_id if id.isdigit() and int(id) in accounts]
    current_uploads = list(uploads())
    
    for account in selected_accounts:
        max_len = CHAR_LIMITS.get(account.network, 500)
        if len(content) > max_len:
            return Alert(
                f"Message too long for {account.network.capitalize()} ({len(content)} characters exceeds {max_len}-character limit).",
                cls=AlertT.error
            )
    
    results = []
    for account in selected_accounts:
        try:
            if account.network == "bluesky":
                result = post_to_bluesky(account, content, current_uploads)
                success = True
            elif account.network == "twitter":
                result = post_to_twitter(account, content, current_uploads)
                success = result.startswith("Posted")
            elif account.network == "mastodon":
                result = post_to_mastodon(account, content, current_uploads)
                success = True
            else:
                result = f"Unknown network: {account.network}"
                success = False
            results.append((account, success, result))
        except Exception as e:
            results.append((account, False, str(e)))
    
    # Clear uploads table after posting
    db.execute("DELETE FROM upload")
    
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

# Posting functions with media
def post_to_bluesky(account, content, uploads):
    credentials = json.loads(account.credentials)
    client = AtprotoClient()
    client.login(credentials["handle"], credentials["password"])
    
    url_pattern = re.compile(r'https?://[^\s]+')
    urls = url_pattern.findall(content)
    facets = []
    if urls:
        text = content
        for url in urls:
            start = text.index(url)
            end = start + len(url)
            facet = models.AppBskyRichtextFacet.Main(
                features=[models.AppBskyRichtextFacet.Link(uri=url)],
                index=models.AppBskyRichtextFacet.ByteSlice(byte_start=start, byte_end=end)
            )
            facets.append(facet)
    
    images = []
    for upload in uploads:
        # Extract the BlobRef from the response
        blob_response = client.upload_blob(upload.data)
        blob_ref = blob_response.blob  # Get the BlobRef object
        images.append(models.AppBskyEmbedImages.Image(alt="", image=blob_ref))
    
    embed = models.AppBskyEmbedImages.Main(images=images) if images else None
    post = client.send_post(text=content, facets=facets if facets else None, embed=embed)
    return f"Posted to Bluesky: {post.uri}"

def post_to_twitter(account, content, uploads):
    """
    Posts a tweet with attached files using Selenium to simulate drag-and-drop behavior.
    
    Args:
        account: Account object with credentials (cookies)
        content: The text content of the tweet
        uploads: List of Upload objects containing file data and metadata
    
    Returns:
        str: Success message or error description
    """
    # Load Twitter cookies from account credentials
    credentials = json.loads(account.credentials)
    cookies = credentials.get("cookies", [])
    
    # Set up Selenium WebDriver in headless mode
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    
    try:
        # Navigate to Twitter and apply cookies
        driver.get("https://twitter.com")
        for cookie in cookies:
            if 'expiry' in cookie:
                del cookie['expiry']
            driver.add_cookie(cookie)
        
        # Go to the tweet compose page
        driver.get("https://twitter.com/compose/tweet")
        
        # Wait for the compose page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tweetTextarea_0']"))
        )
        
        # Handle file uploads if any
        if uploads:
            # Create a temporary directory to store files
            temp_dir = tempfile.mkdtemp()
            file_paths = []
            
            # Save each uploaded file to the temporary directory
            for upload in uploads:
                file_path = os.path.join(temp_dir, upload.filename)
                with open(file_path, "wb") as f:
                    f.write(upload.data)
                file_paths.append(file_path)
            
            # Locate the hidden file input element
            file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            
            # Send the file paths to the file input element to simulate upload
            file_input.send_keys("\n".join(file_paths))
            
            # Wait for Twitter to process the file uploads
            time.sleep(5)  # Adjust this delay based on file size and network speed
            
            # Clean up temporary files
            shutil.rmtree(temp_dir)
        
        # Locate the tweet text area and enter the content
        tweet_textarea = driver.find_element(By.CSS_SELECTOR, "[data-testid='tweetTextarea_0']")
        tweet_textarea.send_keys(content)
        
        # Locate and click the "Post" button
        tweet_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Post']/ancestor::button"))
        )
        tweet_button.click()
        
        # Wait for the tweet to post
        time.sleep(5)
        
        return "Posted successfully!"
    
    except Exception as e:
        return f"Error posting to Twitter: {str(e)}"
    
    finally:
        driver.quit()

def post_to_mastodon(account, content, uploads):
    credentials = json.loads(account.credentials)
    headers = {"Authorization": f"Bearer {credentials['access_token']}"}
    
    media_ids = []
    for upload in uploads:
        media_response = requests.post(
            f"https://{credentials['instance']}/api/v1/media",
            headers=headers,
            files={"file": (upload.filename, upload.data, upload.content_type)}
        )
        if media_response.status_code != 200:
            raise Exception(f"Failed to upload media: {media_response.text}")
        media_ids.append(media_response.json()["id"])
    
    data = {"status": content, "visibility": "public"}
    if media_ids:
        data["media_ids"] = media_ids
    response = requests.post(
        f"https://{credentials['instance']}/api/v1/statuses",
        headers=headers,
        json=data
    )
    if response.status_code not in (200, 201, 202):
        raise Exception(f"Failed to post: {response.text}")
    return f"Posted to Mastodon: {response.json().get('url', 'Success!')}"

if __name__ == "__main__":
    serve()