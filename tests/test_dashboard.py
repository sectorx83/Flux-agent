from flux_agent.remote.dashboard import DASHBOARD_HTML


def test_dashboard_contains_responsive_agent_workspace():
    assert "Flux — Agent workspace" in DASHBOARD_HTML
    assert "@media(max-width:700px)" in DASHBOARD_HTML
    assert 'id="prompt"' in DASHBOARD_HTML
    assert 'id="tasklist"' in DASHBOARD_HTML
    assert 'id="outputPanel"' in DASHBOARD_HTML


def test_dashboard_uses_authenticated_api_and_session_scoped_token():
    assert 'Authorization:"Bearer "+token' in DASHBOARD_HTML
    assert 'sessionStorage.setItem("flux.remote.token",token)' in DASHBOARD_HTML
    assert 'fetch(path' in DASHBOARD_HTML
    assert '"/tasks"' in DASHBOARD_HTML
    assert '"/tasks/"+encodeURIComponent(id)' in DASHBOARD_HTML


def test_dashboard_supports_existing_flux_modes():
    assert '<option value="chat">' in DASHBOARD_HTML
    assert '<option value="plan"' in DASHBOARD_HTML
    assert '<option value="build">' in DASHBOARD_HTML


def test_dashboard_displays_task_result_and_error_safely():
    assert 'task.status==="completed"&&task.result' in DASHBOARD_HTML
    assert 'task.status==="failed"' in DASHBOARD_HTML
    assert 'output.textContent=task.result' in DASHBOARD_HTML
    assert 'output.textContent=task.error' in DASHBOARD_HTML
    assert 'navigator.clipboard.writeText' in DASHBOARD_HTML


def test_dashboard_explains_separate_remote_worker():
    assert "flux remote-worker" in DASHBOARD_HTML
    assert "Waiting in the queue" in DASHBOARD_HTML
