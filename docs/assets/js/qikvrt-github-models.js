
(function(){
  async function askGitHubModels(prompt, token, model){
    const body={
      model:model||'openai/gpt-4o-mini',
      messages:[
        {role:'system',content:'Du bist die QIK-VRT Kognitionskonsole. Antworte auf Deutsch, strukturiere nach Q, I, K und VRT. Sei verständlich, belege Grenzen, vermeide falsche Rechts- oder Wissenschaftsbehauptungen. Grundlage: QIK = Quantität, Information, Kausalität; VRT = verantwortbarer Realitäts-Test; Kognition = Verarbeitung von Unterschieden mit Wirkung und Verantwortung.'},
        {role:'user',content:prompt}
      ]
    };
    const res=await fetch('https://models.github.ai/inference/chat/completions',{
      method:'POST',
      headers:{'Accept':'application/vnd.github+json','Content-Type':'application/json','Authorization':'Bearer '+token,'X-GitHub-Api-Version':'2022-11-28'},
      body:JSON.stringify(body)
    });
    const txt=await res.text();
    if(!res.ok){ throw new Error('GitHub Models Fehler '+res.status+': '+txt.slice(0,700)); }
    const data=JSON.parse(txt);
    return data.choices&&data.choices[0]&&data.choices[0].message?data.choices[0].message.content:txt;
  }
  window.QIKVRTGitHubModels={askGitHubModels};
})();
