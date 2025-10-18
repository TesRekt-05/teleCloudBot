# bot.py
from database import Database
from config import BOT_TOKEN, DATABASE_NAME
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
import asyncio
import logging


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize database
db = Database(DATABASE_NAME)

# Conversation states
WAITING_FOR_FOLDER_NAME = 1
WAITING_FOR_FILE_FOLDER = 2

# Temporary storage for user states
user_data = {}

# Media group collector (for batch uploads)
media_group_buffer = {}
media_group_tasks = {}

# Configuration
MAX_FILES_TO_SHOW = 20
MEDIA_GROUP_TIMEOUT = 3


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user

    # Add user to database
    db.add_user(user.id, user.username, user.first_name)

    welcome_message = f"""
🌟 <b>Welcome to Cloud Organizer Bot, {user.first_name}!</b> 🌟

I help you organize your files on Telegram with unlimited storage! 📦

<b>Available Commands:</b>
/newfolder - Create a new folder
/myfolders - View all your folders
/gallery - 🎨 Open web gallery
/stats - View your storage statistics
/help - Show this message

<b>How it works:</b>
1️⃣ Create folders to organize your files
2️⃣ Send me any file (photo, video, document, etc.)
3️⃣ Choose which folder to store it in
4️⃣ Access your files anytime!

💡 <b>Pro Tip:</b> Send multiple files at once - I'll ask for destination only once!

Let's get started! 🚀
    """

    await update.message.reply_text(welcome_message, parse_mode='HTML')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await start(update, context)


async def gallery_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    webapp_url = f"https://cloudbotfrontend-qfpig3yyk-tesrekt-05s-projects.vercel.app/?userId={user_id}"
    keyboard = [
        [InlineKeyboardButton(
            "📂 Open Gallery", web_app=WebAppInfo(url=webapp_url))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌟 <b>Open Your Cloud Gallery</b>\n\nClick the button below - opens right inside Telegram!",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    user_id = update.effective_user.id
    stats = db.get_user_stats(user_id)

    stats_message = f"""
📊 <b>Your Storage Statistics</b>

📁 Total Folders: {stats['total_folders']}
📎 Total Files: {stats['total_files']}
💾 Total Size: {stats['total_size_mb']:.2f} MB

🔝 <b>Largest Folders:</b>
{stats['top_folders_text']}

Keep organizing! 🚀
    """

    await update.message.reply_text(stats_message, parse_mode='HTML')


async def newfolder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /newfolder command"""
    await update.message.reply_text(
        "📁 <b>Create New Folder</b>\n\n"
        "Please send me the name for your new folder:",
        parse_mode='HTML'
    )
    return WAITING_FOR_FOLDER_NAME


async def receive_folder_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and create the folder"""
    folder_name = update.message.text.strip()
    user_id = update.effective_user.id

    # Validate folder name
    if len(folder_name) > 50:
        await update.message.reply_text(
            "❌ Folder name is too long! Please use 50 characters or less.",
            parse_mode='HTML'
        )
        return ConversationHandler.END

    if db.create_folder(user_id, folder_name):
        await update.message.reply_text(
            f"✅ Folder <b>'{folder_name}'</b> created successfully!\n\n"
            f"You can now send files and choose this folder to store them.",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"❌ Folder <b>'{folder_name}'</b> already exists!\n\n"
            f"Please choose a different name.",
            parse_mode='HTML'
        )

    return ConversationHandler.END


async def myfolders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /myfolders command"""
    user_id = update.effective_user.id
    folders = db.get_user_folders(user_id)

    if not folders:
        await update.message.reply_text(
            "📂 You don't have any folders yet!\n\n"
            "Use /newfolder to create your first folder."
        )
        return

    # Create inline keyboard with folder buttons
    keyboard = []
    for folder_id, folder_name, created_at, file_count in folders:
        # Show file count in each folder
        button_text = f"📁 {folder_name} ({file_count} files)"
        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"view_folder_{folder_id}"
            ),
            InlineKeyboardButton(
                "🗑️ Delete",
                callback_data=f"confirm_delete_folder_{folder_id}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"📂 <b>Your Folders</b> ({len(folders)} total):\n\n"
        f"Click on any folder to view its contents:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def process_media_group(user_id: int, media_group_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Process collected media group after dynamic timeout"""

    # Wait a bit to collect initial files
    await asyncio.sleep(2)

    # Dynamic timeout: wait longer if more files are being uploaded
    current_count = len(media_group_buffer.get(media_group_id, []))

    # Wait 2 seconds per file (up to max 15 seconds)
    dynamic_timeout = min(current_count * 2, 15)

    for i in range(dynamic_timeout):
        await asyncio.sleep(1)
        new_count = len(media_group_buffer.get(media_group_id, []))

        # If no new files in last 3 seconds, process now
        if new_count == current_count:
            last_stable_count = 0
            for _ in range(3):
                await asyncio.sleep(1)
                if len(media_group_buffer.get(media_group_id, [])) == new_count:
                    last_stable_count += 1
                else:
                    break

            if last_stable_count >= 3:
                break  # No new files for 3 seconds, ready to process

        current_count = new_count

    if media_group_id not in media_group_buffer:
        return

    files = media_group_buffer.pop(media_group_id)

    # Remove task reference
    if media_group_id in media_group_tasks:
        del media_group_tasks[media_group_id]

    # Get user folders
    folders = db.get_user_folders(user_id)

    if not folders:
        # Send message to user
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ You need to create a folder first!\n\n"
                 "Use /newfolder to create one."
        )
        return

    # Create folder selection keyboard
    keyboard = []
    for folder_id, folder_name, _, _ in folders:
        keyboard.append([
            InlineKeyboardButton(
                f"📁 {folder_name}",
                callback_data=f"save_batch_{media_group_id}_{folder_id}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Calculate total size
    total_size = sum(f['file_size'] for f in files)
    if total_size < 1024 * 1024:
        size_str = f"{total_size / 1024:.2f} KB"
    else:
        size_str = f"{total_size / (1024 * 1024):.2f} MB"

    # Store files temporarily with media_group_id as key
    user_data[f"batch_{media_group_id}"] = files

    await context.bot.send_message(
        chat_id=user_id,
        text=f"📦 <b>Batch Upload Detected!</b>\n\n"
        f"📎 Files: {len(files)}\n"
        f"📊 Total Size: {size_str}\n\n"
        f"Choose a folder to save all these files:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming files with media group support"""
    user_id = update.effective_user.id
    message = update.message

    # Extract file info
    file_obj = None
    file_type = None
    file_name = None
    file_size = 0

    if message.document:
        file_obj = message.document
        file_type = "document"
        file_name = file_obj.file_name
        file_size = file_obj.file_size
    elif message.photo:
        file_obj = message.photo[-1]
        file_type = "photo"
        file_name = f"photo_{file_obj.file_unique_id}.jpg"
        file_size = file_obj.file_size
    elif message.video:
        file_obj = message.video
        file_type = "video"
        file_name = file_obj.file_name or f"video_{file_obj.file_unique_id}.mp4"
        file_size = file_obj.file_size
    elif message.audio:
        file_obj = message.audio
        file_type = "audio"
        file_name = file_obj.file_name or f"audio_{file_obj.file_unique_id}.mp3"
        file_size = file_obj.file_size

    if not file_obj:
        return

    file_info = {
        'file_id': file_obj.file_id,
        'file_name': file_name,
        'file_type': file_type,
        'file_size': file_size
    }

    # Check if this is part of a media group
    media_group_id = message.media_group_id

    if media_group_id:
        # Part of a media group - collect files
        if media_group_id not in media_group_buffer:
            media_group_buffer[media_group_id] = []

        media_group_buffer[media_group_id].append(file_info)

        # Cancel existing task if any
        if media_group_id in media_group_tasks:
            media_group_tasks[media_group_id].cancel()

        # Create new task to process after timeout
        task = asyncio.create_task(
            process_media_group(user_id, media_group_id, context)
        )
        media_group_tasks[media_group_id] = task

    else:
        # Single file - handle normally
        folders = db.get_user_folders(user_id)

        if not folders:
            await message.reply_text(
                "❌ You need to create a folder first!\n\n"
                "Use /newfolder to create one."
            )
            return

        # Store file info temporarily
        user_data[user_id] = file_info

        # Create folder selection keyboard
        keyboard = []
        for folder_id, folder_name, _, _ in folders:
            keyboard.append([
                InlineKeyboardButton(
                    f"📁 {folder_name}",
                    callback_data=f"save_to_{folder_id}"
                )
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Format file size
        if file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.2f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.2f} MB"

        await message.reply_text(
            f"📎 <b>File Received:</b> {file_name}\n"
            f"📊 <b>Size:</b> {size_str}\n"
            f"📁 <b>Type:</b> {file_type}\n\n"
            f"Choose a folder to save this file:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # Handle "save single file to folder" callback
    if data.startswith("save_to_"):
        folder_id = int(data.split("_")[-1])

        if user_id not in user_data:
            await query.edit_message_text("❌ File data expired. Please send the file again.")
            return

        file_info = user_data[user_id]

        # Save file to database
        db.add_file(
            folder_id,
            file_info['file_id'],
            file_info['file_name'],
            file_info['file_type'],
            file_info['file_size']
        )

        # Clear temporary data
        del user_data[user_id]

        await query.edit_message_text(
            f"✅ <b>File saved successfully!</b>\n\n"
            f"📎 {file_info['file_name']}\n"
            f"Use /myfolders to view all your files.",
            parse_mode='HTML'
        )

    # Handle "save batch files to folder" callback
    elif data.startswith("save_batch_"):
        parts = data.split("_")
        media_group_id = parts[2]
        folder_id = int(parts[3])

        batch_key = f"batch_{media_group_id}"

        if batch_key not in user_data:
            await query.edit_message_text("❌ File data expired. Please send the files again.")
            return

        files = user_data[batch_key]

        # Save all files to database
        for file_info in files:
            db.add_file(
                folder_id,
                file_info['file_id'],
                file_info['file_name'],
                file_info['file_type'],
                file_info['file_size']
            )

        # Clear temporary data
        del user_data[batch_key]

        await query.edit_message_text(
            f"✅ <b>Batch Upload Complete!</b>\n\n"
            f"📦 Saved {len(files)} files successfully!\n"
            f"Use /myfolders to view all your files.",
            parse_mode='HTML'
        )

    # Handle "view folder" callback
    elif data.startswith("view_folder_"):
        folder_id = int(data.split("_")[-1])
        files = db.get_folder_files(folder_id)

        if not files:
            await query.edit_message_text(
                "📂 This folder is empty!\n\n"
                "Send me files to add them to this folder."
            )
            return

        # PAGINATION: Limit files shown
        total_files = len(files)
        files_to_show = files[:MAX_FILES_TO_SHOW]

        # Update message with progress
        await query.edit_message_text(
            f"📂 <b>Folder Contents</b>\n\n"
            f"📊 Total files: {total_files}\n"
            f"📤 Sending files...",
            parse_mode='HTML'
        )

        # Send files with delete buttons
        sent_count = 0
        failed_count = 0

        for file_db_id, file_id, file_name, file_type, file_size, uploaded_at in files_to_show:
            # Format file size
            if file_size:
                if file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.2f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.2f} MB"
            else:
                size_str = "Unknown"

            caption = f"📎 {file_name}\n📊 {size_str}"

            # Create delete button for each file
            delete_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "🗑️ Delete This File",
                    callback_data=f"delete_file_{file_db_id}"
                )
            ]])

            try:
                if file_type == "photo":
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=file_id,
                        caption=caption,
                        reply_markup=delete_keyboard
                    )
                elif file_type == "video":
                    await context.bot.send_video(
                        chat_id=query.message.chat_id,
                        video=file_id,
                        caption=caption,
                        reply_markup=delete_keyboard
                    )
                elif file_type == "audio":
                    await context.bot.send_audio(
                        chat_id=query.message.chat_id,
                        audio=file_id,
                        caption=caption,
                        reply_markup=delete_keyboard
                    )
                else:  # document
                    await context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=file_id,
                        caption=caption,
                        reply_markup=delete_keyboard
                    )
                sent_count += 1
            except Exception as e:
                logging.error(f"Error sending file {file_name}: {e}")
                failed_count += 1

        # Send summary message
        summary = f"✅ Sent {sent_count} files successfully!"
        if failed_count > 0:
            summary += f"\n⚠️ {failed_count} files failed to send (may have been deleted from Telegram)"
        if total_files > MAX_FILES_TO_SHOW:
            summary += f"\n\n📝 Note: Only showing first {MAX_FILES_TO_SHOW} files out of {total_files} total."

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=summary
        )

    # Handle "delete file" callback
    elif data.startswith("delete_file_"):
        file_db_id = int(data.split("_")[-1])

        # Get file info before deleting
        file_info = db.get_file_info(file_db_id)

        if file_info:
            file_name = file_info[0]

            # Delete from database
            db.delete_file(file_db_id)

            # Update the message to show deleted status
            await query.edit_message_caption(
                caption=f"🗑️ <b>DELETED</b>\n\n"
                f"❌ {file_name}\n"
                f"This file has been removed from your cloud.",
                parse_mode='HTML'
            )

            await query.answer("✅ File deleted successfully!", show_alert=True)
        else:
            await query.answer("❌ File not found!", show_alert=True)

    # Handle "confirm delete folder" callback
    elif data.startswith("confirm_delete_folder_"):
        folder_id = int(data.split("_")[-1])

        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Yes, Delete",
                    callback_data=f"delete_folder_{folder_id}"
                ),
                InlineKeyboardButton(
                    "❌ Cancel",
                    callback_data="cancel_delete"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "⚠️ <b>Delete Folder Confirmation</b>\n\n"
            "Are you sure you want to delete this folder?\n"
            "This will delete ALL files inside it!\n\n"
            "This action cannot be undone.",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    # Handle "delete folder" callback
    elif data.startswith("delete_folder_"):
        folder_id = int(data.split("_")[-1])

        # Delete folder and all its files
        db.delete_folder(folder_id)

        await query.edit_message_text(
            "✅ <b>Folder Deleted!</b>\n\n"
            "The folder and all its files have been removed.\n\n"
            "Use /myfolders to see your remaining folders.",
            parse_mode='HTML'
        )

    # Handle "cancel delete" callback
    elif data == "cancel_delete":
        await query.edit_message_text(
            "❌ Deletion cancelled.\n\n"
            "Use /myfolders to view your folders."
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation"""
    await update.message.reply_text(
        "Operation cancelled. Use /help to see available commands."
    )
    return ConversationHandler.END


def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add conversation handler for creating folders
    folder_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("newfolder", newfolder)],
        states={
            WAITING_FOR_FOLDER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               receive_folder_name)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("gallery", gallery_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(folder_conv_handler)
    application.add_handler(CommandHandler("myfolders", myfolders))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(
        MessageHandler(
            filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO,
            handle_file
        )
    )

    # Start the bot
    print("🤖 Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
