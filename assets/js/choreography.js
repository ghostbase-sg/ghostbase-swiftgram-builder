export function clamp01(value){
  return Math.min(1,Math.max(0,Number.isFinite(value) ? value : 0));
}

export function rangeProgress(value,start,end){
  if(end <= start) return value >= end ? 1 : 0;
  return clamp01((value-start)/(end-start));
}

export function smoothstep01(value){
  const t=clamp01(value);
  return t*t*(3-2*t);
}

export function deletedEditState(progress){
  const p=clamp01(progress);
  const zoom=p <= .5
    ? smoothstep01(p/.5)
    : smoothstep01((1-p)/.5);
  const onEditSide=p >= .5;

  return {
    progress:p,
    zoom,
    deletedOpacity:onEditSide ? 0 : 1,
    editOpacity:onEditSide ? 1 : 0,
    deletedCopyOpacity:1-smoothstep01(rangeProgress(p,.12,.4)),
    editCopyOpacity:smoothstep01(rangeProgress(p,.62,.9)),
    historyReveal:smoothstep01(rangeProgress(p,.72,.93)),
  };
}


export function oneTimeSourceState(progress){
  const p=clamp01(progress);
  const onSourceSide=p >= .5;
  const zoom=p <= .5
    ? smoothstep01(p/.5)
    : 1-smoothstep01(rangeProgress(p,.5,.82));
  const sourceDepth=smoothstep01(rangeProgress(p,.52,.82));
  const uiReturn=smoothstep01(rangeProgress(p,.82,.98));

  return {
    progress:p,
    zoom,
    viewerOpacity:onSourceSide ? 0 : 1,
    sourceOpacity:onSourceSide ? 1-uiReturn : 0,
    sourceDepth,
    uiReturn,
  };
}
