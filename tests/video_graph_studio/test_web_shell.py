from pathlib import Path


WEB = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio" / "web"


def test_shell_is_a_seven_stage_local_first_workspace_without_canvas_controls():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for stage in ("source", "videos", "translation", "voice", "output", "review", "activity"):
        assert f'data-stage="{stage}"' in html
        assert f'id="stage-{stage}"' in html
    assert 'id="creator-url"' in html
    assert 'id="discover-creator"' in html
    assert 'data-source-mode="creator"' in html
    assert 'data-source-mode="folder"' in html
    assert 'id="local-folder"' in html
    assert 'id="browse-folder"' in html
    assert 'id="video-catalog"' in html
    assert 'id="allow-partial-catalog"' in html
    assert 'id="load-all-videos-catalog"' in html
    assert 'id="video-search"' in html
    assert 'id="select-all-videos"' in html
    assert 'id="subtitle-status"' in html
    assert 'id="language-search"' in html
    assert 'id="translation-provider"' in html
    assert 'id="language-list"' in html
    assert 'id="voice-provider-list"' in html
    assert 'id="voice-list"' in html
    assert 'id="local-output-root"' in html
    assert 'id="optional-publication"' in html
    assert 'id="destination-matrix"' in html
    assert 'id="campaign-review"' in html
    assert 'id="start-campaign"' in html
    assert 'id="activity-timeline"' in html
    assert 'id="access-dialog"' in html
    assert 'workflow-canvas' not in html
    assert 'zoom-in' not in html and 'zoom-out' not in html and 'fit-graph' not in html
    assert 'class="port ' not in html
    assert "onclick=" not in html.lower()


def test_shell_loads_only_local_versioned_assets():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'href="/styles.css?v=12"' in html
    assert 'type="module" src="/app.js?v=12"' in html
    assert 'src="https://' not in html and 'href="https://' not in html


def test_client_runs_discovery_catalog_and_selected_campaign_through_versioned_contracts():
    script = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'api("/api/v1/contracts")' in script
    assert 'api("/api/v1/languages")' in script
    assert 'api("/api/v1/translation-providers")' in script
    assert 'api("/api/v1/voice-providers")' in script
    assert '/api/v1/folders?path=' in script
    assert 'encodeURIComponent(' in script
    assert '/creator-catalog`' in script
    assert 'templateId:"creator-profile"' in script
    assert 'buildCampaignPayload(state)' in script
    assert '"CMD-RUN-CREATE"' in script
    assert '"CMD-RUN-START"' in script
    assert 'TERMINAL_STATES.has(run.status)' in script
    assert 'sessionStorage.getItem("videoGraph.accessToken")' in script
    assert 'Authorization: `Bearer ${token}`' in script
    assert '"X-Workspace-Id": workspaceId' in script
    assert 'SOURCE_AVAILABLE' in script and 'SOURCE_MISSING' in script and 'UNKNOWN_ASR' in script
    assert 'READY_PRIVATE' in script and 'PLAN_ONLY' in script
    assert 'catalog.truncated' in script
    assert 'id="load-all-videos"' in script
    assert 'state.sourceMode==="folder"' in script
    assert 'state.currentRun=null' in script


def test_layout_is_responsive_and_uses_normal_document_flow():
    styles = (WEB / "styles.css").read_text(encoding="utf-8")
    assert ".workspace-shell" in styles
    assert ".stage-rail" in styles
    assert ".catalog-grid" in styles
    assert ".destination-grid" in styles
    assert ".source-mode-grid" in styles
    assert ".provider-options" in styles
    assert "@media (max-width:900px)" in styles
    assert ".graph-track" not in styles
    assert "cursor: grab" not in styles
