from cadence.workflow import signal_method, SignalMethod


def test_signal_method():
    class TestWorkflow:
        @signal_method()
        def the_signal_method(self):
            pass

    assert TestWorkflow.the_signal_method._signal_method
    assert isinstance(TestWorkflow.the_signal_method._signal_method, SignalMethod)
    assert TestWorkflow.the_signal_method._signal_method.name == "TestWorkflow::the_signal_method"


def test_signal_method_no_paren():
    class TestWorkflow:
        @signal_method
        def the_signal_method(self):
            pass

    assert TestWorkflow.the_signal_method._signal_method
    assert isinstance(TestWorkflow.the_signal_method._signal_method, SignalMethod)
    assert TestWorkflow.the_signal_method._signal_method.name == "TestWorkflow::the_signal_method"


def test_signal_method_custom_name():
    class TestWorkflow:
        @signal_method(name="blah")
        def the_signal_method(self):
            pass
    assert TestWorkflow.the_signal_method._signal_method.name == "blah"
