import base64
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.async_api import async_playwright

NAV_TIMEOUT_MS = 20000
ACTION_TIMEOUT_MS = 10000

_playwright = None
_browser = None
_sessions = {}

FIELD_EXTRACTION_JS = """
() => {
    const isVisible = (el) => {
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || el.offsetParent === null) return false;
        // Some component libraries keep a hidden proxy input around purely so
        // native HTML5 validation still fires for a custom widget — it's not
        // a real interactive field, so skip anything explicitly aria-hidden.
        if (el.getAttribute('aria-hidden') === 'true') return false;
        return true;
    };

    const getLabel = (el) => {
        if (el.id) {
            const label = document.querySelector(`label[for="${el.id}"]`);
            if (label) return label.innerText.trim();
        }
        const parentLabel = el.closest('label');
        if (parentLabel) {
            // The control itself (and its own option text, for selects) can be
            // nested inside the label — strip it out before reading the text.
            const clone = parentLabel.cloneNode(true);
            clone.querySelectorAll('input, select, textarea, button').forEach(c => c.remove());
            const text = clone.innerText.trim();
            if (text) return text;
        }
        if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
        if (el.placeholder) return el.placeholder;
        return '';
    };

    const elements = Array.from(document.querySelectorAll('input, textarea, select, button'));
    const fields = [];
    let index = 0;
    for (const el of elements) {
        const tag = el.tagName.toLowerCase();
        let type = (el.getAttribute('type') || tag).toLowerCase();
        if (type === 'hidden' || !isVisible(el)) continue;

        // react-select and similar libraries render a plain text <input> that
        // is really a searchable dropdown trigger, not free text — the ARIA
        // role is the reliable signal, not the tag/type.
        const isCombobox = el.getAttribute('role') === 'combobox';
        if (isCombobox) type = 'combobox';

        el.setAttribute('data-sanctum-index', String(index));
        const field = {
            index,
            tag,
            type,
            name: el.getAttribute('name') || '',
            label: getLabel(el),
            placeholder: el.getAttribute('placeholder') || '',
            required: el.hasAttribute('required'),
            value: el.value || '',
        };
        if (tag === 'select') {
            field.options = Array.from(el.options).map(o => ({ value: o.value, label: o.text }));
        }
        if (type === 'checkbox' || type === 'radio') {
            field.checked = el.checked;
        }
        if (tag === 'button' || type === 'submit' || type === 'button') {
            field.text = (el.innerText || el.value || '').trim();
        }
        fields.push(field);
        index++;
    }
    return fields;
}
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _playwright, _browser
    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(headless=True)
    yield
    await _browser.close()
    await _playwright.stop()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_page(session_id: str):
    page = _sessions.get(session_id)
    if not page:
        raise HTTPException(status_code=404, detail=f"No session with id {session_id}")
    return page


class NavigateRequest(BaseModel):
    url: str


class FillRequest(BaseModel):
    index: int
    value: str


class ClickRequest(BaseModel):
    index: int


class ComboboxRequest(BaseModel):
    index: int
    value: str


OPTION_SELECTOR = '[role="option"]'


@app.post("/session")
async def create_session():
    context = await _browser.new_context()
    page = await context.new_page()
    session_id = str(uuid.uuid4())
    _sessions[session_id] = page
    return {"session_id": session_id}


@app.delete("/session/{session_id}")
async def close_session(session_id: str):
    page = _get_page(session_id)
    await page.context.close()
    del _sessions[session_id]
    return {"message": "Session closed"}


@app.post("/session/{session_id}/navigate")
async def navigate(session_id: str, body: NavigateRequest):
    page = _get_page(session_id)
    try:
        await page.goto(body.url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Navigation failed: {exc}")
    return {"url": page.url, "title": await page.title()}


@app.get("/session/{session_id}/fields")
async def get_fields(session_id: str):
    page = _get_page(session_id)
    fields = await page.evaluate(FIELD_EXTRACTION_JS)
    return {"fields": fields}


@app.post("/session/{session_id}/fill")
async def fill_field(session_id: str, body: FillRequest):
    page = _get_page(session_id)
    selector = f'[data-sanctum-index="{body.index}"]'

    try:
        tag = await page.eval_on_selector(selector, "el => el.tagName.toLowerCase()")
        field_type = await page.eval_on_selector(selector, "el => el.type || ''")
    except Exception:
        raise HTTPException(status_code=400, detail=f"No field with index {body.index} on the current page")

    # Fields marked type "combobox" by /fields are usually meant for
    # select_combobox, but some (e.g. Google Places-style autocomplete) have
    # role="combobox" purely for accessibility and only ever accept free
    # text — no role="option" list ever appears for those. Rather than guess,
    # plain fill() is still allowed here; select_combobox is the one to try
    # first for anything that looks like a closed set of choices.
    try:
        if tag == "select":
            await page.select_option(selector, body.value, timeout=ACTION_TIMEOUT_MS)
        elif field_type in ("checkbox", "radio"):
            if body.value.strip().lower() in ("true", "1", "yes", "on"):
                await page.check(selector, timeout=ACTION_TIMEOUT_MS)
            else:
                await page.uncheck(selector, timeout=ACTION_TIMEOUT_MS)
        else:
            await page.fill(selector, body.value, timeout=ACTION_TIMEOUT_MS)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fill field {body.index}: {exc}")

    return {"message": f"Filled field {body.index}"}


@app.post("/session/{session_id}/select_combobox")
async def select_combobox(session_id: str, body: ComboboxRequest):
    page = _get_page(session_id)
    selector = f'[data-sanctum-index="{body.index}"]'
    key_js = "els => els.map(e => e.id || e.outerHTML)"

    # A page can have other, unrelated role="option" elements already sitting
    # in the DOM (e.g. a phone country-code picker's closed list) that never
    # actually disappear. wait_for_selector on a broad multi-match selector
    # only checks the first DOM-order match for visibility, so a stale match
    # elsewhere on the page can make it time out even when the options we
    # actually want are already rendered. Diffing DOM state before/after is
    # what reliably isolates the options this specific combobox produced.
    before_keys = set(await page.eval_on_selector_all(OPTION_SELECTOR, key_js))

    try:
        await page.click(selector, timeout=ACTION_TIMEOUT_MS)
        await page.fill(selector, body.value, timeout=ACTION_TIMEOUT_MS)
        await page.wait_for_timeout(400)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to open dropdown for field {body.index}: {exc}")

    after = await page.eval_on_selector_all(
        OPTION_SELECTOR, "els => els.map(e => ({ key: e.id || e.outerHTML, text: e.innerText.trim() }))"
    )
    new_options = [o for o in after if o["key"] not in before_keys]

    if not new_options:
        raise HTTPException(
            status_code=400,
            detail=f"No dropdown options appeared for field {body.index} after typing '{body.value}'.",
        )

    target = body.value.strip().lower()
    match = next((o for o in new_options if o["text"].strip().lower() == target), None)
    if not match:
        match = next((o for o in new_options if target in o["text"].strip().lower()), None)

    if not match:
        available = [o["text"] for o in new_options]
        raise HTTPException(
            status_code=400,
            detail=f"No option matching '{body.value}' for field {body.index}. Available options: {available}",
        )

    match_index = next(i for i, o in enumerate(after) if o["key"] == match["key"])
    try:
        await page.click(f'{OPTION_SELECTOR} >> nth={match_index}', timeout=ACTION_TIMEOUT_MS)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to select option for field {body.index}: {exc}")

    return {"message": f"Selected '{match['text']}' for field {body.index}"}


@app.post("/session/{session_id}/click")
async def click(session_id: str, body: ClickRequest):
    page = _get_page(session_id)
    selector = f'[data-sanctum-index="{body.index}"]'
    try:
        await page.click(selector, timeout=ACTION_TIMEOUT_MS)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to click field {body.index}: {exc}")
    return {"url": page.url, "title": await page.title()}


@app.get("/session/{session_id}/screenshot")
async def screenshot(session_id: str):
    page = _get_page(session_id)
    png_bytes = await page.screenshot(full_page=True)
    return {"image_base64": base64.b64encode(png_bytes).decode("ascii")}
