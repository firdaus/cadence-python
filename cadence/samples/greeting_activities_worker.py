import logging
from cadence.workerfactory import WorkerFactory

logging.basicConfig(level=logging.DEBUG)


class GreetingActivitiesImpl:
    def compose_greeting(self, greeting: str, name: str):
        # raise Exception("Error from Python")
        return greeting + " " + name + "!"


factory = WorkerFactory("localhost", 7933, "sample")
worker = factory.new_worker("python-tasklist")
worker.register_activities_implementation(GreetingActivitiesImpl(), "GreetingActivities")
factory.start()
