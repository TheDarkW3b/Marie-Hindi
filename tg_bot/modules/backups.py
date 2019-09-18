import json
from io import BytesIO
from typing import Optional

from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async

from tg_bot import dispatcher, LOGGER
from tg_bot.__main__ import DATA_IMPORT
from tg_bot.modules.helper_funcs.chat_status import user_admin


@run_async
@user_admin
def import_data(bot: Bot, update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    # TODO: allow uploading doc with command, not just as reply
    # only work with a doc
    if msg.reply_to_message and msg.reply_to_message.document:
        try:
            file_info = bot.get_file(msg.reply_to_message.document.file_id)
        except BadRequest:
            msg.reply_text("आयात करने से पहले फ़ाइल को स्वयं डाउनलोड करने और फिर लोड करने का प्रयास करें")
            return

        with BytesIO() as file:
            file_info.download(out=file)
            file.seek(0)
            data = json.load(file)

        # only import one group
        if len(data) > 1 and str(chat.id) not in data:
            msg.reply_text("इस फ़ाइल में यहाँ एक से अधिक ग्रुप हैं, और किसी के पास इस ग्रुप के समान चैट आईडी नहीं है")
            return

        # Select data source
        if str(chat.id) in data:
            data = data[str(chat.id)]['hashes']
        else:
            data = data[list(data.keys())[0]]['hashes']

        try:
            for mod in DATA_IMPORT:
                mod.__import_data__(str(chat.id), data)
        except Exception:
            msg.reply_text("An exception occured while restoring your data. The process may not be complete. If "
                           "you're having issues with this, message @MenheraChanSupport with your backup file so the "
                           "issue can be debugged. My owners would be happy to help, and every bug "
                           "reported makes me better! Thanks! :)")
            LOGGER.exception("Import for chatid %s with name %s failed.", str(chat.id), str(chat.title))
            return

        # TODO: some of that link logic
        # NOTE: consider default permissions stuff?
        msg.reply_text("बैकअप पूरी तरह से सफलतापूर्वक वापस स्वागत है! :D")


@run_async
@user_admin
def export_data(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    msg.reply_text("")


__mod_name__ = "Backups"

__help__ = """
*Admin only:*
 - /import: एक समूह बटलर बैकअप फ़ाइल का जवाब जितना संभव हो उतना आयात करने के लिए, जिससे ट्रांसफर सुपर सरल हो जाता है! ध्यान दें \ टेलीग्राम प्रतिबंध के कारण फ़ाइलें / फ़ोटो आयात नहीं किए जा सकते।.
 - /export: !! यह अभी तक एक आदेश नहीं है, लेकिन जल्द ही आ जाना चाहिए
"""
IMPORT_HANDLER = CommandHandler("import", import_data)
EXPORT_HANDLER = CommandHandler("export", export_data)

dispatcher.add_handler(IMPORT_HANDLER)
# dispatcher.add_handler(EXPORT_HANDLER)
