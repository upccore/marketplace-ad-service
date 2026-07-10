import pytest

from src.application.exceptions import AdNotFoundError
from src.application.usecases.create_ad import CreateAd
from src.application.usecases.delete_ad import DeleteAd
from src.application.usecases.increment_ad_views import IncrementAdViews
from tests.conftest import FakeUnitOfWork


@pytest.mark.asyncio
async def test_increment_ad_views_bumps_counter(fake_uow: FakeUnitOfWork) -> None:
    create = CreateAd(fake_uow)
    created = await create.execute(
        user_id=1,
        title="T",
        description="d",
        price=100,
        category="c",
        city="x",
    )

    increment = IncrementAdViews(fake_uow)
    ad = await increment.execute(created.id)
    assert ad.views == 1

    ad = await increment.execute(created.id)
    assert ad.views == 2


@pytest.mark.asyncio
async def test_increment_ad_views_not_found(fake_uow: FakeUnitOfWork) -> None:
    increment = IncrementAdViews(fake_uow)

    with pytest.raises(AdNotFoundError):
        await increment.execute(999)


@pytest.mark.asyncio
async def test_increment_ad_views_on_archived_not_found(
    fake_uow: FakeUnitOfWork,
) -> None:
    create = CreateAd(fake_uow)
    created = await create.execute(
        user_id=1,
        title="T",
        description="d",
        price=100,
        category="c",
        city="x",
    )
    delete = DeleteAd(fake_uow)
    await delete.execute(ad_id=created.id, user_id=1)

    increment = IncrementAdViews(fake_uow)
    with pytest.raises(AdNotFoundError):
        await increment.execute(created.id)
