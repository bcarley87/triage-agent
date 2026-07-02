from triage_agent.delivery.dispatcher import OutreachDispatcher


def test_dispatcher_dispatch_returns_none() -> None:
    dispatcher = OutreachDispatcher()
    result = dispatcher.dispatch("candidate-123", "sms", "Please call us back.")
    assert result is None


def test_dispatcher_accepts_all_channels() -> None:
    dispatcher = OutreachDispatcher()
    for channel in ("phone", "sms", "email"):
        dispatcher.dispatch("candidate-123", channel, "Test message")
