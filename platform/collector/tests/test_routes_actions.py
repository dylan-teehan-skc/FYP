"""Tests for action endpoints (run-analysis, run-demo, status)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from collector.routes import actions


class TestRunAnalysis:
    async def test_start(self, client: AsyncClient) -> None:
        with patch.object(actions, "_running_tasks", {}):
            with patch.object(actions, "_run_analysis_task", new_callable=AsyncMock):
                response = await client.post("/actions/run-analysis")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "started"

    async def test_already_running(self, client: AsyncClient) -> None:
        fake_task = asyncio.ensure_future(asyncio.sleep(100))
        with patch.object(actions, "_running_tasks", {"analysis": fake_task}):
            response = await client.post("/actions/run-analysis")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "already_running"
            fake_task.cancel()


class TestRunDemo:
    async def test_start(self, client: AsyncClient) -> None:
        with patch.object(actions, "_running_tasks", {}):
            with patch.object(actions, "_run_demo_task", new_callable=AsyncMock):
                response = await client.post(
                    "/actions/run-demo", json={"rounds": 2}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "started"
                assert data["total_scenarios"] == 10

    async def test_clamp_rounds(self, client: AsyncClient) -> None:
        with patch.object(actions, "_running_tasks", {}):
            with patch.object(actions, "_run_demo_task", new_callable=AsyncMock):
                response = await client.post(
                    "/actions/run-demo", json={"rounds": 50}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["total_scenarios"] == 50

    async def test_already_running(self, client: AsyncClient) -> None:
        fake_task = asyncio.ensure_future(asyncio.sleep(100))
        with patch.object(actions, "_running_tasks", {"demo": fake_task}):
            response = await client.post(
                "/actions/run-demo", json={"rounds": 1}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "already_running"
            fake_task.cancel()


class TestStatus:
    async def test_idle(self, client: AsyncClient) -> None:
        with patch.object(actions, "_running_tasks", {}):
            response = await client.get("/actions/status")
            assert response.status_code == 200
            data = response.json()
            assert data["demo_running"] is False
            assert data["analysis_running"] is False
            assert data["message"] == "Idle"

    async def test_demo_running(self, client: AsyncClient) -> None:
        fake_task = asyncio.ensure_future(asyncio.sleep(100))
        with patch.object(actions, "_running_tasks", {"demo": fake_task}):
            response = await client.get("/actions/status")
            data = response.json()
            assert data["demo_running"] is True
            assert "Demo running" in data["message"]
            fake_task.cancel()

    async def test_both_running(self, client: AsyncClient) -> None:
        t1 = asyncio.ensure_future(asyncio.sleep(100))
        t2 = asyncio.ensure_future(asyncio.sleep(100))
        with patch.object(actions, "_running_tasks", {"demo": t1, "analysis": t2}):
            response = await client.get("/actions/status")
            data = response.json()
            assert data["demo_running"] is True
            assert data["analysis_running"] is True
            t1.cancel()
            t2.cancel()


class TestRunSubprocess:
    async def test_success(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"output", b"")
        with patch("collector.routes.actions.asyncio.create_subprocess_exec",
                    new_callable=AsyncMock, return_value=mock_proc):
            result = await actions._run_subprocess("test", "echo", "hello")
            assert result == "output"

    async def test_failure_raises(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = (b"", b"error details")
        with patch("collector.routes.actions.asyncio.create_subprocess_exec",
                    new_callable=AsyncMock, return_value=mock_proc):
            try:
                await actions._run_subprocess("test", "false")
                assert False, "Should have raised RuntimeError"
            except RuntimeError as e:
                assert "failed" in str(e)
                assert "error details" in str(e)


class TestAnalysisTask:
    async def test_cleans_up_on_success(self) -> None:
        with patch.object(actions, "_running_tasks", {"analysis": AsyncMock()}):
            with patch.object(actions, "_run_subprocess", new_callable=AsyncMock):
                await actions._run_analysis_task()
                assert "analysis" not in actions._running_tasks

    async def test_cleans_up_on_failure(self) -> None:
        with patch.object(actions, "_running_tasks", {"analysis": AsyncMock()}):
            with patch.object(
                actions, "_run_subprocess",
                new_callable=AsyncMock,
                side_effect=RuntimeError("boom"),
            ):
                try:
                    await actions._run_analysis_task()
                except RuntimeError:
                    pass
                assert "analysis" not in actions._running_tasks


class TestDemoTask:
    async def test_cleans_up_on_success(self) -> None:
        with patch.object(actions, "_running_tasks", {"demo": AsyncMock()}):
            with patch.object(actions, "_run_subprocess", new_callable=AsyncMock):
                await actions._run_demo_task(2)
                assert "demo" not in actions._running_tasks

    async def test_cleans_up_on_failure(self) -> None:
        with patch.object(actions, "_running_tasks", {"demo": AsyncMock()}):
            with patch.object(
                actions, "_run_subprocess",
                new_callable=AsyncMock,
                side_effect=RuntimeError("boom"),
            ):
                try:
                    await actions._run_demo_task(1)
                except RuntimeError:
                    pass
                assert "demo" not in actions._running_tasks
