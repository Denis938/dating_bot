import json

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InputMediaPhoto
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database import User, Profile, Preference, Match, Interaction, Rating, Gender
from keyboards import (
    main_menu_kb, profile_menu_kb, edit_profile_kb, gender_kb,
    view_profile_kb, back_kb, delete_confirm_kb, search_settings_kb,
    search_gender_kb
)
from ranking import recalculate_rating
from profile_helpers import calculate_completeness, parse_photo_keys
from redis_cache import ProfileCache
from mq import EventPublisher
from s3_service import S3Service
from metrics import REGISTRATIONS, LIKES, MATCHES

import logging
logger = logging.getLogger(__name__)

router = Router()

cache: ProfileCache | None = None
publisher: EventPublisher | None = None
s3: S3Service | None = None

PROFILE_BATCH_SIZE = 10


def _caption_for_photo(text: str) -> str:
    if len(text) <= 1024:
        return text
    return text[:1020] + "…"


async def _safe_edit_text(callback: CallbackQuery, text: str, reply_markup=None):
    chat_id = callback.message.chat.id
    if callback.message.photo:
        try:
            await callback.message.delete()
        except Exception as e:
            logger.warning("Could not delete photo message: %s", e)
        await callback.bot.send_message(chat_id, text, reply_markup=reply_markup)
    else:
        await callback.message.edit_text(text, reply_markup=reply_markup)


async def _show_photo_or_text(
    callback: CallbackQuery,
    text: str,
    reply_markup,
    photo_keys: list[str] | None,
):
    keys = [k for k in (photo_keys or []) if k]
    if s3 and keys:
        try:
            img = await s3.download_photo(keys[-1])
            photo_file = BufferedInputFile(img, filename="profile.jpg")
            cap = _caption_for_photo(text)
            if callback.message.photo:
                await callback.message.edit_media(
                    InputMediaPhoto(media=photo_file, caption=cap),
                    reply_markup=reply_markup,
                )
            else:
                await callback.bot.send_photo(
                    chat_id=callback.message.chat.id,
                    photo=photo_file,
                    caption=cap,
                    reply_markup=reply_markup,
                )
                try:
                    await callback.message.delete()
                except Exception as e:
                    logger.warning("Could not delete text card: %s", e)
        except Exception as e:
            logger.exception("Photo card failed, falling back to text: %s", e)
            await _safe_edit_text(callback, text, reply_markup)
    else:
        await _safe_edit_text(callback, text, reply_markup)


def setup_services(profile_cache: ProfileCache, event_publisher: EventPublisher, s3_service: S3Service):
    global cache, publisher, s3
    cache = profile_cache
    publisher = event_publisher
    s3 = s3_service


class ProfileForm(StatesGroup):
    name = State()
    age = State()
    gender = State()
    city = State()
    description = State()
    interests = State()
    photo = State()


class PreferenceForm(StatesGroup):
    gender = State()
    min_age = State()
    max_age = State()
    city = State()


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str = None) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        profile = Profile(user_id=user.id)
        session.add(profile)

        preference = Preference(user_id=user.id)
        session.add(preference)

        rating = Rating(user_id=user.id)
        session.add(rating)

        await session.commit()
        REGISTRATIONS.inc()

    return user


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    logger.info(f"/start from telegram_id={message.from_user.id} username={message.from_user.username}")
    try:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        logger.info(f"User ready: id={user.id} telegram_id={user.telegram_id}")
        await message.answer(
            f"👋 Привет! Добро пожаловать в Dating Bot!\n\n"
            f"Твой ID: {user.telegram_id}\n\n"
            "Заполни анкету, чтобы начать знакомиться!",
            reply_markup=main_menu_kb()
        )
    except Exception as e:
        logger.error(f"/start failed: {e}", exc_info=True)
        await message.answer("❌ Ошибка при запуске. Попробуй ещё раз.")


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery):
    await _safe_edit_text(callback,
        "📱 Главное меню\n\nВыбери действие:",
        reply_markup=main_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "my_profile")
async def show_profile(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(
        select(Profile).join(User).where(User.telegram_id == callback.from_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile:
        gender_text = "Мужской" if profile.gender == Gender.MALE else "Женский" if profile.gender == Gender.FEMALE else "Не указан"
        text = (
            "👤 Твоя анкета:\n\n"
            f"📛 Имя: {profile.name or 'Не указано'}\n"
            f"🎂 Возраст: {profile.age or 'Не указан'}\n"
            f"⚧ Пол: {gender_text}\n"
            f"🏙 Город: {profile.city or 'Не указан'}\n"
            f"📝 О себе: {profile.description or 'Не указано'}\n"
            f"💡 Интересы: {profile.interests or 'Не указаны'}\n\n"
            f"📊 Заполненность: {int(profile.completeness * 100)}%"
        )
    else:
        text = "Анкета не найдена. Начни с /start"

    keys = parse_photo_keys(profile.photo_keys) if profile else []
    await _show_photo_or_text(callback, text, profile_menu_kb(), keys)
    await callback.answer()


@router.callback_query(F.data == "edit_profile")
async def edit_profile_menu(callback: CallbackQuery):
    await _safe_edit_text(callback,
        "✏️ Что хочешь изменить?",
        reply_markup=edit_profile_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "edit_name")
async def edit_name(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileForm.name)
    await _safe_edit_text(callback,"Введи своё имя:", reply_markup=back_kb())
    await callback.answer()


@router.message(ProfileForm.name)
async def process_name(message: Message, state: FSMContext, session: AsyncSession):
    result = await session.execute(
        select(Profile).join(User).where(User.telegram_id == message.from_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile:
        profile.name = message.text
        profile.completeness = calculate_completeness(profile)
        await session.commit()
        await _on_profile_updated(session, profile.user_id)

    await state.clear()
    await message.answer("✅ Имя сохранено!", reply_markup=main_menu_kb())


@router.callback_query(F.data == "edit_age")
async def edit_age(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileForm.age)
    await _safe_edit_text(callback,"Введи свой возраст (18-100):", reply_markup=back_kb())
    await callback.answer()


@router.message(ProfileForm.age)
async def process_age(message: Message, state: FSMContext, session: AsyncSession):
    try:
        age = int(message.text)
        if 18 <= age <= 100:
            result = await session.execute(
                select(Profile).join(User).where(User.telegram_id == message.from_user.id)
            )
            profile = result.scalar_one_or_none()

            if profile:
                profile.age = age
                profile.completeness = calculate_completeness(profile)
                await session.commit()
                await _on_profile_updated(session, profile.user_id)

            await state.clear()
            await message.answer("✅ Возраст сохранён!", reply_markup=main_menu_kb())
        else:
            await message.answer("❌ Возраст должен быть от 18 до 100")
    except ValueError:
        await message.answer("❌ Введи число")


@router.callback_query(F.data == "edit_gender")
async def edit_gender(callback: CallbackQuery):
    await _safe_edit_text(callback,"Выбери свой пол:", reply_markup=gender_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("set_gender_"))
async def process_gender(callback: CallbackQuery, session: AsyncSession):
    gender = Gender.MALE if callback.data == "set_gender_male" else Gender.FEMALE

    result = await session.execute(
        select(Profile).join(User).where(User.telegram_id == callback.from_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile:
        profile.gender = gender
        profile.completeness = calculate_completeness(profile)
        await session.commit()
        await _on_profile_updated(session, profile.user_id)

    await _safe_edit_text(callback,"✅ Пол сохранён!", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "edit_city")
async def edit_city(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileForm.city)
    await _safe_edit_text(callback,"Введи свой город:", reply_markup=back_kb())
    await callback.answer()


@router.message(ProfileForm.city)
async def process_city(message: Message, state: FSMContext, session: AsyncSession):
    result = await session.execute(
        select(Profile).join(User).where(User.telegram_id == message.from_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile:
        profile.city = message.text
        profile.completeness = calculate_completeness(profile)
        await session.commit()
        await _on_profile_updated(session, profile.user_id)

    await state.clear()
    await message.answer("✅ Город сохранён!", reply_markup=main_menu_kb())


@router.callback_query(F.data == "edit_description")
async def edit_description(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileForm.description)
    await _safe_edit_text(callback,"Расскажи о себе:", reply_markup=back_kb())
    await callback.answer()


@router.message(ProfileForm.description)
async def process_description(message: Message, state: FSMContext, session: AsyncSession):
    result = await session.execute(
        select(Profile).join(User).where(User.telegram_id == message.from_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile:
        profile.description = message.text
        profile.completeness = calculate_completeness(profile)
        await session.commit()
        await _on_profile_updated(session, profile.user_id)

    await state.clear()
    await message.answer("✅ Описание сохранено!", reply_markup=main_menu_kb())


@router.callback_query(F.data == "edit_interests")
async def edit_interests(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileForm.interests)
    await _safe_edit_text(callback,"Укажи свои интересы (через запятую):", reply_markup=back_kb())
    await callback.answer()


@router.message(ProfileForm.interests)
async def process_interests(message: Message, state: FSMContext, session: AsyncSession):
    result = await session.execute(
        select(Profile).join(User).where(User.telegram_id == message.from_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile:
        profile.interests = message.text
        profile.completeness = calculate_completeness(profile)
        await session.commit()
        await _on_profile_updated(session, profile.user_id)

    await state.clear()
    await message.answer("✅ Интересы сохранены!", reply_markup=main_menu_kb())


@router.callback_query(F.data == "edit_photo")
async def edit_photo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileForm.photo)
    await _safe_edit_text(callback,"Пришли своё фото:", reply_markup=back_kb())
    await callback.answer()


@router.message(ProfileForm.photo, F.photo)
async def process_photo(message: Message, state: FSMContext, session: AsyncSession, bot):
    result = await session.execute(
        select(Profile).join(User).where(User.telegram_id == message.from_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile and s3:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        
        photo_key = await s3.upload_photo(profile.user_id, file_bytes.read(), f"{photo.file_id}.jpg")

        keys = parse_photo_keys(profile.photo_keys)
        keys.append(photo_key)
        profile.photo_keys = json.dumps(keys)
        profile.photo_count = len(keys)
        profile.completeness = calculate_completeness(profile)
        await session.commit()
        await _on_profile_updated(session, profile.user_id)

    await state.clear()
    await message.answer("✅ Фото сохранено!", reply_markup=main_menu_kb())


@router.callback_query(F.data == "search_settings")
async def search_settings(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(
        select(Preference).join(User).where(User.telegram_id == callback.from_user.id)
    )
    pref = result.scalar_one_or_none()

    if pref:
        gender_text = "Мужской" if pref.preferred_gender == Gender.MALE else "Женский" if pref.preferred_gender == Gender.FEMALE else "Любой"
        text = (
            "⚙️ Настройки поиска:\n\n"
            f"⚧ Искать: {gender_text}\n"
            f"🎂 Возраст: {pref.min_age}-{pref.max_age}\n"
            f"🏙 Город: {pref.preferred_city or 'Любой'}"
        )
    else:
        text = "Настройки не найдены"

    await _safe_edit_text(callback,text, reply_markup=search_settings_kb())
    await callback.answer()


async def _on_profile_updated(session: AsyncSession, user_id: int):
    await recalculate_rating(session, user_id)
    if publisher:
        await publisher.publish_profile_updated(user_id)
    if cache:
        await cache.invalidate_all()


async def _load_profiles_to_cache(session: AsyncSession, current_user: User, pref: Preference | None):
    viewed_result = await session.execute(
        select(Interaction.to_user_id).where(Interaction.from_user_id == current_user.id)
    )
    viewed_ids = [row[0] for row in viewed_result.fetchall()]
    viewed_ids.append(current_user.id)

    query = select(Profile).join(User).join(Rating, User.id == Rating.user_id).where(
        Profile.user_id.not_in(viewed_ids),
        Profile.completeness > 0.3
    )

    if pref:
        if pref.preferred_gender:
            query = query.where(Profile.gender == pref.preferred_gender)
        if pref.min_age:
            query = query.where(Profile.age >= pref.min_age)
        if pref.max_age:
            query = query.where(Profile.age <= pref.max_age)
        if pref.preferred_city:
            query = query.where(Profile.city == pref.preferred_city)

    query = query.order_by(Rating.combined_score.desc()).limit(PROFILE_BATCH_SIZE)

    result = await session.execute(query)
    profiles = result.scalars().all()

    if cache and profiles:
        profiles_data = []
        for p in profiles:
            profiles_data.append({
                "user_id": p.user_id,
                "name": p.name,
                "age": p.age,
                "gender": p.gender.value if p.gender else None,
                "city": p.city,
                "description": p.description,
                "interests": p.interests,
                "photo_keys": parse_photo_keys(p.photo_keys),
            })
        await cache.load_profiles(current_user.id, profiles_data)

    return profiles


def _format_profile_text(profile_data: dict) -> str:
    gender = profile_data.get("gender")
    gender_text = "👨" if gender == "male" else "👩" if gender == "female" else ""
    return (
        f"{gender_text} {profile_data.get('name') or 'Без имени'}, {profile_data.get('age') or '?'}\n"
        f"🏙 {profile_data.get('city') or 'Город не указан'}\n\n"
        f"📝 {profile_data.get('description') or 'Нет описания'}\n\n"
        f"💡 Интересы: {profile_data.get('interests') or 'Не указаны'}"
    )


@router.callback_query(F.data == "view_profiles")
async def view_profiles(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user_result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    current_user = user_result.scalar_one_or_none()

    if not current_user:
        await _safe_edit_text(callback,"Сначала зарегистрируйся с /start")
        await callback.answer()
        return

    pref_result = await session.execute(
        select(Preference).where(Preference.user_id == current_user.id)
    )
    pref = pref_result.scalar_one_or_none()

    profile_data = None

    if cache:
        cached = await cache.get_next_profile(current_user.id)
        if cached:
            profile_data = cached
        else:
            profiles = await _load_profiles_to_cache(session, current_user, pref)
            if profiles and cache:
                cached = await cache.get_next_profile(current_user.id)
                if cached:
                    profile_data = cached

    if not profile_data:
        viewed_result = await session.execute(
            select(Interaction.to_user_id).where(Interaction.from_user_id == current_user.id)
        )
        viewed_ids = [row[0] for row in viewed_result.fetchall()]
        viewed_ids.append(current_user.id)

        query = select(Profile).join(User).join(Rating, User.id == Rating.user_id).where(
            Profile.user_id.not_in(viewed_ids),
            Profile.completeness > 0.3
        )

        if pref:
            if pref.preferred_gender:
                query = query.where(Profile.gender == pref.preferred_gender)
            if pref.min_age:
                query = query.where(Profile.age >= pref.min_age)
            if pref.max_age:
                query = query.where(Profile.age <= pref.max_age)
            if pref.preferred_city:
                query = query.where(Profile.city == pref.preferred_city)

        query = query.order_by(Rating.combined_score.desc()).limit(1)

        result = await session.execute(query)
        profile = result.scalar_one_or_none()

        if profile:
            profile_data = {
                "user_id": profile.user_id,
                "name": profile.name,
                "age": profile.age,
                "gender": profile.gender.value if profile.gender else None,
                "city": profile.city,
                "description": profile.description,
                "interests": profile.interests,
                "photo_keys": parse_photo_keys(profile.photo_keys),
            }

    if profile_data:
        await state.update_data(viewing_user_id=profile_data["user_id"])

        view_interaction = Interaction(
            from_user_id=current_user.id,
            to_user_id=profile_data["user_id"],
            action="view"
        )
        session.add(view_interaction)
        await session.commit()

        text = _format_profile_text(profile_data)
        await _show_photo_or_text(
            callback,
            text,
            view_profile_kb(),
            profile_data.get("photo_keys"),
        )
    else:
        await _safe_edit_text(callback,
            "😔 Пока нет подходящих анкет.\n\nПопробуй изменить настройки поиска или зайди позже!",
            reply_markup=back_kb()
        )

    await callback.answer()


@router.callback_query(F.data == "like")
async def like_profile(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    viewing_user_id = data.get("viewing_user_id")

    if not viewing_user_id:
        await callback.answer("Ошибка")
        return

    user_result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    current_user = user_result.scalar_one_or_none()

    like_interaction = Interaction(
        from_user_id=current_user.id,
        to_user_id=viewing_user_id,
        action="like"
    )
    session.add(like_interaction)
    LIKES.inc()

    mutual_result = await session.execute(
        select(Interaction).where(
            Interaction.from_user_id == viewing_user_id,
            Interaction.to_user_id == current_user.id,
            Interaction.action == "like"
        )
    )
    mutual_like = mutual_result.scalar_one_or_none()

    if mutual_like:
        user1_id = min(current_user.id, viewing_user_id)
        user2_id = max(current_user.id, viewing_user_id)

        existing_match = await session.execute(
            select(Match).where(
                Match.user1_id == user1_id,
                Match.user2_id == user2_id,
                Match.is_active == True,
            )
        )
        if existing_match.scalar_one_or_none() is None:
            session.add(Match(user1_id=user1_id, user2_id=user2_id))
            MATCHES.inc()

        await session.commit()

        await recalculate_rating(session, current_user.id)
        await recalculate_rating(session, viewing_user_id)

        if publisher:
            await publisher.publish_match_created(user1_id, user2_id)

        other_result = await session.execute(
            select(Profile).where(Profile.user_id == viewing_user_id)
        )
        other_profile = other_result.scalar_one_or_none()

        await _safe_edit_text(callback,
            f"🎉 У вас взаимная симпатия с {other_profile.name if other_profile else 'пользователем'}!\n\n"
            "Можете начать общение!",
            reply_markup=main_menu_kb()
        )
    else:
        await session.commit()
        await recalculate_rating(session, viewing_user_id)
        if publisher:
            await publisher.publish_interaction(current_user.id, viewing_user_id, "like")
        await view_profiles(callback, session, state)

    await callback.answer()


@router.callback_query(F.data == "skip")
async def skip_profile(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    viewing_user_id = data.get("viewing_user_id")

    if not viewing_user_id:
        await callback.answer("Ошибка")
        return

    user_result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    current_user = user_result.scalar_one_or_none()

    skip_interaction = Interaction(
        from_user_id=current_user.id,
        to_user_id=viewing_user_id,
        action="skip"
    )
    session.add(skip_interaction)
    await session.commit()

    await recalculate_rating(session, viewing_user_id)
    if publisher:
        await publisher.publish_interaction(current_user.id, viewing_user_id, "skip")

    await view_profiles(callback, session, state)
    await callback.answer()


@router.callback_query(F.data == "my_matches")
async def show_matches(callback: CallbackQuery, session: AsyncSession):
    user_result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    current_user = user_result.scalar_one_or_none()

    if not current_user:
        await callback.answer("Ошибка")
        return

    matches_result = await session.execute(
        select(Match).where(
            or_(
                Match.user1_id == current_user.id,
                Match.user2_id == current_user.id
            ),
            Match.is_active == True
        )
    )
    matches = matches_result.scalars().all()

    if matches:
        text = "💕 Твои мэтчи:\n\n"
        for i, match in enumerate(matches, 1):
            other_user_id = match.user2_id if match.user1_id == current_user.id else match.user1_id
            profile_result = await session.execute(
                select(Profile).where(Profile.user_id == other_user_id)
            )
            profile = profile_result.scalar_one_or_none()
            if profile:
                text += f"{i}. {profile.name or 'Без имени'}, {profile.age or '?'}\n"
    else:
        text = "💔 Пока нет мэтчей.\n\nПродолжай смотреть анкеты!"

    await _safe_edit_text(callback,text, reply_markup=back_kb())
    await callback.answer()


@router.callback_query(F.data == "delete_profile")
async def confirm_delete(callback: CallbackQuery):
    await _safe_edit_text(callback,
        "⚠️ Ты уверен, что хочешь удалить свою анкету?\n\nЭто действие нельзя отменить.",
        reply_markup=delete_confirm_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_delete")
async def delete_profile(callback: CallbackQuery, session: AsyncSession):
    user_result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        await callback.answer("Ошибка")
        return

    for model in [Rating, Preference, Profile]:
        result = await session.execute(select(model).where(model.user_id == user.id))
        obj = result.scalar_one_or_none()
        if obj:
            await session.delete(obj)

    await session.commit()

    profile = Profile(user_id=user.id)
    session.add(profile)
    pref = Preference(user_id=user.id)
    session.add(pref)
    rating = Rating(user_id=user.id)
    session.add(rating)
    await session.commit()

    if cache:
        await cache.invalidate_all()

    await _safe_edit_text(callback,
        "🗑 Анкета удалена.\n\nМожешь заполнить новую!",
        reply_markup=main_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "edit_search")
async def edit_search_menu(callback: CallbackQuery):
    await _safe_edit_text(callback,
        "⚙️ Что изменить в настройках поиска?",
        reply_markup=search_settings_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "edit_search_gender")
async def edit_search_gender(callback: CallbackQuery):
    await _safe_edit_text(callback,"Кого ищешь?", reply_markup=search_gender_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("search_"))
async def process_search_gender(callback: CallbackQuery, session: AsyncSession):
    user_result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = user_result.scalar_one_or_none()
    pref_result = await session.execute(
        select(Preference).where(Preference.user_id == user.id)
    )
    pref = pref_result.scalar_one_or_none()

    if pref:
        if callback.data == "search_male":
            pref.preferred_gender = Gender.MALE
        elif callback.data == "search_female":
            pref.preferred_gender = Gender.FEMALE
        else:
            pref.preferred_gender = None
        await session.commit()

    if cache:
        await cache.invalidate(user.id)

    await _safe_edit_text(callback,"✅ Настройки поиска обновлены!", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "edit_search_age")
async def edit_search_age(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PreferenceForm.min_age)
    await _safe_edit_text(callback,
        "Введи минимальный возраст (18-100):",
        reply_markup=back_kb()
    )
    await callback.answer()


@router.message(PreferenceForm.min_age)
async def process_min_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if 18 <= age <= 100:
            await state.update_data(min_age=age)
            await state.set_state(PreferenceForm.max_age)
            await message.answer("Теперь введи максимальный возраст:")
        else:
            await message.answer("❌ Возраст должен быть от 18 до 100")
    except ValueError:
        await message.answer("❌ Введи число")


@router.message(PreferenceForm.max_age)
async def process_max_age(message: Message, state: FSMContext, session: AsyncSession):
    try:
        age = int(message.text)
        if 18 <= age <= 100:
            data = await state.get_data()
            min_age = data.get("min_age", 18)

            user_result = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = user_result.scalar_one_or_none()
            pref_result = await session.execute(
                select(Preference).where(Preference.user_id == user.id)
            )
            pref = pref_result.scalar_one_or_none()

            if pref:
                pref.min_age = min_age
                pref.max_age = age
                await session.commit()

            if cache:
                await cache.invalidate(user.id)

            await state.clear()
            await message.answer(
                f"✅ Диапазон возраста: {min_age}-{age}",
                reply_markup=main_menu_kb()
            )
        else:
            await message.answer("❌ Возраст должен быть от 18 до 100")
    except ValueError:
        await message.answer("❌ Введи число")


@router.callback_query(F.data == "edit_search_city")
async def edit_search_city(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PreferenceForm.city)
    await _safe_edit_text(callback,"Введи город для поиска (или 'любой'):", reply_markup=back_kb())
    await callback.answer()


@router.message(PreferenceForm.city)
async def process_search_city(message: Message, state: FSMContext, session: AsyncSession):
    user_result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = user_result.scalar_one_or_none()
    pref_result = await session.execute(
        select(Preference).where(Preference.user_id == user.id)
    )
    pref = pref_result.scalar_one_or_none()

    if pref:
        pref.preferred_city = None if message.text.lower() in ("любой", "любой город", "все") else message.text
        await session.commit()

    if cache:
        await cache.invalidate(user.id)

    await state.clear()
    await message.answer("✅ Город поиска обновлён!", reply_markup=main_menu_kb())


@router.callback_query(F.data == "back")
async def go_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_main_menu(callback)
