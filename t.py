import os
import json
import logging
import http.client
from urllib.parse import quote, urlparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple

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

# ==================== CONFIGURATION - EDIT HERE ====================
class Config:
    """All configuration settings - Edit these values"""
    
    # Telegram Bot Settings
    BOT_TOKEN = "8333576895:AAELRgTBOmWt0SK6SQN46Lmt3lxw75L88xA"  # Get from @BotFather
    ADMIN_IDS = [1451422178]  # Your Telegram User IDs
    BOT_USERNAME = "HYPERTERABOX_ROBOT"  # Without @
    
    # RapidAPI Settings
    RAPIDAPI_KEY = "fcdef36fbdmshabfa1f6458fba41p1a5020jsnb92890561254"
    RAPIDAPI_HOST = "http://terabox-downloader-direct-download-link-generator1.p.rapidapi.com"
    
    # Bot Settings
    MAX_FILE_SIZE = 2147483648  # 2GB in bytes
    ALLOWED_USERS_ONLY = False  # Set True for private bot
    REQUEST_TIMEOUT = 30  # seconds
    DOWNLOAD_PATH = "downloads"  # Local storage folder
    
    # Messages
    WELCOME_MESSAGE = """
👋 **Welcome to Terabox Video Downloader!**

📥 **How to Use:**
1. Send me any Terabox video link
2. I'll extract video information
3. Get direct download links

✅ **Supported Links:**
• terabox.com
• www.terabox.com  
• 1024terabox.com
• and other Terabox domains

⚡ **Ready to download!**
"""
    
    HELP_MESSAGE = """
📖 **TERABOX DOWNLOADER BOT HELP**

**Commands:**
/start - Start the bot
/help - Show this help message
/stats - Bot statistics (Admin only)
/users - Show user count (Admin only)
/broadcast - Send message to all users (Admin only)

**How to Download:**
1. Copy Terabox video link
2. Send/paste it to this bot
3. Wait for processing
4. Click download button

**Features:**
✅ Direct download links
✅ Multiple quality options
✅ Fast processing
✅ No file size limits
✅ Private & secure

**Note:** This bot uses official Terabox API.
"""
    
    ADMIN_HELP = """
👑 **ADMIN COMMANDS**

/stats - Bot usage statistics
/users - Total users count  
/broadcast - Send message to all users
/restart - Restart bot (maintenance)
/logs - Get recent logs

**Quick Stats:**
• Total Users: {total_users}
• Today's Usage: {today_usage}
• Total Downloads: {total_downloads}
"""
# ==================== END CONFIGURATION ====================

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('terabox_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TeraboxDownloader:
    """Main Terabox Downloader Bot Class"""
    
    def __init__(self):
        """Initialize the bot"""
        self.config = Config
        self.user_data_file = "users.json"
        self.stats_file = "stats.json"
        self.load_data()
        
    def load_data(self):
        """Load user data and statistics"""
        try:
            # Load users data
            if os.path.exists(self.user_data_file):
                with open(self.user_data_file, 'r') as f:
                    self.users_data = json.load(f)
            else:
                self.users_data = {"users": [], "last_active": {}}
            
            # Load statistics
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    self.stats = json.load(f)
            else:
                self.stats = {
                    "total_requests": 0,
                    "successful_downloads": 0,
                    "failed_downloads": 0,
                    "daily_requests": {},
                    "user_activity": {}
                }
                
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            self.users_data = {"users": [], "last_active": {}}
            self.stats = {
                "total_requests": 0,
                "successful_downloads": 0,
                "failed_downloads": 0,
                "daily_requests": {},
                "user_activity": {}
            }
    
    def save_data(self):
        """Save user data and statistics"""
        try:
            with open(self.user_data_file, 'w') as f:
                json.dump(self.users_data, f, indent=2)
            
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    def update_user(self, user_id: int, username: str, first_name: str):
        """Update user information"""
        user_info = {
            "id": user_id,
            "username": username,
            "first_name": first_name,
            "joined": datetime.now().isoformat()
        }
        
        # Add user if not exists
        if not any(u["id"] == user_id for u in self.users_data["users"]):
            self.users_data["users"].append(user_info)
        
        # Update last active
        self.users_data["last_active"][str(user_id)] = datetime.now().isoformat()
        self.save_data()
    
    def update_stats(self, success: bool = True):
        """Update bot statistics"""
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
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.config.ADMIN_IDS
    
    def is_allowed_user(self, user_id: int) -> bool:
        """Check if user is allowed to use bot"""
        if not self.config.ALLOWED_USERS_ONLY:
            return True
        return user_id in self.config.ADMIN_IDS
    
    def is_terabox_link(self, url: str) -> bool:
        """Check if URL is valid Terabox link"""
        terabox_domains = [
            'terabox.com',
            'www.terabox.com',
            '1024terabox.com',
            'www.1024terabox.com',
            'teraboxapp.com'
        ]
        
        try:
            parsed_url = urlparse(url.lower())
            return any(domain in parsed_url.netloc for domain in terabox_domains)
        except:
            return False
    
    async def extract_video_info(self, terabox_url: str) -> Optional[Dict]:
        """Extract video information using RapidAPI"""
        try:
            logger.info(f"Extracting video info from: {terabox_url}")
            
            conn = http.client.HTTPSConnection(self.config.RAPIDAPI_HOST, timeout=self.config.REQUEST_TIMEOUT)
            
            # Prepare API request
            api_endpoint = f"/url?url={quote(terabox_url)}"
            
            conn.request("GET", api_endpoint, headers={
                'x-rapidapi-key': self.config.RAPIDAPI_KEY,
                'x-rapidapi-host': self.config.RAPIDAPI_HOST
            })
            
            res = conn.getresponse()
            data = res.read()
            response_text = data.decode("utf-8")
            
            logger.debug(f"API Response: {response_text[:200]}...")
            
            # Parse response
            result = json.loads(response_text)
            
            if res.status == 200 and ('download_links' in result or 'direct_link' in result):
                logger.info("Video info extracted successfully")
                return result
            else:
                logger.error(f"API Error: Status {res.status}, Response: {response_text}")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {e}")
            return None
        except http.client.HTTPException as e:
            logger.error(f"HTTP Error: {e}")
            return None
        except Exception as e:
            logger.error(f"Extraction Error: {e}")
            return None
    
    async def start_command(self, update: Update, context: CallbackContext):
        """Handle /start command"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Check if user is allowed
        if not self.is_allowed_user(user.id):
            await update.message.reply_text("❌ Sorry, this bot is currently private.")
            return
        
        # Update user data
        self.update_user(user.id, user.username or "", user.first_name or "")
        
        # Create welcome keyboard
        keyboard = [
            [
                InlineKeyboardButton("📖 Help", callback_data="help"),
                InlineKeyboardButton("🔗 Example", callback_data="example")
            ],
            [
                InlineKeyboardButton("📊 Stats", callback_data="stats"),
                InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/yourusername")
            ]
        ]
        
        if self.is_admin(user.id):
            keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send welcome message
        welcome_text = self.config.WELCOME_MESSAGE.replace("{name}", user.first_name)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: CallbackContext):
        """Handle /help command"""
        user = update.effective_user
        
        if self.is_admin(user.id):
            # Admin help
            help_text = self.config.ADMIN_HELP.format(
                total_users=len(self.users_data["users"]),
                today_usage=self.stats["daily_requests"].get(datetime.now().strftime("%Y-%m-%d"), 0),
                total_downloads=self.stats["successful_downloads"]
            )
        else:
            # User help
            help_text = self.config.HELP_MESSAGE
        
        await update.message.reply_text(help_text, parse_mode='Markdown', disable_web_page_preview=True)
    
    async def handle_message(self, update: Update, context: CallbackContext):
        """Handle text messages (Terabox links)"""
        user = update.effective_user
        message_text = update.message.text.strip()
        
        # Check if user is allowed
        if not self.is_allowed_user(user.id):
            await update.message.reply_text("❌ Sorry, this bot is currently private.")
            return
        
        # Check if it's a Terabox link
        if not self.is_terabox_link(message_text):
            await update.message.reply_text(
                "❌ Please send a valid Terabox link!\n\n"
                "📌 **Example:**\n"
                "• https://terabox.com/s/xxxxxx\n"
                "• https://1024terabox.com/s/xxxxxx\n\n"
                "Use /help for more information.",
                parse_mode='Markdown'
            )
            return
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            "⏳ Processing your link...\n"
            "This may take a few seconds."
        )
        
        try:
            # Extract video information
            video_info = await self.extract_video_info(message_text)
            
            if video_info:
                # Update statistics
                self.update_stats(success=True)
                
                # Edit processing message
                await processing_msg.edit_text("✅ Link processed successfully!")
                
                # Send video details with download buttons
                await self.send_video_details(update, video_info, message_text)
                
            else:
                # Update failed statistics
                self.update_stats(success=False)
                
                await processing_msg.edit_text(
                    "❌ Could not extract video information.\n\n"
                    "Possible reasons:\n"
                    "• Link is expired\n"
                    "• Video is private/removed\n"
                    "• API limit reached\n\n"
                    "Please try again with a different link."
                )
                
        except Exception as e:
            logger.error(f"Error in handle_message: {e}")
            await processing_msg.edit_text(f"⚠️ Error: {str(e)}\n\nPlease try again later.")
    
    async def send_video_details(self, update: Update, video_info: Dict, original_url: str):
        """Send video details with download buttons"""
        try:
            # Extract video information
            title = video_info.get('title', 'Unknown Title')[:100]
            size = video_info.get('size', 'N/A')
            duration = video_info.get('duration', 'N/A')
            thumbnail = video_info.get('thumbnail')
            
            # Create message
            message = f"""
📹 **Video Details:**
┌───────────────
│ 🎬 **Title:** `{title}`
│ 💾 **Size:** `{size}`
│ ⏱️ **Duration:** `{duration}`
└───────────────

**Choose download quality:**
            """
            
            # Create download buttons
            keyboard = []
            download_links = {}
            
            # Extract download links from different possible API responses
            if 'download_links' in video_info:
                download_links = video_info['download_links']
            elif 'direct_link' in video_info:
                download_links = {'direct': video_info['direct_link']}
            elif 'links' in video_info:
                download_links = video_info['links']
            
            # Add download buttons for available qualities
            quality_buttons = []
            for quality, link in download_links.items():
                if link:  # Check if link is not empty
                    quality_text = quality.replace('_', ' ').title()
                    quality_buttons.append(
                        InlineKeyboardButton(f"⬇️ {quality_text}", url=link)
                    )
            
            # Add buttons in rows of 2
            for i in range(0, len(quality_buttons), 2):
                row = quality_buttons[i:i+2]
                keyboard.append(row)
            
            # Add utility buttons
            keyboard.append([
                InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{original_url}"),
                InlineKeyboardButton("📋 New Link", callback_data="new")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send message with thumbnail if available
            if thumbnail:
                try:
                    await update.message.reply_photo(
                        photo=thumbnail,
                        caption=message,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    return
                except:
                    pass  # Fallback to text message
            
            # Send text message without thumbnail
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"Error in send_video_details: {e}")
            await update.message.reply_text("❌ Error displaying video information.")
    
    async def button_callback(self, update: Update, context: CallbackContext):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "help":
            await self.help_command(update, context)
        
        elif data == "example":
            await query.edit_message_text(
                "📌 **Example Terabox Links:**\n\n"
                "• https://terabox.com/s/1AbC2DeF3GhI\n"
                "• https://1024terabox.com/s/1XyZ2AbC3DeF\n"
                "• https://www.terabox.com/s/1QwE2RtY3UiO\n\n"
                "Just copy and paste any Terabox link!",
                parse_mode='Markdown'
            )
        
        elif data == "stats":
            user = query.from_user
            if self.is_admin(user.id):
                stats_text = self.get_admin_stats()
                await query.edit_message_text(stats_text, parse_mode='Markdown')
            else:
                await query.edit_message_text(
                    f"📊 **Your Stats:**\n\n"
                    f"• User ID: `{user.id}`\n"
                    f"• Username: @{user.username or 'N/A'}\n"
                    f"• Last Active: {self.users_data['last_active'].get(str(user.id), 'N/A')}\n\n"
                    f"Total Bot Users: {len(self.users_data['users'])}",
                    parse_mode='Markdown'
                )
        
        elif data == "admin":
            user = query.from_user
            if self.is_admin(user.id):
                keyboard = [
                    [InlineKeyboardButton("📊 Statistics", callback_data="stats")],
                    [InlineKeyboardButton("👥 User List", callback_data="userlist")],
                    [InlineKeyboardButton("🔄 Restart Bot", callback_data="restart")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "👑 **Admin Panel**\n\nSelect an option:",
                    reply_markup=reply_markup
                )
        
        elif data == "userlist":
            user = query.from_user
            if self.is_admin(user.id):
                users_list = "\n".join([f"• @{u['username'] or 'NoUsername'} ({u['id']})" 
                                      for u in self.users_data['users'][:20]])
                await query.edit_message_text(
                    f"👥 **Total Users:** {len(self.users_data['users'])}\n\n"
                    f"{users_list}\n\n"
                    f"Use /stats for more details.",
                    parse_mode='Markdown'
                )
        
        elif data.startswith("refresh_"):
            # Extract original URL
            original_url = data.replace("refresh_", "")
            await query.edit_message_text("🔄 Refreshing download links...")
            
            # Re-extract video info
            video_info = await self.extract_video_info(original_url)
            if video_info:
                await self.send_video_details(update, video_info, original_url)
            else:
                await query.edit_message_text("❌ Failed to refresh. Link may have expired.")
        
        elif data == "new":
            await query.edit_message_text(
                "📥 **Send a new Terabox link:**\n\n"
                "Just paste any Terabox video URL here.",
                parse_mode='Markdown'
            )
        
        elif data == "back":
            await self.start_command(update, context)
    
    def get_admin_stats(self) -> str:
        """Get admin statistics"""
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        return f"""
📊 **ADMIN STATISTICS**

👥 **Users:**
• Total Users: {len(self.users_data['users'])}
• Active Today: {sum(1 for uid, time in self.users_data['last_active'].items() 
                     if time.startswith(today))}
• Active Yesterday: {sum(1 for uid, time in self.users_data['last_active'].items() 
                        if time.startswith(yesterday))}

📈 **Usage:**
• Total Requests: {self.stats['total_requests']}
• Successful: {self.stats['successful_downloads']}
• Failed: {self.stats['failed_downloads']}
• Success Rate: {(self.stats['successful_downloads']/self.stats['total_requests']*100 
                 if self.stats['total_requests'] > 0 else 0):.1f}%

📅 **Today's Requests:** {self.stats['daily_requests'].get(today, 0)}
📅 **Yesterday's Requests:** {self.stats['daily_requests'].get(yesterday, 0)}

🔄 **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
    
    async def stats_command(self, update: Update, context: CallbackContext):
        """Handle /stats command (Admin only)"""
        user = update.effective_user
        
        if not self.is_admin(user.id):
            await update.message.reply_text("❌ This command is for administrators only.")
            return
        
        stats_text = self.get_admin_stats()
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def users_command(self, update: Update, context: CallbackContext):
        """Handle /users command (Admin only)"""
        user = update.effective_user
        
        if not self.is_admin(user.id):
            await update.message.reply_text("❌ This command is for administrators only.")
            return
        
        total_users = len(self.users_data["users"])
        await update.message.reply_text(
            f"👥 **Total Users:** {total_users}\n"
            f"📅 **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode='Markdown'
        )
    
    async def broadcast_command(self, update: Update, context: CallbackContext):
        """Handle /broadcast command (Admin only)"""
        user = update.effective_user
        
        if not self.is_admin(user.id):
            await update.message.reply_text("❌ This command is for administrators only.")
            return
        
        # Check if message text is provided
        if not context.args:
            await update.message.reply_text(
                "Usage: /broadcast <message>\n\n"
                "Example: /broadcast Hello users!"
            )
            return
        
        message = " ".join(context.args)
        total_users = len(self.users_data["users"])
        
        # Confirm broadcast
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Send", callback_data=f"broadcast_yes_{message[:50]}"),
                InlineKeyboardButton("❌ Cancel", callback_data="broadcast_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📢 **Broadcast Confirmation**\n\n"
            f"Message: {message}\n"
            f"To: {total_users} users\n\n"
            f"Are you sure?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def error_handler(self, update: Update, context: CallbackContext):
        """Handle errors"""
        logger.error(f"Error occurred: {context.error}")
        
        try:
            # Send error message to admin
            error_msg = f"❌ Bot Error:\n{context.error}"
            for admin_id in self.config.ADMIN_IDS:
                await context.bot.send_message(chat_id=admin_id, text=error_msg)
        except:
            pass
    
    def run(self):
        """Run the Telegram bot"""
        logger.info("🚀 Starting Terabox Downloader Bot...")
        
        # Check configuration
        if self.config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            logger.error("❌ Please set your BOT_TOKEN in Config class!")
            return
        
        if self.config.RAPIDAPI_KEY == "YOUR_RAPIDAPI_KEY_HERE":
            logger.error("❌ Please set your RAPIDAPI_KEY in Config class!")
            return
        
        # Create downloads directory
        os.makedirs(self.config.DOWNLOAD_PATH, exist_ok=True)
        
        # Create application
        application = Application.builder().token(self.config.BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("users", self.users_command))
        application.add_handler(CommandHandler("broadcast", self.broadcast_command))
        
        # Handle text messages (Terabox links)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Handle button callbacks
        application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Add error handler
        application.add_error_handler(self.error_handler)
        
        # Start bot
        logger.info("✅ Bot is running...")
        logger.info(f"🤖 Bot Username: @{self.config.BOT_USERNAME}")
        logger.info(f"👑 Admin IDs: {self.config.ADMIN_IDS}")
        logger.info(f"📁 Download Path: {self.config.DOWNLOAD_PATH}")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    # Import timedelta for stats
    from datetime import timedelta
    
    print("""
    ╔═══════════════════════════════════════╗
    ║     TERABOX DOWNLOADER BOT v2.0       ║
    ║        Complete All-in-One           ║
    ╚═══════════════════════════════════════╝
    
    📝 Instructions:
    1. Edit Config class at the top of this file
    2. Set your BOT_TOKEN and RAPIDAPI_KEY
    3. Set your ADMIN_ID (your Telegram ID)
    4. Run: python terabox_bot.py
    
    ⚠️  Make sure to install dependencies first:
    pip install python-telegram-bot
    
    """)
    
    # Create and run bot
    bot = TeraboxDownloader()
    bot.run()
