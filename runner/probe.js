/* jobpilot 页面探测：在页面里做确定性抽取，返回 {url,title,module,controls[]}。
 * 只读，不改页面。可在 Claude 的浏览器工具里用 evaluate 注入。 */
(() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').replace(/[：:*＊]/g, '').trim();
  const controls = [];
  const els = [...document.querySelectorAll('input, select, textarea, [contenteditable="true"]')];

  els.forEach((el, i) => {
    const type = (el.getAttribute('type') || '').toLowerCase();
    if (type === 'hidden' || type === 'submit' || type === 'button' || type === 'reset') return;

    const box = el.closest('.el-form-item, .ant-form-item, .form-item, .form-group, .field, tr, li');
    let label = el.getAttribute('aria-label') || '';
    if (!label && box) {
      const lab = box.querySelector('label, .el-form-item__label, .ant-form-item-label, .label, .form-label');
      if (lab) label = lab.innerText;
    }
    if (!label && el.labels && el.labels.length) label = el.labels[0].innerText;
    if (!label) label = el.getAttribute('placeholder') || '';
    label = clean(label);

    let kind = 'text';
    const widget = (el.className || '').toString();
    if (el.tagName === 'SELECT') kind = 'enum';
    else if (el.tagName === 'TEXTAREA' || el.isContentEditable) kind = 'long_text';
    else if (type === 'file') kind = 'file';
    else if (type === 'checkbox' || type === 'radio') kind = 'bool';
    else if (type === 'date') kind = 'date';
    else if (type === 'month') kind = 'month';
    else if (/el-select|ant-select/.test(widget) || el.closest('.el-select, .ant-select')) kind = 'enum';
    else if (/el-date|ant-picker/.test(widget) || el.closest('.el-date-editor, .ant-picker')) kind = 'date';

    let options = [];
    if (el.tagName === 'SELECT') {
      options = [...el.options].map(o => o.text.trim()).filter(Boolean);
    } else if (kind === 'enum' && box) {
      options = [...box.querySelectorAll('.el-select-dropdown__item, .ant-select-item-option, option')]
        .map(o => o.innerText.trim()).filter(Boolean);
    }

    controls.push({
      index: i,
      label,
      kind,
      required: !!(box && (box.querySelector('.required, .is-required') || /[*＊]/.test(box.innerText || ''))),
      maxlength: el.getAttribute('maxlength') ? Number(el.getAttribute('maxlength')) : null,
      options,
      current: el.value !== undefined ? el.value : '',
      widget: kind === 'enum' ? 'select' : (kind === 'date' ? 'date' : 'input'),
      hint: box ? clean(box.innerText).slice(0, 80) : ''
    });
  });

  const heading = document.querySelector('h1, h2, .page-title, .el-page-header__title');
  return {
    url: location.href,
    title: document.title || '',
    module: heading ? clean(heading.innerText) : '页面',
    controls
  };
})()
