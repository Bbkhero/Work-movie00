import os, requests
import logging
import random
import asyncio
import string
import pytz
from datetime import timedelta
from datetime import datetime as dt
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup , ForceReply
from database.ia_filterdb import Media, get_file_details, get_bad_files, unpack_new_file_id
from database.users_chats_db import db
from utils import formate_file_name,  get_settings, save_group_settings, is_req_subscribed, get_size, get_shortlink, is_check_admin, get_status, temp, get_readable_time
import re
import base64
from info import *
import traceback
logger = logging.getLogger(__name__)
# CHECK COMPONENTS FOLDER FOR MORE COMMANDS
@Client.on_message(filters.command("invite") & filters.private & filters.user(ADMINS))
async def invite(client, message):
    toGenInvLink = message.command[1]
    if len(toGenInvLink) != 14:
        return await message.reply("Invalid chat id\nAdd -100 before chat id if You did not add any yet.") 
    try:
        link = await client.export_chat_invite_link(toGenInvLink)
        await message.reply(link)
    except Exception as e:
        print(f'Error while generating invite link : {e}\nFor chat:{toGenInvLink}')
        await message.reply(f'Error while generating invite link : {e}\nFor chat:{toGenInvLink}')

def detect_language(text):
    try:
        data = {"text": text} 
        response = requests.post("https://bisal-ai-api.vercel.app/lang", data=data)
        return response.text
    except Exception as e:
        return "hi"

@Client.on_message(filters.command("tts") & filters.private)
async def tts(client, message):
    try:
        msg = await client.ask(message.chat.id, "<b>Semd Me Some Text To Convert Into Audio Files.</b>" , reply_to_message_id = message.id, filters = filters.text ,
                               reply_markup =ForceReply(True))
        if not msg.text:
            return await message.reply("Send Me Some Text To Convert Into Audio After Giving/tts Command")
        m = await message.reply("<b>Converting...</b>")
        toConvert = msg.text.replace("\n", " ").replace("`", "")
        lang = detect_language(toConvert)
        if lang == 'en' or lang == 'hi':
            voice = "en-US-JennyNeural" if lang == 'en' else "hi-IN-SwaraNeural"
            command = f'edge-tts --voice \"{voice}\" --text \"{toConvert}\" --write-media \"tts.mp3\"'
            os.system(command)
        else:
            voice = "hi-IN-SwaraNeural"
            command = f'edge-tts --voice \"{voice}\" --text \"{toConvert}\" --write-media \"tts.mp3\"'
            os.system(command)
        await m.delete()
        await message.reply_voice("tts.mp3")
        os.remove("tts.mp3")
    except Exception as e:
        await m.edit('<b>Something Went Wrong! Please Use Another Text \nOr Report In Support Group: https://t.me/+EHl6mMfmjHdhZTE9</b>')
        print('err in tts',e)
        try:
            os.remove("tts.mp3")
        except:pass
@Client.on_message(filters.command("start") & filters.incoming)
async def start(client:Client, message): 
    pm_mode = False
    try:
         data = message.command[1]
         if data.startswith('pm_mode_'):
             pm_mode = True
    except:
        pass
    m = message
    user_id = m.from_user.id
    if len(m.command) == 2 and m.command[1].startswith('notcopy'):
        _, userid, verify_id, file_id = m.command[1].split("_", 3)
        user_id = int(userid)
        grp_id = temp.CHAT.get(user_id, 0)
        settings = await get_settings(grp_id)         
        verify_id_info = await db.get_verify_id_info(user_id, verify_id)
        if not verify_id_info or verify_id_info["verified"]:
            await message.reply("<b>Link Expired Try Again...</b>")
            return  
        ist_timezone = pytz.timezone('Asia/Kolkata')
        if await db.user_verified(user_id):
            key = "third_time_verified"
        else:
            key = "second_time_verified" if await db.is_user_verified(user_id) else "last_verified"
        current_time = dt.now(tz=ist_timezone)
        result = await db.update_notcopy_user(user_id, {key:current_time})
        await db.update_verify_id_info(user_id, verify_id, {"verified":True})
        if key == "third_time_verified": 
            num = 3 
        else: 
            num =  2 if key == "second_time_verified" else 1 
        if key == "third_time_verified":
            msg = script.THIRDT_VERIFY_COMPLETE_TEXT
        else:
            msg = script.SECOND_VERIFY_COMPLETE_TEXT if key == "second_time_verified" else script.VERIFY_COMPLETE_TEXT
        await client.send_message(settings['log'], script.VERIFIED_LOG_TEXT.format(m.from_user.mention, user_id, dt.now(pytz.timezone('Asia/Kolkata')).strftime('%d %B %Y'), num))
        btn = [[
            InlineKeyboardButton("‼️ Click Here To Get File‼️", url=f"https://telegram.me/{temp.U_NAME}?start=file_{grp_id}_{file_id}"),
        ]]
        reply_markup=InlineKeyboardMarkup(btn)
        await m.reply_photo(
            photo=(VERIFY_IMG),
            caption=msg.format(message.from_user.mention, get_readable_time(TWO_VERIFY_GAP)),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return 
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        status = get_status()
        aks=await message.reply_text(f"<b>Yes {status},\nHow Can I Help You??</b>")
        await asyncio.sleep(600)
        await aks.delete()
        await m.delete()
        if (str(message.chat.id)).startswith("-100") and not await db.get_chat(message.chat.id):
            total=await client.get_chat_members_count(message.chat.id)
            group_link = await message.chat.export_invite_link()
            user = message.from_user.mention if message.from_user else "Dear" 
            await client.send_message(LOG_CHANNEL, script.NEW_GROUP_TXT.format(temp.B_LINK, message.chat.title, message.chat.id, message.chat.username, group_link, total, user))       
            await db.add_chat(message.chat.id, message.chat.title)
        return 
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.NEW_USER_TXT.format(temp.B_LINK, message.from_user.id, message.from_user.mention))
        try: 
            refData = message.command[1]
            if refData and refData.split("-", 1)[0] == "biisal":
                Fullref = refData.split("-", 1)
                refUserId = int(Fullref[1])
                await db.update_point(refUserId)
                newPoint = await db.get_point(refUserId)
                if AUTH_CHANNEL and await is_req_subscribed(client, message):
                        buttons = [[
                            InlineKeyboardButton('Add Me In You Group, url=f'http://t.me/{temp.U_NAME}?startgroup='start')
                            ],[
                            InlineKeyboardButton('Features', callback_data='features'),
                            InlineKeyboardButton('Buy Premium', callback_data='premium'),
                            ],
                            [
                            InlineKeyboardButton('Get Free Premium', callback_data=f'free_premium#{message.from_user.id}')
                            ],
                            [
                            InlineKeyboardButton('Your Points', callback_data=f'point#{message.from_user.id}'),
                            InlineKeyboardButton('About', callback_data='about')
                            ],
                            [
                            InlineKeyboardButton('Earn Money With Bot', callback_data='earn')
                            ]]
                        reply_markup = InlineKeyboardMarkup(buttons)
                        await message.reply_photo(photo=START_IMG, caption=script.START_TXT.format(message.from_user.mention, get_status(), message.from_user.id),
                            reply_markup=reply_markup,
                            parse_mode=enums.ParseMode.HTML)
                try: 
                    if newPoint == 0:
                        await client.send_message(refUserId , script.REF_PREMEUM.format(PREMIUM_POINT))
                    else: 
                        await client.send_message(refUserId , script.REF_START.format(message.from_user.mention() , newPoint))
                except : pass
        except Exception as e:
            traceback.print_exc()
            pass
    if len(message.command) != 2:
        buttons = [[
            InlineKeyboardButton('Add Me In Your Group', url=f'http://t.me/{temp.U_NAME}?startgroup=start')
        ],[
            InlineKeyboardButton('Features', callback_data='features'),
            InlineKeyboardButton('Buy Premium', callback_data='premium'),
        ],
        [
            InlineKeyboardButton('Get Free Premium', callback_data=f'free_premium#{message.from_user.id}')
        ],
        [
            InlineKeyboardButton('Your Points ', callback_data=f'point#{message.from_user.id}'),
            InlineKeyboardButton('About', callback_data='about')
        ],
        [
            InlineKeyboardButton('Earn Money With Bot', callback_data='earn')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(photo=START_IMG, caption=script.START_TXT.format(message.from_user.mention, get_status(), message.from_user.id),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return
    if AUTH_CHANNEL and not await is_req_subscribed(client, message):
        try:
            invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL), creates_join_request=True)
        except ChatAdminRequired:
            logger.error("Make Sure Bot Is Admin In Forcesub Channel")
            return
        btn = [[
            InlineKeyboardButton("Join Now", url=invite_link.invite_link)
        ]]

        if message.command[1] != "subscribe":
            
            try:
                chksub_data = message.command[1].replace('pm_mode_', '') if pm_mode else message.command[1]
                kk, grp_id, file_id = chksub_data.split('_', 2)
                pre = 'checksubp' if kk == 'filep' else 'checksub'
                btn.append(
                    [InlineKeyboardButton("Try Again", callback_data=f"checksub#{file_id}#{int(grp_id)}")]
                )
            except (IndexError, ValueError):
                print('IndexError: ', IndexError)
                btn.append(
                    [InlineKeyboardButton("Try Again", url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}")]
                )
        await client.send_message(
            chat_id=message.from_user.id,
            text="<b>First Join Our Backup Channel Then You Will Get Movie, Otherwise You Will Not Get It.\n\nClick Join Button</b>",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.HTML
        )
        return

    if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help"]:
        buttons = [[
            InlineKeyboardButton('Add Me In You Groups', url=f'http://t.me/{temp.U_NAME}?startgroup=start')
        ],[
            InlineKeyboardButton('Features', callback_data='features'),
            InlineKeyboardButton('Buy Premium', callback_data='premium'),
        ],
        [
            InlineKeyboardButton('Get Free Premium', callback_data=f'free_premium#{message.from_user.id}')
        ],
        [
            InlineKeyboardButton('You Points ', callback_data=f'point#{message.from_user.id}'),
            InlineKeyboardButton('About', callback_data='about')
        ],
        [
            InlineKeyboardButton('Earn Money With Bot', callback_data='earn')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        return await message.reply_photo(photo=START_IMG, caption=script.START_TXT.format(message.from_user.mention, get_status(), message.from_user.id),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        
    if data.startswith('pm_mode_'):
        pm_mode = True
        data = data.replace('pm_mode_', '')
    try:
        pre, grp_id, file_id = data.split('_', 2)
    except:
        pre, grp_id, file_id = "", 0, data

    user_id = m.from_user.id
    if not await db.has_premium_access(user_id):
        grp_id = int(grp_id)
        user_verified = await db.is_user_verified(user_id)
        settings = await get_settings(grp_id , pm_mode=pm_mode)
        is_second_shortener = await db.use_second_shortener(user_id, settings.get('verify_time', TWO_VERIFY_GAP)) 
        is_third_shortener = await db.use_third_shortener(user_id, settings.get('third_verify_time', THREE_VERIFY_GAP))
        if settings.get("is_verify", IS_VERIFY) and not user_verified or is_second_shortener or is_third_shortener:
            verify_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
            await db.create_verify_id(user_id, verify_id)
            temp.CHAT[user_id] = grp_id
            verify = await get_shortlink(f"https://telegram.me/{temp.U_NAME}?start=notcopy_{user_id}_{verify_id}_{file_id}", grp_id, is_second_shortener, is_third_shortener , pm_mode=pm_mode)
            buttons = [[
                InlineKeyboardButton(text="Verify", url=verify)
            ],[
                InlineKeyboardButton(text="How To Verify", url=settings['tutorial']),
            ]]
            reply_markup=InlineKeyboardMarkup(buttons)
            if await db.user_verified(user_id): 
                msg = script.THIRDT_VERIFICATION_TEXT
            else:            
                msg = script.SECOND_VERIFICATION_TEXT if is_second_shortener else script.VERIFICATION_TEXT
            d = await m.reply_text(
                text=msg.format(message.from_user.mention, get_status()),
                protect_content = False,
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            await asyncio.sleep(300) 
            await d.delete()
            await m.delete()
            return
            
    if data and data.startswith("allfiles"):
        _, key = data.split("_", 1)
        files = temp.FILES_ID.get(key)
        if not files:
            await message.reply_text("<b>All Files Not Found</b>")
            return
        files_to_delete = []
        for file in files:
            user_id = message.from_user.id 
            grp_id = temp.CHAT.get(user_id)
            settings = await get_settings(grp_id, pm_mode=pm_mode)
            CAPTION = settings['caption']
            f_caption = CAPTION.format(
                file_name=formate_file_name(file.file_name),
                file_size=get_size(file.file_size),
                file_caption=file.caption
            )
            btn = [[
                InlineKeyboardButton("Wath & Download", callback_data=f'stream#{file.file_id}')
            ]]
            toDel = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file.file_id,
                caption=f_caption,
                reply_markup=InlineKeyboardMarkup(btn)
            )
            files_to_delete.append(toDel)

        delCap = "<b>All {} Files Will Be Deleted {} To Avoid Copyright Violation!</b>".format(len(files_to_delete), f'{FILE_AUTO_DEL_TIMER / 60} Minutes' if FILE_AUTO_DEL_TIMER >= 60 else f'{FILE_AUTO_DEL_TIMER} Seconds')
        afterDelCap = "<b>All {} Files Are Deleted After {} To Avoid Copyright Violation!</b>".format(len(files_to_delete), f'{FILE_AUTO_DEL_TIMER / 60} Minutes' if FILE_AUTO_DEL_TIMER >= 60 else f'{FILE_AUTO_DEL_TIMER} Secons')
        replyed = await message.reply(
            delCap
        )
        await asyncio.sleep(FILE_AUTO_DEL_TIMER)
        for file in files_to_delete:
            try:
                await file.delete()
            except:
                pass
        return await replyed.edit(
            afterDelCap,
        )
    if not data:
        return

    files_ = await get_file_details(file_id)           
    if not files_:
        pre, file_id = ((base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")).split("_", 1)
        return await message.reply('<b>All Files Not Found</b>')
    files = files_[0]
    settings = await get_settings(grp_id , pm_mode=pm_mode)
    CAPTION = settings['caption']
    f_caption = CAPTION.format(
        file_name = formate_file_name(files.file_name),
        file_size = get_size(files.file_size),
        file_caption=files.caption
    )
    btn = [[
        InlineKeyboardButton("Watch & Download", callback_data=f'stream#{file_id}')
    ]]
    toDel=await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        reply_markup=InlineKeyboardMarkup(btn)
    )
    delCap = "<b>Your File Will Be Deleted After {} Kindly Forward This File In Saved Messages!</b>".format(f'{FILE_AUTO_DEL_TIMER / 60} Minutes' if FILE_AUTO_DEL_TIMER >= 60 else f'{FILE_AUTO_DEL_TIMER} Seconds')
    afterDelCap = "<b>Youre File Is Deleted After {} To Avoid Copyright Violation !</b>".format(f'{FILE_AUTO_DEL_TIMER / 60} Minutes' if FILE_AUTO_DEL_TIMER >= 60 else f'{FILE_AUTO_DEL_TIMER} Seconds') 
    replyed = await message.reply(
        delCap,
        reply_to_message_id= toDel.id)
    await asyncio.sleep(FILE_AUTO_DEL_TIMER)
    await toDel.delete()
    return await replyed.edit(afterDelCap)

@Client.on_message(filters.command('delete'))
async def delete(bot, message):
    if message.from_user.id not in ADMINS:
        await message.reply('Only The Bot Can Use This Command... ')
        return
    """Delete file from database"""
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply("Precessing...", quote=True)
    else:
        await message.reply('Reply to file with /delete which you want to delete', quote=True)
        return
    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit('<b>This Is Not Supported File Format</b>')
        return
    
    file_id, file_ref = unpack_new_file_id(media.file_id)
    result = await Media.collection.delete_one({
        '_id': file_id,
    })
    if result.deleted_count:
        await msg.edit('<b>File Ise Successfully Deleted From Database</b>')
    else:
        file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
        result = await Media.collection.delete_many({
            'file_name': file_name,
            'file_size': media.file_size,
            'mime_type': media.mime_type
            })
        if result.deleted_count:
            await msg.edit('<b>File Is Successfully Deleted From Database</b>')
        else:
            result = await Media.collection.delete_many({
                'file_name': media.file_name,
                'file_size': media.file_size,
                'mime_type': media.mime_type
            })
            if result.deleted_count:
                await msg.edit('<b>File Is Successfully Deleted From Database</b>')
            else:
                await msg.edit('<b>File Is Not Found In Database</b>')

@Client.on_message(filters.command('deleteall'))
async def delete_all_index(bot, message):
    files = await Media.count_documents()
    if int(files) == 0:
        return await message.reply_text('Not have files to delete')
    btn = [[
            InlineKeyboardButton(text="Yes", callback_data="all_files_delete")
        ],[
            InlineKeyboardButton(text="Cancel", callback_data="close_data")
        ]]
    if message.from_user.id not in ADMINS:
        await message.reply('Only Bot Owner Can Use This Command... ')
        return
    await message.reply_text('<b>This Will Delete All Index File.\nDo You Want To Contenue??</b>', reply_markup=InlineKeyboardMarkup(btn))

@Client.on_message(filters.command('settings'))
async def settings(client, message):
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return await message.reply("<b>You Are Anonymous Admin You Can't Use This Command...</b>")
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<code>.</code>")
    grp_id = message.chat.id
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>You Are Not Admin In This Group</b>')
    settings = await get_settings(grp_id)
    title = message.chat.title
    if settings is not None:
            buttons = [[
                InlineKeyboardButton('Auto Filter', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}'),
                InlineKeyboardButton('On' if settings["auto_filter"] else 'Off ✗', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}')
            ],[
                InlineKeyboardButton('Imdb', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}'),
                InlineKeyboardButton('On' if settings["imdb"] else 'Off ✗', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}')
            ],[
                InlineKeyboardButton('Spell Check ', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}'),
                InlineKeyboardButton('On' if settings["spell_check"] else 'Off ✗', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}')
            ],[
                InlineKeyboardButton('Auto delete', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}'),
                InlineKeyboardButton(f'{get_readable_time(DELETE_TIME)}' if settings["auto_delete"] else 'Off ✗', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}')
            ],[
                InlineKeyboardButton('Result Mode', callback_data=f'setgs#link#{settings["link"]}#{str(grp_id)}'),
                InlineKeyboardButton('Link' if settings["link"] else 'Button', callback_data=f'setgs#link#{settings["link"]}#{str(grp_id)}')
            ],[
                InlineKeyboardButton('Verify', callback_data=f'setgs#is_verify#{settings["is_verify"]}#{grp_id}'),
                InlineKeyboardButton('On' if settings["is_verify"] else 'Off ✗', callback_data=f'setgs#is_verify#{settings["is_verify"]}#{grp_id}')
            ],[
                InlineKeyboardButton('Close', callback_data='close_data')
            ]]
            await message.reply_text(
                text=f"Change Your Setting For <b>'{title}'</b> As Your Wish",
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
    else:
        await message.reply_text('<b>Somthing Went Wrong </b>')

@Client.on_message(filters.command('set_template'))
async def save_template(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>Use Thi Command In Group...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>You Are Not Admin In This Group</b>')
    try:
        template = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("Command Incomplete!")    
    await save_group_settings(grp_id, 'template', template)
    await message.reply_text(f"Successfully changed template for {title} to\n\n{template}", disable_web_page_preview=True)
    
@Client.on_message(filters.command("send"))
async def send_msg(bot, message):
    if message.from_user.id not in ADMINS:
        await message.reply('<b>Only Bot Owner Can Use This Command...</b>')
        return
    if message.reply_to_message:
        target_ids = message.text.split(" ")[1:]
        if not target_ids:
            await message.reply_text("<b>Please Provide One Or More User Ids As A Space ...</b>")
            return
        out = "\n\n"
        success_count = 0
        try:
            users = await db.get_all_users()
            for target_id in target_ids:
                try:
                    user = await bot.get_users(target_id)
                    out += f"{user.id}\n"
                    await message.reply_to_message.copy(int(user.id))
                    success_count += 1
                except Exception as e:
                    out += f"‼️ Error In This Id - <code>{target_id}</code> <code>{str(e)}</code>\n"
            await message.reply_text(f"<b> Successfully Message Sent In`{success_count}` Id\n<code>{out}</code></b>")
        except Exception as e:
            await message.reply_text(f"<b>‼️ Error - <code>{e}</code></b>")
    else:
        await message.reply_text("<b>Ise This Command As A Repy To Any Message ,For Eg- <code>/send userid1 userid2</code></b>")

@Client.on_message(filters.regex("#request"))
async def send_request(bot, message):
    try:
        request = message.text.split(" ", 1)[1]
    except:
        await message.reply_text("<b>‼️ Your Request Is Incomplete</b>")
        return
    buttons = [[
        InlineKeyboardButton('Biew Request', url=f"{message.link}")
    ],[
        InlineKeyboardButton('Show Option', callback_data=f'show_options#{message.from_user.id}#{message.id}')
    ]]
    sent_request = await bot.send_message(REQUEST_CHANNEL, script.REQUEST_TXT.format(message.from_user.mention, message.from_user.id, request), reply_markup=InlineKeyboardMarkup(buttons))
    btn = [[
         InlineKeyboardButton('View Your Request', url=f"{sent_request.link}")
    ]]
    await message.reply_text("<b>Successfully Request Has Been Added , Please Wait Sometime...</b>", reply_markup=InlineKeyboardMarkup(btn))

@Client.on_message(filters.command("search"))
async def search_files(bot, message):
    if message.from_user.id not in ADMINS:
        await message.reply('Only the bot owner can use this command... 😑')
        return
    chat_type = message.chat.type
    if chat_type != enums.ChatType.PRIVATE:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, this command won't work in groups. It only works in my PM!</b>")  
    try:
        keyword = message.text.split(" ", 1)[1]
    except IndexError:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, give me a keyword along with the command to delete files.</b>")
    files, total = await get_bad_files(keyword)
    if int(total) == 0:
        await message.reply_text('<i>I could not find any files with this keyword </i>')
        return 
    file_names = "\n\n".join(f"{index + 1}. {item['file_name']}" for index, item in enumerate(files))
    file_data = f" Your search - '{keyword}':\n\n{file_names}"    
    with open("file_names.txt", "w" , encoding='utf-8') as file:
        file.write(file_data)
    await message.reply_document(
        document="file_names.txt",
        caption=f"<b>By Your Search, I Found - <code>{total}</code> Files</b>",
        parse_mode=enums.ParseMode.HTML
    )
    os.remove("file_names.txt")

@Client.on_message(filters.command("deletefiles"))
async def deletemultiplefiles(bot, message):
    if message.from_user.id not in ADMINS:
        await message.reply('Only The Bot Owner Can Use This Command... ')
        return
    chat_type = message.chat.type
    if chat_type != enums.ChatType.PRIVATE:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, This Command Wont Work In Group. It Only Work On Pm !!</b>")
    else:
        pass
    try:
        keyword = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, Give Me A Keyword Along With The Command To Delete Files.</b>")
    files, total = await get_bad_files(keyword)
    if int(total) == 0:
        await message.reply_text('<i>I Could Not Find Any Files With This Keywords</i>')
        return 
    btn = [[
       InlineKeyboardButton("Yes, Continue", callback_data=f"killfilesak#{keyword}")
       ],[
       InlineKeyboardButton("No, Abort Operation", callback_data="close_data")
    ]]
    await message.reply_text(
        text=f"<b>Total Files Found - <code>{total}</code>\n\nDo You Want To Continue?\n\nNote:- This Could Be A Destructive Action!!</b>",
        reply_markup=InlineKeyboardMarkup(btn),
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_message(filters.command("del_file"))
async def delete_files(bot, message):
    if message.from_user.id not in ADMINS:
        await message.reply('Only the bot owner can use this command... ')
        return
    chat_type = message.chat.type
    if chat_type != enums.ChatType.PRIVATE:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, this command won't work in groups. It only works on my PM!</b>")    
    try:
        keywords = message.text.split(" ", 1)[1].split(",")
    except IndexError:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, give me keywords separated by commas along with the command to delete files.</b>")   
    deleted_files_count = 0
    not_found_files = []
    for keyword in keywords:
        result = await Media.collection.delete_many({'file_name': keyword.strip()})
        if result.deleted_count:
            deleted_files_count += 1
        else:
            not_found_files.append(keyword.strip())
    if deleted_files_count > 0:
        await message.reply_text(f'<b>{deleted_files_count} file successfully deleted from the database </b>')
    if not_found_files:
        await message.reply_text(f'<b>Files not found in the database - <code>{", ".join(not_found_files)}</code></b>')

@Client.on_message(filters.command('set_caption'))
async def save_caption(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>You Are Not Admin In This Group</b>')
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>Use This Command In Group...</b>")
    try:
        caption = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("Command Incomplete!")
    await save_group_settings(grp_id, 'caption', caption)
    await message.reply_text(f"Successfully changed caption for {title} to\n\n{caption}", disable_web_page_preview=True) 
    
@Client.on_message(filters.command('set_tutorial'))
async def save_tutorial(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>Use This Command In Group...</b>")
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>You Are Not Admin In This Group</b>')
    try:
        tutorial = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("<b>Command Incomplete!!\n\nuse like this -</b>\n\n<code>/set_caption https://t.me/HD_Movies_Group_2024</code>")    
    await save_group_settings(grp_id, 'tutorial', tutorial)
    await message.reply_text(f"<b>Successfully changed tutorial for {title} to</b>\n\n{tutorial}", disable_web_page_preview=True)
    
@Client.on_message(filters.command('set_shortner'))
async def set_shortner(c, m):
    grp_id = m.chat.id
    chat_type = m.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await m.reply_text("<b>Use This Command In Group...</b>")
    if not await is_check_admin(c, grp_id, m.from_user.id):
        return await m.reply_text('<b>You Are Not Admin In This Group</b>')        
    if len(m.text.split()) == 1:
        await m.reply("<b>Use this command like this - \n\n`/set_shortner tnshort.net 06b24eb6bbb025713cd522fb3f696b6d5de11354`</b>")
        return        
    sts = await m.reply("<b>Checking...</b>")
    await asyncio.sleep(1.2)
    await sts.delete()
    try:
        URL = m.command[1]
        API = m.command[2]
        resp = requests.get(f'https://{URL}/api?api={API}&url=https://telegram.dog/HD_Movies_Group_2024').json()
        if resp['status'] == 'success':
            SHORT_LINK = resp['shortenedUrl']
        await save_group_settings(grp_id, 'shortner', URL)
        await save_group_settings(grp_id, 'api', API)
        await m.reply_text(f"<b><u>Successfully Your Shortener Is Added</u>\n\nDemo - {SHORT_LINK}\n\nSite - `{URL}`\n\nApi - `{API}`</b>", quote=True)
        user_id = m.from_user.id
        user_info = f"@{m.from_user.username}" if m.from_user.username else f"{m.from_user.mention}"
        link = (await c.get_chat(m.chat.id)).invite_link
        grp_link = f"[{m.chat.title}]({link})"
        log_message = f"#New_Shortner_Set_For_1st_Verify\n\nName - {user_info}\nId - `{user_id}`\n\nDomain name - {URL}\nApi - `{API}`\nGroup link - {grp_link}"
        await c.send_message(LOG_API_CHANNEL, log_message, disable_web_page_preview=True)
    except Exception as e:
        await save_group_settings(grp_id, 'shortner', SHORTENER_WEBSITE)
        await save_group_settings(grp_id, 'api', SHORTENER_API)
        await m.reply_text(f"<b><u>Error Occurred!!</u>\n\nAuto Added Bot Owner Default Shortner\n\nIf You Want Change Then Use correct Format Or Add Valid Shortlink Domain Name& Api\n\nYou Can Also Contact Our<a href=https://t.me/+EHl6mMfmjHdhZTE9>Support Group</a> For Solve This Issue...\n\nLike -\n\n`/set_shortner mdiskshortner.link e7beb3c8f756dfa15d0bec495abc65f58c0dfa95`\n\nError - <code>{e}</code></b>", quote=True)

@Client.on_message(filters.command('set_shortner_2'))
async def set_shortner_2(c, m):
    grp_id = m.chat.id
    chat_type = m.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await m.reply_text("<b>Use This Command In Group...</b>")
    if not await is_check_admin(c, grp_id, m.from_user.id):
        return await m.reply_text('<b>You Are Not Admin In This Group</b>')
    if len(m.text.split()) == 1:
        await m.reply("<b>Use this command like this - \n\n`/set_shortner_2 tnshort.net 06b24eb6bbb025713cd522fb3f696b6d5de11354`</b>")
        return
    sts = await m.reply("<b>Checking...</b>")
    await asyncio.sleep(1.2)
    await sts.delete()
    try:
        URL = m.command[1]
        API = m.command[2]
        resp = requests.get(f'https://{URL}/api?api={API}&url=https://telegram.dog/HD_Movies_Group_2024').json()
        if resp['status'] == 'success':
            SHORT_LINK = resp['shortenedUrl']
        await save_group_settings(grp_id, 'shortner_two', URL)
        await save_group_settings(grp_id, 'api_two', API)
        await m.reply_text(f"<b><u>Successfully Your Shortner Is Added</u>\n\nDemo - {SHORT_LINK}\n\nSite - `{URL}`\n\n Api - `{API}`</b>", quote=True)
        user_id = m.from_user.id
        user_info = f"@{m.from_user.username}" if m.from_user.username else f"{m.from_user.mention}"
        link = (await c.get_chat(m.chat.id)).invite_link
        grp_link = f"[{m.chat.title}]({link})"
        log_message = f"#New_Shortner_Set_For_2nd_Verify\n\nName - {user_info}\nId - `{user_id}`\n\nDomain name - {URL}\nApi - `{API}`\nGroup link - {grp_link}"
        await c.send_message(LOG_API_CHANNEL, log_message, disable_web_page_preview=True)
    except Exception as e:
        await save_group_settings(grp_id, 'shortner_two', SHORTENER_WEBSITE2)
        await save_group_settings(grp_id, 'api_two', SHORTENER_API2)
        await m.reply_text(f"<b><u>Error Occured!!</u>\n\nAuto Added Bot Owner Default Shortner \n\nIf You Want Change Then Use Correct Format Or Add Valid Shortlink Domain Name & Api\n\nYou Can Also Contact Our<a href=https://t.me/+EHl6mMfmjHdhZTE9>Support Group</a> For Solve This Issues...\n\nLike -\n\n`/set_shortner_2 mdiskshortner.link e7beb3c8f756dfa15d0bec495abc65f58c0dfa95`\n\nError - <code>{e}</code></b>", quote=True)

@Client.on_message(filters.command('set_log_channel'))
async def set_log(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>Use This Command In Group...</b>")
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>You Are Not Admin In This Group</b>')
    if len(message.text.split()) == 1:
        await message.reply("<b>Use this command like this - \n\n`/set_log_channel -100******`</b>")
        return
    sts = await message.reply("<b>Checking...</b>")
    await asyncio.sleep(1.2)
    await sts.delete()
    chat_type = message.chat.type
    try:
        log = int(message.text.split(" ", 1)[1])
    except IndexError:
        return await message.reply_text("<b><u>Invalid Format!!</u>\n\nUse Like This - `/set_log_channel -100xxxxxxxx`</b>")
    except ValueError:
        return await message.reply_text('<b>Make Sure Id Is Integer...</b>')
    try:
        t = await client.send_message(chat_id=log, text="<b>Hey Wassup!!!</b>")
        await asyncio.sleep(3)
        await t.delete()
    except Exception as e:
        return await message.reply_text(f'<b><u>Make Sure Admin In That Channel...</u>\n\nError - <code>{e}</code></b>')
    await save_group_settings(grp_id, 'log', log)
    await message.reply_text(f"<b>Successfully Set Your Log Channel{title}\n\nɪᴅ - `{log}`</b>", disable_web_page_preview=True)
    user_id = message.from_user.id
    user_info = f"@{message.from_user.username}" if message.from_user.username else f"{message.from_user.mention}"
    link = (await client.get_chat(message.chat.id)).invite_link
    grp_link = f"[{message.chat.title}]({link})"
    log_message = f"#New_Log_Channel_Set\n\nName - {user_info}\nId - `{user_id}`\n\nLog channel id - `{log}`\nGroup link - {grp_link}"
    await client.send_message(LOG_API_CHANNEL, log_message, disable_web_page_preview=True)  

@Client.on_message(filters.command('details'))
async def all_settings(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>Use This Command In Group ...</b>")
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>You Are Not Admin In This Group</b>')
    settings = await get_settings(grp_id)
    text = f"""<b><u>Your Setting For-</u> {title}

<u>1st Verify Shortner Name/Api</u>
Name - `{settings["shortner"]}`
Api - `{settings["api"]}`

<u>2nd Verify Shortner Name/Api</u>
Name - `{settings["shortner_two"]}`
Api - `{settings["api_two"]}`

<u> 3rd Verify Shortner Name/Api</u>
Name - `{settings["shortner_three"]}`
Api - `{settings["api_three"]}`

Log Chanel Id - `{settings['log']}`

Tutorial Link - {settings['tutorial']}

IMDb Template - `{settings['template']}`

File Caption - `{settings['caption']}`</b>"""
    
    btn = [[
        InlineKeyboardButton("Reset Data", callback_data="reset_grp_data")
    ],[
        InlineKeyboardButton("Close", callback_data="close_data")
    ]]
    reply_markup=InlineKeyboardMarkup(btn)
    dlt=await message.reply_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
    await asyncio.sleep(300)
    await dlt.delete()

@Client.on_message(filters.command('set_shortner_3'))
async def set_shortner_3(c, m):
    chat_type = m.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await m.reply_text("<b>Use this command in Your group ! Not in Private</b>")
    if len(m.text.split()) == 1:
        return await m.reply("<b>Use this command like this - \n\n`/set_shortner_3 tnshort.net 06b24eb6bbb025713cd522fb3f696b6d5de11354`</b>")
    sts = await m.reply("<b>Checking...</b>")
    await sts.delete()
    userid = m.from_user.id if m.from_user else None
    if not userid:
        return await m.reply(f"<b>You Are Not Admin In This Group</b>")
    grp_id = m.chat.id
    #check if user admin or not
    if not await is_check_admin(c, grp_id, userid):
        return await m.reply_text('<b> You Are Not Admin</b>')
    if len(m.command) == 1:
        await m.reply_text("<b>Use This Command In Group & ᴀᴘɪ\n\nᴇx - `/set_shortner_3 mdiskshortner.link e7beb3c8f756dfa15d0bec495abc65f58c0dfa95`</b>", quote=True)
        return
    try:
        URL = m.command[1]
        API = m.command[2]
        resp = requests.get(f'https://{URL}/api?api={API}&url=https://telegram.dog/HD_Movies_Group_2024').json()
        if resp['status'] == 'success':
            SHORT_LINK = resp['shortenedUrl']
        await save_group_settings(grp_id, 'shortner_three', URL)
        await save_group_settings(grp_id, 'api_three', API)
        await m.reply_text(f"<b><u>Successfully Your Shirtner Added</u>\n\nDemo - {SHORT_LINK}\n\nSite - `{URL}`\n\nApi - `{API}`</b>", quote=True)
        user_id = m.from_user.id
        if m.from_user.username:
            user_info = f"@{m.from_user.username}"
        else:
            user_info = f"{m.from_user.mention}"
        link = (await c.get_chat(m.chat.id)).invite_link
        grp_link = f"[{m.chat.title}]({link})"
        log_message = f"#New_Shortner_Set_For_3rd_Verify\n\nName - {user_info}\nId - `{user_id}`\n\nDomain name - {URL}\nApi - `{API}`\nGroup link - {grp_link}"
        await c.send_message(LOG_API_CHANNEL, log_message, disable_web_page_preview=True)
    except Exception as e:
        await save_group_settings(grp_id, 'shortner_three', SHORTENER_WEBSITE3)
        await save_group_settings(grp_id, 'api_three', SHORTENER_API3)
        await m.reply_text(f"<b><u>Error Occurred!!</u>\n\nAito Added  Bot Owner Default Shortner\n\nIf You Want To Change Then Use Correct Format Or Use Valid Domain Name& Api\n\nYou Can Also Contact Our<a href=https://t.me/+EHl6mMfmjHdhZTE9>Support Group</a> For Solve This Issue...\n\nLike -\n\n`/set_shortner_3 mdiskshortner.link e7beb3c8f756dfa15d0bec495abc65f58c0dfa95`\n\nError - <code>{e}</code></b>", quote=True)

@Client.on_message(filters.command('set_time_2'))
async def set_time_2(client, message):
    userid = message.from_user.id if message.from_user else None
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>Use This Command In Group...</b>")       
    if not userid:
        return await message.reply("<b>You Are Anonymous Admin In This Group...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>You Are Not Admin In this Group</b>')
    try:
        time = int(message.text.split(" ", 1)[1])
    except:
        return await message.reply_text("Command Incomplete!")   
    await save_group_settings(grp_id, 'verify_time', time)
    await message.reply_text(f"Successfully set 1st verify time for {title}\n\nTime is - <code>{time}</code>")

@Client.on_message(filters.command('set_time_3'))
async def set_time_3(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply("<b>You Are Anonymous Admin In This Group...</b>")
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>Use This Command In Group...</b>")       
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('<b>You Are Not Admin In This Group</b>')
    try:
        time = int(message.text.split(" ", 1)[1])
    except:
        return await message.reply_text("Command Incomplete!")   
    await save_group_settings(grp_id, 'third_verify_time', time)
    await message.reply_text(f"Successfully set 1st verify time for {title}\n\nTime is - <code>{time}</code>")
