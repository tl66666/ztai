var JobHunterInterviewController=(function(e){Object.defineProperty(e,Symbol.toStringTag,{value:`Module`});function t(e,t){let n=e(t);if(!n)throw Error(`Missing interview audio control: #${t}`);return n}function n(e,n){let{userId:r,state:i,request:a,byId:o,toast:s,withLoading:c,downloadBlob:l,downloadResponse:u,media:d,capabilities:f}=e,p=d.createObjectUrlRegistry({create:e=>URL.createObjectURL(e),revoke:e=>URL.revokeObjectURL(e)});function m(e=``){return f.extensionForMime(e)}function h(e=`interview-answer`){return e.replace(/\.[^.]+$/,``)||`interview-answer`}async function g(e){let t=window.AudioContext||window.webkitAudioContext;if(!t)throw Error(`当前浏览器不支持音频解码`);let n=await d.decodeAudioBlob(e,t),r=Math.min(2,n.numberOfChannels),i=n.sampleRate,a=n.length,o=r*2,s=a*o,c=new ArrayBuffer(44+s),l=new DataView(c),u=(e,t)=>{for(let n=0;n<t.length;n+=1)l.setUint8(e+n,t.charCodeAt(n))};u(0,`RIFF`),l.setUint32(4,36+s,!0),u(8,`WAVE`),u(12,`fmt `),l.setUint32(16,16,!0),l.setUint16(20,1,!0),l.setUint16(22,r,!0),l.setUint32(24,i,!0),l.setUint32(28,i*o,!0),l.setUint16(32,o,!0),l.setUint16(34,16,!0),u(36,`data`),l.setUint32(40,s,!0);let f=Array.from({length:r},(e,t)=>n.getChannelData(t)),p=44;for(let e=0;e<a;e+=1)for(let t=0;t<r;t+=1){let n=Math.max(-1,Math.min(1,f[t][e]));l.setInt16(p,n<0?n*32768:n*32767,!0),p+=2}return new Blob([c],{type:`audio/wav`})}async function _(e,t=`wav`){if(!e){s(`没有可下载的音频文件`);return}if(!a.raw)throw Error(`ApiClient.raw is required for audio downloads`);if(t===`wav`){try{let t=await a.raw(`/uploads/${encodeURIComponent(e)}`);if(!t.ok)throw Error(`音频读取失败`);l(await g(await t.blob()),`${h(e)}.wav`),s(`WAV 音频已开始下载`)}catch(e){s(`WAV 导出失败：${e.message}`)}return}let n=await a.raw(`/uploads/${encodeURIComponent(e)}/download/${t}`),r=t===`original`?f.audioFileDescriptor({name:e,type:``}).filename:`${h(e)}.${t}`;await u(n,r)}async function v(e,t=`upload`,n=0){return d.computeAudioMetrics(e,{source:t,startedAt:n,AudioContext:window.AudioContext||window.webkitAudioContext||null})}function y(e=`answer`){let n=t(o,e===`room`?`roomAudioPlayback`:`audioPlayback`),r=t(o,e===`room`?`roomAudioMetricPreview`:`audioMetricPreview`),a=t(o,e===`room`?`roomAudioPlaybackStatus`:`audioPlaybackStatus`),s=t(o,e===`room`?`roomAudioDownloadLink`:`audioDownloadLink`);if(i.audioBlob){let t=p.replace(e,i.audioBlob),r=f.audioFileDescriptor(i.audioBlob);n.src=t,n.dataset.url=t,s.href=t,s.download=r.filename,s.classList.remove(`hidden`),a.classList.remove(`hidden`,`is-warning`),a.textContent=r.mayNotPlay?f.audioPlaybackErrorMessage():`已载入 ${r.filename}，可回放或下载原文件。`,a.classList.toggle(`is-warning`,r.mayNotPlay),n.onerror=()=>{a.textContent=f.audioPlaybackErrorMessage(),a.classList.remove(`hidden`),a.classList.add(`is-warning`),s.classList.remove(`hidden`)},n.oncanplay=()=>{r.mayNotPlay||a.classList.remove(`is-warning`)}}let c=i.audioMetrics||{},l=c.duration_seconds==null?`未知`:`${c.duration_seconds}s`;r.classList.remove(`hidden`),r.innerHTML=`
      <span>时长 ${l}</span>
      <span>音量 ${c.average_volume||0}</span>
      <span>停顿 ${(c.silence_ratio||0)*100}%</span>
      <span>爆音 ${(c.clipping_ratio||0)*100}%</span>
    `}function b(){return i.recordingController||=d.createRecordingController({acquireStream:()=>navigator.mediaDevices.getUserMedia({audio:!0}),createRecorder:(e,t)=>t?new MediaRecorder(e,t):new MediaRecorder(e),createBlob:(e,t)=>new Blob(e,t),computeMetrics:v,publish:({blob:e,metrics:t,target:n})=>{i.audioBlob=e,i.audioMetrics=t,y(n),s(`录音已生成，可以回放或分析`)},onError:e=>{s(e?.name===`NotAllowedError`?`未获得麦克风权限，请上传音频或使用文字回答`:`录音发生错误，请上传音频或使用文字回答`)}}),i.recordingController}async function x(e=`answer`){let t=f.audioInputPlan(window,navigator);if(!t.canRecord){s(`当前浏览器不能直接录音，请上传音频或使用文字回答`);return}let n=await b().start({target:e,format:t.recorderFormat});n.ok?s(e===`room`?`模拟面试录音开始`:`真实录音开始`):n.reason===`busy`&&s(`正在启动或录制音频，请先停止当前录音`)}function S(){b().stop()||s(`当前没有正在录制的音频`)}async function C(){b().invalidate();let e=t(o,`audioFileInput`).files?.[0];e&&(i.audioBlob=e,i.audioMetrics=await v(e,`upload`),y(`answer`),s(`已载入上传音频，可以回放或分析`))}async function w(e=`answer`){if(!i.audioBlob){s(`请先录音或上传音频`);return}let l=t(o,e===`room`?`roomAnswer`:`answerInput`).value.trim();if(!l){s(`请补充转写文本，AI 需要结合内容和声音一起分析`);return}let u=new FormData,d=f.audioFileDescriptor(i.audioBlob);u.append(`audio`,i.audioBlob,d.filename),u.append(`user_id`,String(r)),u.append(`transcript`,l),Number.isFinite(i.audioMetrics?.duration_seconds)&&u.append(`duration_seconds`,String(i.audioMetrics.duration_seconds)),u.append(`metrics`,JSON.stringify(i.audioMetrics||{}));let p=await c(()=>a(`/interview/analyze-audio`,{method:`POST`,body:u}),`AI 正在分析真实录音...`);if(!p.success){s(p.message||`录音分析失败`);return}let m={score:p.overall_score,summary:p.summary,voice:p,suggestions:p.tips};if(e===`room`){let e=t(o,`roomFeedback`);e.classList.remove(`hidden`),e.innerHTML=n.renderFeedbackHtml(m)}else n.renderFeedback(m);await n.loadTrainingRecords()}function T(){let e=f.speechRecognition(window),t=f.audioInputPlan(window,navigator);f.applyCapabilityUI(document,{speech:e,audio:t})}function E(){let e=f.speechRecognition(window);e.Recognition&&(i.recognition=new e.Recognition,i.recognition.lang=`zh-CN`,i.recognition.continuous=!0,i.recognition.interimResults=!0,i.speechController=d.bindSpeechRecognition(i.recognition,{getText:()=>t(o,`answerInput`).value.replace(/\s*$/,``),setText:e=>{t(o,`answerInput`).value=e},setActive:e=>{i.recognizing=e,t(o,`voiceBtn`).classList.toggle(`recording`,e)},onError:e=>{let t=e?.error===`not-allowed`||e?.error===`service-not-allowed`;s(t?`未获得语音识别权限，请直接使用文字回答`:`语音识别暂时不可用，请直接使用文字回答`)}}))}function D(){if(!i.recognition){s(`当前浏览器不支持语音识别，可以使用 Chrome 尝试`);return}if(i.recognizing){try{i.recognition.stop()}catch{i.speechController?.finish()}return}if(i.speechController?.begin(),!f.startSpeechSafely(i.recognition).ok){i.speechController?.finish(),s(`无法启动语音识别，请直接使用文字回答`);return}s(`正在语音录入`)}return{extensionFromMime:m,downloadSaved:_,getRecordingController:b,startRecording:x,stopRecording:S,handleUpload:C,computeMetrics:v,renderPreview:y,analyzeRecorded:w,applyCapabilities:T,setupSpeechRecognition:E,toggleVoiceInput:D}}function r(e){return{opening:`自我介绍`,resume_deep_dive:`项目深挖`,technical:`技术追问`,professional:`专业追问`,behavioral:`行为面`,candidate_questions:`反问环节`,finished:`面试结束`}[e]||e}function i(e=``){return String(e).replace(/\\/g,`\\\\`).replace(/'/g,`\\'`).replace(/\n/g,` `)}function a(e){return{general:`通用面试`,career:`跟随求职方向`,test:`软件测试`,python:`Python / Flask`,frontend:`前端基础`,ai:`AI Agent`,tech:`计算机 / 软件 / AI`,ops:`运营 / 新媒体`,marketing:`市场 / 销售`,finance:`财务 / 会计`,education:`教育 / 师范`,hr:`行政 / 人事`}[e]||e}function o(e){try{return JSON.parse(String(e||`{}`))}catch{return{}}}function s(e){return e?new Date(String(e)).toLocaleString():``}function c(e){return o(e).summary||``}function l(e,t){let n=e(t);if(!n)throw Error(`Missing interview training control: #${t}`);return n}function u(e){let{userId:t,apiBaseUrl:n,state:r,request:u,byId:d,escapeHtml:f,renderText:p,toast:m,withLoading:h,renderIcons:g,selectedCareerProfile:_,loadDashboard:v,confirmAction:y}=e;async function b(e=`all`){let t=e===`career`?_():e;r.currentPracticeCategory=e;let n=await u(`/questions?category=${encodeURIComponent(t)}`),o=n.success?n.data:[];l(d,`questionList`).innerHTML=o.length?o.map((t,n)=>`
        <article class="question-card">
          <b>${n+1}. ${f(t.question)}</b>
          <small>${a(t.category)} · 点击“练习”后可输入自己的回答</small>
          <div class="list-actions">
            <button class="ghost small" onclick="selectQuestion('${i(t.question)}', '${i(e===`career`?`career`:t.category)}')">练习</button>
            <button class="ghost small" onclick="showSampleAnswer('${i(t.answer)}')">参考答案</button>
          </div>
        </article>
      `).join(``):`<article class="question-card"><b>暂无题目</b><small>换一个分类试试</small></article>`}function x(e,t){l(d,`practiceQuestion`).value=e,r.currentPracticeCategory=t,l(d,`practiceAnswer`).focus(),m(`题目已放入练习区`)}function S(e){let t=l(d,`practiceResult`);t.classList.remove(`hidden`),t.innerHTML=`<h4>参考答案</h4>${p(e)}`}function C(e,t,n,r){return`
      <section class="record-column">
        <h4>${f(e)}<span>${n.length}</span></h4>
        ${n.length?n.map(e=>`
          <article class="record-card">
            ${r(e)}
            <div class="record-actions">
              <button class="ghost small" onclick="viewTrainingRecord('${t}', ${e.id})">查看详情</button>
              <button class="ghost small danger" onclick="deleteTrainingRecord('${t}', ${e.id})">删除</button>
            </div>
          </article>
        `).join(``):`<article class="record-card"><b>暂无记录</b><small>完成训练后会自动出现在这里</small></article>`}
      </section>
    `}async function w(){let e=d(`trainingRecords`);if(!e)return;let n=await u(`/training-records/${t}`);if(!n.success)return;let r=n.interviews||[],i=n.practices||[],o=n.audios||[];e.innerHTML=`
      ${C(`模拟面试`,`interview`,r,e=>`
        <b>${f(e.job_title||`模拟面试`)}</b>
        <small>${s(e.created_at)} · ${e.score??0} 分</small>
        <p>${f(c(e.feedback)||`已完成一轮模拟面试。`)}</p>
      `)}
      ${C(`答题练习`,`practice`,i,e=>`
        <b>${f(a(e.category))} · ${e.score??0} 分</b>
        <small>${s(e.created_at)}</small>
        <p>${f(e.question||``)}</p>
      `)}
      ${C(`语音录音`,`audio`,o,e=>`
        <b>语音表达分析 · ${e.score??0} 分</b>
        <small>${s(e.created_at)}${e.audio_file?` · 已保存音频`:``}</small>
        <p>${f((e.transcript||``).slice(0,90))}</p>
      `)}
    `,g()}async function T(e,n){let r=await u(`/training-records/${t}`);if(!r.success){m(`记录读取失败`);return}let i=((e===`interview`?r.interviews:e===`practice`?r.practices:r.audios)||[]).find(e=>Number(e.id)===Number(n));if(!i){m(`记录不存在或已删除`);return}let a=l(d,`recordDetail`);a.classList.remove(`hidden`),a.innerHTML=D(e,i),a.scrollIntoView({behavior:`smooth`,block:`nearest`})}function E(e){let t=o(e),n=Array.isArray(t)?t:t.turns||t.conversation||[];return n.length?n.map(e=>{let t=e.role||e.speaker||`记录`,n=e.content||e.text||e.question||e.answer||``;return`<div class="conversation-line"><b>${f(t)}</b><span>${f(n)}</span></div>`}).join(``):`<div>暂无完整对话记录。</div>`}function D(e,t){let r=o(t.feedback),a=o(t.metrics);return e===`audio`?`
        <h4>语音复盘详情：${t.score??0} 分</h4>
        <div><b>时间</b><br>${s(t.created_at)}</div>
        <div><b>转写文本</b><br>${f(t.transcript||`暂无转写文本`)}</div>
        <div><b>声音指标</b><br>时长 ${a.duration_seconds||0}s，平均音量 ${a.average_volume||0}，停顿占比 ${Math.round((a.silence_ratio||0)*100)}%，爆音占比 ${Math.round((a.clipping_ratio||0)*100)}%</div>
        ${t.audio_file?`
          <audio controls src="${n}/uploads/${encodeURIComponent(t.audio_file)}"></audio>
          <div class="audio-downloads">
            <button class="ghost small" onclick="downloadSavedAudio('${i(t.audio_file)}', 'wav')">下载 WAV</button>
            <button class="ghost small" onclick="downloadSavedAudio('${i(t.audio_file)}', 'mp3')">下载 MP3</button>
            <button class="ghost small" onclick="downloadSavedAudio('${i(t.audio_file)}', 'original')">下载原始音频</button>
          </div>
          <small>WAV 可由浏览器本地转换；MP3 由后端 ffmpeg 转码生成。</small>
        `:``}
        <div><b>AI 建议</b><br>${f(r.summary||``)}</div>
        ${(r.tips||[]).map(e=>`<div>• ${f(e)}</div>`).join(``)}
      `:e===`practice`?`
        <h4>答题记录详情：${t.score??0} 分</h4>
        <div><b>时间</b><br>${s(t.created_at)}</div>
        <div><b>题目</b><br>${f(t.question||``)}</div>
        <div><b>我的回答</b><br>${f(t.answer||``)}</div>
        <div><b>维度评分</b><br>${Object.entries(r.dimension_scores||{}).map(([e,t])=>`${f(e)}：${f(String(t))}`).join(`　`)||`暂无`}</div>
        ${(r.problems||[]).map(e=>`<div>• ${f(e)}</div>`).join(``)}
        ${r.sample_answer?`<h4>参考答案</h4>${p(r.sample_answer)}`:``}
        ${r.upgrade?`<h4>表达升级</h4><div>${f(r.upgrade)}</div>`:``}
      `:`
      <h4>模拟面试详情：${t.score??0} 分</h4>
      <div><b>岗位</b><br>${f(t.job_title||`模拟面试`)}</div>
      <div><b>时间</b><br>${s(t.created_at)}</div>
      <div><b>总体反馈</b><br>${f(r.summary||c(t.feedback)||`暂无总结`)}</div>
      ${(r.suggestions||[]).map(e=>`<div>• ${f(e)}</div>`).join(``)}
      <h4>面试对话</h4>
      ${E(t.conversation)}
    `}async function O(e,t){if(!y(`确定删除这条训练记录吗？`))return;let n=await u(`/training-records/${e}/${t}`,{method:`DELETE`});if(!n.success){m(n.message||`删除失败`);return}m(`训练记录已删除`),await Promise.all([w(),v()])}async function k(){if(!y(`确定清空所有面试、答题和语音记录吗？`))return;let e=await u(`/training-records/${t}/clear`,{method:`DELETE`});if(!e.success){m(e.message||`清空失败`);return}m(`训练记录已清空`),await Promise.all([w(),v()])}async function A(){let e=await h(()=>u(`/interview/professional-pack`,{method:`POST`,body:{category:l(d,`professionalCategory`).value,career_profile:_(),level:l(d,`professionalLevel`).value,job_title:l(d,`professionalJobTitle`).value||l(d,`interviewJobTitle`).value||`目标岗位`}}),`AI 正在生成专业面试题组...`);if(!e.success){m(e.message||`题组生成失败`);return}l(d,`professionalPack`).innerHTML=e.questions.map((e,t)=>`
      <article class="question-card">
        <b>${t+1}. ${f(e.question)}</b>
        <small>${f(e.focus)} · ${f(e.difficulty)}</small>
        <div class="list-actions">
          <button class="ghost small" onclick="selectProfessionalQuestion('${i(e.question)}')">作答</button>
          <button class="ghost small" onclick="showProfessionalReference('${i(e.reference)}')">参考思路</button>
        </div>
      </article>
    `).join(``)}function j(e){l(d,`professionalQuestion`).value=e,l(d,`professionalAnswer`).focus(),m(`专业问题已放入作答区`)}function M(e){let t=l(d,`professionalResult`);t.classList.remove(`hidden`),t.innerHTML=`<h4>参考思路</h4>${p(e)}`}async function N(){let e=l(d,`professionalQuestion`).value.trim(),n=l(d,`professionalAnswer`).value.trim();if(!e||!n){m(`请先选择专业问题并填写回答`);return}let r=await u(`/interview/practice-feedback`,{method:`POST`,body:{question:e,answer:n,user_id:t,category:l(d,`professionalCategory`).value,career_profile:_(),job_title:l(d,`professionalJobTitle`).value||l(d,`interviewJobTitle`).value||`目标岗位`}});if(!r.success){m(r.message||`评分失败`);return}let i=l(d,`professionalResult`);i.classList.remove(`hidden`),i.innerHTML=`
      <h4>专业回答评分：${r.score} 分</h4>
      <div><b>维度分</b><br>${Object.entries(r.dimension_scores).map(([e,t])=>`${e}：${t}`).join(`　`)}</div>
      <div><b>命中关键词</b><br>${f((r.hits||[]).join(`、`)||`暂无`)}</div>
      ${(r.problems||[]).map(e=>`<div>• ${f(e)}</div>`).join(``)}
      <h4>参考答案</h4>${p(r.sample_answer)}
      <h4>追问建议</h4>${f(r.follow_up||`把回答继续落到你的项目经历、测试工具和实际结果上。`)}
    `,await w()}async function P(){let e=l(d,`practiceQuestion`).value.trim(),n=l(d,`practiceAnswer`).value.trim();if(!e||!n){m(`请先填写题目和你的回答`);return}let i=await u(`/interview/practice-feedback`,{method:`POST`,body:{question:e,answer:n,category:r.currentPracticeCategory,career_profile:_(),job_title:l(d,`interviewJobTitle`).value||`目标岗位`,user_id:t}});if(!i.success){m(i.message||`评分失败`);return}let a=l(d,`practiceResult`);a.classList.remove(`hidden`),a.innerHTML=`
      <h4>练习评分：${i.score} 分</h4>
      <div><b>维度分</b><br>${Object.entries(i.dimension_scores).map(([e,t])=>`${e}：${t}`).join(`　`)}</div>
      <div><b>命中关键词</b><br>${f((i.hits||[]).join(`、`)||`暂无`)}</div>
      ${(i.problems||[]).map(e=>`<div>• ${f(e)}</div>`).join(``)}
      <h4>参考答案</h4>${p(i.sample_answer)}
      <h4>表达升级</h4>${f(i.upgrade)}
    `,await w()}return{loadQuestions:b,selectQuestion:x,showSampleAnswer:S,loadRecords:w,renderRecordColumn:C,viewRecord:T,renderRecordDetail:D,renderConversation:E,deleteRecord:O,clearRecords:k,loadProfessionalPack:A,selectProfessionalQuestion:j,showProfessionalReference:M,scoreProfessionalAnswer:N,scorePractice:P}}function d(e,t){let n=e(t);if(!n)throw Error(`Missing interview control: #${t}`);return n}function f(e){let{userId:t,state:l,request:f,byId:p,toast:m,renderIcons:h,selectedCareerProfile:g,buildInterviewStartPayload:_,escapeHtml:v,loadDashboard:y,submission:b}=e;function x(e){l.interviewStageIndex=Math.max(0,Number(e.progress||1)-1),l.currentInterviewSession=e,d(p,`currentQuestion`).textContent=e.question,d(p,`interviewStageLabel`).textContent=r(e.stage);let t=Math.min(100,e.progress/e.total*100),n=d(p,`interviewProgress`);n.style.width=`${t}%`,n.parentElement?.classList.toggle(`has-progress`,t>0),d(p,`roomQuestion`).textContent=e.question,d(p,`roomStageLabel`).textContent=r(e.stage),d(p,`roomProgress`).style.width=`${t}%`}function S(e){x(e),d(p,`roomAnswer`).value=``,d(p,`roomFeedback`).classList.add(`hidden`),d(p,`interviewRoom`).classList.remove(`hidden`),h()}async function C(){let e=l.interviewOpportunityHandoff,n=e?.resumeId||d(p,`interviewResumeSelect`).value||l.resumes[0]?.id;if(!n){m(`请先保存或选择简历`);return}let r=_({user_id:t,resume_id:Number(n),job_title:d(p,`interviewJobTitle`).value||`软件测试工程师`,jd:d(p,`interviewJd`).value,career_profile:g(),mode:`campus`},e),i=await f(`/interview/sessions`,{method:`POST`,body:r});if(!i.success){m(i.message||`面试创建失败`);return}l.activeInterview=i.session_id,l.pendingInterviewSubmission=null,l.interviewSubmitting=!1,l.interviewOpportunityHandoff=null,x(i),d(p,`interviewFeedback`).classList.add(`hidden`),S(i)}function w(e){let t=e.voice.dimension_scores||{};return`
      <h4>即时反馈：${e.score} 分</h4>
      <div>${v(e.summary)}</div>
      <div>语速：${e.voice.estimated_speech_rate} 字/分钟（${e.voice.pace_label||`自然`}），口头禅：${e.voice.filler_count} 次，结构分：${e.voice.structure_score}</div>
      <div><b>维度分</b><br>${Object.entries(t).map(([e,t])=>`${e}：${t}`).join(`　`)}</div>
      ${e.voice.audio_quality?`<div><b>真实录音质量</b><br>${v(e.voice.audio_quality)}</div>`:``}
      ${e.answer_upgrade?`<div><b>表达升级</b><br>${v(e.answer_upgrade)}</div>`:``}
      ${(e.suggestions||[]).map(e=>`<div>• ${v(e)}</div>`).join(``)}
    `}function T(e){let t=d(p,`interviewFeedback`);t.classList.remove(`hidden`),t.innerHTML=w(e)}async function E(){if(!l.activeInterview){m(`请先开始模拟面试`);return}if(l.interviewSubmitting)return;let e=d(p,`answerInput`),t=e.value.trim();if(!t){m(`请先输入回答`);return}let n=await b.submitInterviewAnswer(l,t,{createId:()=>globalThis.crypto&&typeof globalThis.crypto.randomUUID==`function`?globalThis.crypto.randomUUID():`interview-${Date.now()}-${Math.random().toString(36).slice(2)}`,send:e=>f(`/interview/sessions/${l.activeInterview}/answer`,{method:`POST`,body:{answer:e.answer,submission_id:e.submissionId,expected_stage_index:e.expectedStageIndex}}),reload:()=>f(`/interview/sessions/${l.activeInterview}`)});if(n.kind===`success`){let t=n.session;x(t),e.value=``,T(t.feedback),t.stage===`finished`&&await Promise.all([y(),k.loadRecords()]);return}if(n.kind===`conflict_recovered`){x(n.session),e.value=``,m(`面试进度已同步，请回答当前问题`);return}n.kind!==`busy`&&m(`提交结果不确定，请重试`)}async function D(){let e=d(p,`roomAnswer`),t=e.value.trim();if(!t){m(`请先输入本轮回答`);return}d(p,`answerInput`).value=t,await E(),e.value=``;let n=d(p,`roomFeedback`);n.classList.remove(`hidden`),n.innerHTML=d(p,`interviewFeedback`).innerHTML}async function O(){let e=d(p,`answerInput`).value.trim();if(!e){m(`请先输入或语音录入回答`);return}let t=await f(`/interview/analyze-voice`,{method:`POST`,body:{answer:e}});T({score:t.overall_score,summary:`表达分析完成`,voice:t,suggestions:t.tips})}let k=u(e),A=n(e,{renderFeedback:T,renderFeedbackHtml:w,loadTrainingRecords:k.loadRecords});return{start:C,updateQuestion:x,openRoom:S,stageName:r,sendAnswer:E,sendRoomAnswer:D,renderFeedback:T,renderFeedbackHtml:w,analyzeVoice:O,extensionFromMime:A.extensionFromMime,downloadSavedAudio:A.downloadSaved,getRecordingController:A.getRecordingController,startAudioRecording:A.startRecording,stopAudioRecording:A.stopRecording,handleAudioUpload:A.handleUpload,computeAudioMetrics:A.computeMetrics,renderAudioPreview:A.renderPreview,analyzeRecordedAudio:A.analyzeRecorded,applyBrowserCapabilities:A.applyCapabilities,setupSpeechRecognition:A.setupSpeechRecognition,toggleVoiceInput:A.toggleVoiceInput,loadQuestions:k.loadQuestions,escapeAttr:i,categoryName:a,selectQuestion:k.selectQuestion,showSampleAnswer:k.showSampleAnswer,loadTrainingRecords:k.loadRecords,renderRecordColumn:k.renderRecordColumn,viewTrainingRecord:k.viewRecord,renderRecordDetail:k.renderRecordDetail,safeJson:o,renderConversation:k.renderConversation,parseFeedbackSummary:c,formatDate:s,deleteTrainingRecord:k.deleteRecord,clearTrainingRecords:k.clearRecords,loadProfessionalPack:k.loadProfessionalPack,selectProfessionalQuestion:k.selectProfessionalQuestion,showProfessionalReference:k.showProfessionalReference,scoreProfessionalAnswer:k.scoreProfessionalAnswer,scorePractice:k.scorePractice}}return e.createInterviewController=f,e})({});