function clamp01(value){
  return Math.min(1,Math.max(0,Number.isFinite(value) ? value : 0));
}

function rangeProgress(value,start,end){
  if(end <= start) return value >= end ? 1 : 0;
  return clamp01((value-start)/(end-start));
}

function smoothstep01(value){
  const t=clamp01(value);
  return t*t*(3-2*t);
}

function deletedEditState(progress){
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

function oneTimeSourceState(progress){
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

const SCENE_WEIGHTS = [135,150,110,90,60,140,85,85,220,210,100,100,130,100];

function createScrollDirector(root = document){
  const cinematic = root.querySelector('#cinematic');
  const scenes = [...root.querySelectorAll('[data-scene]')];
  const deletedScene = scenes.find(scene => scene.getAttribute('data-scene') === 'deleted');
  const editScene = scenes.find(scene => scene.getAttribute('data-scene') === 'edit-history');
  const oneTimeScene = scenes.find(scene => scene.getAttribute('data-scene') === 'one-time');
  const sourceScene = scenes.find(scene => scene.getAttribute('data-scene') === 'source-depth');
  let raf = 0;
  let running = false;

  const totalWeight = SCENE_WEIGHTS.reduce((sum,value)=>sum+value,0);
  const boundaries = SCENE_WEIGHTS.reduce((acc,value,index)=>{
    const start = index === 0 ? 0 : acc[index-1].end;
    acc.push({start,end:start + value / totalWeight});
    return acc;
  },[]);

  const deletedIndex = scenes.indexOf(deletedScene);
  const editIndex = scenes.indexOf(editScene);
  const deletedRange = boundaries[deletedIndex] || {start:0,end:0};
  const editRange = boundaries[editIndex] || {start:0,end:0};
  const deletedEditWindow = {
    start: deletedRange.start + (deletedRange.end-deletedRange.start) * .55,
    end: editRange.start + (editRange.end-editRange.start) * .45,
  };

  const oneTimeIndex = scenes.indexOf(oneTimeScene);
  const sourceIndex = scenes.indexOf(sourceScene);
  const oneTimeRange = boundaries[oneTimeIndex] || {start:0,end:0};
  const sourceRange = boundaries[sourceIndex] || {start:0,end:0};
  const oneTimeSourceWindow = {
    start: oneTimeRange.start + (oneTimeRange.end-oneTimeRange.start) * .58,
    end: sourceRange.start + (sourceRange.end-sourceRange.start) * .82,
  };

  function applyDeletedEditState(progress){
    if(!cinematic || !deletedScene || !editScene) return;
    const transitionProgress = rangeProgress(progress,deletedEditWindow.start,deletedEditWindow.end);
    const state = deletedEditState(transitionProgress);
    const active = progress >= deletedEditWindow.start && progress <= deletedEditWindow.end;

    cinematic.style.setProperty('--deleted-edit-progress',String(state.progress));
    cinematic.style.setProperty('--deleted-edit-zoom',String(state.zoom));
    cinematic.style.setProperty('--deleted-proof-opacity',String(state.deletedOpacity));
    cinematic.style.setProperty('--edit-proof-opacity',String(state.editOpacity));
    cinematic.style.setProperty('--deleted-copy-opacity',String(state.deletedCopyOpacity));
    cinematic.style.setProperty('--edit-copy-opacity',String(state.editCopyOpacity));
    cinematic.style.setProperty('--edit-history-reveal',String(state.historyReveal));
    cinematic.setAttribute('data-match-cut-side',state.editOpacity === 1 ? 'edit' : 'deleted');

    if(active){
      deletedScene.setAttribute('data-transition-visible','true');
      editScene.setAttribute('data-transition-visible','true');
    }else{
      deletedScene.removeAttribute('data-transition-visible');
      editScene.removeAttribute('data-transition-visible');
    }
  }

  function applyOneTimeSourceState(progress){
    if(!cinematic || !oneTimeScene || !sourceScene) return;
    const transitionProgress = rangeProgress(progress,oneTimeSourceWindow.start,oneTimeSourceWindow.end);
    const state = oneTimeSourceState(transitionProgress);
    const active = progress >= oneTimeSourceWindow.start && progress <= oneTimeSourceWindow.end;

    cinematic.style.setProperty('--one-time-source-progress',String(state.progress));
    cinematic.style.setProperty('--one-time-source-zoom',String(state.zoom));
    cinematic.style.setProperty('--one-time-proof-opacity',String(state.viewerOpacity));
    cinematic.style.setProperty('--source-proof-opacity',String(state.sourceOpacity));
    cinematic.style.setProperty('--source-depth-progress',String(state.sourceDepth));
    cinematic.style.setProperty('--source-ui-return',String(state.uiReturn));
    cinematic.setAttribute('data-source-cut-side',state.sourceOpacity > 0 ? 'source' : 'viewer');

    if(active){
      oneTimeScene.setAttribute('data-source-transition-visible','true');
      sourceScene.setAttribute('data-source-transition-visible','true');
    }else{
      oneTimeScene.removeAttribute('data-source-transition-visible');
      sourceScene.removeAttribute('data-source-transition-visible');
    }
  }

  function update(){
    raf = 0;
    if(!cinematic || !scenes.length) return;
    const rect = cinematic.getBoundingClientRect();
    const travel = Math.max(1,cinematic.offsetHeight - window.innerHeight);
    const progress = clamp01((-rect.top) / travel);
    cinematic.style.setProperty('--cinematic-progress',String(progress));

    let activeIndex = boundaries.findIndex(({end},index)=>progress < end || index === boundaries.length - 1);
    if(activeIndex < 0) activeIndex = scenes.length - 1;

    scenes.forEach((scene,index)=>{
      const range = boundaries[index] || {start:0,end:1};
      const local = clamp01((progress - range.start) / Math.max(.00001,range.end-range.start));
      scene.style.setProperty('--scene-progress',String(local));
      if(index === activeIndex){scene.setAttribute('data-active','true');}
      else{scene.removeAttribute('data-active');}
    });

    applyDeletedEditState(progress);
    applyOneTimeSourceState(progress);
  }

  function schedule(){if(!raf) raf = requestAnimationFrame(update);}

  function start(){
    if(running) return;
    running = true;
    window.addEventListener('scroll',schedule,{passive:true});
    window.addEventListener('resize',schedule,{passive:true});
    update();
  }

  function stop(){
    if(!running) return;
    running = false;
    window.removeEventListener('scroll',schedule);
    window.removeEventListener('resize',schedule);
    if(raf){cancelAnimationFrame(raf);raf=0;}
  }

  return {start,stop,update};
}

const STORAGE_KEY='jg_lang';

const I18N={
  en:{
    skipToProject:'Skip cinematic chapter',navProject:'Project',navDownload:'Download',navGithub:'GitHub',navCommunity:'Community',navSupport:'Support',
    heroEyebrow:'Alternative Telegram client for iOS',heroThesis:'There is always more beneath the surface.',captureHardwarePending:'Hardware reference pending final licensed source.',productArrival:'Telegram, with more control.',
    capturePending:'Capture pending',deletedTitle:'Deleted doesn’t mean gone.',deletedBody:'When Jerkgram has already received the message, its conversation context can remain readable after deletion.',
    editTitle:'See what changed.',editBody:'The current message stays in the chat. Edit History reveals the earlier versions that existed before it.',
    ghostTitle:'Be there. Without looking like you are.',ghostBody:'Presence controls are shown as product behavior, not as a promise to bypass server-side limits.',
    giftsTitle:'Closed for sale. Sometimes still available.',giftsBody:'Jerkgram can surface a closed gift only when Telegram’s server still returns and accepts it.',
    oneTimeTitle:'View once doesn’t have to disappear.',oneTimeBody:'The final site will show the exact behavior reproduced by the release used for capture.',
    sourceTitle:'The interface is only the surface.',monkeyPending:'Exact Telegram monkey asset required. No substitute will be generated.',
    botTitle:'Use Telegram as a bot account.',botBody:'The final proof sequence will show entry, session identity and a real chat from the current build.',
    protectedTitle:'Control the boundary.',protectedBody:'The final scene will reflect only the exact protected-content scope verified in the current release.',
    projectEyebrow:'The project',openSourceTitle:'Jerkgram is open source.',openSourceBody:'Built in the open, with the public source available for inspection and contribution.',viewSource:'View source',
    ecosystemTitle:'One project. More than one platform.',iosState:'Current client.',androidState:'In development.',communityState:'Testing, feedback and discussion.',sourceState:'Public source, same project.',
    communityTitle:'Follow the project.',updatesState:'Releases and project updates.',communityHelpState:'Feedback, testing and installation help.',
    supportEyebrow:'Support',supportFragmentTitle:'Independent by design.',supportFragmentBody:'Infrastructure sponsorships and voluntary contributions help keep development moving without turning access into a purchase.',supportJerkgram:'Support Jerkgram',
    downloadEyebrow:'Stable release',downloadTitle:'Get Jerkgram.',releaseChecking:'Checking public release metadata…',versionLabel:'Version',buildLabel:'Build',telegramBaseLabel:'Telegram base',viewReleases:'View GitHub Releases ↗',installationGuide:'Installation Guide',
    legal:'Jerkgram is an independent project and is not an official Telegram application. Telegram is a trademark of its respective owner.'
  },
  ru:{
    skipToProject:'Пропустить кинематографическую главу',navProject:'Проект',navDownload:'Скачать',navGithub:'GitHub',navCommunity:'Сообщество',navSupport:'Поддержать',
    heroEyebrow:'Альтернативный Telegram-клиент для iOS',heroThesis:'Под поверхностью всегда есть больше.',captureHardwarePending:'Финальный лицензированный источник для hardware-сцены ещё не подставлен.',productArrival:'Telegram. Больше контроля.',
    capturePending:'Съёмка ожидается',deletedTitle:'Удалено — не значит потеряно.',deletedBody:'Если Jerkgram уже получил сообщение, контекст разговора может остаться читаемым и после удаления.',
    editTitle:'Смотри, что изменилось.',editBody:'Текущая версия остаётся в чате. Edit History показывает предыдущие версии, которые существовали до неё.',
    ghostTitle:'Будь в чате. Не выглядя присутствующим.',ghostBody:'Управление присутствием показывается как поведение клиента, без обещаний обойти серверные ограничения.',
    giftsTitle:'Снято с продажи. Иногда всё ещё доступно.',giftsBody:'Jerkgram может показать закрытый подарок только тогда, когда сервер Telegram всё ещё возвращает и принимает его.',
    oneTimeTitle:'View once не обязано исчезать.',oneTimeBody:'Финальный сайт покажет только то поведение, которое воспроизводится в сборке, использованной для съёмки.',
    sourceTitle:'Интерфейс — только поверхность.',monkeyPending:'Нужен точный исходный monkey-asset Telegram. Подмены генерироваться не будут.',
    botTitle:'Используй Telegram как бот-аккаунт.',botBody:'Финальная proof-сцена покажет вход, идентичность сессии и реальный чат из текущей сборки.',
    protectedTitle:'Контролируй границу.',protectedBody:'Финальная сцена покажет только тот scope protected content, который подтверждён в текущем релизе.',
    projectEyebrow:'Проект',openSourceTitle:'Jerkgram — open source.',openSourceBody:'Проект разрабатывается открыто: публичный исходный код доступен для просмотра и участия.',viewSource:'Открыть исходники',
    ecosystemTitle:'Один проект. Больше одной платформы.',iosState:'Текущий клиент.',androidState:'В разработке.',communityState:'Тестирование, обратная связь и обсуждение.',sourceState:'Публичные исходники того же проекта.',
    communityTitle:'Следи за проектом.',updatesState:'Релизы и новости проекта.',communityHelpState:'Обратная связь, тестирование и помощь с установкой.',
    supportEyebrow:'Поддержка',supportFragmentTitle:'Независимый по замыслу.',supportFragmentBody:'Спонсорство инфраструктуры и добровольная поддержка помогают развивать проект, не превращая доступ в покупку.',supportJerkgram:'Поддержать Jerkgram',
    downloadEyebrow:'Stable-релиз',downloadTitle:'Скачать Jerkgram.',releaseChecking:'Проверяем публичные данные о релизе…',versionLabel:'Версия',buildLabel:'Сборка',telegramBaseLabel:'База Telegram',viewReleases:'Открыть GitHub Releases ↗',installationGuide:'Инструкция по установке',
    legal:'Jerkgram — независимый проект и не является официальным приложением Telegram. Telegram — товарный знак соответствующего правообладателя.'
  }
};

function normalizeLanguage(lang){return lang==='ru'?'ru':'en';}
function getLanguage(){const saved=localStorage.getItem(STORAGE_KEY);if(saved==='ru'||saved==='en') return saved;return navigator.language?.toLowerCase().startsWith('ru')?'ru':'en';}
function translateDocument(root=document,lang=getLanguage()){const locale=I18N[normalizeLanguage(lang)];root.documentElement && (root.documentElement.lang=normalizeLanguage(lang));root.querySelectorAll('[data-i18n]').forEach(el=>{const value=locale[el.dataset.i18n];if(value) el.textContent=value;});root.querySelectorAll('[data-lang]').forEach(button=>{const active=button.dataset.lang===normalizeLanguage(lang);button.setAttribute('aria-pressed',String(active));});}
function setLanguage(lang,root=document){const normalized=normalizeLanguage(lang);localStorage.setItem(STORAGE_KEY,normalized);translateDocument(root,normalized);document.dispatchEvent(new CustomEvent('jg-language-changed',{detail:{lang:normalized}}));}

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const director = createScrollDirector(document);
function syncMotionMode(){document.documentElement.dataset.motion = reducedMotion.matches ? 'reduced' : 'full';if(reducedMotion.matches){director.stop();}else{director.start();}}
if(reducedMotion.addEventListener) reducedMotion.addEventListener('change',syncMotionMode);
syncMotionMode();
const initialLanguage=getLanguage();
translateDocument(document,initialLanguage);
document.querySelectorAll('[data-lang]').forEach(button=>button.addEventListener('click',()=>setLanguage(button.dataset.lang,document)));
const _s=document.querySelector('[data-release-state]');if(_s)_s.textContent='Preview build — release metadata is not loaded here.';const _d=document.querySelector('[data-release-download]');if(_d){_d.href='https://github.com/ghostbase-sg/jerkgram-telegram-builder/releases';_d.textContent='View GitHub Releases ↗';}
