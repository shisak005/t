import os
import json
import logging
import http.client
import time
from urllib.parse import quote, urlparse
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8333576895:AAELRgTBOmWt0SK6SQN46Lmt3lxw75L88xA"
ADMIN_IDS = [1451422178]

# RapidAPI - Check if this is correct
RAPIDAPI_KEY = "fcdef36fbdmshabfa1f6458fba41p1a5020jsnb92890561254"
RAPIDAPI_HOST = "terabox-downloader-direct-download-link-generator1.p.rapidapi.com"

# ==================== END CONFIGURATION ====================

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TeraboxBot:
    def __init__(self):
        self.users_file = "users.json"
        self.load_users()
    
    def load_users(self):
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        else:
            self.users = []
    
    def save_user(self, user_id, username):
        user = {"id": user_id, "username": username, "first_seen": datetime.now().isoformat()}
        
        # Check if user already exists
        for u in self.users:
            if u["id"] == user_id:
                return
        
        self.users.append(user)
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def is_admin(self, user_id):
        return user_id in ADMIN_IDS
    
    def is_terabox_link(self, url):
        """Check if URL is from Terabox"""
        terabox_domains = [
            'terabox.com',
            '1024terabox.com',
            'terabox.app',
            'www.terabox.com'
        ]
        
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc.replace('www.', '')
            return any(tb_domain in domain for tb_domain in terabox_domains)
        except:
            return False
    
    async def get_direct_link(self, terabox_url):
        """Get direct download link from API"""
        try:
            logger.info(f"Getting direct link for: {terabox_url}")
            
            # Prepare the request
            conn = http.client.HTTPSConnection(RAPIDAPI_HOST)
            
            # Try different endpoints
            endpoints = [
                f"/direct-download?url={quote(terabox_url)}",
                f"/download?url={quote(terabox_url)}",
                f"/url?url={quote(terabox_url)}",
                f"/api?url={quote(terabox_url)}"
            ]
            
            headers = {
                'x-rapidapi-key': RAPIDAPI_KEY,
                'x-rapidapi-host': RAPIDAPI_HOST
            }
            
            for endpoint in endpoints:
                try:
                    logger.info(f"Trying endpoint: {endpoint}")
                    conn.request("GET", endpoint, headers=headers)
                    
                    response = conn.getresponse()
                    
                    if response.status == 200:
                        data = response.read().decode('utf-8')
                        result = json.loads(data)
                        
                        logger.info(f"API Response: {result}")
                        
                        # Try to find direct link in response
                        direct_link = None
                        
                        # Check common response formats
                        if isinstance(result, dict):
                            # Check for direct_link, download_link, link, url
                            for key in ['direct_link', 'download_link', 'link', 'url', 'download_url']:
                                if key in result and result[key]:
                                    if isinstance(result[key], str) and result[key].startswith('http'):
                                        direct_link = result[key]
                                        break
                            
                            # Check in data field
                            if not direct_link and 'data' in result and isinstance(result['data'], dict):
                                for key in ['direct_link', 'download_link', 'link', 'url']:
                                    if key in result['data'] and result['data'][key]:
                                        if isinstance(result['data'][key], str) and result['data'][key].startswith('http'):
                                            direct_link = result['data'][key]
                                            break
                        
                        if direct_link:
                            logger.info(f"✅ Found direct link: {direct_link}")
                            return {
                                'direct_link': direct_link,
                                'title': result.get('title', 'Download'),
                                'size': result.get('size', 'Unknown')
                            }
                
                except Exception as e:
                    logger.warning(f"Endpoint {endpoint} failed: {e}")
                    continue
            
            logger.error("❌ No direct link found")
            return None
            
        except Exception as e:
            logger.error(f"Error getting direct link: {e}")
            return None
    
    async def start(self, update: Update, context: CallbackContext):
        """Handle /start command"""
        user = update.effective_user
        self.save_user(user.id, user.username or "")
        
        welcome_text = """
🤖 *Terabox Direct Download Bot*

*How to use:*
1. Send any Terabox link
2. Get direct download link
3. Click to download

*Supported domains:*
• terabox.com
• 1024terabox.com  
• terabox.app

*Example links:*
• https://terabox.com/s/xxxxxx
• https://1024terabox.com/s/xxxxxx

Send me a Terabox link now! 🚀
"""
        
        keyboard = [
            [InlineKeyboardButton("📖 Help", callback_data="help")],
            [InlineKeyboardButton("🔗 Examples", callback_data="examples")]
        ]
        
        if self.is_admin(user.id):
            keyboard.append([InlineKeyboardButton("👑 Admin", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def help(self, update: Update, context: CallbackContext):
        """Handle /help command"""
        help_text = """
*Terabox Download Bot Help*

*Commands:*
/start - Start the bot
/help - Show this help

*How to download:*
1. Copy Terabox link
2. Send to bot
3. Get download button
4. Click to download

*Note:*
• Links must be from terabox.com, 1024terabox.com, or terabox.app
• Some videos may not be downloadable
• Maximum file size: 2GB
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: CallbackContext):
        """Handle text messages with Terabox links"""
        user = update.effective_user
        text = update.message.text.strip()
        
        # Save user
        self.save_user(user.id, user.username or "")
        
        # Check if it's a Terabox link
        if not self.is_terabox_link(text):
            await update.message.reply_text(
                "❌ *Please send a valid Terabox link!*\n\n"
                "*Valid examples:*\n"
                "• `https://terabox.com/s/xxxxxx`\n"
                "• `https://1024terabox.com/s/xxxxxx`\n"
                "• `https://terabox.app/s/xxxxxx`\n\n"
                "Make sure the link starts with https://",
                parse_mode='Markdown'
            )
            return
        
        # Show processing message
        msg = await update.message.reply_text("⏳ *Processing your link...*", parse_mode='Markdown')
        
        try:
            # Get direct download link
            result = await self.get_direct_link(text)
            
            if result and 'direct_link' in result:
                # Success - show download button
                await msg.edit_text("✅ *Link processed successfully!*", parse_mode='Markdown')
                
                # Create download message
                download_text = f"""
📥 *Download Ready*

*Title:* {result.get('title', 'File')}
*Size:* {result.get('size', 'Unknown')}

Click below to download:
"""
                
                keyboard = [
                    [InlineKeyboardButton("⬇️ Download Now", url=result['direct_link'])],
                    [InlineKeyboardButton("🔄 Try Another", callback_data="new")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    download_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
            else:
                # Failed
                await msg.edit_text(
                    "❌ *Failed to get download link*\n\n"
                    "*Possible reasons:*\n"
                    "• Link expired or invalid\n"
                    "• Video is private/removed\n"
                    "• File too large (>2GB)\n"
                    "• API temporary issue\n\n"
                    "*Try:*\n"
                    "1. Check link is correct\n"
                    "2. Try different link\n"
                    "3. Wait few minutes",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error processing link: {e}")
            await msg.edit_text(
                "⚠️ *Error processing link*\n\n"
                "Please try again with a different link.",
                parse_mode='Markdown'
            )
    
    async def button_handler(self, update: Update, context: CallbackContext):
        """Handle button callbacks"""
        query = update.callback_query
        
        # Always answer callback first to prevent timeout
        await query.answer()
        
        data = query.data
        
        if data == "help":
            await self.help(update, context)
        
        elif data == "examples":
            examples = """
*Example Terabox Links:*

*Format 1:*
`https://terabox.com/s/1LQyTj3pGxYzABC123`

*Format 2:*
`https://1024terabox.com/s/1XYZ123ABC456`

*Format 3:*
`https://terabox.app/s/1ABCDEFG1234567`

*How to get link:*
1. Open Terabox app/website
2. Find video/file
3. Click Share button
4. Copy the link
5. Send to this bot
"""
            await query.message.reply_text(examples, parse_mode='Markdown')
        
        elif data == "admin":
            user = query.from_user
            if self.is_admin(user.id):
                keyboard = [
                    [InlineKeyboardButton("📊 Stats", callback_data="stats")],
                    [InlineKeyboardButton("👥 Users", callback_data="users")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text(
                    "*Admin Panel*\nSelect option:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        
        elif data == "stats":
            user = query.from_user
            if self.is_admin(user.id):
                stats_text = f"""
*Bot Statistics*

*Total Users:* {len(self.users)}
*Today's Date:* {datetime.now().strftime('%Y-%m-%d')}
*Bot Status:* ✅ Running
"""
                await query.message.reply_text(stats_text, parse_mode='Markdown')
        
        elif data == "users":
            user = query.from_user
            if self.is_admin(user.id):
                if self.users:
                    users_list = "\n".join([f"• @{u['username'] or 'NoUsername'}" for u in self.users[-10:]])
                    await query.message.reply_text(
                        f"*Recent Users ({len(self.users)} total):*\n\n{users_list}",
                        parse_mode='Markdown'
                    )
                else:
                    await query.message.reply_text("*No users yet*", parse_mode='Markdown')
        
        elif data == "new":
            await query.message.reply_text(
                "🆕 *Send new Terabox link:*\n\n"
                "Paste your link below:",
                parse_mode='Markdown'
            )
        
        elif data == "back":
            # Go back to start
            await self.start(update, context)
    
    async def error_handler(self, update: Update, context: CallbackContext):
        """Handle errors"""
        logger.error(f"Error: {context.error}")
        
        # Don't show error to user, just log it
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ An error occurred. Please try again.",
                    parse_mode='Markdown'
                )
            except:
                pass
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Terabox Bot...")
        
        # Check config
        if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            logger.error("Please set BOT_TOKEN!")
            return
        
        # Create app
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(CallbackQueryHandler(self.button_handler))
        app.add_error_handler(self.error_handler)
        
        # Start
        logger.info("Bot started!")
        app.run_polling()

if __name__ == "__main__":
    print("""
╔══════════════════════════╗
║   Terabox Download Bot   ║
╚══════════════════════════╝
    
Starting bot...
    """)
    
    bot = TeraboxBot()
    bot.run()
