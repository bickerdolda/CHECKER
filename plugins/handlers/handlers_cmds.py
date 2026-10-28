from pyrogram import filters
from pyromod import Client
from pyrogram.types import CallbackQuery
from utilsdf.cmds_desing import *


@Client.on_callback_query(filters.regex("home"))
async def handler_home(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    await callback_query.edit_message_text(
        text=text_home.format(user_id),
        reply_markup=buttons_cmds,
    )


@Client.on_callback_query(filters.regex("gates"))
async def handler_gates(client: Client, callback_query: CallbackQuery):
    gates_auth = text_gates_auth
    gates_chargeds = (
        text_gates_charged
    )
    gates_specials = (
        text_gates_especials
    )

    # improve in the future using database
    count_status_gates = (
        lambda text: gates_auth.count(text)
        + gates_chargeds.count(text)
        + gates_specials.count(text)
    )
    gates_on = count_status_gates("✅")
    gates_off = count_status_gates("❌")
    gates_mantenience = count_status_gates("⚠️")
    total = gates_on + gates_off + gates_mantenience

    await callback_query.edit_message_text(
        f"""
𝙒𝙚𝙡𝙘𝙤𝙢𝙚 »

𝙏𝙤𝙩𝙖𝙡 -» <code>{total}</code>
𝙊𝙣 -» <code>{gates_on} ✅</code>
𝙊𝙛𝙛 -» <code>{gates_off} ❌</code>
<code>𝙎𝙚𝙡𝙚𝙘𝙩 𝙩𝙝𝙚 𝙩𝙮𝙥𝙚 𝙤𝙛 𝙜𝙖𝙩𝙚 𝙮𝙤𝙪 𝙬𝙖𝙣𝙩 𝙛𝙤𝙧 𝙮𝙤𝙪𝙧 𝙪𝙨𝙚!</code>""",
        reply_markup=buttons_gates,
    )


@Client.on_callback_query(filters.regex("auths") | filters.regex("auths_2"))
async def handler_auths(client: Client, callback_query: CallbackQuery):
    if callback_query.data == "auths":
        await callback_query.edit_message_text(
            text_gates_auth, reply_markup=buttons_auth_page_1
        )
    elif callback_query.data == "auths_2":
        await callback_query.edit_message_text(
            text_gates_auth_2, reply_markup=buttons_auth_page_2
        )


@Client.on_callback_query(filters.regex("chargeds") | filters.regex("chargeds_2"))
async def handler_chargeds(client: Client, callback_query: CallbackQuery):
    if callback_query.data == "chargeds":
        await callback_query.edit_message_text(
            text_gates_charged, reply_markup=buttons_charged_page_1
        )
    elif callback_query.data == "chargeds_2":
        await callback_query.edit_message_text(
            text_gates_charged_2, reply_markup=buttons_charged_page_2
        )
    elif callback_query.data == "chargeds_3":
        await callback_query.edit_message_text(
            text_gates_charged_3, reply_markup=buttons_charged_page_3
        )
    elif callback_query.data == "chargeds_4":
        await callback_query.edit_message_text(
            text_gates_charged_4, reply_markup=buttons_charged_page_4
        )
    elif callback_query.data == "chargeds_5":
        await callback_query.edit_message_text(
            text_gates_charged_5, reply_markup=buttons_charged_page_5
        )


@Client.on_callback_query(
    filters.regex("specials")
    | filters.regex("specials_2")
    | filters.regex("specials_3")
)
async def handler_specials(client: Client, callback_query: CallbackQuery):
    if callback_query.data == "specials":
        await callback_query.edit_message_text(
            text_gates_especials, reply_markup=buttons_specials_page_1
        )
    elif callback_query.data == "specials_2":
        await callback_query.edit_message_text(
            text_gates_especials_2, reply_markup=buttons_specials_page_2
        )
    elif callback_query.data == "specials_3":
        await callback_query.edit_message_text(
            text_gates_especials_3, reply_markup=buttons_specials_page_3
        )


@Client.on_callback_query(filters.regex("tools"))
async def handler_tools(client: Client, callback_query: CallbackQuery):
    await callback_query.edit_message_text(
        text_tools, reply_markup=return_home_and_exit
    )


@Client.on_callback_query(filters.regex("exit"))
async def handler_exit(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
  
