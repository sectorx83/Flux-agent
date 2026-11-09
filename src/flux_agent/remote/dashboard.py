"""Responsive Flux Agent control-room dashboard."""

DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#090b12">
<title>Flux · Control room</title>
<style>
:root{color-scheme:dark;--bg:#090b12;--panel:#111521;--panel2:#151b2a;--line:#242c3d;--muted:#8792a8;--text:#eef2fb;--violet:#9b8cff;--cyan:#56d7e8;--lime:#b8ef7b;--pink:#f08bb8;--shadow:0 18px 55px #0005}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 75% -15%,#34265d66,transparent 38%),radial-gradient(ellipse at 5% 55%,#123f4b30,transparent 32%),var(--bg);color:var(--text);font:14px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;min-height:100vh}
button,input,textarea,select{font:inherit}button{cursor:pointer}.shell{display:grid;grid-template-columns:250px minmax(0,1fr);min-height:100vh}.side{border-right:1px solid var(--line);padding:26px 17px;background:#0c0f18c9;display:flex;flex-direction:column;gap:28px}.brand{display:flex;align-items:center;gap:12px;padding:0 10px}.mark{width:37px;height:37px;border-radius:13px;background:linear-gradient(140deg,var(--violet),#5f9cff 60%,var(--cyan));display:grid;place-items:center;color:#0a0c13;font-weight:900;font-size:19px;box-shadow:0 0 28px #8e7dff55}.brand strong{font-size:17px;letter-spacing:.02em}.brand small{display:block;color:var(--muted);font-size:10px;letter-spacing:.17em;text-transform:uppercase}.navlabel{color:#59647a;font-size:10px;font-weight:800;letter-spacing:.16em;padding:0 12px;margin-bottom:7px}.nav{display:grid;gap:5px}.nav button{border:1px solid transparent;background:transparent;color:#a7b0c3;text-align:left;padding:11px 12px;border-radius:11px;display:flex;align-items:center;gap:12px;transition:.18s}.nav button:hover{background:#ffffff08;color:var(--text)}.nav button.active{background:linear-gradient(100deg,#8e7dff22,#56d7e80d);border-color:#8e7dff38;color:#fff}.ico{width:19px;text-align:center;color:var(--cyan);font-size:16px}.sidefoot{margin-top:auto;border:1px solid var(--line);border-radius:14px;padding:13px;background:#111521}.pulse{width:7px;height:7px;border-radius:50%;background:var(--lime);display:inline-block;box-shadow:0 0 12px var(--lime);margin-right:7px}.sidefoot small{color:var(--muted);display:block;margin-top:5px}.main{padding:30px clamp(18px,4vw,54px) 48px;max-width:1600px;width:100%;margin:auto}.top{display:flex;justify-content:space-between;align-items:center;gap:18px;margin-bottom:30px}.eyebrow{color:var(--cyan);font-size:10px;letter-spacing:.2em;text-transform:uppercase;font-weight:800}.top h1{font-size:clamp(25px,3vw,34px);letter-spacing:-.045em;margin:5px 0 0}.topright{display:flex;align-items:center;gap:10px}.statuspill{border:1px solid #b8ef7b33;background:#b8ef7b0d;color:var(--lime);border-radius:99px;padding:8px 12px;font-size:11px}.avatar{height:37px;width:37px;border-radius:50%;display:grid;place-items:center;background:#24233a;border:1px solid #8173d955;color:#c9c0ff;font-weight:700}.grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:16px}.card{background:linear-gradient(145deg,#151a28ed,#10141fef);border:1px solid var(--line);border-radius:18px;padding:19px;box-shadow:var(--shadow);min-width:0}.welcome{grid-column:span 8;position:relative;overflow:hidden;min-height:210px;padding:27px;background:linear-gradient(110deg,#211d3d,#151b2b 65%,#10232b)}.welcome:after{content:"";position:absolute;width:260px;height:260px;border:1px solid #9b8cff33;border-radius:50%;right:5%;top:-90px;box-shadow:0 0 0 24px #9b8cff08,0 0 0 50px #9b8cff06}.welcome h2{font-size:clamp(22px,3vw,31px);letter-spacing:-.04em;margin:9px 0}.welcome p{color:#aeb8cb;max-width:490px;margin:0 0 20px}.btn{border:0;border-radius:10px;padding:10px 15px;background:linear-gradient(100deg,#a99aff,#72dce7);color:#10121b;font-weight:800;box-shadow:0 8px 24px #8e7dff28}.btn:hover{filter:brightness(1.08);transform:translateY(-1px)}.ghost{background:#ffffff08;border:1px solid var(--line);color:#dce3f2;box-shadow:none}.stat{grid-column:span 2;min-height:150px}.stathead{color:var(--muted);font-size:11px;display:flex;justify-content:space-between}.statnum{font-size:32px;letter-spacing:-.05em;font-weight:750;margin:14px 0 3px}.statnote{font-size:10px;color:var(--muted)}.accent{color:var(--cyan)}.stat:nth-child(3) .accent{color:var(--lime)}.stat:nth-child(4) .accent{color:var(--violet)}.sectionhead{display:flex;align-items:center;justify-content:space-between;margin:27px 2px 13px}.sectionhead h3{font-size:14px;margin:0;letter-spacing:.01em}.sectionhead span{color:var(--muted);font-size:11px}.composer{grid-column:span 7}.activity{grid-column:span 5}.cardtitle{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px}.cardtitle h3{margin:0;font-size:14px}.hint{font-size:10px;color:var(--muted)}textarea{width:100%;min-height:116px;resize:vertical;background:#0b0f18;border:1px solid #2b3448;border-radius:12px;padding:14px;color:var(--text);outline:none}textarea:focus,input:focus,select:focus{border-color:#9282ff;box-shadow:0 0 0 3px #9282ff20}.composefoot{display:flex;align-items:center;gap:10px;margin-top:12px}.composefoot select{background:#0b0f18;border:1px solid var(--line);border-radius:9px;color:#cbd4e6;padding:10px}.composefoot .btn{margin-left:auto}.tasklist{display:grid;gap:9px}.task{display:flex;align-items:center;gap:12px;padding:11px 12px;border:1px solid #252d3e;border-radius:12px;background:#0c111b}.taskicon{width:33px;height:33px;border-radius:10px;background:#8e7dff18;color:var(--violet);display:grid;place-items:center}.taskbody{min-width:0;flex:1}.taskbody strong{display:block;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.taskbody small{font-size:10px;color:var(--muted)}.tag{font-size:9px;border-radius:99px;padding:4px 8px;background:#ffffff0b;color:#aeb8cb;text-transform:uppercase;letter-spacing:.08em}.tag.completed{color:var(--lime);background:#b8ef7b12}.tag.failed{color:var(--pink);background:#f08bb812}.tag.running{color:var(--cyan);background:#56d7e812}.activityempty{padding:28px 8px;text-align:center;color:var(--muted);font-size:12px}.bottomrow{grid-column:span 12;display:grid;grid-template-columns:1fr 1fr;gap:16px}.mini{display:flex;align-items:center;justify-content:space-between;gap:15px}.mini strong{font-size:12px}.mini small{display:block;color:var(--muted);font-size:10px}.mini .glyph{font-size:21px;color:var(--violet)}.toast{position:fixed;bottom:22px;right:22px;padding:12px 16px;background:#20283a;border:1px solid #44506b;border-radius:12px;box-shadow:var(--shadow);z-index:10;max-width:min(90vw,400px);display:none}.login{max-width:440px;margin:12vh auto;padding:28px}.login h2{margin:8px 0}.login p{color:var(--muted)}.login input{width:100%;margin:12px 0;background:#0b0f18;border:1px solid var(--line);border-radius:10px;padding:13px;color:var(--text)}.hidden{display:none!important}
@media(max-width:1100px){.stat{grid-column:span 3}.welcome{grid-column:span 12}.composer,.activity{grid-column:span 12}}
@media(max-width:700px){.shell{display:block}.side{position:sticky;top:0;z-index:5;height:auto;padding:12px 14px;border-right:0;border-bottom:1px solid var(--line);flex-direction:row;align-items:center;justify-content:space-between}.brand{padding:0}.mark{width:33px;height:33px}.navlabel,.sidefoot{display:none}.nav{display:flex;gap:3px;overflow:auto;max-width:62vw}.nav button{padding:8px 10px;font-size:0;gap:0}.nav button .ico{font-size:17px}.main{padding:22px 14px 36px}.top{margin-bottom:20px}.top h1{font-size:25px}.statuspill{font-size:0;padding:9px}.statuspill .pulse{margin:0}.avatar{display:none}.grid{gap:11px}.card{padding:15px;border-radius:15px}.stat{grid-column:span 6;min-height:125px}.statnum{font-size:27px}.welcome{min-height:190px}.bottomrow{grid-template-columns:1fr}.composefoot{flex-wrap:wrap}.composefoot .btn{width:100%;margin:0}.composefoot select{flex:1}.task{padding:9px}.sectionhead{margin-top:21px}}
</style>
</head>
<body>
<div id="login" class="card login">
 <div class="brand" style="padding:0"><div class="mark">ϟ</div><div><strong>flux</strong><small>agent control room</small></div></div>
 <h2>Welcome back.</h2><p>Connect to your Flux host using its remote admin token. The token stays in this browser session only.</p>
 <form id="loginForm"><input id="tokenInput" type="password" autocomplete="current-password" placeholder="FLUX_REMOTE_TOKEN" required minlength="32"><button class="btn" style="width:100%">Connect to Flux ↗</button></form>
 <p class="hint">Your Flux remote API must be running with HTTPS when accessed over a network.</p>
</div>
<div id="app" class="shell hidden">
 <aside class="side">
  <div class="brand"><div class="mark">ϟ</div><div><strong>flux</strong><small>agent control room</small></div></div>
  <div><div class="navlabel">WORKSPACE</div><nav class="nav">
   <button class="active" data-target="overview"><span class="ico">◈</span>Overview</button>
   <button data-target="agent"><span class="ico">✳</span>Agent</button>
   <button data-target="tasks"><span class="ico">▤</span>Tasks</button>
   <button data-target="integrations"><span class="ico">⌘</span>Integrations</button>
   <button data-target="settings"><span class="ico">⚙</span>Settings</button>
  </nav></div>
  <div class="sidefoot"><span class="pulse"></span><strong style="font-size:11px">Host connected</strong><small>Authenticated remote session</small></div>
 </aside>
 <main class="main">
  <header class="top"><div><div class="eyebrow">FLUX / SYSTEM OVERVIEW</div><h1>Control room</h1></div><div class="topright"><span class="statuspill"><i class="pulse"></i> LIVE</span><div class="avatar">F</div></div></header>
  <section id="overview" class="grid">
   <div class="card welcome"><div class="eyebrow">YOUR AGENT IS READY</div><h2>Make things happen.<br><span style="color:var(--cyan)">Keep the control.</span></h2><p>Send a task, watch its progress, and keep every operation connected to the same Flux engine that powers your CLI.</p><button class="btn" onclick="document.querySelector('#prompt').focus()">＋ Create a task</button></div>
   <div class="card stat"><div class="stathead">TOTAL TASKS <span class="accent">↗</span></div><div class="statnum" id="total">—</div><div class="statnote">Across this workspace</div></div>
   <div class="card stat"><div class="stathead">COMPLETED <span class="accent">✓</span></div><div class="statnum" id="completed">—</div><div class="statnote">Successfully finished</div></div>
   <div class="card stat"><div class="stathead">IN PROGRESS <span class="accent">◌</span></div><div class="statnum" id="running">—</div><div class="statnote">Queued or processing</div></div>
   <div class="card stat"><div class="stathead">FAILED <span class="accent">!</span></div><div class="statnum" id="failed">—</div><div class="statnote">Need attention</div></div>
   <div class="card composer" id="agent"><div class="cardtitle"><h3>Start something</h3><span class="hint">NEW TASK · REMOTE EXECUTION</span></div><textarea id="prompt" maxlength="20000" placeholder="Tell Flux what you want done…&#10;&#10;Example: Plan a Telegram integration and list the credentials I need."></textarea><div class="composefoot"><select id="mode" aria-label="Task mode"><option value="chat">Chat mode</option><option value="plan" selected>Plan mode</option><option value="build">Build mode</option></select><span class="hint">Build actions still require host-side approval.</span><button class="btn" id="send">Run task ↗</button></div></div>
   <div class="card activity" id="tasks"><div class="cardtitle"><h3>Recent activity</h3><button class="btn ghost" id="refresh" style="padding:7px 10px;font-size:10px">Refresh ↻</button></div><div id="tasklist" class="tasklist"><div class="activityempty">Connect to Flux to load activity.</div></div></div>
   <div class="bottomrow">
    <div class="card mini" id="integrations"><div><strong>Integrations centre</strong><small>Connect services through the Flux host and its official adapters.</small></div><span class="glyph">⌘</span></div>
    <div class="card mini" id="settings"><div><strong>Session & security</strong><small>Token is held in session memory. Disconnect to clear it.</small></div><button class="btn ghost" id="logout">Disconnect</button></div>
   </div>
  </section>
 </main>
</div>
<div id="toast" class="toast" role="status"></div>
<script>
(() => {
 let token = sessionStorage.getItem("flux.remote.token") || "";
 let records = [];
 const $ = id => document.getElementById(id);
 const auth = () => ({Authorization:"Bearer "+token});
 function toast(message){$("toast").textContent=message;$("toast").style.display="block";clearTimeout(toast.timer);toast.timer=setTimeout(()=>$("toast").style.display="none",3600)}
 async function api(path, options={}) {
  const response=await fetch(path,{...options,headers:{...auth(),...(options.headers||{})}});
  if(response.status===401){disconnect();throw new Error("Authentication failed. Check your remote token.");}
  const data=await response.json().catch(()=>({detail:"Unexpected server response"}));
  if(!response.ok)throw new Error(data.detail||"Request failed ("+response.status+")");
  return data;
 }
 function showApp(){ $("login").classList.add("hidden");$("app").classList.remove("hidden");}
 function disconnect(){token="";sessionStorage.removeItem("flux.remote.token");$("app").classList.add("hidden");$("login").classList.remove("hidden");}
 function render(){
  const counts={completed:0,failed:0,running:0};
  records.forEach(t=>{if(t.status==="completed")counts.completed++;else if(t.status==="failed")counts.failed++;else counts.running++});
  $("total").textContent=records.length;$("completed").textContent=counts.completed;$("running").textContent=counts.running;$("failed").textContent=counts.failed;
  const list=$("tasklist");list.replaceChildren();
  if(!records.length){list.innerHTML='<div class="activityempty">No tasks yet. Your first one is one prompt away.</div>';return}
  records.slice(0,7).forEach(t=>{
   const row=document.createElement("div");row.className="task";
   const icon=document.createElement("div");icon.className="taskicon";icon.textContent=t.mode==="build"?"⌘":t.mode==="plan"?"◎":"✳";
   const body=document.createElement("div");body.className="taskbody";
   const title=document.createElement("strong");title.textContent=t.prompt||("Task #"+t.id);
   const meta=document.createElement("small");meta.textContent="#"+t.id+" · "+t.mode+" · "+new Date(t.created_at).toLocaleString();
   const tag=document.createElement("span");tag.className="tag "+(t.status||"");tag.textContent=t.status||"unknown";
   body.append(title,meta);row.append(icon,body,tag);list.append(row);
  });
 }
 async function refresh(){try{const data=await api("/tasks");records=data.tasks||[];render()}catch(e){toast(e.message)}}
 $("loginForm").addEventListener("submit",async e=>{e.preventDefault();token=$("tokenInput").value.trim();try{await api("/health");await api("/tasks");sessionStorage.setItem("flux.remote.token",token);showApp();await refresh()}catch(err){toast(err.message)}});
 $("send").addEventListener("click",async()=>{const prompt=$("prompt").value.trim();if(!prompt){toast("Write a task first.");return}
 const button=$("send");button.disabled=true;button.textContent="Submitting…";
 try{const task=await api("/tasks",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt,mode:$("mode").value})});$("prompt").value="";toast("Task #"+task.id+" added to the Flux queue.");await refresh()}
 catch(e){toast(e.message)}finally{button.disabled=false;button.textContent="Run task ↗"}
 });
 $("refresh").addEventListener("click",refresh);$("logout").addEventListener("click",disconnect);
 document.querySelectorAll(".nav button").forEach(button=>button.addEventListener("click",()=>{document.querySelectorAll(".nav button").forEach(b=>b.classList.remove("active"));button.classList.add("active");const target=$(button.dataset.target);if(target)target.scrollIntoView({behavior:"smooth",block:"center"})}));
 if(token){showApp();api("/health").then(refresh).catch(()=>{})}
 setInterval(()=>{if(token)refresh()},10000);
})();
</script>
</body></html>"""
