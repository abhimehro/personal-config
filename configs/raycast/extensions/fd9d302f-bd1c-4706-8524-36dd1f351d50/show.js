"use strict";var ve=Object.create;var V=Object.defineProperty;var _e=Object.getOwnPropertyDescriptor;var Se=Object.getOwnPropertyNames;var Ee=Object.getPrototypeOf,Ae=Object.prototype.hasOwnProperty;var Ce=(e,t)=>{for(var n in t)V(e,n,{get:t[n],enumerable:!0})},re=(e,t,n,r)=>{if(t&&typeof t=="object"||typeof t=="function")for(let a of Se(t))!Ae.call(e,a)&&a!==n&&V(e,a,{get:()=>t[a],enumerable:!(r=_e(t,a))||r.enumerable});return e};var P=(e,t,n)=>(n=e!=null?ve(Ee(e)):{},re(t||!e||!e.__esModule?V(n,"default",{value:e,enumerable:!0}):n,e)),Re=e=>re(V({},"__esModule",{value:!0}),e);var Ke={};Ce(Ke,{default:()=>me,onlyName:()=>te,openIn:()=>v,terminal:()=>C});module.exports=Re(Ke);var l=require("@raycast/api");var d=P(require("react")),u=require("@raycast/api");var ae=Object.prototype.hasOwnProperty;function j(e,t){var n,r;if(e===t)return!0;if(e&&t&&(n=e.constructor)===t.constructor){if(n===Date)return e.getTime()===t.getTime();if(n===RegExp)return e.toString()===t.toString();if(n===Array){if((r=e.length)===t.length)for(;r--&&j(e[r],t[r]););return r===-1}if(!n||typeof e=="object"){r=0;for(n in e)if(ae.call(e,n)&&++r&&!ae.call(t,n)||!(n in t)||!j(e[n],t[n]))return!1;return Object.keys(t).length===r}}return e!==e&&t!==t}var A=P(require("node:fs")),H=P(require("node:path"));var le=P(require("node:child_process")),ue=require("node:buffer"),I=P(require("node:stream")),fe=require("node:util");var de=require("react/jsx-runtime");var G=globalThis;function Te(e){let t=(0,d.useRef)(e),n=(0,d.useRef)(0);return j(e,t.current)||(t.current=e,n.current+=1),(0,d.useMemo)(()=>t.current,[n.current])}function x(e){let t=(0,d.useRef)(e);return t.current=e,t}function Pe(e,t){let n=e instanceof Error?e.message:String(e);return(0,u.showToast)({style:u.Toast.Style.Failure,title:t?.title??"Something went wrong",message:t?.message??n,primaryAction:t?.primaryAction??se(e),secondaryAction:t?.primaryAction?se(e):void 0})}var se=e=>{let t=!0,n="[Extension Name]...",r="";try{let s=JSON.parse((0,A.readFileSync)((0,H.join)(u.environment.assetsPath,"..","package.json"),"utf8"));n=`[${s.title}]...`,r=`https://raycast.com/${s.owner||s.author}/${s.name}`,(!s.owner||s.access==="public")&&(t=!1)}catch{}let a=u.environment.isDevelopment||t,i=e instanceof Error?e?.stack||e?.message||"":String(e);return{title:a?"Copy Logs":"Report Error",onAction(s){s.hide(),a?u.Clipboard.copy(i):(0,u.open)(`https://github.com/raycast/extensions/issues/new?&labels=extension%2Cbug&template=extension_bug_report.yml&title=${encodeURIComponent(n)}&extension-url=${encodeURI(r)}&description=${encodeURIComponent(`#### Error:
\`\`\`
${i}
\`\`\`
`)}`)}}};function he(e,t,n){let r=(0,d.useRef)(0),[a,i]=(0,d.useState)({isLoading:!0}),s=x(e),f=x(n?.abortable),o=x(t||[]),h=x(n?.onError),p=x(n?.onData),y=x(n?.onWillExecute),$=x(n?.failureToastOptions),z=x(a.data),O=(0,d.useRef)(null),m=(0,d.useRef)({page:0}),W=(0,d.useRef)(!1),L=(0,d.useRef)(!0),ne=(0,d.useRef)(50),_=(0,d.useCallback)(()=>(f.current&&(f.current.current?.abort(),f.current.current=new AbortController),++r.current),[f]),S=(0,d.useCallback)((...k)=>{let g=_();y.current?.(k),i(c=>({...c,isLoading:!0}));let R=Ie(s.current)(...k);function T(c){return c.name=="AbortError"||g===r.current&&(h.current?h.current(c):u.environment.launchType!==u.LaunchType.Background&&Pe(c,{title:"Failed to fetch latest data",primaryAction:{title:"Retry",onAction(E){E.hide(),O.current?.(...o.current||[])}},...$.current}),i({error:c,isLoading:!1})),c}return typeof R=="function"?(W.current=!0,R(m.current).then(({data:c,hasMore:E,cursor:ke})=>(g===r.current&&(m.current&&(m.current.cursor=ke,m.current.lastItem=c?.[c.length-1]),p.current&&p.current(c,m.current),E&&(ne.current=c.length),L.current=E,i(xe=>m.current.page===0?{data:c,isLoading:!1}:{data:(xe.data||[])?.concat(c),isLoading:!1})),c),c=>(L.current=!1,T(c)))):(W.current=!1,R.then(c=>(g===r.current&&(p.current&&p.current(c),i({data:c,isLoading:!1})),c),T))},[p,h,o,s,i,O,y,m,$,_]);O.current=S;let N=(0,d.useCallback)(()=>{m.current={page:0};let k=o.current||[];return S(...k)},[S,o]),ge=(0,d.useCallback)(async(k,g)=>{let R;try{if(g?.optimisticUpdate){_(),typeof g?.rollbackOnError!="function"&&g?.rollbackOnError!==!1&&(R=structuredClone(z.current?.value));let T=g.optimisticUpdate;i(c=>({...c,data:T(c.data)}))}return await k}catch(T){if(typeof g?.rollbackOnError=="function"){let c=g.rollbackOnError;i(E=>({...E,data:c(E.data)}))}else g?.optimisticUpdate&&g?.rollbackOnError!==!1&&i(c=>({...c,data:R}));throw T}finally{g?.shouldRevalidateAfter!==!1&&(u.environment.launchType===u.LaunchType.Background||u.environment.commandMode==="menu-bar"?await N():N())}},[N,z,i,_]),be=(0,d.useCallback)(()=>{m.current.page+=1;let k=o.current||[];S(...k)},[m,o,S]);(0,d.useEffect)(()=>{m.current={page:0},n?.execute!==!1?S(...t||[]):_()},[Te([t,n?.execute,S]),f,m]),(0,d.useEffect)(()=>()=>{_()},[_]);let we=n?.execute!==!1?a.isLoading:!1,ye={...a,isLoading:we},$e=W.current?{pageSize:ne.current,hasMore:L.current,onLoadMore:be}:void 0;return{...ye,revalidate:N,mutate:ge,pagination:$e}}function Ie(e){return e===Promise.all||e===Promise.race||e===Promise.resolve||e===Promise.reject?e.bind(Promise):e}var F=e=>!!e&&typeof e=="object"&&typeof e.removeListener=="function"&&typeof e.emit=="function"&&typeof e.reallyExit=="function"&&typeof e.listeners=="function"&&typeof e.kill=="function"&&typeof e.pid=="number"&&typeof e.on=="function",B=Symbol.for("signal-exit emitter"),J=class{constructor(){if(this.emitted={afterExit:!1,exit:!1},this.listeners={afterExit:[],exit:[]},this.count=0,this.id=Math.random(),G[B])return G[B];Object.defineProperty(G,B,{value:this,writable:!1,enumerable:!1,configurable:!1})}on(t,n){this.listeners[t].push(n)}removeListener(t,n){let r=this.listeners[t],a=r.indexOf(n);a!==-1&&(a===0&&r.length===1?r.length=0:r.splice(a,1))}emit(t,n,r){if(this.emitted[t])return!1;this.emitted[t]=!0;let a=!1;for(let i of this.listeners[t])a=i(n,r)===!0||a;return t==="exit"&&(a=this.emit("afterExit",n,r)||a),a}},Z=class{onExit(){return()=>{}}load(){}unload(){}},q=class{#o;#t;#e;#s;#i;#a;#r;#n;constructor(t){this.#o=process.platform==="win32"?"SIGINT":"SIGHUP",this.#t=new J,this.#a={},this.#r=!1,this.#n=[],this.#n.push("SIGHUP","SIGINT","SIGTERM"),globalThis.process.platform!=="win32"&&this.#n.push("SIGALRM","SIGABRT","SIGVTALRM","SIGXCPU","SIGXFSZ","SIGUSR2","SIGTRAP","SIGSYS","SIGQUIT","SIGIOT"),globalThis.process.platform==="linux"&&this.#n.push("SIGIO","SIGPOLL","SIGPWR","SIGSTKFLT"),this.#e=t,this.#a={};for(let n of this.#n)this.#a[n]=()=>{let r=this.#e.listeners(n),{count:a}=this.#t,i=t;if(typeof i.__signal_exit_emitter__=="object"&&typeof i.__signal_exit_emitter__.count=="number"&&(a+=i.__signal_exit_emitter__.count),r.length===a){this.unload();let s=this.#t.emit("exit",null,n),f=n==="SIGHUP"?this.#o:n;s||t.kill(t.pid,f)}};this.#i=t.reallyExit,this.#s=t.emit}onExit(t,n){if(!F(this.#e))return()=>{};this.#r===!1&&this.load();let r=n?.alwaysLast?"afterExit":"exit";return this.#t.on(r,t),()=>{this.#t.removeListener(r,t),this.#t.listeners.exit.length===0&&this.#t.listeners.afterExit.length===0&&this.unload()}}load(){if(!this.#r){this.#r=!0,this.#t.count+=1;for(let t of this.#n)try{let n=this.#a[t];n&&this.#e.on(t,n)}catch{}this.#e.emit=(t,...n)=>this.#l(t,...n),this.#e.reallyExit=t=>this.#c(t)}}unload(){this.#r&&(this.#r=!1,this.#n.forEach(t=>{let n=this.#a[t];if(!n)throw new Error("Listener not defined for signal: "+t);try{this.#e.removeListener(t,n)}catch{}}),this.#e.emit=this.#s,this.#e.reallyExit=this.#i,this.#t.count-=1)}#c(t){return F(this.#e)?(this.#e.exitCode=t||0,this.#t.emit("exit",this.#e.exitCode,null),this.#i.call(this.#e,this.#e.exitCode)):0}#l(t,...n){let r=this.#s;if(t==="exit"&&F(this.#e)){typeof n[0]=="number"&&(this.#e.exitCode=n[0]);let a=r.call(this.#e,t,...n);return this.#t.emit("exit",this.#e.exitCode,null),a}else return r.call(this.#e,t,...n)}},K=null,Ue=(e,t)=>(K||(K=F(process)?new q(process):new Z),K.onExit(e,t));function Oe(e,{timeout:t}={}){let n=new Promise((f,o)=>{e.on("exit",(h,p)=>{f({exitCode:h,signal:p,timedOut:!1})}),e.on("error",h=>{o(h)}),e.stdin&&e.stdin.on("error",h=>{o(h)})}),r=Ue(()=>{e.kill()});if(t===0||t===void 0)return n.finally(()=>r());let a,i=new Promise((f,o)=>{a=setTimeout(()=>{e.kill("SIGTERM"),o(Object.assign(new Error("Timed out"),{timedOut:!0,signal:"SIGTERM"}))},t)}),s=n.finally(()=>{clearTimeout(a)});return Promise.race([i,s]).finally(()=>r())}var Y=class extends Error{constructor(){super("The output is too big"),this.name="MaxBufferError"}};function We(e){let{encoding:t}=e,n=t==="buffer",r=new I.default.PassThrough({objectMode:!1});t&&t!=="buffer"&&r.setEncoding(t);let a=0,i=[];return r.on("data",s=>{i.push(s),a+=s.length}),r.getBufferedValue=()=>n?Buffer.concat(i,a):i.join(""),r.getBufferedLength=()=>a,r}async function ie(e,t){let n=We(t);return await new Promise((r,a)=>{let i=s=>{s&&n.getBufferedLength()<=ue.constants.MAX_LENGTH&&(s.bufferedData=n.getBufferedValue()),a(s)};(async()=>{try{await(0,fe.promisify)(I.default.pipeline)(e,n),r()}catch(s){i(s)}})(),n.on("data",()=>{n.getBufferedLength()>8e7&&i(new Y)})}),n.getBufferedValue()}async function oe(e,t){e.destroy();try{return await t}catch(n){return n.bufferedData}}async function Le({stdout:e,stderr:t},{encoding:n},r){let a=ie(e,{encoding:n}),i=ie(t,{encoding:n});try{return await Promise.all([r,a,i])}catch(s){return Promise.all([{error:s,exitCode:null,signal:s.signal,timedOut:s.timedOut||!1},oe(e,a),oe(t,i)])}}function Me(e){let t=typeof e=="string"?`
`:10,n=typeof e=="string"?"\r":13;return e[e.length-1]===t&&(e=e.slice(0,-1)),e[e.length-1]===n&&(e=e.slice(0,-1)),e}function ce(e,t){return e.stripFinalNewline?Me(t):t}function De({timedOut:e,timeout:t,signal:n,exitCode:r}){return e?`timed out after ${t} milliseconds`:n!=null?`was killed with ${n}`:r!=null?`failed with exit code ${r}`:"failed"}function ze({stdout:e,stderr:t,error:n,signal:r,exitCode:a,command:i,timedOut:s,options:f,parentError:o}){let p=`Command ${De({timedOut:s,timeout:f?.timeout,signal:r,exitCode:a})}: ${i}`,y=n?`${p}
${n.message}`:p,$=[y,t,e].filter(Boolean).join(`
`);return n?n.originalMessage=n.message:n=o,n.message=$,n.shortMessage=y,n.command=i,n.exitCode=a,n.signal=r,n.stdout=e,n.stderr=t,"bufferedData"in n&&delete n.bufferedData,n}function Ne({stdout:e,stderr:t,error:n,exitCode:r,signal:a,timedOut:i,command:s,options:f,parentError:o}){if(n||r!==0||a!==null)throw ze({error:n,exitCode:r,signal:a,stdout:e,stderr:t,command:s,timedOut:i,options:f,parentError:o});return e}async function b(e,t,n){if(process.platform!=="darwin")throw new Error("AppleScript is only supported on macOS");let{humanReadableOutput:r,language:a,timeout:i,...s}=Array.isArray(t)?n||{}:t||{},f=r!==!1?[]:["-ss"];a==="JavaScript"&&f.push("-l","JavaScript"),Array.isArray(t)&&f.push("-",...t);let o=le.default.spawn("osascript",f,{...s,env:{PATH:"/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"}}),h=Oe(o,{timeout:i??1e4});o.stdin.end(e);let[{error:p,exitCode:y,signal:$,timedOut:z},O,m]=await Le(o,{encoding:"utf8"},h),W=ce({stripFinalNewline:!0},O),L=ce({stripFinalNewline:!0},m);return Ne({stdout:W,stderr:L,error:p,exitCode:y,signal:$,timedOut:z,command:"osascript",options:n,parentError:new Error})}var D=require("@raycast/api"),U=P(require("fs")),X=(0,D.getPreferenceValues)(),M=X.sshConfig==="localStorage"?"localStorage":X.sshConfigFile||X.sshConfig.replace("~",process.env.HOME||"");function Ve(e){let n=U.readFileSync(e,"utf8").split(`
`),r=[],a=null;for(let i of n){let s=i.trim();if(!(s.startsWith("#")||s==="")){if(s.startsWith("Host ")&&s!=="Host *")a!==null&&r.push(a),a={id:r.length.toString(),address:"",name:s.substring(5),user:""};else if(a!==null){let f=s.indexOf(" "),o=s.substring(0,f),h=s.substring(f+1);switch(o){case"HostName":a.address=h;break;case"User":a.user=h;break;case"Port":a.port=h;break;case"IdentityFile":a.sshKey=h;break;case"HostNameKey":break;case"RemoteCommand":a.command=h;break;default:break}}}}return a!==null&&r.push(a),r}function je(e,t){let n="";for(let r of t)n+=`Host ${r.name}
`,n+=`  HostName ${r.address}
`,r.user&&(n+=`  User ${r.user}
`),r.port&&(n+=`  Port ${r.port}
`),r.sshKey&&(n+=`  IdentityFile ${r.sshKey}
`),r.command&&(n+=`  RemoteCommand ${r.command}
`),n+=`
`;U.writeFileSync(e,n.trimEnd())}async function Q(){switch(M){case"localStorage":{let{connections:e}=await D.LocalStorage.allItems();return e?JSON.parse(e):[]}default:return U.existsSync(M)?Ve(M):[]}}async function pe(e){switch(M){case"localStorage":await D.LocalStorage.setItem("connections",JSON.stringify(e));break;default:je(M,e);break}}var w=require("react/jsx-runtime"),ee=(0,l.getPreferenceValues)(),C=ee.terminal,v=ee.openin,te=ee.onlyname;async function Fe(e){let t;if(te)t=["ssh",e.name].join(" ");else{let o="";e.sshKey&&(o=`-i ${e.sshKey} `);let h="";e.port&&(h=`-p ${e.port} `);let p="",y="";e.command&&(p=`\\"${e.command}\\" `,y="-t");let $=e.address;e.user&&($=`${encodeURIComponent(e.user)}@${$}`),t=["ssh",y,o,$,h,p].filter(Boolean).join(" ")}let n=`
      -- For the latest version:
      -- https://github.com/DavidMChan/custom-alfred-warp-scripts

      -- Set this property to true to always open in a new window
      property open_in_new_window : ${v=="newWindow"}

      -- Set this property to true to always open in a new tab
      property open_in_new_tab : ${v=="newTab"}

      -- Don't change this :)
      property opened_new_window : false

      -- Handlers
      on new_window()
          tell application "System Events" to tell process "Warp"
              click menu item "New Window" of menu "File" of menu bar 1
              set frontmost to true
          end tell
          delay 0.5
      end new_window

      on new_tab()
          tell application "System Events" to tell process "Warp"
              click menu item "New Tab" of menu "File" of menu bar 1
              set frontmost to true
          end tell
      end new_tab

      on call_forward()
          tell application "Warp" to activate
      end call_forward

      on is_running()
          application "Warp" is running
      end is_running

      on has_windows()
          if not is_running() then return false
          tell application "System Events"
              if windows of process "Warp" is {} then return false
          end tell
          true
      end has_windows

      on send_text(custom_text)
          tell application "System Events"
              keystroke custom_text
          end tell
      end send_text


      -- Main
      if not is_running() then
          call_forward()
          set opened_new_window to true
      else
          call_forward()
          set opened_new_window to false
      end if

      if has_windows() then
          if open_in_new_window and not opened_new_window then
              new_window()
          else if open_in_new_tab and not opened_new_window then
              new_tab()
          end if
      else
          new_window()
      end if


      -- Make sure a window exists before we continue, or the write may fail
      repeat until has_windows()
          delay 0.5
      end repeat
      delay 0.5

      send_text("${t}")
      call_forward()
  `,r=`
    tell application "Terminal"
      do script ""
      activate
      set position of front window to {1, 1}
      set shell to do script "${t}" in window 1
    end tell

    tell application "System Events" to tell process "Terminal"
        set frontmost to true
        windows where title contains "bash"
        if result is not {} then perform action "AXRaise" of item 1 of result
    end tell
  `,a=`
    -- Set this property to true to open in a new window instead of a new tab
      property open_in_new_window : ${v=="newWindow"}

    on new_window()
    	tell application "iTerm" to create window with default profile
    end new_window

    on new_tab()
    	tell application "iTerm" to tell the first window to create tab with default profile
    end new_tab

    on call_forward()
    	tell application "iTerm" to activate
    end call_forward

    on is_running()
    	application "iTerm" is running
    end is_running

    on is_processing()
    	tell application "iTerm" to tell the first window to tell current session to get is processing
    end is_processing

    on has_windows()
    	if not is_running() then return false
    	if windows of application "iTerm" is {} then return false
    	true
    end has_windows

    on send_text(custom_text)
    	tell application "iTerm" to tell the first window to tell current session to write text custom_text
    end send_text

    -- Main
    if has_windows() then
      if open_in_new_window then
        new_window()
      else
        new_tab()
      end if
    else
    	-- If iTerm is not running and we tell it to create a new window, we get two
    	-- One from opening the application, and the other from the command
    	if is_running() then
    		new_window()
    	else
    		call_forward()
    	end if
    end if

    -- Make sure a window exists before we continue, or the write may fail
    repeat until has_windows()
    	delay 0.01
    end repeat

    send_text("${t}")
    call_forward()
  `,i=`
  -- Set this property to true to always open in a new window
  property open_in_new_window : ${v=="newWindow"}

  -- Set this property to true to always open in a new tab
  property open_in_new_tab : ${v=="newTab"}

  -- Don't change this :)
  property opened_new_window : false

  -- Handlers
  on new_window()
      tell application "Alacritty"
          activate
          delay 0.5
          tell application "System Events" to tell process "Alacritty"
              keystroke "n" using {command down}
          end tell
      end tell
      delay 0.5
  end new_window

  on new_tab()
      tell application "Alacritty"
          activate
          tell application "System Events" to tell process "Alacritty"
              keystroke "t" using {command down}
          end tell
      end tell
      delay 0.5
  end new_tab

  on call_forward()
      tell application "Alacritty" to activate
      tell application "Alacritty" to reopen
  end call_forward

  on is_running()
      application "Alacritty" is running
  end is_running

  on has_windows()
      if not is_running() then return false
      tell application "System Events"
          if windows of process "Alacritty" is {} then return false
      end tell
      true
  end has_windows

  on send_text(custom_text)
      tell application "System Events" to tell process "Alacritty"
          keystroke custom_text
      end tell
  end send_text


  -- Main
  if not is_running() then
      call_forward()
      set opened_new_window to true
  else
      call_forward()
      set opened_new_window to false
  end if

  if not has_windows() then
    tell application "Alacritty" to reopen
    delay 0.2
    tell application "Alacritty" to activate
  end if

  if open_in_new_window and not opened_new_window then
      new_window()
  else if open_in_new_tab and not opened_new_window then
      new_tab()
  end if


  -- Make sure a window exists before we continue, or the write may fail
  repeat until has_windows()
      delay 0.5
  end repeat
  delay 0.5
  send_text("${t}
") -- Enter at the end of string
  call_forward()
  `,s=`
  -- Set this property to true to open in a new window instead of a new tab
  property open_in_new_window : ${v=="newWindow"}

  on new_window()
      tell application "System Events" 
          launch application "Hyper"
      end tell
  end new_window

  on new_tab()
      tell application "System Events"
          -- Check if Hyper is already running
          set isRunning to (exists process "Hyper")

          if isRunning then
              -- If Hyper is running, bring it to the front and open a new tab
              tell application "Hyper" to activate
              tell application "System Events" to keystroke "t" using command down
          else
              -- If Hyper isn't running, launch it
              launch application "Hyper"
          end if
      end tell
  end new_tab

  on call_forward()
      tell application "Hyper" to activate
  end call_forward

  on is_running()
      application "Hyper" is running
  end is_running

  -- Hyper doesn't have a direct equivalent to 'is processing', so we'll assume it's ready if it's running
  on is_processing()
      is_running()
  end is_processing

  on has_windows()
      if not is_running() then return false
      -- Hyper always has at least one window, so we'll just check if it's running
      true
  end has_windows

  on send_text(custom_text)
      tell application "System Events"
          keystroke custom_text & return
      end tell
  end send_text

  -- Main
  if has_windows() then
      if open_in_new_window then
          new_window()
      else
          new_tab()
      end if
  else
      -- If Hyper is not running and we tell it to create a new window, we get two
      -- One from opening the application, and the other from the command
      if is_running() then
          new_window()
      else
          call_forward()
      end if
  end if 


  -- Give Hyper some time to load 
  repeat until has_windows()
      delay 0.5
  end repeat
  delay 0.5

  send_text("${t}")
  call_forward()
  `,f=`
  -- Set this property to true to open in a new window instead of a new tab
  property open_in_new_window : ${v=="newWindow"}

  on new_window()
      tell application "Ghostty"
          activate
          tell application "System Events" to tell process "Ghostty"
              keystroke "n" using {command down}
          end tell
      end tell
      delay 0.5
  end new_window

  on new_tab()
      tell application "Ghostty"
          activate
          tell application "System Events" to tell process "Ghostty"
              keystroke "t" using {command down}
          end tell
      end tell
      delay 0.5
  end new_tab

  on call_forward()
      tell application "Ghostty" to activate
  end call_forward

  on is_running()
      application "Ghostty" is running
  end is_running

  on has_windows()
      if not is_running() then return false
      tell application "System Events"
          if windows of process "Ghostty" is {} then return false
      end tell
      true
  end has_windows

  on send_text(custom_text)
      tell application "System Events" to tell process "Ghostty"
          keystroke custom_text & return
      end tell
  end send_text

  -- Main
  if has_windows() then
      if open_in_new_window then
          new_window()
      else
          new_tab()
      end if
  else
      if is_running() then
          new_window()
      else
          call_forward()
      end if
  end if

  -- Give Ghostty some time to load
  repeat until has_windows()
      delay 0.5
  end repeat
  delay 0.5

  send_text("${t}")
  call_forward()
  `;if(C=="iTerm")try{await b(a)}catch(o){await b(r),console.log(o)}else if(C=="Warp")try{await b(n)}catch(o){await b(r),console.log(o)}else if(C=="Alacritty")try{await(0,l.closeMainWindow)(),await b(i)}catch(o){await b(r),console.log(o)}else if(C=="Hyper")try{await b(s)}catch(o){await b(r),console.log(o)}else if(C=="Ghostty")try{await b(f)}catch(o){await b(r),console.log(o)}else await b(r);await(0,l.showHUD)(`\u2705 Connection [${e.name}] opened with [${C}].`)}function He(e){if(te)return e.name;let t=[];e.sshKey&&t.push(`-i ${e.sshKey}`),e.port&&t.push(`-p ${e.port}`),e.command&&t.push(`"${e.command}"`);let n=e.user?`${e.user}@${e.address}`:e.address;return t.unshift("ssh",n),t.filter(Boolean).join(" ")}function me(){let{isLoading:e,data:t=[],revalidate:n}=he(Q);async function r(a){if(await(0,l.confirmAlert)({title:"Remove Connection",message:`Are you sure you want to remove connection [${a.name}]?`,primaryAction:{title:"Remove",style:l.Alert.ActionStyle.Destructive},dismissAction:{title:"Cancel"}})){let s=await Q();s=s.filter(f=>f.id!==a.id),await pe(s),n(),await(0,l.showHUD)(`\u{1F5D1} Connection [${a.name}] removed!`)}}return(0,w.jsx)(l.List,{isLoading:e,children:t.map(a=>(0,w.jsx)(l.List.Item,{actions:(0,w.jsx)(Ge,{item:a,onItemRemove:r}),id:a.id,title:a.name,subtitle:Be(a)},a.name))})}function Ge({item:e,onItemRemove:t}){let n=He(e);return(0,w.jsxs)(l.ActionPanel,{children:[(0,w.jsxs)(l.ActionPanel.Section,{title:"Operations",children:[(0,w.jsx)(l.Action,{icon:l.Icon.Terminal,title:"Open Connection",onAction:()=>Fe(e)}),(0,w.jsx)(l.Action.CopyToClipboard,{title:"Copy Connection String",content:n,shortcut:{modifiers:["cmd"],key:"c"}}),(0,w.jsx)(l.Action.Paste,{icon:l.Icon.Text,title:"Paste Connection String",content:n,shortcut:{modifiers:["cmd"],key:"v"},onPaste:()=>(0,l.showHUD)(`\u{1F4DD} Pasting conn. [${e.name}] to active app`)})]}),(0,w.jsx)(l.ActionPanel.Section,{title:"Danger zone",children:(0,w.jsx)(l.Action,{title:"Remove Connection",icon:l.Icon.Trash,style:l.Action.Style.Destructive,onAction:()=>t(e),shortcut:{modifiers:["ctrl"],key:"x"}})})]})}function Be(e){return`${e.user?e.user+"@":""}${e.address}${e.port?" Port: "+e.port:""}${e.sshKey?" SSH Key: "+e.sshKey:""} ${e.command?' Command: "'+e.command+'"':""}`}0&&(module.exports={onlyName,openIn,terminal});
