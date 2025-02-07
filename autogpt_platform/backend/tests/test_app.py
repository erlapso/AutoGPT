import pytest
from unittest.mock import MagicMock
from backend import app

def test_run_processes_exception_stop_called():
    """
    Test that run_processes calls stop() on all processes even if one process's start() method raises an exception.
    """
    p1 = MagicMock(name="Process1")
    p2 = MagicMock(name="Process2")
    p3 = MagicMock(name="Process3")
    
    def faulty_start(*args, **kwargs):
        if kwargs.get("background"):
            raise Exception("Intentional Exception")
    p2.start.side_effect = faulty_start
    
    with pytest.raises(Exception, match="Intentional Exception"):
        app.run_processes(p1, p2, p3)
    
    p1.start.assert_called_once_with(background=True)
    p2.start.assert_called_once_with(background=True)
    p3.start.assert_not_called()
    
    p1.stop.assert_called_once()
    p2.stop.assert_called_once()
    p3.stop.assert_called_once()

def test_run_processes_success_calls_start_and_stop():
    """
    Test that run_processes successfully calls start on all processes with the correct
    background parameter and then calls stop on all processes when no exceptions occur.
    """
    p1 = MagicMock(name="Process1")
    p2 = MagicMock(name="Process2")
    p3 = MagicMock(name="Process3")
    
    app.run_processes(p1, p2, p3, test_kwarg="test")
    
    p1.start.assert_called_once_with(background=True, test_kwarg="test")
    p2.start.assert_called_once_with(background=True, test_kwarg="test")
    p3.start.assert_called_once_with(background=False, test_kwarg="test")
    
    p1.stop.assert_called_once()
    p2.stop.assert_called_once()
    p3.stop.assert_called_once()

def test_run_processes_last_process_failure_calls_stop_on_all():
    """
    Test that if the start() method of the last process (foreground process) raises an exception,
    all processes have their stop() method called.
    """
    p1 = MagicMock(name="Process1")
    p2 = MagicMock(name="Process2")
    p3 = MagicMock(name="Process3")
    
    def faulty_start(*args, **kwargs):
        if not kwargs.get("background"):
            raise Exception("Foreground process failure")
    p3.start.side_effect = faulty_start
    
    with pytest.raises(Exception, match="Foreground process failure"):
        app.run_processes(p1, p2, p3, custom_kwarg="value")
    
    p1.start.assert_called_once_with(background=True, custom_kwarg="value")
    p2.start.assert_called_once_with(background=True, custom_kwarg="value")
    p3.start.assert_called_once_with(background=False, custom_kwarg="value")
    
    p1.stop.assert_called_once()
    p2.stop.assert_called_once()
    p3.stop.assert_called_once()

def test_run_processes_empty_raises_index_error():
    """
    Test that run_processes raises an IndexError when called without any processes.
    """
    with pytest.raises(IndexError):
        app.run_processes()

def test_run_processes_stop_failure_propagates_exception():
    """
    Test that if the stop() method of a process fails (raises an exception),
    run_processes propagates that exception and stops calling stop() on subsequent processes.
    """
    p1 = MagicMock(name="Process1")
    p2 = MagicMock(name="Process2")
    p3 = MagicMock(name="Process3")
    
    p1.stop.side_effect = Exception("Stop failure")
    
    with pytest.raises(Exception, match="Stop failure"):
        app.run_processes(p1, p2, p3, custom_kwarg="value")
    
    p1.start.assert_called_once_with(background=True, custom_kwarg="value")
    p2.start.assert_called_once_with(background=True, custom_kwarg="value")
    p3.start.assert_called_once_with(background=False, custom_kwarg="value")
    
    p1.stop.assert_called_once()
    p2.stop.assert_not_called()
    p3.stop.assert_not_called()

def test_run_processes_single_process_success():
    """
    Test that when run_processes is called with a single process, it starts the process
    in the foreground (background=False) and subsequently calls stop() on it.
    """
    process = MagicMock(name="SingleProcess")
    app.run_processes(process, test_kwarg="value")
    
    process.start.assert_called_once_with(background=False, test_kwarg="value")
    process.stop.assert_called_once()

def test_run_processes_call_order():
    """
    Test that run_processes calls the start() methods in order
    (all processes except the last with background=True and the last with background=False)
    and then calls stop() on all processes in the same original order.
    """
    call_log = []
    
    def make_start(name):
        def start(background, **kwargs):
            call_log.append(("start", name, background))
        return start

    def make_stop(name):
        def stop():
            call_log.append(("stop", name))
        return stop

    p1 = MagicMock(name="Process1")
    p2 = MagicMock(name="Process2")
    p3 = MagicMock(name="Process3")
    
    # Override start and stop methods with custom functions that log the calls.
    p1.start.side_effect = make_start("Process1")
    p2.start.side_effect = make_start("Process2")
    p3.start.side_effect = make_start("Process3")
    p1.stop.side_effect = make_stop("Process1")
    p2.stop.side_effect = make_stop("Process2")
    p3.stop.side_effect = make_stop("Process3")
    
    # Run processes with an additional keyword argument.
    app.run_processes(p1, p2, p3, dummy="value")
    
    expected_log = [
        ("start", "Process1", True),
        ("start", "Process2", True),
        ("start", "Process3", False),
        ("stop", "Process1"),
        ("stop", "Process2"),
        ("stop", "Process3"),
    ]
    assert call_log == expected_log
