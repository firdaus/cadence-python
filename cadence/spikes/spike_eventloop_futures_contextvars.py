import asyncio
import contextvars
from asyncio import Future
from dataclasses import dataclass


@dataclass
class WorkflowContext:
    name: str
    activity_future: Future = None


workflow_context = contextvars.ContextVar("workflow_context")


def call_activity_method():
    activity_future = asyncio.get_event_loop().create_future()
    workflow_context.get().activity_future = activity_future
    return activity_future


def get_workflow_name():
    return workflow_context.get().name


async def workflow_proc(context):
    workflow_context.set(context)
    print(f"[{get_workflow_name()}] Coroutine Startup")

    print(f"[{get_workflow_name()}] Coroutine Waiting on Future 1")
    result = await call_activity_method()
    print(f"[{get_workflow_name()}] Coroutine Unblocked 1: {result}")

    print(f"[{get_workflow_name()}] Coroutine Waiting on Future 2")
    result = await call_activity_method()
    print(f"[{get_workflow_name()}] Coroutine Unblocked 2: {result}")

    print(f"[{get_workflow_name()}] Coroutine Waiting on Future 3 ")
    result = await call_activity_method()
    print(f"[{get_workflow_name()}] Coroutine Unblocked 3: {result}")
    print(f"[{get_workflow_name()}] Coroutine Terminating")


def run_once(loop):
    loop.call_soon(loop.stop)
    loop.run_forever()


if __name__ == '__main__':
    event_loop = asyncio.get_event_loop()
    task1_context = WorkflowContext("worker 1")
    task1 = event_loop.create_task(workflow_proc(task1_context))
    task2_context = WorkflowContext("worker 2")
    task2 = event_loop.create_task(workflow_proc(task2_context))
    print("Iteration 1:")
    run_once(event_loop)
    task1_context.activity_future.set_result("result 1")
    print("Iteration 2:")
    run_once(event_loop)
    task1_context.activity_future.set_result("result 2")
    run_once(event_loop)
    task2_context.activity_future.set_result("result 1")
    run_once(event_loop)
    task2_context.activity_future.set_result("result 2")
    run_once(event_loop)
    task2_context.activity_future.set_result("result 3")
    run_once(event_loop)
    task1_context.activity_future.set_result("result 3")
    run_once(event_loop)

