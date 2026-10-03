// GOOD — AN INTERFACE BEING OPERATED, drawn for a device's screen (DeviceDemo `{"screen": {"object": …}}`). It
// ENCODES "you write it, it sends": the draft types itself in and the send button lights when it is done. Every
// word — the recipient, the draft, the button — comes from props, so the film writes them in its own language.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
import {clamp01, seg} from '@runtime/motion';
import {mix} from '@runtime/dna';
import {onAccentInk} from '@runtime/onAccent';

export const META: ObjectMeta = {aspect: 9 / 19.5, provenance: 'product-ui'};

export const ComposeScreen: React.FC<ObjectProps & {to?: string; draft?: string; send?: string}> =
  ({w, h, t, dna, to = '', draft = '', send = ''}) => {
  const surf = dna?.surface ?? '#ffffff', ink = dna?.fg ?? '#14171c', dim = dna?.dim ?? '#5b6472';
  const acc = dna?.accent ?? '#3563e9';
  const chars = [...draft];
  // @truncates: typing — every character of the draft has arrived by t = 0.7
  const typed = chars.slice(0, Math.round(chars.length * clamp01(seg(t, 0.15, 0.7)))).join('');
  const sent = t > 0.82;
  const px = Math.round(w * 0.055);
  return (
    <div style={{width: w, height: h, background: surf, position: 'relative', font: `400 ${px}px/1.5 var(--f-body, Inter, sans-serif)`}}>
      <div style={{position: 'absolute', left: w * 0.07, right: w * 0.07, top: h * 0.07, color: dim, fontSize: px * 0.8,
        borderBottom: `1px solid ${mix(surf, ink, 0.15)}`, paddingBottom: px * 0.4}}>{to}</div>
      <div style={{position: 'absolute', left: w * 0.07, right: w * 0.07, top: h * 0.15, color: ink}}>{typed}</div>
      <div style={{position: 'absolute', right: w * 0.07, bottom: h * 0.05, padding: `${px * 0.4}px ${px * 0.9}px`,
        borderRadius: px, fontWeight: 700, fontSize: px * 0.8,
        background: sent ? acc : mix(surf, ink, 0.1), color: sent ? onAccentInk(acc) : dim}}>{send}</div>
    </div>
  );
};
