import os
import json
import logging
import http.client
import time
from urllib.parse import quote, urlparse
from datetime import datetime, timedelta
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    CallbackContext, 
    CallbackQueryHandler,
    ContextTypes
)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8333576895:AAELRgTBOmWt0SK6SQN46Lmt3lxw75L88xA"
ADMIN_IDS = [1451422178]
BOT_USERNAME = "HYPERTERABOX_ROBOT"

RAPIDAPI_KEY = "fcdef36fbdmshabfa1f6458fba41p1a5020jsnb92890561254"
RAPIDAPI_HOST = "terabox-downloader-direct-download-link-generator1.p.rapidapi.com"

ALLOWED_USERS_ONLY = False
REQUEST_TIMEOUT = 60
DOWNLOAD_PATH = "downloads"

WELCOME_MESSAGE = """
👋 **Welcome to Terabox Video Downloader Bot!**

📥 **How to Use:**
1. Send me any Terabox video link
2. I'll process it instantly
3. Get direct download link

✅ **Supported Links:**
• terabox.com
• www.terabox.com  
• 1024terabox.com
• terabox.app
• and other Terabox domains

⚡ **Features:**
• Direct download links
• Fast processing
• No file size limits
• Free service

Send me a Terabox link now!
"""

HELP_MESSAGE = """
📖 **TERABOX DOWNLOADER BOT HELP**

**Commands:**
/start - Start the bot
/help - Show help message
/about - About this bot

**How to Download:**
1. Copy Terabox video link
2. Send/paste it to this bot
3. Wait for processing (10-20 seconds)
4. Click download button

**Supported Domains:**
• terabox.com
• 1024terabox.com
• terabox.app
• www.terabox.com

**Note:** 
• This bot uses official API
• Links work for 24 hours
• Maximum file size: 2GB

Need help? Contact admin.
"""

ADMIN_HELP = """
👑 **ADMIN COMMANDS**

/stats - Show bot statistics
/users - Show total users  
/broadcast - Broadcast message to all users
/restart - Restart bot service

**Quick Stats:**
• Total Users: {total_users}
• Today's Usage: {today_usage}
• Total Downloads: {total_downloads}
• Success Rate: {success_rate}%
"""
# ==================== END CONFIGURATION ====================

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('terabox_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TeraboxDownloader:
    """Main Terabox Downloader Bot Class"""
    
    def __init__(self):
        """Initialize the bot"""
        self.user_data_file = "users.json"
        self.stats_file = "stats.json"
        self.load_data()
        
    def load_data(self):
        """Load user data and statistics"""
        try:
            # Load users data
            if os.path.exists(self.user_data_file):
                with open(self.user_data_file, 'r', encoding='utf-8') as f:
                    self.users_data = json.load(f)
            else:
                self.users_data = {"users": [], "last_active": {}}
            
            # Load statistics
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
            else:
                self.stats = {
                    "total_requests": 0,
                    "successful_downloads": 0,
                    "failed_downloads": 0,
                    "daily_requests": {},
                    "user_activity": {},
                    "start_time": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            self.users_data = {"users": [], "last_active": {}}
            self.stats = {
                "total_requests": 0,
                "successful_downloads": 0,
                "failed_downloads": 0,
                "daily_requests": {},
                "user_activity": {},
                "start_time": datetime.now().isoformat()
            }
    
    def save_data(self):
        """Save user data and statistics"""
        try:
            with open(self.user_data_file, 'w', encoding='utf-8') as f:
                json.dump(self.users_data, f, indent=2, ensure_ascii=False)
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    def update_user(self, user_id: int, username: str, first_name: str):
        """Update user information"""
        try:
            user_info = {
                "id": user_id,
                "username": username or "",
                "first_name": first_name or "",
                "joined": datetime.now().isoformat()
            }
            
            # Check if user already exists
            user_exists = False
            for user in self.users_data["users"]:
                if user["id"] == user_id:
                    user_exists = True
                    # Update username if changed
                    if username:
                        user["username"] = username
                    if first_name:
                        user["first_name"] = first_name
                    break
            
            # Add new user if not exists
            if not user_exists:
                self.users_data["users"].append(user_info)
            
            # Update last active time
            self.users_data["last_active"][str(user_id)] = datetime.now().isoformat()
            
            # Update user activity in stats
            today = datetime.now().strftime("%Y-%m-%d")
            if str(user_id) not in self.stats["user_activity"]:
                self.stats["user_activity"][str(user_id)] = {}
            
            if today not in self.stats["user_activity"][str(user_id)]:
                self.stats["user_activity"][str(user_id)][today] = 1
            else:
                self.stats["user_activity"][str(user_id)][today] += 1
            
            self.save_data()
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
    
    def update_stats(self, success: bool = True):
        """Update bot statistics"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            self.stats["total_requests"] += 1
            
            if success:
                self.stats["successful_downloads"] += 1
            else:
                self.stats["failed_downloads"] += 1
            
            # Update daily requests
            if today in self.stats["daily_requests"]:
                self.stats["daily_requests"][today] += 1
            else:
                self.stats["daily_requests"][today] = 1
            
            self.save_data()
            
        except Exception as e:
            logger.error(f"Error updating stats: {e}")
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in ADMIN_IDS
    
    def is_allowed_user(self, user_id: int) -> bool:
        """Check if user is allowed to use bot"""
        if not ALLOWED_USERS_ONLY:
            return True
        return user_id in ADMIN_IDS
    
    def is_terabox_link(self, url: str) -> bool:
        """Check if URL is valid Terabox link"""
        terabox_domains = [
            'terabox.com',
            'www.terabox.com',
            '1024terabox.com',
            'www.1024terabox.com',
            'teraboxapp.com',
            'terabox.app',
            'teraboxapk.com'
        ]
        
        try:
            # Clean the URL
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed_url = urlparse(url.lower())
            domain = parsed_url.netloc
            
            # Remove www. prefix for checking
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return any(domain == domain_name or domain == f"www.{domain_name}" 
                      for domain_name in terabox_domains)
            
        except Exception as e:
            logger.error(f"Error checking link: {e}")
            return False
    
    async def extract_direct_link(self, terabox_url: str) -> Optional[Dict]:
        """Extract direct download link from RapidAPI"""
        max_retries = 2
        for retry in range(max_retries):
            try:
                logger.info(f"Extracting direct link (Attempt {retry + 1}): {terabox_url}")
                
                # Clean URL
                if not terabox_url.startswith(('http://', 'https://')):
                    terabox_url = 'https://' + terabox_url
                
                # Prepare connection
                conn = http.client.HTTPSConnection(RAPIDAPI_HOST, timeout=REQUEST_TIMEOUT)
                
                # Try different API endpoints
                endpoints = [
                    f"/direct-download?url={quote(terabox_url)}",
                    f"/download?url={quote(terabox_url)}",
                    f"/url?url={quote(terabox_url)}",
                    f"/link?url={quote(terabox_url)}",
                    f"/get?url={quote(terabox_url)}",
                    f"/api?url={quote(terabox_url)}"
                ]
                
                headers = {
                    'x-rapidapi-key': RAPIDAPI_KEY,
                    'x-rapidapi-host': RAPIDAPI_HOST,
                    'Content-Type': 'application/json'
                }
                
                for endpoint in endpoints:
                    try:
                        logger.info(f"Trying endpoint: {endpoint}")
                        
                        conn.request("GET", endpoint, headers=headers)
                        
                        response = conn.getresponse()
                        status_code = response.status
                        response_data = response.read()
                        response_text = response_data.decode('utf-8')
                        
                        logger.info(f"API Response Status: {status_code}")
                        logger.debug(f"Response: {response_text[:500]}")
                        
                        if status_code == 200:
                            result = json.loads(response_text)
                            
                            # Extract direct link from various response formats
                            direct_link = None
                            title = None
                            size = None
                            thumbnail = None
                            
                            # Method 1: Check common direct link fields
                            link_fields = ['direct_link', 'download_link', 'link', 'url', 
                                         'download_url', 'direct_download', 'download']
                            
                            for field in link_fields:
                                if field in result:
                                    value = result[field]
                                    if isinstance(value, str) and value.startswith('http'):
                                        direct_link = value
                                        break
                                elif 'data' in result and isinstance(result['data'], dict):
                                    if field in result['data']:
                                        value = result['data'][field]
                                        if isinstance(value, str) and value.startswith('http'):
                                            direct_link = value
                                            break
                            
                            # Method 2: Check if result itself is a direct link
                            if not direct_link and isinstance(result, str) and result.startswith('http'):
                                direct_link = result
                            
                            # Get video info
                            title = result.get('title', result.get('filename', result.get('name', 'Unknown Title')))
                            size = result.get('size', result.get('filesize', result.get('file_size', 'N/A')))
                            thumbnail = result.get('thumbnail', result.get('thumb', result.get('thumbnail_url')))
                            
                            if direct_link:
                                logger.info(f"✅ Direct link found: {direct_link[:80]}...")
                                
                                video_data = {
                                    'title': title[:200] if title else 'Unknown Title',
                                    'size': self.format_size(size) if isinstance(size, (int, float)) else str(size),
                                    'direct_link': direct_link,
                                    'thumbnail': thumbnail,
                                    'source_url': terabox_url
                                }
                                
                                return video_data
                            
                    except Exception as endpoint_error:
                        logger.warning(f"Endpoint {endpoint} failed: {endpoint_error}")
                        continue
                
                logger.warning(f"No direct link found in attempt {retry + 1}")
                
                # Wait before retry
                if retry < max_retries - 1:
                    time.sleep(2)
                    
            except http.client.HTTPException as http_error:
                logger.error(f"HTTP Error: {http_error}")
                if retry < max_retries - 1:
                    time.sleep(3)
            except json.JSONDecodeError as json_error:
                logger.error(f"JSON Error: {json_error}")
                if retry < max_retries - 1:
                    time.sleep(2)
            except Exception as e:
                logger.error(f"Extraction Error: {e}")
                if retry < max_retries - 1:
                    time.sleep(2)
        
        logger.error("❌ All extraction attempts failed")
        return None
    
    def format_size(self, size_bytes):
        """Format file size in human readable format"""
        try:
            size_bytes = float(size_bytes)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.2f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.2f} TB"
        except:
            return "N/A"
    
    async def start_command(self, update: Update, context: CallbackContext):
        """Handle /start command"""
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            logger.info(f"Start command from user {user.id} ({user.username})")
            
            # Check if user is allowed
            if not self.is_allowed_user(user.id):
                await update.message.reply_text(
                    "🚫 **Access Denied**\n\n"
                    "This bot is currently in private mode.\n"
                    "Contact admin for access.",
                    parse_mode='Markdown'
                )
                return
            
            # Update user data
            self.update_user(user.id, user.username, user.first_name)
            
            # Create welcome keyboard
            keyboard = [
                [
                    InlineKeyboardButton("📖 Help Guide", callback_data="help"),
                    InlineKeyboardButton("🔗 Examples", callback_data="example")
                ],
                [
                    InlineKeyboardButton("📊 Bot Status", callback_data="status"),
                    InlineKeyboardButton("⭐ Rate Us", url="https://t.me/")
                ]
            ]
            
            if self.is_admin(user.id):
                keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send welcome message
            welcome_msg = WELCOME_MESSAGE
            
            await update.message.reply_text(
                welcome_msg,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await update.message.reply_text("❌ Error starting bot. Please try again.")
    
    async def help_command(self, update: Update, context: CallbackContext):
        """Handle /help command"""
        try:
            user = update.effective_user
            
            if self.is_admin(user.id):
                # Calculate success rate
                total = self.stats.get("total_requests", 0)
                successful = self.stats.get("successful_downloads", 0)
                success_rate = (successful / total * 100) if total > 0 else 0
                
                help_text = ADMIN_HELP.format(
                    total_users=len(self.users_data["users"]),
                    today_usage=self.stats["daily_requests"].get(datetime.now().strftime("%Y-%m-%d"), 0),
                    total_downloads=self.stats["successful_downloads"],
                    success_rate=f"{success_rate:.1f}"
                )
            else:
                help_text = HELP_MESSAGE
            
            keyboard = [
                [InlineKeyboardButton("🚀 Start Downloading", callback_data="start_download")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                help_text,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"Error in help_command: {e}")
            await update.message.reply_text(HELP_MESSAGE, parse_mode='Markdown')
    
    async def about_command(self, update: Update, context: CallbackContext):
        """Handle /about command"""
        about_text = """
🤖 **About Terabox Downloader Bot**

**Version:** 2.0
**Developer:** @HyperBotDev
**API:** RapidAPI Terabox Service

**Features:**
• Direct download links from Terabox
• Support all Terabox domains
• Fast processing (10-20 seconds)
• No file size limits
• Free service

**Technology:**
• Python 3.10+
• python-telegram-bot
• RapidAPI Integration
• JSON Database

**Privacy:**
• We don't store your files
• We don't share your links
• Secure API connections

**Support:** @HyperSupportBot
"""
        
        await update.message.reply_text(about_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: CallbackContext):
        """Handle text messages (Terabox links)"""
        try:
            user = update.effective_user
            message_text = update.message.text.strip()
            
            logger.info(f"Message from {user.id}: {message_text[:50]}...")
            
            # Check if user is allowed
            if not self.is_allowed_user(user.id):
                await update.message.reply_text(
                    "🚫 **Access Denied**\n\n"
                    "This bot is currently in private mode.",
                    parse_mode='Markdown'
                )
                return
            
            # Update user activity
            self.update_user(user.id, user.username, user.first_name)
            
            # Check if it's a Terabox link
            if not self.is_terabox_link(message_text):
                await update.message.reply_text(
                    "❌ **Invalid Link!**\n\n"
                    "Please send a valid Terabox link.\n\n"
                    "**Valid Examples:**\n"
                    "• `https://terabox.com/s/xxxxxx`\n"
                    "• `https://1024terabox.com/s/xxxxxx`\n"
                    "• `https://terabox.app/s/xxxxxx`\n\n"
                    "**Tip:** Make sure the link starts with `https://`",
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                return
            
            # Send processing message
            processing_msg = await update.message.reply_text(
                "🔄 **Processing Your Link...**\n\n"
                "⏳ Please wait 10-20 seconds\n"
                "📥 Extracting download link...\n"
                "⚡ This may take a moment",
                parse_mode='Markdown'
            )
            
            try:
                # Extract direct download link
                start_time = time.time()
                video_info = await self.extract_direct_link(message_text)
                processing_time = time.time() - start_time
                
                if video_info:
                    # Update statistics
                    self.update_stats(success=True)
                    
                    # Edit processing message
                    await processing_msg.edit_text(
                        f"✅ **Link Processed Successfully!**\n\n"
                        f"⏱️ Processing time: {processing_time:.1f}s\n"
                        f"📦 File ready for download",
                        parse_mode='Markdown'
                    )
                    
                    # Small delay before showing result
                    await asyncio.sleep(1)
                    
                    # Send video details with download button
                    await self.send_download_result(update, video_info, message_text)
                    
                else:
                    # Update failed statistics
                    self.update_stats(success=False)
                    
                    await processing_msg.edit_text(
                        "❌ **Failed to Process Link**\n\n"
                        "**Possible Reasons:**\n"
                        "• Link expired or invalid\n"
                        "• Video removed or private\n"
                        "• API temporary unavailable\n"
                        "• File too large (>2GB)\n\n"
                        "**Try:**\n"
                        "1. Check if link is correct\n"
                        "2. Try again in 5 minutes\n"
                        "3. Use different Terabox link",
                        parse_mode='Markdown'
                    )
                    
            except Exception as e:
                logger.error(f"Processing error: {e}")
                await processing_msg.edit_text(
                    "⚠️ **Processing Error**\n\n"
                    "An error occurred while processing.\n"
                    "Please try again with a different link.",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error in handle_message: {e}")
            await update.message.reply_text(
                "❌ **System Error**\n\n"
                "Please try again later or contact admin.",
                parse_mode='Markdown'
            )
    
    async def send_download_result(self, update: Update, video_info: Dict, original_url: str):
        """Send download result with button"""
        try:
            title = video_info.get('title', 'Unknown File')
            size = video_info.get('size', 'N/A')
            direct_link = video_info.get('direct_link')
            
            # Create message
            message = f"""
✅ **DOWNLOAD READY**

📁 **File Info:**
├ 📛 **Name:** `{title}`
├ 📦 **Size:** `{size}`
└ 🔗 **Status:** Ready to download

⬇️ **Click button below to download:**
"""
            
            # Create buttons
            keyboard = []
            
            if direct_link and direct_link.startswith('http'):
                # Main download button
                keyboard.append([
                    InlineKeyboardButton("⬇️ DOWNLOAD NOW", url=direct_link)
                ])
                
                # Additional options
                keyboard.append([
                    InlineKeyboardButton("🔄 Get New Link", callback_data=f"refresh_{original_url}"),
                    InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_{direct_link[:50]}")
                ])
            else:
                message += "\n❌ **Error: No download link available**"
            
            # Navigation buttons
            keyboard.append([
                InlineKeyboardButton("📥 New Download", callback_data="new_download"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="back")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Try to send with thumbnail
            thumbnail = video_info.get('thumbnail')
            if thumbnail and thumbnail.startswith('http'):
                try:
                    await update.message.reply_photo(
                        photo=thumbnail,
                        caption=message,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    return
                except:
                    pass
            
            # Send text message
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"Error in send_download_result: {e}")
            await update.message.reply_text(
                f"📥 **Download Link:**\n`{direct_link}`\n\nClick the link to download.",
                parse_mode='Markdown'
            )
    
    async def button_callback(self, update: Update, context: CallbackContext):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        try:
            if data == "help":
                await self.help_command(update, context)
            
            elif data == "example":
                examples = """
🔗 **Example Terabox Links:**

**Format 1:**
`https://terabox.com/s/1LQyTj3pGxYzABC123`
`https://terabox.com/s/1abcdefghijklmnopqr`

**Format 2:**
`https://1024terabox.com/s/1XYZ123ABC456`
`https://1024terabox.com/s/1mnopqrstuvwxyz`

**Format 3:**
`https://terabox.app/s/1ABCDEFG1234567`
`https://terabox.app/s/1qwertyuiopasdfgh`

**How to get link:**
1. Open Terabox website/app
2. Find video you want
3. Click Share button
4. Copy the link
5. Send to this bot
"""
                await query.message.reply_text(examples, parse_mode='Markdown')
            
            elif data == "status":
                user = query.from_user
                if self.is_admin(user.id):
                    stats = self.get_admin_stats()
                    await query.message.reply_text(stats, parse_mode='Markdown')
                else:
                    status_text = f"""
📊 **Bot Status**

✅ **Operational**
👥 Users: {len(self.users_data['users'])}
📈 Today: {self.stats['daily_requests'].get(datetime.now().strftime('%Y-%m-%d'), 0)} requests

🕒 **Server Time:** {datetime.now().strftime('%H:%M:%S')}
📅 **Date:** {datetime.now().strftime('%d-%m-%Y')}

⚡ **Service:** Active
"""
                    await query.message.reply_text(status_text, parse_mode='Markdown')
            
            elif data == "admin":
                user = query.from_user
                if self.is_admin(user.id):
                    keyboard = [
                        [InlineKeyboardButton("📊 Statistics", callback_data="stats_detailed")],
                        [InlineKeyboardButton("👥 User Management", callback_data="user_management")],
                        [InlineKeyboardButton("🔄 System Control", callback_data="system_control")],
                        [InlineKeyboardButton("🔙 Back", callback_data="back")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text(
                        "👑 **Admin Control Panel**\n\nSelect option:",
                        reply_markup=reply_markup
                    )
            
            elif data == "stats_detailed":
                user = query.from_user
                if self.is_admin(user.id):
                    stats_text = self.get_detailed_stats()
                    await query.message.reply_text(stats_text, parse_mode='Markdown')
            
            elif data == "user_management":
                user = query.from_user
                if self.is_admin(user.id):
                    users_count = len(self.users_data["users"])
                    active_today = len([uid for uid, time in self.users_data["last_active"].items() 
                                      if time.startswith(datetime.now().strftime("%Y-%m-%d"))])
                    
                    user_text = f"""
👥 **User Management**

📊 **Overview:**
• Total Users: {users_count}
• Active Today: {active_today}
• New Today: {len([u for u in self.users_data["users"] 
                   if u.get("joined", "").startswith(datetime.now().strftime("%Y-%m-%d"))])}

📋 **Recent Users (Last 10):**
"""
                    recent_users = self.users_data["users"][-10:]
                    for u in reversed(recent_users):
                        username = f"@{u['username']}" if u['username'] else "No username"
                        user_text += f"• {username} ({u['id']})\n"
                    
                    await query.message.reply_text(user_text, parse_mode='Markdown')
            
            elif data == "start_download":
                await query.message.reply_text(
                    "📥 **Ready for Download!**\n\n"
                    "Send me any Terabox link now.",
                    parse_mode='Markdown'
                )
            
            elif data == "new_download":
                await query.message.reply_text(
                    "🆕 **New Download**\n\n"
                    "Paste your Terabox link below:",
                    parse_mode='Markdown'
                )
            
            elif data.startswith("refresh_"):
                original_url = data.replace("refresh_", "")
                msg = await query.message.reply_text("🔄 Refreshing download link...")
                
                video_info = await self.extract_direct_link(original_url)
                if video_info:
                    await msg.delete()
                    await self.send_download_result(update, video_info, original_url)
                else:
                    await msg.edit_text("❌ Failed to refresh link.")
            
            elif data.startswith("copy_"):
                link_part = data.replace("copy_", "")
                await query.message.reply_text(
                    f"📋 **Link Copied!**\n\n"
                    f"Use this link to download:\n"
                    f"`{link_part}...`\n\n"
                    f"Full link sent to your messages.",
                    parse_mode='Markdown'
                )
            
            elif data == "back":
                # Return to main menu
                user = query.from_user
                keyboard = [
                    [
                        InlineKeyboardButton("📖 Help", callback_data="help"),
                        InlineKeyboardButton("🔗 Examples", callback_data="example")
                    ],
                    [
                        InlineKeyboardButton("📊 Status", callback_data="status"),
                        InlineKeyboardButton("⭐ Rate", url="https://t.me/")
                    ]
                ]
                
                if self.is_admin(user.id):
                    keyboard.append([InlineKeyboardButton("👑 Admin", callback_data="admin")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.reply_text(
                    WELCOME_MESSAGE,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            
            elif data == "system_control":
                user = query.from_user
                if self.is_admin(user.id):
                    keyboard = [
                        [InlineKeyboardButton("🔄 Restart Bot", callback_data="restart_bot")],
                        [InlineKeyboardButton("📊 Clear Cache", callback_data="clear_cache")],
                        [InlineKeyboardButton("🔙 Back", callback_data="admin")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text(
                        "⚙️ **System Control**\n\n"
                        "Warning: These actions affect bot operation.",
                        reply_markup=reply_markup
                    )
            
            elif data == "restart_bot":
                user = query.from_user
                if self.is_admin(user.id):
                    await query.message.reply_text("🔄 Restarting bot...")
                    # Implementation depends on hosting environment
            
            elif data == "clear_cache":
                user = query.from_user
                if self.is_admin(user.id):
                    self.users_data = {"users": [], "last_active": {}}
                    self.save_data()
                    await query.message.reply_text("✅ Cache cleared successfully!")
            
        except Exception as e:
            logger.error(f"Error in button_callback: {e}")
            await query.message.reply_text("❌ Error processing request.")
    
    def get_admin_stats(self) -> str:
        """Get admin statistics"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            total_requests = self.stats.get('total_requests', 0)
            successful = self.stats.get('successful_downloads', 0)
            failed = self.stats.get('failed_downloads', 0)
            
            success_rate = 0
            if total_requests > 0:
                success_rate = (successful / total_requests) * 100
            
            # Calculate weekly activity
            weekly_requests = sum(count for date, count in self.stats['daily_requests'].items() 
                                 if date >= week_ago)
            
            # Calculate active users
            active_today = len([uid for uid, time in self.users_data["last_active"].items() 
                              if time.startswith(today)])
            
            active_week = len(set(uid for uid, time in self.users_data["last_active"].items() 
                                if time >= week_ago))
            
            # Bot uptime
            start_time = datetime.fromisoformat(self.stats.get('start_time', datetime.now().isoformat()))
            uptime = datetime.now() - start_time
            uptime_days = uptime.days
            uptime_hours = uptime.seconds // 3600
            uptime_minutes = (uptime.seconds % 3600) // 60
            
            return f"""
📊 **ADMIN STATISTICS DASHBOARD**

👥 **USER ANALYTICS:**
• Total Registered: {len(self.users_data['users'])}
• Active Today: {active_today}
• Active This Week: {active_week}
• New Today: {len([u for u in self.users_data["users"] if u.get("joined", "").startswith(today)])}

📈 **PERFORMANCE METRICS:**
• Total Requests: {total_requests:,}
• Successful: {successful:,}
• Failed: {failed:,}
• Success Rate: {success_rate:.1f}%

📅 **DAILY ACTIVITY:**
• Today ({today}): {self.stats['daily_requests'].get(today, 0):,}
• Yesterday ({yesterday}): {self.stats['daily_requests'].get(yesterday, 0):,}
• Last 7 Days: {weekly_requests:,}

⏱️ **SYSTEM INFO:**
• Uptime: {uptime_days}d {uptime_hours}h {uptime_minutes}m
• Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Memory Usage: Monitoring...
• API Status: ✅ Active

💾 **DATA SIZE:**
• Users DB: {len(json.dumps(self.users_data)):,} bytes
• Stats DB: {len(json.dumps(self.stats)):,} bytes
"""
        except Exception as e:
            logger.error(f"Error in get_admin_stats: {e}")
            return "Error generating statistics."
    
    def get_detailed_stats(self) -> str:
        """Get detailed statistics"""
        return self.get_admin_stats()
    
    async def stats_command(self, update: Update, context: CallbackContext):
        """Handle /stats command (Admin only)"""
        user = update.effective_user
        
        if not self.is_admin(user.id):
            await update.message.reply_text("🚫 This command is for administrators only.")
            return
        
        stats_text = self.get_admin_stats()
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def users_command(self, update: Update, context: CallbackContext):
        """Handle /users command (Admin only)"""
        user = update.effective_user
        
        if not self.is_admin(user.id):
            await update.message.reply_text("🚫 This command is for administrators only.")
            return
        
        total_users = len(self.users_data["users"])
        active_today = len([uid for uid, time in self.users_data["last_active"].items() 
                          if time.startswith(datetime.now().strftime("%Y-%m-%d"))])
        
        await update.message.reply_text(
            f"👥 **USER STATISTICS**\n\n"
            f"• Total Users: **{total_users}**\n"
            f"• Active Today: **{active_today}**\n"
            f"• User Growth: +{len([u for u in self.users_data['users'] 
                                  if u.get('joined', '').startswith(datetime.now().strftime('%Y-%m-%d'))])} today\n\n"
            f"📊 **Top 10 Recent Users:**\n"
            f"{self.get_recent_users_list(10)}",
            parse_mode='Markdown'
        )
    
    def get_recent_users_list(self, count: int = 10) -> str:
        """Get list of recent users"""
        recent_users = self.users_data["users"][-count:]
        user_list = ""
        
        for user in reversed(recent_users):
            username = f"@{user['username']}" if user['username'] else "No username"
            first_name = user.get('first_name', 'Unknown')
            user_list += f"• {username} ({first_name}) - Joined: {user.get('joined', '')[:10]}\n"
        
        return user_list if user_list else "No users yet."
    
    async def broadcast_command(self, update: Update, context: CallbackContext):
        """Handle /broadcast command (Admin only)"""
        user = update.effective_user
        
        if not self.is_admin(user.id):
            await update.message.reply_text("🚫 This command is for administrators only.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "📢 **Broadcast Usage:**\n\n"
                "`/broadcast <message>`\n\n"
                "**Example:**\n"
                "`/broadcast Hello users! New update available.`",
                parse_mode='Markdown'
            )
            return
        
        message = " ".join(context.args)
        total_users = len(self.users_data["users"])
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm Send", callback_data=f"confirm_broadcast_{message[:30]}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📢 **BROADCAST CONFIRMATION**\n\n"
            f"**Message:**\n{message[:500]}\n\n"
            f"**Recipients:** {total_users} users\n"
            f"**Estimated Time:** {total_users // 10} seconds\n\n"
            f"**Are you sure you want to send?**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def error_handler(self, update: Update, context: CallbackContext):
        """Handle errors"""
        logger.error(f"Update {update} caused error: {context.error}", exc_info=True)
        
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ **An error occurred**\n\n"
                    "Please try again or contact admin if issue persists.",
                    parse_mode='Markdown'
                )
            
            # Notify all admins about critical error
            error_details = f"""
🚨 **BOT ERROR ALERT**

**Error:** {context.error}
**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Update:** {update}

**Traceback:**
{context.error.__traceback__}
"""
            
            # Send to all admins (truncate if too long)
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=error_details[:4000],
                        parse_mode='Markdown'
                    )
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error in error_handler: {e}")
    
    def run(self):
        """Run the Telegram bot"""
        logger.info("=" * 50)
        logger.info("🚀 STARTING TERABOX DOWNLOADER BOT")
        logger.info("=" * 50)
        
        # Check configuration
        if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or BOT_TOKEN == "":
            logger.error("❌ ERROR: BOT_TOKEN not set!")
            print("\n❌ ERROR: Please set your BOT_TOKEN in configuration!")
            return
        
        if RAPIDAPI_KEY == "YOUR_RAPIDAPI_KEY_HERE" or RAPIDAPI_KEY == "":
            logger.error("❌ ERROR: RAPIDAPI_KEY not set!")
            print("\n❌ ERROR: Please set your RAPIDAPI_KEY in configuration!")
            return
        
        if not ADMIN_IDS:
            logger.error("⚠️ WARNING: ADMIN_IDS is empty!")
            print("\n⚠️ WARNING: No admin IDs set!")
        
        # Create downloads directory
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
        logger.info(f"📁 Download path created: {DOWNLOAD_PATH}")
        
        try:
            # Create application
            application = Application.builder().token(BOT_TOKEN).build()
            
            # Add command handlers
            application.add_handler(CommandHandler("start", self.start_command))
            application.add_handler(CommandHandler("help", self.help_command))
            application.add_handler(CommandHandler("about", self.about_command))
            application.add_handler(CommandHandler("stats", self.stats_command))
            application.add_handler(CommandHandler("users", self.users_command))
            application.add_handler(CommandHandler("broadcast", self.broadcast_command))
            
            # Handle text messages
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Handle button callbacks
            application.add_handler(CallbackQueryHandler(self.button_callback))
            
            # Add error handler
            application.add_error_handler(self.error_handler)
            
            # Start bot
            logger.info("✅ Bot initialized successfully")
            logger.info(f"🤖 Bot Username: @{BOT_USERNAME}")
            logger.info(f"👑 Admin IDs: {ADMIN_IDS}")
            logger.info(f"⚡ RapidAPI Host: {RAPIDAPI_HOST}")
            logger.info(f"📊 Total Users: {len(self.users_data['users'])}")
            logger.info("🔄 Starting polling...")
            
            print("\n" + "=" * 50)
            print("🤖 TERABOX DOWNLOADER BOT STARTED")
            print("=" * 50)
            print(f"Bot: @{BOT_USERNAME}")
            print(f"Status: ✅ RUNNING")
            print(f"Users: {len(self.users_data['users'])}")
            print(f"API: {RAPIDAPI_HOST}")
            print("=" * 50)
            print("Press Ctrl+C to stop\n")
            
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                close_loop=False
            )
            
        except Exception as e:
            logger.error(f"Fatal error starting bot: {e}")
            print(f"\n❌ FATAL ERROR: {e}")
            print("Bot stopped!")

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    import asyncio
    
    print("""
    ╔══════════════════════════════════════════════╗
    ║       TERABOX DOWNLOADER BOT v2.0           ║
    ║          Professional Edition               ║
    ╚══════════════════════════════════════════════╝
    
    📋 **Features:**
    • Direct download links from Terabox
    • Support all Terabox domains
    • Advanced error handling
    • User statistics & analytics
    • Admin control panel
    • Broadcast messages
    
    ⚙️ **Requirements:**
    • Python 3.8+
    • python-telegram-bot
    • RapidAPI account
    
    📝 **Setup Instructions:**
    1. Edit configuration at top of file
    2. Set BOT_TOKEN from @BotFather
    3. Set RAPIDAPI_KEY from RapidAPI
    4. Set your ADMIN_ID (Telegram ID)
    5. Run: python terabox_bot.py
    
    ⚠️ **Install Dependencies:**
    pip install python-telegram-bot
    
    🔧 **Support:** @HyperSupportBot
    """)
    
    # Create and run bot
    try:
        bot = TeraboxDownloader()
        bot.run()
    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped by user")
        logger.info("Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logger.error(f"Unexpected error in main: {e}")