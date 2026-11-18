// One shared readout for every chart mark. Hover and keyboard focus show the same thing.
(() => {
  const tip = document.getElementById("tip");
  if (!tip) return;

  const show = (el) => {
    const [head, value, detail] = el.dataset.tip.split("|");
    tip.replaceChildren();
    for (const [cls, text] of [["tip-value", value], ["tip-head", head], ["tip-detail", detail]]) {
      if (!text) continue;
      const line = document.createElement("div");
      line.className = cls;
      line.textContent = text;
      tip.append(line);
    }
    tip.hidden = false;
    const mark = (el.querySelector(".bar, .slice > i") || el).getBoundingClientRect();  // .mark anchors on itself
    const box = tip.getBoundingClientRect();
    const x = Math.max(8, Math.min(mark.left + mark.width / 2 - box.width / 2, innerWidth - box.width - 8));
    let y = mark.top - box.height - 8;
    if (y < 8) y = mark.bottom + 8;
    tip.style.left = `${x}px`;
    tip.style.top = `${y}px`;
  };
  const hide = () => { tip.hidden = true; };

  for (const el of document.querySelectorAll("[data-tip]")) {
    el.addEventListener("pointerenter", () => show(el));
    el.addEventListener("pointerleave", hide);
    el.addEventListener("focus", () => show(el));
    el.addEventListener("blur", hide);
  }
  addEventListener("scroll", hide, { passive: true });
})();
