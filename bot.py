import os
import sqlite3
import logging
from pathlib import Path
from html import escape
await msg.reply_text(t('edit(context,'heimport os
    field=context.user_data.get_field') if step=='editvalue' else step
    value=(msg.text or '').strip()
    if field=='photo':
        if not msg.photo:await msg.reply_text(t(context,'photo',uid));return
        value=msg.photo[-1].file_id
    elif field=='age':
        try:age=int(value)
        except ValueError:age=0
        if age<18:
            if step!='editvalue':
                code=lang(context,uid);remove(uid);context.user_data.clear();await msg.reply_text(T[code]['under']);return
            await msg.reply_text(t(context,'badage',uid));return
        if age>120:await msg.reply_text(t(context,'badage',uid));return
        value=age
    elif (not value and field!='bio') or len(value)>{'name':50,'city':100,'bio':500}.get(field,500):
        await msg.reply_text(t(context,'bad',uid));return
    put(uid,**{field:value})
    if step=='editvalue':
        context.user_data.pop('edit_field',None)
        put(uid,confirmed=0)
        await show_preview(update,context);return
    next_step={'name':'age','age':'city','city':'gender','bio':'photo'}
    if field=='photo':await show_preview(update,context)
    elif field=='city':await msg.reply_text(t(context,'gender',uid),reply_markup=kb([[(t(context,'man',uid),'gender:man'),(t(context,'woman',uid),'gender:woman'),(t(context,'other',uid),'gender:other')]]));context.user_data['step']='gender'
    else:
        context.user_data['step']=next_step[field]
        await msg.reply_text(t(context,next_step[field],uid))

async def send_match(context,uid,target):
    for receiver,partner in ((uid,target),(target,uid)):
        p=get(partner)
        if not p:continue
        url=f'tg://user?id={partner}'
        if p['username']:url='https://t.me/'+p['username'].lstrip('@')
        caption=t(context,'matched',receiver)+'\n'+escape(str(p['name']))+'\n'+t(context,'contact',receiver)+': '+escape(url)
        try:await context.bot.send_message(receiver,caption,parse_mode=ParseMode.HTML,disable_web_page_preview=True)
        except Exception:logging.exception('Match notification failed')

async def search_next(update,context):
    uid=update.effective_user.id;p=get(uid)
    if not p or not p['confirmed'] or not p['active']:
        await context.bot.send_message(update.effective_chat.id,t(context,'need_confirm',uid));return
    if not p['gender'] or not p['preference']:
        await context.bot.send_message(update.effective_chat.id,t(context,'need_preferences',uid));return
    with conn() as c:
        target=c.execute('''SELECT p.* FROM profiles p WHERE p.user_id!=? AND p.confirmed=1 AND p.active=1
            AND p.photo IS NOT NULL AND p.age>=18 AND p.gender IS NOT NULL AND p.preference IS NOT NULL
            AND (?='everyone' OR p.gender=?)
            AND (p.preference='everyone' OR p.preference=?)
            AND NOT EXISTS (SELECT 1 FROM likes l WHERE l.from_id=? AND l.to_id=p.user_id)
            AND NOT EXISTS (SELECT 1 FROM skips s WHERE s.from_id=? AND s.to_id=p.user_id)
            AND NOT EXISTS (SELECT 1 FROM blocks b WHERE (b.from_id=? AND b.to_id=p.user_id) OR (b.from_id=p.user_id AND b.to_id=?))
            ORDER BY RANDOM() LIMIT 1''',(uid,p['preference'],p['preference'],p['gender'],uid,uid,uid,uid)).fetchone()
    if not target:
        context.user_data.pop('current_target',None)
        await context.bot.send_message(update.effective_chat.id,t(context,'nonefound',uid));return
    target_id=target['user_id'];context.user_data['current_target']=target_id
    await context.bot.send_photo(update.effective_chat.id,target['photo'],caption=profile_caption(target,context),parse_mode=ParseMode.HTML,
        reply_markup=kb([[(t(context,'like',uid),f'act:like:{target_id}'),(t(context,'skip',uid),f'act:skip:{target_id}')],[(t(context,'block',uid),f'act:block:{target_id}'),(t(context,'report',uid),f'act:report:{target_id}')]]))

async def search(update,context):
    context.user_data.pop('step',None)
    await search_next(update,context)

async def profile(update,context):
    uid=update.effective_user.id;p=get(uid)
    if not p or not p['photo']:
        await update.message.reply_text(t(context,'need',uid));return
    await update.message.reply_photo(p['photo'],caption=profile_caption(p,context),parse_mode=ParseMode.HTML)

async def edit(update,context):
    uid=update.effective_user.id;p=get(uid)
    if not p or not p['photo']:
        await update.message.reply_text(t(context,'need',uid));return
    context.user_data['step']='editmenu'
    await update.message.reply_text(t(context,'editq',uid),reply_markup=edit_keyboard(context,uid))

async def delete(update,context):
    uid=update.effective_user.id
    await update.message.reply_text(t(context,'deleteq',uid),reply_markup=kb([[(t(context,'yes',uid),'delete:yes'),(t(context,'no',uid),'delete:no')]]))

async def help_cmd(update,context):
    uid=update.effective_user.id
    await update.message.reply_text('/start /profile /edit /search /delete /pause /resume /cancel /help\n'+t(context,'pause_help',uid))

async def cancel(update,context):
    uid=update.effective_user.id;context.user_data.clear()
    await update.message.reply_text(t(context,'cancel',uid))

async def pause(update,context):
    uid=update.effective_user.id
    if not get(uid):await update.message.reply_text(t(context,'need',uid));return
    put(uid,active=0);await update.message.reply_text(t(context,'paused',uid))

async def resume(update,context):
    uid=update.effective_user.id;p=get(uid)
    if not p or not p['confirmed']:await update.message.reply_text(t(context,'need_confirm',uid));return
    put(uid,active=1);await update.message.reply_text(t(context,'resumed',uid))

async def error_handler(update,context):
    logging.error('Telegram bot error: %s',context.error,exc_info=context.error)

def main():
    if not TOKEN:raise SystemExit('BOT_TOKEN missing. Windows CMD: set "BOT_TOKEN=your_token"')
    init_db()
    app=Application.builder().token(TOKEN).build()
    for name,func in [('start',start),('search',search),('profile',profile),('edit',edit),('delete',delete),('help',help_cmd),('cancel',cancel),('pause',pause),('resume',resume)]:
        app.add_handler(CommandHandler(name,func))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND & filters.ChatType.PRIVATE,messages))
    app.add_error_handler(error_handler)
    logging.info('TindraVen running')
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__=='__main__':main()
