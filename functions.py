# Telegram
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from db import *
from pybot import BASE_AMOUNT, cur
import datetime


def button(update, context):
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    message_id = update.callback_query['message']['message_id']
    original_text = update.callback_query['message']['text']
    original_markup = update.callback_query['message']['reply_markup']['inline_keyboard']
    if not legitUser(user_id):
        return
    callback_data = update.callback_query['data']
    if callback_data == 'cancel':
        context.bot.delete_message(chat_id, message_id)
    elif callback_data == 'factoryreset':
        context.bot.edit_message_text(
            'Please wait momentarily...', chat_id, message_id)
        try:
            resetdb()
            context.bot.edit_message_text(
                'Reset everything!', chat_id, message_id)
        except Exception as e:
            context.bot.edit_message_text(
                f'Failed to reset - {e}', chat_id, message_id)
    elif callback_data.startswith('disp'):
        context.bot.edit_message_text(
            'Loading... Please wait.', chat_id, message_id)
        txt = '<u>Amount of SOCash</u>'
        mode = callback_data[4:]
        pointslist = getPoints(mode=mode)
        if mode == 'house':
            maxes = []
            for i in range(6):
                for j in range(6):
                    if pointslist[6 * i + j][1] == max([points[1] for points in pointslist[6 * i: 6 * i + 6]]) and pointslist[6 * i + j][1] > BASE_AMOUNT:
                        maxes.append(6 * i + j)
        for counter, og in enumerate(pointslist):
            og_id = og[0]
            house = og[2]
            points = og[1]
            if counter % 6 == 0:
                if mode == 'house':
                    txt += f'\n\n<u>{house} Total: ${sum([i[1] for i in pointslist[counter:counter + 6]])}</u>'
                else:
                    txt += '\n'
            if mode == 'house' and counter in maxes:
                txt += '<b>'
            txt += f'\n{house} {og_id}: ${points}'
            if mode == 'house' and counter in maxes:
                txt += f' (Top {house} contributor!)</b>'
        context.bot.edit_message_text(
            txt, chat_id, message_id, parse_mode=ParseMode.HTML)
    elif callback_data.startswith('add'):
        msg = context.bot.edit_message_text(
            'Adding, please hold on...', chat_id, message_id)
        id = int(callback_data.split('.')[1])
        ocomm = callback_data.split('.')[2] == 'ocomm'
        username = None
        try:
            username = context.bot.getChat(id).username
        except:
            pass
        addUser(id, ocomm, username)
        msg.edit_text(
            f'Done! @{context.bot.getChat(id).username} is now a registered {"OComm" if ocomm else "Station Master"}!')
    elif callback_data.startswith('revoke'):
        msg = context.bot.edit_message_text(
            'Revoking, please hold on...', chat_id, message_id)
        id = callback_data.split('.')[1]
        revokeAdmin([id])
        msg.edit_text(
            f'Done! @{context.bot.getChat(id).username} is no longer an admin!')
    elif callback_data.startswith('log'):
        context.bot.edit_message_text("Loading...", chat_id, message_id)
        page_no = int(callback_data.split('.')[1])
        count, logs = getlogs(page_no)
        if not logs:
            om = InlineKeyboardMarkup(
                [[InlineKeyboardButton(button['text'], callback_data=button['callback_data']) for button in row] for row in original_markup])
            context.bot.edit_message_text(
                original_text, chat_id, message_id, reply_markup=om)
            context.bot.answer_callback_query(
                update.callback_query.id, "No more logs to view!")
            return
        txt = generate_logs(logs, context)
        buttons = []
        if page_no > 0:
            buttons.append(InlineKeyboardButton(
                "Previous", callback_data=f"log.{page_no-1}"))
        if count > (page_no + 1) * 20:
            buttons.append(InlineKeyboardButton(
                "Next", callback_data=f"log.{page_no+1}"))
        context.bot.edit_message_text(
            txt, chat_id, message_id, reply_markup=InlineKeyboardMarkup([buttons]))


def start(update, context):
    user = update.message.from_user
    user_id = user.id
    chat_id = update.message.chat.id
    ocomm = isOComm(user_id)
    if legitUser(user_id):
        context.bot.sendMessage(
            chat_id, f'Hi, {full_name(user)}. You are an {"authorized user. To add others as admin, you can forward their message to me or use the /addadmin command" if ocomm else "station master"}. View /help for more.')
    else:
        context.bot.sendMessage(
            chat_id, 'Welcome to the SOCash bot! To be added as an admin, type /me to get your user id and then send that to an existing admin, or you can get an exiting admin to forward a message by you to me.')


def me(update, context):
    user = update.message.from_user
    user_id = user.id
    chat_id = update.message.chat.id
    context.bot.sendMessage(
        chat_id, f'{full_name(user)}, your user id is {user_id}')


def reset(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    if accessDenied(update, context) or not isOComm(user_id):
        return
    msg = context.bot.sendMessage(chat_id, 'Please wait a moment...')
    try:
        resetpoints()
        msg.edit_text('Successfully reset points!')
    except Exception as e:
        msg.edit_text(f'Failed to reset - {e}')


def addadmin(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    if accessDenied(update, context):
        return
    toAdd = update.message.text.split(' ')[1:]
    sm = toAdd[0].lower() == "sm"
    if sm:
        toAdd.pop(0)
    added = []
    for user in toAdd:
        if (not user.isnumeric()) or context.bot.getChat(int(user)).get_member(int(user)).user.is_bot:
            continue
        username = None
        try:
            username = context.bot.getChat(user).username
        except:
            pass
        if addUser(int(user), not sm, username):
            added.append(int(user))
    if added:
        context.bot.sendMessage(
            chat_id, f'Added {len(added)} user as {"station master" if sm else "admin"} successfully!')
    else:
        context.bot.sendMessage(
            chat_id, 'Failed to add anyone. Are they already admin?')


def factoryreset(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    if accessDenied(update, context) or not isOComm(user_id):
        return
    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton('Yes', callback_data='factoryreset'),
            InlineKeyboardButton('No', callback_data='cancel')
        ]
    ])
    context.bot.sendMessage(
        chat_id, 'Are you sure you want to reset all SOCash amounts to 0 and remove all authorized users?', reply_markup=markup)


def display(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    if accessDenied(update, context):
        return
    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton('By house', callback_data='disphouse'),
                InlineKeyboardButton('In descending order',
                                     callback_data='dispdsc')
            ]
        ]
    )
    context.bot.sendMessage(
        chat_id, 'How would you like to display?', reply_markup=markup)


def isNumber(x):  # because isnumeric() doesn't recognize negative numbers?
    try:
        int(x)
        return True
    except:
        return False


def add(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    if accessDenied(update, context):
        return
    args = update.message.text.strip().upper().split(' ')[1:]
    if len(args) < 2 or not isNumber(args[-1]):
        context.bot.sendMessage(
            chat_id, 'Invalid format! If you want to add $10 to Aikon 3 and Barg 2, type /add A3 B2 10. Upper/Lowercase does not matter.')
        return
    msg = context.bot.sendMessage(chat_id, 'Please hold on...')
    amt = int(args[-1])
    ogs = args[:-1]
    invalid = []
    valid = []
    houses = getHouses()
    for og in ogs:
        if len(og) != 2 or og[0] not in houses or og[1] not in '123456':
            invalid.append(og)
            continue
        valid.append(og)
    if not valid:
        msg.edit_text('Failed to add to any OG. Please check your format.')
        return
    res = addPoints(valid, amt, user_id)
    og_list = [f'{i[1]} {i[0]}' for i in res]
    points = [i[2] for i in res]
    txt = f'Done! {"Added" if amt > 0 else "Removed"} ${amt if amt > 0 else -amt} {"to" if amt > 0 else "from"} {", ".join(og_list)}. Run /display to see the scoreboard.'
    for i, p in enumerate(points):
        txt += f'\n{og_list[i]}: ${p}'
    if invalid:
        txt += '\nInvalid OGs: ' + ', '.join(invalid)
    msg.edit_text(txt)


def massadd(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    if accessDenied(update, context):
        return
    args = update.message.text.strip().split(' ')[1:]
    if len(args) != 1 or not args[0].isnumeric():
        context.bot.sendMessage(
            chat_id, 'Invalid format! If you want to give every OG $10, do /massadd 10')
        return
    amt = int(args[0])
    addAll(amt, user_id)
    context.bot.sendMessage(
        chat_id, f'Succeessfully added ${amt} to every OG!')


def help(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    if accessDenied(update, context):
        return
    OComm = isOComm(user_id)
    txt = 'Forward a message from a user to add/remove them as admin\n\n' if OComm else ''
    txt += '/me - Sends you your user id. Required to add as admin\n\n'
    txt += '/addadmin <u>userid(s)</u> - Adds the following user(s) as an admin. Separate user ids with a space\n\n' if OComm else ''
    txt += '/revoke <u>usernames/user ids</u> - Revokes admin privilegs from the following people. Unlike /addadmin, this works with usernames\n\n' if OComm else ''
    txt += '/add <u>OG(s)</u> <u>amount</u> - Adds the specified amount of SOCash to the OG(s) specified. Works for one or more OGs at a time.\n'
    txt += 'e.g. If you want to add $10 to Aikon 3 and Barg 2, type /add A3 B2 10. Upper/Lowercase does not matter.\n\n'
    txt += '/massadd <u>amount</u> - Adds the specified amount of SOCash to all OGs\n\n'
    txt += '/display - Displays the scoreboard\n\n'
    txt += '/admins - Displays all admins\n\n' if OComm else ''
    txt += '/reset - Resets the SOCash amount to 0 for ALL OGs. USE WITH CAUTION!\n\n' if OComm else ''
    context.bot.sendMessage(chat_id, txt, parse_mode=ParseMode.HTML)


def accessDenied(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    if not legitUser(user_id):
        context.bot.sendMessage(
            chat_id, 'You are not an authorized user! To get added as an admin, please type /me and send your user id to any admin so they can add you.')
        return True
    return False


def forwarded(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    if not isOComm(user_id):
        return
    if update.message.forward_from is None:
        context.bot.sendMessage(
            chat_id, f'Due to {update.message.forward_sender_name}\'s privacy settings, I cannot add them. Get them to PM me /me and send you their user id!')
        return
    if update.message.forward_from == context.bot.get_me():
        context.bot.sendMessage(chat_id, 'You cannot make me an admin!')
        return
    if update.message.forward_from.is_bot:
        context.bot.sendMessage(chat_id, 'You can only make humans admins!')
        return
    if update.message.forward_from == user_id:
        context.bot.sendMessage(
            chat_id, 'You cannot forward a message from yourself!')
        return
    forwardedFrom = update.message.forward_from
    legit = legitUser(forwardedFrom.id)
    if legit:
        txt = f'@{forwardedFrom.username} is already a registered {legit}. Do you want to revoke their admin privileges?'
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    'Yes', callback_data=f'revoke.{forwardedFrom.id}'),
                InlineKeyboardButton('Cancel', callback_data='cancel')

            ]
        ])
    else:
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    'OComm', callback_data=f'add.{forwardedFrom.id}.ocomm'),
                InlineKeyboardButton(
                    'Station Master', callback_data=f'add.{forwardedFrom.id}.sm')
            ],
            [
                InlineKeyboardButton('Cancel', callback_data='cancel')
            ]
        ])
        txt = f'Do you want to add @{forwardedFrom.username} as admin?'
    context.bot.sendMessage(chat_id, txt, reply_markup=markup)


def getusername(update, context):
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    if accessDenied(update, context) or not isOComm(user_id):
        return
    msg = context.bot.sendMessage(
        chat_id, "Hold on, this might take very long...")
    idList = list(filter(lambda x: x[1] == None, getAdmins()))
    for user, _, _ in idList:
        try:
            username = context.bot.getChat(user).username
            cur.execute(
                f"UPDATE users SET username = '{username}' WHERE chat_id = {user}")
        except:
            pass
    msg.edit_text("Successfully refreshed all usernames!")


def revoke(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    if accessDenied(update, context) or not isOComm(user_id):
        return
    args = update.message.text.strip().split(' ')[1:]
    adminList = getAdmins()
    userList = {user[1]: user[0] for user in adminList}
    valid = []
    for user in args:
        user = user.strip('@')
        if user.isnumeric() and int(user) in userList.values():
            valid.append(user)
        elif user in userList.keys():
            valid.append(str(userList[user]))
    removed = revokeAdmin(valid) if len(valid) > 0 else []
    if removed:
        removed = ['@' + user for user in removed]
        r = ', '.join(removed)
        txt = f'Successfully removed {r}.'
    else:
        txt = 'Did not remove anyone! I accept usernames, user ids or forwarded messages.'
    context.bot.sendMessage(chat_id, txt)


def admins(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    if accessDenied(update, context) or not isOComm(user_id):
        return
    userList = getAdmins()
    ocommList = filter(lambda x: x[2] == 0, userList)
    smList = filter(lambda x: x[2] == 1, userList)
    ocomm = ', '.join([('@' + user[1]) for user in ocommList])
    sm = ', '.join([('@' + user[1]) for user in smList])
    context.bot.sendMessage(
        chat_id, f'The OComm are {ocomm}\n\nThe Station Masters are {sm}')


def log(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    if accessDenied(update, context) or not isOComm(user_id):
        return

    msg = context.bot.sendMessage(chat_id, "Retrieving logs...")
    count, logs = getlogs(0)
    txt = ''
    if count == 0:
        txt = 'Log is empty'
    txt = generate_logs(logs, context)
    markup = None
    if count > 20:
        markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Next", callback_data="log.1")]])
    msg.edit_text(txt, reply_markup=markup)


def generate_logs(logs, context):
    txt = ""
    for lg in logs:
        un, og_id, house_id, amount, time = lg
        time = time.astimezone(datetime.timezone(datetime.timedelta(hours=8)))
        timestr = f"{time.day}/{time.month} {doubledigit(time.hour)}:{doubledigit(time.minute)}"
        un = ('@' + un) if not isNumber(un) else un
        txt += f'{timestr} {un} {"added" if amount > 0 else "removed"} ${amount if amount > 0 else -amount} {"to" if amount > 0 else "from"} {"all OGs" if og_id is None and house_id is None else f"{getHouse(house_id)} {og_id}"}\n'
    return txt


def doubledigit(x):
    return f'0{x}' if x < 10 else f'{x}'


def full_name(effective_user):
    first_name = effective_user.first_name
    last_name = effective_user.last_name
    if not (first_name and last_name):
        return first_name or last_name
    return ' '.join([first_name, last_name])
