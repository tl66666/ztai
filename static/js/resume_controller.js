var JobHunterResumeController=(function(e){Object.defineProperty(e,Symbol.toStringTag,{value:`Module`});function t(e,t){let n=e(t);if(!n)throw Error(`Missing resume control: #${t}`);return n}function n(e){let{userId:n,state:r,request:i,byId:a,escapeHtml:o,toast:s,renderIcons:c,syncAgentContext:l,loadDashboard:u,downloadResponse:d,withLoading:f,jumpToModule:p,closeAgentDrawer:m,apiBaseUrl:h,renderText:g,selectedCareerProfile:_,careerProfileLabel:v,clearMatchOpportunityLink:y,buildMatchPayload:b}=e;function x(e=``){t(a,`editingResumeNotice`).classList.toggle(`hidden`,!r.editingResumeId);let n=t(a,`editingResumeText`);n.textContent=e?`当前版本：${e}。修改后点击“更新当前简历”保存。`:`修改后点击“更新当前简历”保存。`}function S(){let e=`<option value="">选择简历</option>${r.resumes.map(e=>`<option value="${e.id}">${o(e.title)}</option>`).join(``)}`;for(let n of[`tailorResumeSelect`,`interviewResumeSelect`,`exportResumeSelect`,`analysisResumeSelect`,`skillResumeSelect`])t(a,n).innerHTML=e}async function C(){let e=await i(`/resumes/${n}`);r.resumes=e.success?e.data:[],t(a,`resumeCount`).textContent=String(r.resumes.length),t(a,`resumeList`).innerHTML=r.resumes.length?r.resumes.map(e=>`
        <article class="list-item" data-resume-id="${e.id}" tabindex="-1">
          <b>${o(e.title)}</b>
          <small>${new Date(e.updated_at||e.created_at||``).toLocaleString()}${e.file_type?` · 原件 ${o(e.file_type.toUpperCase())}`:``}</small>
          <div class="list-actions">
            <button class="ghost small" onclick="fillResume(${e.id})">编辑</button>
            <button class="ghost small" onclick="openOriginalResume(${e.id})">打开原件</button>
            <label class="ghost small file-action">替换原件<input type="file" accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg" onchange="replaceOriginalResume(${e.id}, this)"></label>
            <button class="ghost small" onclick="analyzeResume(${e.id})">诊断</button>
            <button class="ghost small" onclick="deleteResume(${e.id})">删除</button>
          </div>
        </article>
      `).join(``):`<div class="list-item"><b>暂无简历</b><small>先保存一份简历</small></div>`,S(),l(),c()}async function w(e){let n=await i(`/resumes/detail/${e}`);if(!n.success)return;t(a,`resumeTitle`).value=n.data.title;let o=t(a,`resumeContent`);o.value=n.data.content,r.editingResumeId=e,t(a,`saveResumeBtn`).innerHTML=`<i data-lucide="save"></i>更新当前简历`,x(n.data.title),c(),p(`resume`,`input`),t(a,`resumeTitle`).focus(),o.scrollTop=0,s(`正在编辑：${n.data.title}`)}function T(){m(),p(`resume`,`input`);let e=t(a,`resumeFile`);e.focus({preventScroll:!0}),e.click()}function E(){let e=t(a,`resumeFile`).files?.[0],n=t(a,`resumeTitle`);!e||n.value.trim()||(n.value=e.name.replace(/\.[^.]+$/,``).slice(0,300))}function D(){r.editingResumeId=null,t(a,`resumeTitle`).value=``,t(a,`resumeContent`).value=``,t(a,`resumeFile`).value=``,t(a,`saveResumeBtn`).innerHTML=`<i data-lucide="save"></i>保存简历`,x(),c(),s(`已退出简历编辑模式`)}function O(e){window.open(`${h}/resumes/${e}/original`,`_blank`)}async function k(){let e=t(a,`resumeFile`),o=e.files?.[0],l=t(a,`resumeTitle`).value.trim(),d=t(a,`resumeContent`).value.trim();if(!l){s(`请填写简历标题`);return}let f;if(o){let e=new FormData;e.append(`file`,o),e.append(`user_id`,String(n)),e.append(`title`,l),f=await i(`/resumes/upload`,{method:`POST`,body:e})}else if(r.editingResumeId){if(!d){s(`请粘贴简历内容或上传文件`);return}f=await i(`/resumes/${r.editingResumeId}`,{method:`PUT`,body:{title:l,content:d}})}else{if(!d){s(`请粘贴简历内容或上传文件`);return}f=await i(`/resumes`,{method:`POST`,body:{user_id:n,title:l,content:d}})}if(!f.success){s(f.message||`保存失败`);return}s(r.editingResumeId?`简历已更新`:`简历已保存`),e.value=``,r.editingResumeId=null,t(a,`saveResumeBtn`).innerHTML=`<i data-lucide="save"></i>保存简历`,x(),await C(),await u(),c()}function A(){return r.resumes[0]?.id}async function j(e){let n=t(a,`exportResumeSelect`).value||A();if(!n){s(`请先选择要导出的简历`);return}if(!i.raw)throw Error(`ApiClient.raw is required for resume exports`);let r=await i.raw(`/resumes/${n}/export/${e}`);await d(r,e===`pdf`?`resume.pdf`:`resume.docx`)}async function M(e,n){let r=t(a,n),o=r.files?.[0];if(!o)return;let s=new FormData;if(s.append(`file`,o),!i.raw)throw Error(`ApiClient.raw is required for document conversion`);let c=await i.raw(`/convert/${e}`,{method:`POST`,body:s});await d(c,e===`pdf-to-word`?`converted.docx`:`converted.pdf`),r.value=``}async function N(){let e=await i(`/resume-generator`,{method:`POST`,body:{name:`唐乐`,job_target:`软件测试工程师`,skills:`Python, Flask, Selenium, Pytest, JMeter, Postman, MySQL`}});t(a,`resumeTitle`).value=`唐乐-软件测试工程师-项目版`,t(a,`resumeContent`).value=e.resume_content,s(`已生成一份可继续修改的示例简历`)}function P(e){let n=t(a,`resumeAuditResult`);n.classList.remove(`hidden`),n.innerHTML=`
      <h4>综合评分：${e.score}</h4>
      <div class="score-grid">
        ${Object.entries(e.section_scores||{}).map(([e,t])=>`<div><span>${o(e)}</span><b>${t}</b></div>`).join(``)}
      </div>
      <div><b>一句话定位</b><br>${o(e.positioning)}</div>
      <div><b>优势证据</b><br>${(e.strengths||[]).map(e=>`• ${o(e)}`).join(`<br>`)}</div>
      <div><b>客观锐评</b><br>${(e.brutal_comments||[]).map(e=>`• ${o(e)}`).join(`<br>`)}</div>
      <div><b>HR 初筛风险</b><br>${(e.risks||[]).map(e=>`• ${o(e)}`).join(`<br>`)}</div>
      <div><b>证据缺口</b><br>${(e.evidence_gaps||[]).map(e=>`• ${o(e)}`).join(`<br>`)}</div>
      <div><b>优先修改项</b><br>${(e.actions||[]).map(e=>`• ${o(e)}`).join(`<br>`)}</div>
      <div><b>项目经历建议</b><br>${(e.project_suggestions||[]).map(e=>`• ${o(e)}`).join(`<br>`)}</div>
      <div class="result-actions">
        <button class="primary" onclick="improveSelectedResume()">生成优化版并保存</button>
        <button class="ghost" onclick="jumpToModule('resume','jd')">去做 JD 优化</button>
        <button class="ghost" onclick="jumpToModule('resume','skills')">看技能图谱</button>
        <button class="ghost" onclick="jumpToModule('interview','mock')">去模拟面试</button>
      </div>
    `}async function F(e){let n=await f(()=>i(`/resumes/${e}/audit`,{method:`POST`,body:{job_title:t(a,`analysisJobTitle`).value||t(a,`jobTitleInput`).value,jd:t(a,`analysisJdInput`).value||t(a,`jdInput`).value}}),`AI 正在诊断简历表达...`);t(a,`analysisResumeSelect`).value=String(e),p(`resume`,`analysis`),P(n)}function I(){return t(a,`analysisResumeSelect`).value||A()}async function L(){let e=I();if(!e){s(`请先选择要分析的简历`);return}let n=await f(()=>i(`/resumes/${e}/audit`,{method:`POST`,body:{job_title:t(a,`analysisJobTitle`).value,jd:t(a,`analysisJdInput`).value,career_profile:_()}}),`AI 正在做简历结构诊断...`);if(!n.success){s(n.message||`诊断失败`);return}P(n)}async function R(){let e=I();if(!e){s(`请先选择要修改的简历`);return}let n=await f(()=>i(`/resumes/${e}/improve`,{method:`POST`,body:{job_title:t(a,`analysisJobTitle`).value||t(a,`jobTitleInput`).value,jd:t(a,`analysisJdInput`).value||t(a,`jdInput`).value,career_profile:_(),save:!0}}),`AI 正在生成可投递优化版...`);if(!n.success){s(n.message||`优化失败`);return}let r=t(a,`resumeAuditResult`);r.classList.remove(`hidden`),r.innerHTML=`
      <h4>已生成优化版：${o(n.new_title||`新简历版本`)}</h4>
      <div><b>${n.ai_used?`AI 深度改写：已通读完整简历并按目标岗位调整表达。`:`本地事实保真版：模型不可用时保留原始事实并完成结构整理。`}</b></div>
      <div><b>改写策略</b><br>${(n.strategy||[]).map(e=>`• ${o(e)}`).join(`<br>`)}</div>
      <h4>优化内容预览</h4>${g(n.improved_resume||``)}
      <div class="result-actions">
        <button class="primary" onclick="jumpToModule('resume','manage')">查看我的简历</button>
        <button class="ghost" onclick="jumpToModule('resume','export')">导出新版本</button>
        <button class="ghost" onclick="prepareInterviewFromJd()">带入模拟面试</button>
      </div>
    `,await C(),await u()}async function z(e){await i(`/resumes/${e}`,{method:`DELETE`}),s(`简历已删除`),await Promise.all([C(),u()])}function B(){return t(a,`tailorResumeSelect`).value||A()}function V(){return t(a,`skillResumeSelect`).value||A()}async function H(){let e=B();if(!e){s(`请先选择简历`);return}let n=await f(()=>i(`/resumes/${e}/tailor`,{method:`POST`,body:{job_title:t(a,`jobTitleInput`).value,jd:t(a,`jdInput`).value,career_profile:_()}}),`AI 正在按 JD 优化简历...`),r=t(a,`tailorResult`);r.classList.remove(`hidden`);let c=n.jd_focus||{};r.innerHTML=`
      <h4>匹配分：${n.match_score}</h4>
      <div class="score-grid">
        ${Object.entries(n.score_detail||{}).map(([e,t])=>`<div><span>${o(e)}</span><b>${t}</b></div>`).join(``)}
      </div>
      <div><b>候选人定位</b><br>${o(n.positioning)}</div>
      <div><b>客观锐评</b><br>${(n.brutal_comments||[]).map(e=>`• ${o(e)}`).join(`<br>`)}</div>
      <div><b>JD 聚焦</b><br>
        硬技能：${o((c.硬技能||[]).join(`、`)||`未明显出现`)}<br>
        测试能力：${o((c.测试能力||[]).join(`、`)||`未明显出现`)}<br>
        AI 能力：${o((c[`AI 能力`]||[]).join(`、`)||`未明显出现`)}
      </div>
      <div><b>已命中</b><br>${o((n.matched_keywords||[]).join(`、`)||`暂无`)}</div>
      <div><b>待补齐</b><br>${o((n.keyword_gaps||[]).join(`、`)||`暂无`)}</div>
      <div><b>面试讲述要点</b><br>${(n.interview_talking_points||[]).map(e=>`• ${o(e)}`).join(`<br>`)}</div>
      <h4>优化版本</h4>${g(n.ai_rewrite||n.tailored_resume)}
      <div class="result-actions">
        <button class="primary" onclick="prepareInterviewFromJd()">带入模拟面试</button>
        <button class="ghost" onclick="prepareApplicationFromJd()">新增投递记录</button>
        <button class="ghost" onclick="jumpToModule('resume','export')">去导出简历</button>
      </div>
    `}async function U(){let e=B();if(!e){s(`请先选择简历`);return}let n=b({resume_id:Number(e),job_title:t(a,`jobTitleInput`).value,jd:t(a,`jdInput`).value,job_requirements:t(a,`jdInput`).value,career_profile:_()},r.matchOpportunityId),c=await f(()=>i(`/job-match`,{method:`POST`,body:n}),`AI 正在计算岗位匹配度...`);if(!c.success){s(c.message||`岗位匹配失败`);return}y();let l=t(a,`tailorResult`);l.classList.remove(`hidden`),l.innerHTML=`<h4>岗位匹配：${c.match_score}</h4>${g(c.analysis)}<br><b>待补齐：</b>${o((c.missing_keywords||[]).join(`、`))}
      <div class="result-actions">
        <button class="primary" onclick="prepareInterviewFromJd()">带入模拟面试</button>
        <button class="ghost" onclick="prepareApplicationFromJd()">新增投递记录</button>
      </div>`,await u()}async function W(){let e=t(a,`jdInput`).value.trim();if(!e){s(`请先粘贴岗位 JD`);return}let n=await f(()=>i(`/ai/analyze-jd`,{method:`POST`,body:{jd_content:e,job_title:t(a,`jobTitleInput`).value,career_profile:_()}}),`AI 正在拆解 JD...`),r=t(a,`tailorResult`);r.classList.remove(`hidden`);let c=n.focus||{};r.innerHTML=`
      <h4>JD 岗位画像</h4>
      <div><b>求职方向</b><br>${o(n.profile?.label||v())}</div>
      <div><b>核心关键词</b><br>${o((n.keywords||[]).join(`、`)||`暂无`)}</div>
      <div><b>能力聚焦</b><br>
        ${Object.entries(c).map(([e,t])=>`${o(e)}：${o((t||[]).join(`、`)||`未明显出现`)}`).join(`<br>`)}
      </div>
      <div><b>风险提示</b><br>${(n.risk_flags||[]).map(e=>`• ${o(e)}`).join(`<br>`)||`暂无明显风险词`}</div>
      ${g(n.content||``)}
      <div class="result-actions">
        <button class="primary" onclick="tailorResume()">用这份 JD 优化简历</button>
        <button class="ghost" onclick="prepareInterviewFromJd()">带入模拟面试</button>
      </div>
    `}async function G(){let e=V();if(!e){s(`请先选择简历`);return}let n=await i(`/skills/radar`,{method:`POST`,body:{resume_id:Number(e),career_profile:_(),job_title:t(a,`analysisJobTitle`).value||t(a,`jobTitleInput`).value}}),c=window.Chart;r.skillChart&&r.skillChart.destroy(),r.skillChart=typeof c==`function`?new c(t(a,`skillChart`),{type:`radar`,data:{labels:n.radar_data.map(e=>e.category),datasets:[{label:`能力值`,data:n.radar_data.map(e=>e.score),backgroundColor:`rgba(255,122,182,0.18)`,borderColor:`#ff7ab6`,pointBackgroundColor:`#66dbc2`}]},options:{scales:{r:{min:0,max:10}},plugins:{legend:{display:!1}}}}):null;let l=t(a,`skillResult`);l.classList.remove(`hidden`),l.innerHTML=`
      <h4>技能图谱解读</h4>
      ${(n.radar_data||[]).map(e=>`
        <div><b>${o(e.category)}：${e.score}/10</b><br>
        已命中：${o((e.matched||[]).join(`、`)||`暂无`)}<br>
        建议：${o(e.suggestion||`补充真实项目证据，把技能写进项目过程和结果。`)}</div>
      `).join(``)}
      <div class="result-actions">
        <button class="primary" onclick="jumpToModule('resume','analysis')">去修改简历</button>
        <button class="ghost" onclick="jumpToModule('interview','professional')">按短板练专业面试</button>
      </div>
    `}async function K(e,n){let o=n.files?.[0];if(!o)return;let c=new FormData;c.append(`file`,o);let l=await f(()=>i(`/resumes/${e}/replace-file`,{method:`POST`,body:c}),`正在替换并解析原始简历...`);if(n.value=``,!l.success){s(l.message||`替换失败`);return}if(s(`原文件已替换，文本内容已重新解析`),await C(),r.editingResumeId===e){let n=await i(`/resumes/detail/${e}`);t(a,`resumeContent`).value=n.data.content||``}}return{load:C,updateSelects:S,fill:w,openUploadFromAgent:T,fillTitleFromFile:E,setEditNotice:x,cancelEdit:D,openOriginal:O,save:k,export:j,convertDocument:M,generate:N,renderAudit:P,analyze:F,selectedAnalysisId:I,auditSelected:L,improveSelected:R,remove:z,selectedResumeId:A,selectedTailorId:B,selectedSkillId:V,tailor:H,match:U,analyzeJd:W,renderSkills:G,replaceOriginal:K}}return e.createResumeController=n,e})({});