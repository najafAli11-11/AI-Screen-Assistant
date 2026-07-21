from app.services.session_store import SessionStore


def test_session_store_tracks_context_window():
    store = SessionStore()
    session = store.create("en", "tester")

    for index in range(5):
        session.add_exchange(f"question {index}", f"answer {index}")

    assert store.get(session.session_id) is session
    assert len(session.context_window) == 3
    assert session.context_window[0]["user"] == "question 2"
