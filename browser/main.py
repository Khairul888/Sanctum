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
        return style.display !== 'none' && style.visibility !== 'hidden' && el.offsetParent !== null;
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
        const type = (el.getAttribute('type') || tag).toLowerCase();
        if (type === 'hidden' || !isVisible(el)) continue;

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
