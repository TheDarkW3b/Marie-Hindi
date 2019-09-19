import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, CommandHandler, run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import is_user_admin, user_admin, can_restrict
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import antiflood_sql as sql

FLOOD_GROUP = 3


@run_async
@loggable
def check_flood(bot: Bot, update: Update) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if not user:  # ignore channels
        return ""

    # ignore admins
    if is_user_admin(chat, user.id):
        sql.update_flood(chat.id, None)
        return ""

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        chat.kick_member(user.id)
        msg.reply_text("अन्य लोगों को परेशान न करें जिन्हें अब आपको इस समूह की कोई आवश्यकता नहीं है...")

        return "<b>{}:</b>" \
               "\n#BANNED" \
               "\n<b>User:</b> {}" \
               "\nFlooded the group.".format(html.escape(chat.title),
                                             mention_html(user.id, user.first_name))

    except BadRequest:
        msg.reply_text("आप इस सेवा का उपयोग तब तक नहीं कर सकते जब तक आप मुझे परमिशन नहीं देते.")
        sql.set_flood(chat.id, 0)
        return "<b>{}:</b>" \
               "\n#INFO" \
               "\nकिक की अनुमति नहीं है, इसलिए एंटिफ्लड रोक दिए गए हैं.".format(chat.title)


@run_async
@user_admin
@can_restrict
@loggable
def set_flood(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    if len(args) >= 1:
        val = args[0].lower()
        if val == "off" or val == "no" or val == "0":
            sql.set_flood(chat.id, 0)
            message.reply_text("मैं अब स्पैम करने वालों को माफ नहीं करूंगा.")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat.id, 0)
                message.reply_text("मैं अब स्पैम करने वालों को माफ नहीं करूंगा.")
                return "<b>{}:</b>" \
                       "\n#SETFLOOD" \
                       "\n<b>Admin:</b> {}" \
                       "\nDisabled antiflood.".format(html.escape(chat.title), mention_html(user.id, user.first_name))

            elif amount < 3:
                message.reply_text("एंटीफ्लड 0 हे या 3 से बड़ी संख्या में हे!")
                return ""

            else:
                sql.set_flood(chat.id, amount)
                message.reply_text("एंटीफ्लड {} को सेट कर दिया है ".format(amount))
                return "<b>{}:</b>" \
                       "\n#SETFLOOD" \
                       "\n<b>Admin:</b> {}" \
                       "\nSet antiflood to <code>{}</code>.".format(html.escape(chat.title),
                                                                    mention_html(user.id, user.first_name), amount)

        else:
            message.reply_text("मुझे समझ नहीं आ रहा है कि आप क्या कह रहे हैं .... या तो नंबर का उपयोग करें या Yes/No का उपयोग करें")

    return ""


@run_async
def flood(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]

    limit = sql.get_flood_limit(chat.id)
    if limit == 0:
        update.effective_message.reply_text("मैं अभी मैसेज कंट्रोल नहीं कर रहा हूं!")
    else:
        update.effective_message.reply_text(
            " {} मैं एक ही समय में संदेश भेजने वाले व्यक्ति को छोड़ दूंगा".format(limit))


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "वर्तमान में नियंत्रण लागू नहीं करना."
    else:
        return " संदेश नियंत्रण के लिए सेट है `{}`.".format(limit)


__help__ = """
 - /flood: अपने वर्तमान संदेश नियंत्रण को जानने के लिए..

*Admin only:*
 - /setflood <int/'no'/'off'>: स्पैम नियंत्रण को ऑन और ऑफ
"""

__mod_name__ = "AntiFlood"

FLOOD_BAN_HANDLER = MessageHandler(Filters.all & ~Filters.status_update & Filters.group, check_flood)
SET_FLOOD_HANDLER = CommandHandler("setflood", set_flood, pass_args=True, filters=Filters.group)
FLOOD_HANDLER = CommandHandler("flood", flood, filters=Filters.group)

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)
