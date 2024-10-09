# check if user in fsub or not
from database.users_chats_db import db
from pyrogram.errors import UserNotParticipant
import asyncio
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import traceback
async def is_user_fsub(bot , message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    fSub = await db.getFsub(chat_id)
    if fSub is None:
        return True
    #now checking if user in fsub chat id or not
    else:
        invite_link = await bot.export_chat_invite_link(chat_id=fSub)
        try:
            #getting chat invite link
            await bot.get_chat_member(fSub , user_id)
            return True
        except UserNotParticipant:
            join_button = InlineKeyboardButton("Join Channel", url=invite_link)
            keyboard = [[join_button]]  # Create a list of lists for the InlineKeyboardMarkup
            if message.from_user:
                k = await message.reply(
                    f"<b>⚠ DEAR USER {message.from_user.mention}!\n\nTO SEND MESSAGES IN THE GROUP, YOU HAVE TO JOIN THIS CHANNEL FIRST 🥶</b>",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                k = await message.reply(
                    "<b>⚠ YOU NEED TO JOIN OUR CHANNEL BEFORE SENDING MESSAGES TO THIS GROUP 🥶</b>",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            await message.delete()
            await asyncio.sleep(40)
            await k.delete()
            return False
        except Exception as e:
            traceback.print_exc()
            print('Err Got in is_user_fsub : ',e)
            return True
