from unittest.mock import Mock, call

import pytest
from baby_steps import given, then, when
from pytest import raises

from vedro.core import Dispatcher, Report
from vedro.events import (
    CleanupEvent,
    ScenarioFailedEvent,
    ScenarioPassedEvent,
    ScenarioSkippedEvent,
)

from ._utils import (
    dispatcher,
    fire_arg_parsed_event,
    fire_failed_event,
    fire_startup_event,
    make_scenario_result,
    rerunner,
    scheduler_,
)

__all__ = ("rerunner", "scheduler_", "dispatcher")  # fixtures


@pytest.mark.asyncio
@pytest.mark.usefixtures(rerunner.__name__)
async def test_rerun_validation(dispatcher: Dispatcher):
    with when, raises(BaseException) as exc_info:
        await fire_arg_parsed_event(dispatcher, reruns=-1)

    with then:
        assert exc_info.type is AssertionError


@pytest.mark.asyncio
@pytest.mark.parametrize("reruns", [0, 1, 3])
@pytest.mark.usefixtures(rerunner.__name__)
async def test_rerun_failed(reruns: int, *, dispatcher: Dispatcher, scheduler_: Mock):
    with given:
        await fire_arg_parsed_event(dispatcher, reruns)
        await fire_startup_event(dispatcher, scheduler_)

        scenario_result = make_scenario_result().mark_failed()
        scenario_failed_event = ScenarioFailedEvent(scenario_result)

    with when:
        await dispatcher.fire(scenario_failed_event)

    with then:
        assert scheduler_.mock_calls == [call.schedule(scenario_result.scenario)] * reruns


@pytest.mark.asyncio
@pytest.mark.parametrize("reruns", [0, 1, 3])
@pytest.mark.usefixtures(rerunner.__name__)
async def test_dont_rerun_passed(reruns: int, *, dispatcher: Dispatcher, scheduler_: Mock):
    with given:
        await fire_arg_parsed_event(dispatcher, reruns)
        await fire_startup_event(dispatcher, scheduler_)

        scenario_result = make_scenario_result().mark_passed()
        scenario_passed_event = ScenarioPassedEvent(scenario_result)

    with when:
        await dispatcher.fire(scenario_passed_event)

    with then:
        assert scheduler_.mock_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("repeats", [0, 1])
@pytest.mark.usefixtures(rerunner.__name__)
async def test_dont_repeat_skipped(repeats: int, *, dispatcher: Dispatcher, scheduler_: Mock):
    with given:
        await fire_arg_parsed_event(dispatcher, repeats)
        await fire_startup_event(dispatcher, scheduler_)

        scenario_result = make_scenario_result().mark_skipped()
        scenario_skipped_event = ScenarioSkippedEvent(scenario_result)

    with when:
        await dispatcher.fire(scenario_skipped_event)

    with then:
        assert scheduler_.mock_calls == []


@pytest.mark.asyncio
@pytest.mark.usefixtures(rerunner.__name__)
async def test_dont_rerun_rerunned(dispatcher: Dispatcher, scheduler_: Mock):
    with given:
        await fire_arg_parsed_event(dispatcher, reruns=1)
        await fire_startup_event(dispatcher, scheduler_)

        scenario_failed_event = await fire_failed_event(dispatcher)
        scheduler_.reset_mock()

    with when:
        await dispatcher.fire(scenario_failed_event)

    with then:
        assert scheduler_.mock_calls == []


@pytest.mark.asyncio
@pytest.mark.usefixtures(rerunner.__name__)
async def test_add_summary(dispatcher: Dispatcher, scheduler_: Mock):
    with given:
        reruns = 3
        await fire_arg_parsed_event(dispatcher, reruns=reruns)
        await fire_startup_event(dispatcher, scheduler_)
        await fire_failed_event(dispatcher)

        report = Report()
        cleanup_event = CleanupEvent(report)

    with when:
        await dispatcher.fire(cleanup_event)

    with then:
        assert report.summary == [f"rerun 1 scenario, {reruns} times"]


@pytest.mark.asyncio
@pytest.mark.usefixtures(rerunner.__name__)
async def test_dont_add_summary(dispatcher: Dispatcher, scheduler_: Mock):
    with given:
        await fire_arg_parsed_event(dispatcher, reruns=0)
        await fire_startup_event(dispatcher, scheduler_)
        await fire_failed_event(dispatcher)

        report = Report()
        cleanup_event = CleanupEvent(report)

    with when:
        await dispatcher.fire(cleanup_event)

    with then:
        assert report.summary == []
