from aiogram import Router, types
from aiogram import Bot
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.deep_linking import decode_payload, create_start_link
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db_connection import Database

router = Router()
db = Database()


async def create_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="💎 Профиль", callback_data="my_profile"),
        types.InlineKeyboardButton(text="👥 Рефералы", callback_data="referral_system"),
        types.InlineKeyboardButton(text="💰 Депозит", callback_data="my_deposit"),
        types.InlineKeyboardButton(text="🎁 Бонусы", callback_data="bonuses"),
        types.InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help"),
        types.InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
    )

    builder.adjust(2, 2, 2)

    return builder.as_markup()


@router.message(Command('start'))
async def cmd_start(message: Message):
    await db.connect()

    keyboard = await create_main_keyboard()

    payload = message.text
    args = payload.split()
    user_id = message.from_user.id

    existing_user = await db.fetch("SELECT * FROM users WHERE user_id = %s", user_id)

    if not existing_user:
        if len(args) > 1:
            try:
                referrer_id = decode_payload(args[1])
                referrer = await db.fetch("SELECT * FROM users WHERE user_id = %s", referrer_id)

                if not referrer or len(referrer) == 0:
                    await message.answer("Недействительная реферальная ссылка.", reply_markup=keyboard)
                    return

                referrer = referrer[0]

                if not referrer['can_invite']:
                    await message.answer("Этот пользователь не может приглашать новых пользователей.",
                                         reply_markup=keyboard)
                    return

                await db.execute(
                    "INSERT INTO users (user_id, has_used_referral, deposit) VALUES (%s, %s, %s)",
                    (user_id, 1, 500)  # Добавляем 500 рублей бонуса
                )
                await db.execute(
                    "INSERT INTO referrals (user_id, referrer_id) VALUES (%s, %s)",
                    (user_id, referrer_id)
                )

                await db.execute(
                    "UPDATE users SET deposit = deposit + 500 WHERE user_id = %s",
                    (referrer_id,)
                )

                await message.answer(
                    "🎉 Вы успешно стали рефералом! Вам начислен бонус 500 рублей!\n"
                    "💵 Ваш реферер также получил 500 рублей бонуса!",
                    reply_markup=keyboard
                )
                return

            except Exception as e:
                print(f"Ошибка при обработке реферальной ссылки: {e}")
                await message.answer(
                    "Добро пожаловать в EZBet Casino!",
                    reply_markup=keyboard
                )
                return

        else:
            await db.execute(
                "INSERT INTO users (user_id, has_used_referral, deposit) VALUES (%s, %s, %s)",
                (user_id, 0, 0)
            )
            await message.answer(
                "Добро пожаловать в EZBet Casino! Используйте реферальную ссылку для приглашения друзей "
                "и получения бонусов 500 рублей каждому!",
                reply_markup=keyboard
            )
            return

    if len(args) > 1:
        try:
            referrer_id = decode_payload(args[1])

            if referrer_id == user_id:
                await message.answer(
                    "Вы не можете использовать свою собственную реферальную ссылку!",
                    reply_markup=keyboard
                )
                return

            existing_referral = await db.fetch(
                "SELECT * FROM referrals WHERE user_id = %s",
                (user_id,)
            )
            if existing_referral:
                await message.answer(
                    "Вы уже были добавлены в рефералы.",
                    reply_markup=keyboard
                )
                return

            referrer = await db.fetch(
                "SELECT * FROM users WHERE user_id = %s",
                (referrer_id,)
            )

            if not referrer or len(referrer) == 0:
                await message.answer(
                    "Недействительная реферальная ссылка.",
                    reply_markup=keyboard
                )
                return

            referrer = referrer[0]

            if not referrer['can_invite']:
                await message.answer(
                    "Этот пользователь не может приглашать новых пользователей.",
                    reply_markup=keyboard
                )
                return

            user_data = await db.fetch(
                "SELECT * FROM users WHERE user_id = %s",
                (user_id,)
            )
            if not user_data or len(user_data) == 0:
                await message.answer(
                    "Пользователь не найден.",
                    reply_markup=keyboard
                )
                return

            user_data = user_data[0]

            if not user_data['has_used_referral']:
                await message.answer(
                    "Вы не можете стать рефералом, так как ранее не использовали реферальную ссылку.",
                    reply_markup=keyboard
                )
                return

            await db.execute(
                "INSERT INTO referrals (user_id, referrer_id) VALUES (%s, %s)",
                (user_id, referrer_id)
            )
            await db.execute(
                "UPDATE users SET deposit = deposit + 500 WHERE user_id = %s",
                (user_id,)
            )
            await db.execute(
                "UPDATE users SET deposit = deposit + 500 WHERE user_id = %s",
                (referrer_id,)
            )

            await message.answer(
                "🎉 Вы успешно стали рефералом! Вам начислен бонус 500 рублей!\n"
                "💵 Ваш реферер также получил 500 рублей бонуса!",
                reply_markup=keyboard
            )

        except Exception as e:
            print(f"Ошибка при обработке реферальной ссылки: {e}")
            await message.answer(
                "Произошла ошибка при обработке реферальной ссылки.",
                reply_markup=keyboard
            )
    else:
        await message.answer(
            "Добро пожаловать обратно в EZBet Casino!",
            reply_markup=keyboard
        )


@router.callback_query(lambda c: c.data == "my_profile")
async def show_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_data = await db.fetch("SELECT * FROM users WHERE user_id = %s", (user_id,))

    if user_data:
        user_data = user_data[0]
        text = (
            f"👤 Ваш профиль:\n"
            f"🆔 ID: {user_id}\n"
            f"💰 Баланс: {user_data.get('deposit', 0)} руб.\n"
            f"📊 Рефералов: {await get_referrals_count(user_id)}"
        )
    else:
        text = "Профиль не найден"

    await callback.message.edit_text(text, reply_markup=await create_main_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data == "referral_system")
async def show_referral_info(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    referrals_count = await get_referrals_count(user_id)
    referral_link = await create_start_link(bot, str(user_id), encode=True)

    text = (
        "👥 Реферальная система\n\n"
        f"🔗 Ваша реферальная ссылка:\n{referral_link}\n\n"
        f"👥 Приглашено пользователей: {referrals_count}\n"
        f"💰 Доход с рефералов: {referrals_count * 500} руб.\n\n"
        "💵 За каждого приглашенного друга вы и он получаете по 500 рублей!"
    )

    await callback.message.edit_text(text, reply_markup=await create_main_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data == "my_deposit")
async def show_deposit(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_data = await db.fetch("SELECT deposit FROM users WHERE user_id = %s", (user_id,))

    if user_data:
        deposit = user_data[0]['deposit']
        text = f"💰 Ваш текущий депозит: {deposit} руб."
    else:
        text = "Данные не найдены"

    await callback.message.edit_text(text, reply_markup=await create_main_keyboard())
    await callback.answer()


async def get_referrals_count(user_id):
    referrals = await db.fetch(
        "SELECT COUNT(*) as count FROM referrals WHERE referrer_id = %s",
        (user_id,)
    )
    return referrals[0]['count'] if referrals else 0