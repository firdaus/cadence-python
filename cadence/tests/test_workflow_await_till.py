from cadence.workflow import Workflow


def run_once(loop):
    loop.call_soon(loop.stop)
    loop.run_forever()


def test_await_till(monkeypatch, event_loop, decision_context):
    from unittest.mock import Mock
    workflow_task = Mock()
    workflow_task.decider = decision_context.decider
    monkeypatch.setattr("cadence.decision_loop.ITask.current", lambda: workflow_task)
    x = 0
    try:
        task = event_loop.create_task(Workflow.await_till(lambda: x == 2))
        run_once(event_loop)
        assert decision_context.awaited

        decision_context.unblock()
        run_once(event_loop)
        assert decision_context.awaited

        x = 2
        decision_context.unblock()
        run_once(event_loop)
        assert not decision_context.awaited
    finally:
        task.cancel()
