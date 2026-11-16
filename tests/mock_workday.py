"""A fake Workday tenant for deterministic tests (no network, no real account).

Mimics the Workday flow and `data-automation-id` markup: job page -> Apply Manually -> sign-in ->
My Information -> My Experience -> Application Questions -> Review (button says "Submit") -> confirmation.
Submissions are POSTed to /submit so tests can assert whether a real "submit" happened.
"""
import json
from typing import List

MOCK_HOST = "acme.wd5.myworkdayjobs.com"
MOCK_JOB_URL = f"https://{MOCK_HOST}/en-US/External/job/Boston/Software-Engineer_R-1"
MOCK_EMAIL = "jane.doe@example.com"
MOCK_PASSWORD = "mock-password"
AUTH_QUESTION = "Are you legally authorized to work in the United States?"
FREE_TEXT_QUESTION = "Why do you want to work here?"

_HTML = """<!doctype html><html><body><div id="app"></div><script>
const S = {step: 'job', data: {}, errors: [], modal: false};
const TITLES = {info: 'My Information', experience: 'My Experience', questions: 'Application Questions', review: 'Review'};
const ORDER = ['info', 'experience', 'questions', 'review'];
const text = (id, label) => `<div data-automation-id="formField-${id}"><label>${label}</label>
  <input type="text" data-automation-id="${id}" value="${S.data[id] || ''}"></div>`;
const drop = (id, label, opts) => `<div data-automation-id="formField-${id}"><label>${label}</label>
  <button type="button" aria-haspopup="listbox" data-automation-id="${id}">${S.data[id] || 'Select One'}</button>
  <ul role="listbox" hidden>${opts.map(o => `<li role="option">${o}</li>`).join('')}</ul></div>`;
const errs = () => S.errors.map(e => `<div data-automation-id="errorMessage">${e}</div>`).join('');
const nav = label => `<button data-automation-id="pageFooterNextButton">${label}</button>`;

function render() {
  let h = '';
  if (S.step === 'job') {
    h = `<h1>Software Engineer</h1><button data-automation-id="adventureButton">Apply</button>` +
        (S.modal ? `<div><button data-automation-id="applyManually">Apply Manually</button></div>` : '');
  } else if (S.step === 'signin') {
    h = `${errs()}<input data-automation-id="email" type="text"><input data-automation-id="password" type="password">
         <button data-automation-id="signInSubmitButton">Sign In</button>`;
  } else if (S.step === 'done') {
    h = `<h2>Application Submitted</h2><p>Thank you for applying.</p>`;
  } else {
    h = `<div data-automation-id="progressBarActiveStep">${TITLES[S.step]}</div>${errs()}`;
    if (S.step === 'info') {
      h += text('legalNameSection_firstName', 'First Name') + text('legalNameSection_lastName', 'Last Name') +
           drop('countryDropdown', 'Country', ['United States of America', 'Canada']) +
           text('addressSection_addressLine1', 'Address Line 1') + text('addressSection_city', 'City') +
           drop('addressSection_countryRegion', 'State', ['Massachusetts', 'Texas']) +
           text('addressSection_postalCode', 'Postal Code') + text('phone-number', 'Phone Number');
    } else if (S.step === 'experience') {
      h += `<input type="file" data-automation-id="file-upload-input-ref">`;
    } else if (S.step === 'questions') {
      h += drop('q_auth', '__AUTH__', ['Yes', 'No']) + text('q_why', '__WHY__');
    } else if (S.step === 'review') {
      h += `<p>Please review your application.</p>`;
    }
    h += nav(S.step === 'review' ? 'Submit' : 'Next');
  }
  document.getElementById('app').innerHTML = h;
}

function validate() {
  const need = {info: ['legalNameSection_firstName', 'legalNameSection_lastName', 'addressSection_city'],
                questions: ['q_auth', 'q_why']}[S.step] || [];
  return need.filter(id => !S.data[id]).map(id => `The field ${id} is required and must have a value.`);
}

document.addEventListener('input', e => { const id = e.target.dataset.automationId; if (id) S.data[id] = e.target.value; });
document.addEventListener('click', e => {
  const t = e.target, id = t.dataset.automationId;
  if (t.matches('button[aria-haspopup="listbox"]')) { t.nextElementSibling.hidden = !t.nextElementSibling.hidden; return; }
  if (t.matches('[role="option"]')) {
    const btn = t.parentElement.previousElementSibling;
    S.data[btn.dataset.automationId] = t.textContent; btn.textContent = t.textContent; t.parentElement.hidden = true; return;
  }
  if (id === 'adventureButton') { S.modal = true; render(); }
  else if (id === 'applyManually') { S.step = 'signin'; render(); }
  else if (id === 'signInSubmitButton') {
    const em = document.querySelector('[data-automation-id="email"]').value;
    const pw = document.querySelector('[data-automation-id="password"]').value;
    if (em === '__EMAIL__' && pw === '__PASSWORD__') { S.step = 'info'; S.errors = []; }
    else { S.errors = ['The email or password is incorrect.']; }
    render();
  } else if (id === 'pageFooterNextButton') {
    S.errors = validate();
    if (S.errors.length) { render(); return; }
    if (S.step === 'review') {
      fetch('/submit', {method: 'POST', body: JSON.stringify(S.data)}).then(() => { S.step = 'done'; render(); });
    } else { S.step = ORDER[ORDER.indexOf(S.step) + 1]; render(); }
  }
});
render();
</script></body></html>"""


class MockWorkday:
    """Installs itself on a Playwright page and records POSTs to /submit."""

    def __init__(self, page):
        self.submissions: List[dict] = []
        html = (
            _HTML.replace("__AUTH__", AUTH_QUESTION)
            .replace("__WHY__", FREE_TEXT_QUESTION)
            .replace("__EMAIL__", MOCK_EMAIL)
            .replace("__PASSWORD__", MOCK_PASSWORD)
        )
        self._html = html
        page.route(f"https://{MOCK_HOST}/**", self._handle)

    def _handle(self, route) -> None:
        request = route.request
        if request.method == "POST":
            self.submissions.append(json.loads(request.post_data or "{}"))
            route.fulfill(status=200, content_type="application/json", body="{}")
        else:
            route.fulfill(status=200, content_type="text/html", body=self._html)
