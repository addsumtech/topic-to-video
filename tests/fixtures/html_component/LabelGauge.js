// COMPONENT · LabelGauge <label-gauge> — a labelled dial: the needle swept to value on a min..max arc, the
// reading under it and the range's two ends at the arc's feet.
// TEST FIXTURE (tests/test_html_workshop.py) — the "correct" case every HTML-workshop check is judged on.
// Light DOM only; built once from its attributes; every animation is CSS keyframes (LabelGauge.css); no
// time, randomness or network; every word and number it draws is one of its attribute values.
customElements.define('label-gauge', class extends HTMLElement {
  // neutral demo attributes `workshop.py check` renders it with — never film copy
  static demo = {label: 'Demo reading', value: '6', min: '0', max: '10', unit: 'units'};

  connectedCallback() {
    if (this._built) return;            // build ONCE: a re-attach must not duplicate the parts
    this._built = true;
    const attr = (k) => this.getAttribute(k) || '';
    const num = (k, d) => { const v = parseFloat(attr(k)); return isFinite(v) ? v : d; };
    const min = num('min', 0), max = num('max', 1), val = num('value', min);
    const frac = max > min ? Math.min(1, Math.max(0, (val - min) / (max - min))) : 0;
    this.style.setProperty('--label-gauge-to', (-90 + 180 * frac) + 'deg');
    const part = (parent, cls, text) => {
      const e = document.createElement('div');
      e.className = 'label-gauge__' + cls;
      if (text != null) e.textContent = text;
      parent.appendChild(e);
      return e;
    };
    const dial = part(this, 'dial');
    part(dial, 'needle');
    part(dial, 'hub');
    const ends = part(this, 'ends');
    part(ends, 'end', attr('min'));
    part(ends, 'end', attr('max'));
    const reading = part(this, 'reading');
    part(reading, 'value', attr('value'));
    part(reading, 'unit', attr('unit'));
    part(this, 'label', attr('label'));
  }
});
