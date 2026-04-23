import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import User, Profile, Rating, Interaction, Match

logger = logging.getLogger(__name__)

PRIMARY_WEIGHT = 0.4
BEHAVIORAL_WEIGHT = 0.6


async def calculate_primary_score(session: AsyncSession, user_id: int) -> float:
    result = await session.execute(
        select(Profile).where(Profile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return 0.0

    completeness_score = profile.completeness or 0.0

    photo_score = min(profile.photo_count / 3, 1.0) if profile.photo_count else 0.0

    has_description = 1.0 if profile.description else 0.0

    return completeness_score * 0.5 + photo_score * 0.2 + has_description * 0.3


async def calculate_behavioral_score(session: AsyncSession, user_id: int) -> float:
    likes_received = await session.execute(
        select(func.count()).select_from(Interaction).where(
            Interaction.to_user_id == user_id,
            Interaction.action == "like"
        )
    )
    like_count = likes_received.scalar() or 0

    total_views = await session.execute(
        select(func.count()).select_from(Interaction).where(
            Interaction.to_user_id == user_id,
            Interaction.action.in_(["like", "skip"])
        )
    )
    total_count = total_views.scalar() or 0

    like_ratio = like_count / total_count if total_count > 0 else 0.5

    matches_count_result = await session.execute(
        select(func.count()).select_from(Match).where(
            (Match.user1_id == user_id) | (Match.user2_id == user_id),
            Match.is_active == True
        )
    )
    match_count = matches_count_result.scalar() or 0
    match_score = min(match_count / 5, 1.0)

    initiated_result = await session.execute(
        select(func.count()).select_from(Interaction).where(
            Interaction.from_user_id == user_id,
            Interaction.action == "like"
        )
    )
    initiated = initiated_result.scalar() or 0
    activity_score = min(initiated / 20, 1.0)

    return like_ratio * 0.4 + match_score * 0.3 + activity_score * 0.3


async def recalculate_rating(session: AsyncSession, user_id: int) -> Rating:
    primary = await calculate_primary_score(session, user_id)
    behavioral = await calculate_behavioral_score(session, user_id)
    combined = primary * PRIMARY_WEIGHT + behavioral * BEHAVIORAL_WEIGHT

    result = await session.execute(
        select(Rating).where(Rating.user_id == user_id)
    )
    rating = result.scalar_one_or_none()

    if rating:
        rating.primary_score = round(primary, 4)
        rating.behavioral_score = round(behavioral, 4)
        rating.combined_score = round(combined, 4)
    else:
        rating = Rating(
            user_id=user_id,
            primary_score=round(primary, 4),
            behavioral_score=round(behavioral, 4),
            combined_score=round(combined, 4),
        )
        session.add(rating)

    await session.commit()
    logger.info(f"Rating updated for user {user_id}: primary={primary:.4f} behavioral={behavioral:.4f} combined={combined:.4f}")
    return rating


async def recalculate_all_ratings(session: AsyncSession):
    result = await session.execute(select(User.id))
    user_ids = [row[0] for row in result.fetchall()]

    for user_id in user_ids:
        await recalculate_rating(session, user_id)

    logger.info(f"Recalculated ratings for {len(user_ids)} users")
