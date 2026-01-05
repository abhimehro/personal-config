"use strict";var Je=Object.create;var V=Object.defineProperty;var Ze=Object.getOwnPropertyDescriptor;var qe=Object.getOwnPropertyNames;var Ye=Object.getPrototypeOf,Qe=Object.prototype.hasOwnProperty;var Xe=(e,t)=>{for(var r in t)V(e,r,{get:t[r],enumerable:!0})},fe=(e,t,r,a)=>{if(t&&typeof t=="object"||typeof t=="function")for(let n of qe(t))!Qe.call(e,n)&&n!==r&&V(e,n,{get:()=>t[n],enumerable:!(a=Ze(t,n))||a.enumerable});return e};var L=(e,t,r)=>(r=e!=null?Je(Ye(e)):{},fe(t||!e||!e.__esModule?V(r,"default",{value:e,enumerable:!0}):r,e)),et=e=>fe(V({},"__esModule",{value:!0}),e);var St={};Xe(St,{default:()=>We});module.exports=et(St);var Y=require("@raycast/api"),Fe=require("react");var at=require("@raycast/api");var pe=L(require("fs"));var ee=L(require("path"));var tt=require("@raycast/api"),rt=()=>{if(!process.env.HOME)throw new Error("$HOME environment variable is not set.");return ee.default.join(process.env.HOME,"Library")};var de=()=>ee.default.join(rt(),...he);var nt=()=>{try{let e=de(),t=pe.default.readFileSync(e,"utf-8"),r=JSON.parse(t).profile.info_cache;return r?Object.keys(r)[0]:"Default"}catch{return"Default"}};var he=["Application Support","Google","Chrome","Local State"],z=nt(),te="CHROME_PROFILE_KEY";var me=`
  # \u{1F6A8}Error: Google Chrome browser is not installed
  ## This extension depends on Google Chrome browser. You must install it to continue.

  If you have [Homebrew](https://brew.sh/) installed then press \u23CE (Enter Key) to install Google Chrome browser.

  [Click here](https://www.google.com/chrome/) if you want to download manually.

  [![Google Chrome](https://www.google.com/chrome/static/images/chrome-logo-m100.svg)]()
`;var ge=`
# \u{1F6A8}Error: Something happened while trying to run your command

[![Google Chrome](https://www.google.com/chrome/static/images/chrome-logo-m100.svg)]()
`,j="An Error Occurred",B="Google Chrome not installed";var ot=require("react/jsx-runtime");var ye=require("react"),m=require("@raycast/api"),re=require("child_process");var we=require("os"),$e=require("path"),G=require("react/jsx-runtime"),st=(()=>{try{return(0,re.execSync)("brew --prefix",{encoding:"utf8"}).trim()}catch{return(0,we.cpus)()[0].model.includes("Apple")?"/opt/homebrew":"/usr/local"}})();function be(){return(0,$e.join)(st,"bin/brew")}function it(e){try{return(0,re.execSync)(`${be()} install --cask ${e}`,{maxBuffer:10*1024*1024})}catch(t){let r=t;throw r&&r.code===127?(r.stderr=`Brew executable not found at ${be()}`,r):t}}function ke(){let[e,t]=(0,ye.useState)(!0);return(0,G.jsx)(m.Detail,{actions:(0,G.jsx)(m.ActionPanel,{children:e&&(0,G.jsx)(m.Action,{title:"Install with Homebrew",onAction:async()=>{if(!e)return;let r=new m.Toast({style:m.Toast.Style.Animated,title:"Installing..."});await r.show();try{it("google-chrome"),await r.hide()}catch{await r.hide(),await(0,m.showToast)(m.Toast.Style.Failure,j,"An unknown error occurred while trying to install")}r.title="Installed! Please go back and try again.",r.style=m.Toast.Style.Success,await r.show(),t(!1)}})}),markdown:me})}var N=require("@raycast/api");var ve=require("react/jsx-runtime");function xe(){return(0,N.showToast)(N.Toast.Style.Failure,j,"Something happened while trying to run your command"),(0,ve.jsx)(N.Detail,{markdown:ge})}var s=require("@raycast/api");var Ee=L(require("node:process"),1),Se=require("node:util"),ne=require("node:child_process"),ct=(0,Se.promisify)(ne.execFile);async function S(e,{humanReadableOutput:t=!0,signal:r}={}){if(Ee.default.platform!=="darwin")throw new Error("macOS only");let a=t?[]:["-ss"],n={};r&&(n.signal=r);let{stdout:i}=await ct("osascript",["-e",e,a],n);return i.trim()}var A=require("@raycast/api");var u=L(require("react")),c=require("@raycast/api");var Te=Object.prototype.hasOwnProperty;function H(e,t){var r,a;if(e===t)return!0;if(e&&t&&(r=e.constructor)===t.constructor){if(r===Date)return e.getTime()===t.getTime();if(r===RegExp)return e.toString()===t.toString();if(r===Array){if((a=e.length)===t.length)for(;a--&&H(e[a],t[a]););return a===-1}if(!r||typeof e=="object"){a=0;for(r in e)if(Te.call(e,r)&&++a&&!Te.call(t,r)||!(r in t)||!H(e[r],t[r]))return!1;return Object.keys(t).length===a}}return e!==e&&t!==t}var I=L(require("node:fs")),K=L(require("node:path"));var _e=require("react/jsx-runtime");var Re=require("node:url");function lt(e){let t=(0,u.useRef)(e),r=(0,u.useRef)(0);return H(e,t.current)||(t.current=e,r.current+=1),(0,u.useMemo)(()=>t.current,[r.current])}function y(e){let t=(0,u.useRef)(e);return t.current=e,t}function ut(e,t){let r=e instanceof Error?e.message:String(e);return(0,c.showToast)({style:c.Toast.Style.Failure,title:t?.title??"Something went wrong",message:t?.message??r,primaryAction:t?.primaryAction??Ae(e),secondaryAction:t?.primaryAction?Ae(e):void 0})}var Ae=e=>{let t=!0,r="[Extension Name]...",a="";try{let o=JSON.parse((0,I.readFileSync)((0,K.join)(c.environment.assetsPath,"..","package.json"),"utf8"));r=`[${o.title}]...`,a=`https://raycast.com/${o.owner||o.author}/${o.name}`,(!o.owner||o.access==="public")&&(t=!1)}catch{}let n=c.environment.isDevelopment||t,i=e instanceof Error?e?.stack||e?.message||"":String(e);return{title:n?"Copy Logs":"Report Error",onAction(o){o.hide(),n?c.Clipboard.copy(i):(0,c.open)(`https://github.com/raycast/extensions/issues/new?&labels=extension%2Cbug&template=extension_bug_report.yml&title=${encodeURIComponent(r)}&extension-url=${encodeURI(a)}&description=${encodeURIComponent(`#### Error:
\`\`\`
${i}
\`\`\`
`)}`)}}};function Ce(e,t,r){let a=(0,u.useRef)(0),[n,i]=(0,u.useState)({isLoading:!0}),o=y(e),d=y(r?.abortable),w=y(t||[]),$=y(r?.onError),k=y(r?.onData),h=y(r?.onWillExecute),b=y(r?.failureToastOptions),x=y(n.data),P=(0,u.useRef)(null),g=(0,u.useRef)({page:0}),Q=(0,u.useRef)(!1),X=(0,u.useRef)(!0),ue=(0,u.useRef)(50),_=(0,u.useCallback)(()=>(d.current&&(d.current.current?.abort(),d.current.current=new AbortController),++a.current),[d]),R=(0,u.useCallback)((...E)=>{let p=_();h.current?.(E),i(l=>({...l,isLoading:!0}));let O=ft(o.current)(...E);function U(l){return l.name=="AbortError"||p===a.current&&($.current?$.current(l):c.environment.launchType!==c.LaunchType.Background&&ut(l,{title:"Failed to fetch latest data",primaryAction:{title:"Retry",onAction(C){C.hide(),P.current?.(...w.current||[])}},...b.current}),i({error:l,isLoading:!1})),l}return typeof O=="function"?(Q.current=!0,O(g.current).then(({data:l,hasMore:C,cursor:He})=>(p===a.current&&(g.current&&(g.current.cursor=He,g.current.lastItem=l?.[l.length-1]),k.current&&k.current(l,g.current),C&&(ue.current=l.length),X.current=C,i(Ke=>g.current.page===0?{data:l,isLoading:!1}:{data:(Ke.data||[])?.concat(l),isLoading:!1})),l),l=>(X.current=!1,U(l)))):(Q.current=!1,O.then(l=>(p===a.current&&(k.current&&k.current(l),i({data:l,isLoading:!1})),l),U))},[k,$,w,o,i,P,h,g,b,_]);P.current=R;let W=(0,u.useCallback)(()=>{g.current={page:0};let E=w.current||[];return R(...E)},[R,w]),Ve=(0,u.useCallback)(async(E,p)=>{let O;try{if(p?.optimisticUpdate){_(),typeof p?.rollbackOnError!="function"&&p?.rollbackOnError!==!1&&(O=structuredClone(x.current?.value));let U=p.optimisticUpdate;i(l=>({...l,data:U(l.data)}))}return await E}catch(U){if(typeof p?.rollbackOnError=="function"){let l=p.rollbackOnError;i(C=>({...C,data:l(C.data)}))}else p?.optimisticUpdate&&p?.rollbackOnError!==!1&&i(l=>({...l,data:O}));throw U}finally{p?.shouldRevalidateAfter!==!1&&(c.environment.launchType===c.LaunchType.Background||c.environment.commandMode==="menu-bar"?await W():W())}},[W,x,i,_]),ze=(0,u.useCallback)(()=>{g.current.page+=1;let E=w.current||[];R(...E)},[g,w,R]);(0,u.useEffect)(()=>{g.current={page:0},r?.execute!==!1?R(...t||[]):_()},[lt([t,r?.execute,R]),d,g]),(0,u.useEffect)(()=>()=>{_()},[_]);let je=r?.execute!==!1?n.isLoading:!1,Be={...n,isLoading:je},Ge=Q.current?{pageSize:ue.current,hasMore:X.current,onLoadMore:ze}:void 0;return{...Be,revalidate:W,mutate:Ve,pagination:Ge}}function ft(e){return e===Promise.all||e===Promise.race||e===Promise.resolve||e===Promise.reject?e.bind(Promise):e}function dt(e,t){let r=this[e];return r instanceof Date?`__raycast_cached_date__${r.toISOString()}`:Buffer.isBuffer(r)?`__raycast_cached_buffer__${r.toString("base64")}`:t}function ht(e,t){return typeof t=="string"&&t.startsWith("__raycast_cached_date__")?new Date(t.replace("__raycast_cached_date__","")):typeof t=="string"&&t.startsWith("__raycast_cached_buffer__")?Buffer.from(t.replace("__raycast_cached_buffer__",""),"base64"):t}var pt=Symbol("cache without namespace"),Pe=new Map;function ae(e,t,r){let a=r?.cacheNamespace||pt,n=Pe.get(a)||Pe.set(a,new c.Cache({namespace:r?.cacheNamespace})).get(a);if(!n)throw new Error("Missing cache");let i=y(e),o=y(t),d=(0,u.useSyncExternalStore)(n.subscribe,()=>{try{return n.get(i.current)}catch(h){console.error("Could not get Cache data:",h);return}}),w=(0,u.useMemo)(()=>{if(typeof d<"u"){if(d==="undefined")return;try{return JSON.parse(d,ht)}catch(h){return console.warn("The cached data is corrupted",h),o.current}}else return o.current},[d,o]),$=y(w),k=(0,u.useCallback)(h=>{let b=typeof h=="function"?h($.current):h;if(typeof b>"u")n.set(i.current,"undefined");else{let x=JSON.stringify(b,dt);n.set(i.current,x)}return b},[n,i,$]);return[w,k]}function J(e,t){try{let r=o=>o.startsWith("http")?o:`https://${o}`,n=(typeof e=="string"?new Re.URL(r(e)):e).hostname;switch(process.env.FAVICON_PROVIDER??"raycast"){case"none":return{source:t?.fallback??c.Icon.Link,mask:t?.mask};case"apple":return{source:t?.fallback??c.Icon.Link,mask:t?.mask};case"duckduckgo":case"duckDuckGo":return{source:`https://icons.duckduckgo.com/ip3/${n}.ico`,fallback:t?.fallback??c.Icon.Link,mask:t?.mask};case"google":return{source:`https://www.google.com/s2/favicons?sz=${t?.size??64}&domain=${n}`,fallback:t?.fallback??c.Icon.Link,mask:t?.mask};case"legacy":case"raycast":default:return{source:`https://api.ray.so/favicon?url=${n}&size=${t?.size??64}`,fallback:t?.fallback??c.Icon.Link,mask:t?.mask}}}catch(r){return console.error(r),c.Icon.Link}}var T=class e{constructor(t,r,a,n,i,o){this.title=t;this.url=r;this.favicon=a;this.windowsId=n;this.tabIndex=i;this.sourceLine=o}static TAB_CONTENTS_SEPARATOR="~~~";static parse(t){let r=t.split(this.TAB_CONTENTS_SEPARATOR);return new e(r[0],r[1],r[2],+r[3],+r[4],t)}key(){return`${this.windowsId}${e.TAB_CONTENTS_SEPARATOR}${this.tabIndex}`}urlWithoutScheme(){try{return this.url.replace(/(^\w+:|^)\/\//,"").replace("www.","")}catch{return this.url}}realFavicon(){try{return new URL(this.favicon||"/favicon.ico",this.url).href}catch{return this.favicon||""}}googleFavicon(){try{return J(this.url)}catch{return{source:""}}}};async function Ie(e){let t=e?`execute t javascript \xAC
        "document.head.querySelector('link[rel~=icon]') ? document.head.querySelector('link[rel~=icon]').href : '';"`:'""';await Z();try{return(await S(`
      set _output to ""
      tell application "Google Chrome"
        repeat with w in windows
          set _w_id to get id of w as inches as string
          set _tab_index to 1
          repeat with t in tabs of w
            set _title to get title of t
            set _url to get URL of t
            set _favicon to ${t}
            set _output to (_output & _title & "${T.TAB_CONTENTS_SEPARATOR}" & _url & "${T.TAB_CONTENTS_SEPARATOR}" & _favicon & "${T.TAB_CONTENTS_SEPARATOR}" & _w_id & "${T.TAB_CONTENTS_SEPARATOR}" & _tab_index & "\\n")
            set _tab_index to _tab_index + 1
          end repeat
        end repeat
      end tell
      return _output
  `)).split(`
`).filter(a=>a.length!==0).map(a=>T.parse(a))}catch(r){return r.message.includes(`Can't get application "Google Chrome"`)&&A.LocalStorage.removeItem("is-installed"),await Z(),[]}}async function D({url:e,query:t,profileCurrent:r,profileOriginal:a,openTabInProfile:n}){setTimeout(()=>{(0,A.popToRoot)({clearSearchBar:!0})},3e3),await Promise.all([(0,A.closeMainWindow)({clearRootSearch:!0}),Z()]);let i="",o=d=>`
    set profile to quoted form of "${d}"
    set link to quoted form of "${e||"about:blank"}"
    do shell script "open -na 'Google Chrome' --args --profile-directory=" & profile & " " & link
  `;switch(n){case"default":i=`
        set winExists to false
        tell application "Google Chrome"
            repeat with win in every window
                if index of win is 1 then
                    set winExists to true
                    exit repeat
                end if
            end repeat

            if not winExists then
                make new window
            else
                activate
            end if

            tell window 1
                set newTab to make new tab `+(e?`with properties {URL:"${e}"}`:t?'with properties {URL:"https://www.google.com/search?q='+t+'"}':"")+`
            end tell
        end tell
        return true

  `;break;case"profile_current":i=o(r);break;case"profile_original":i=o(a);break}return await S(i)}async function Oe(e){await S(`
    tell application "Google Chrome"
      activate
      set _wnd to first window where id is ${e.windowsId}
      set index of _wnd to 1
      set active tab index of _wnd to ${e.tabIndex}
    end tell
    return true
  `)}async function Ue(e){await S(`
    tell application "Google Chrome"
      activate
      set _wnd to first window where id is ${e.windowsId}
      set index of _wnd to 1
      set active tab index of _wnd to ${e.tabIndex}
      close active tab of _wnd
    end tell
    return true
  `)}async function Le(e){await S(`
    tell application "Google Chrome"
      activate
      set _wnd to first window where id is ${e.windowsId}
      set index of _wnd to 1
      set active tab index of _wnd to ${e.tabIndex}
      tell active tab of _wnd to reload
    end tell
    return true
  `)}var Z=async()=>{if(await A.LocalStorage.getItem("is-installed"))return;if(await S(`
set isInstalled to false
try
    do shell script "osascript -e 'exists application \\"Google Chrome\\"'"
    set isInstalled to true
end try

return isInstalled`)==="false")throw new Error(B);A.LocalStorage.setItem("is-installed",!0)};async function oe(e){await Z(),await S(`
    set link to quoted form of "${e}"
    do shell script "open -na 'Google Chrome' --args --guest " & link
  `)}var f=require("react/jsx-runtime"),M=class{static NewTab=gt;static TabList=bt;static TabHistory=yt};function gt({query:e,url:t}){let{openTabInProfile:r}=(0,s.getPreferenceValues)(),[a]=ae(te,z),n="Open Empty Tab";return e?n=`Search "${e}"`:t&&(n=`Open URL "${t}"`),(0,f.jsx)(s.ActionPanel,{title:"New Tab",children:(0,f.jsx)(s.Action,{onAction:()=>D({url:t,query:e,profileCurrent:a,openTabInProfile:r}),title:n})})}function bt({tab:e,onTabClosed:t}){return(0,f.jsxs)(s.ActionPanel,{title:e.title,children:[(0,f.jsx)(wt,{tab:e}),(0,f.jsx)(kt,{tab:e}),(0,f.jsx)(s.Action,{title:"Open in Guest Window",icon:{source:s.Icon.Person},onAction:async()=>{try{await oe(e.url),await(0,s.closeMainWindow)()}catch(r){throw r instanceof Error?new Error(r.message):r}}}),(0,f.jsx)(s.Action.CopyToClipboard,{title:"Copy URL",content:e.url}),(0,f.jsx)(s.Action.CopyToClipboard,{title:"Copy Title",content:e.title,shortcut:{modifiers:["cmd","shift"],key:"enter"}}),(0,f.jsx)($t,{tab:e,onTabClosed:t}),(0,f.jsx)(s.ActionPanel.Section,{children:(0,f.jsx)(s.Action.CreateQuicklink,{quicklink:{link:e.url,name:e.title,application:"Google Chrome"},shortcut:{modifiers:["cmd"],key:"s"}})})]})}function yt({title:e,url:t,profile:r}){let{openTabInProfile:a}=(0,s.getPreferenceValues)(),[n]=ae(te,z);return(0,f.jsxs)(s.ActionPanel,{title:e,children:[(0,f.jsx)(s.Action,{onAction:()=>D({url:t,profileOriginal:r,profileCurrent:n,openTabInProfile:a}),title:"Open"}),(0,f.jsx)(s.Action,{title:"Open in Guest Window",icon:{source:s.Icon.Person},onAction:async()=>{await oe(t),await(0,s.closeMainWindow)()}}),(0,f.jsxs)(s.ActionPanel.Section,{title:"Open in profile",children:[(0,f.jsx)(s.Action,{onAction:()=>D({url:t,profileOriginal:r,profileCurrent:n,openTabInProfile:"profile_current"}),title:"Open in Current Profile"}),(0,f.jsx)(s.Action,{onAction:()=>D({url:t,profileOriginal:r,profileCurrent:n,openTabInProfile:"profile_original"}),title:"Open in Original Profile"})]}),(0,f.jsx)(s.Action.CopyToClipboard,{title:"Copy URL",content:t,shortcut:{modifiers:["cmd"],key:"c"}})]})}function wt(e){async function t(){try{await Oe(e.tab),await(0,s.closeMainWindow)()}catch(r){throw r instanceof Error?new Error("Issue with tab: '"+e.tab.sourceLine+`'
`+r.message):r}}return(0,f.jsx)(s.ActionPanel.Item,{title:"Open Tab",icon:{source:s.Icon.Eye},onAction:t})}function $t(e){async function t(){await Ue(e.tab),await(0,s.closeMainWindow)(),e.onTabClosed?.()}return(0,f.jsx)(s.Action,{title:"Close Tab",icon:{source:s.Icon.XMarkCircle},onAction:t,shortcut:{modifiers:["cmd","shift"],key:"w"}})}function kt(e){async function t(){try{await Le(e.tab),await(0,s.closeMainWindow)()}catch(r){throw r instanceof Error?new Error("Issue with tab: '"+e.tab.sourceLine+`'
`+r.message):r}}return(0,f.jsx)(s.Action,{title:"Reload Tab",icon:{source:s.Icon.ArrowClockwise},onAction:t,shortcut:{modifiers:["cmd","shift"],key:"r"}})}var v=require("@raycast/api");var F=require("react/jsx-runtime"),q=class{static TabList=Et;static TabHistory=vt};function xt(e){let t=["javascript:","data:","about:","chrome:","file:"],r=e.toLowerCase().trim();if(t.some(a=>r.startsWith(a)))return{icon:{source:v.Icon.ExclamationMark,tintColor:v.Color.Orange},isInvalid:!0};try{return new URL(e),{icon:J(e),isInvalid:!1}}catch{return{icon:{source:v.Icon.ExclamationMark,tintColor:v.Color.Orange},isInvalid:!0}}}function vt({profile:e,entry:{url:t,title:r,id:a},type:n}){let{icon:i,isInvalid:o}=xt(t);return(0,F.jsx)(v.List.Item,{id:`${e}-${n}-${a}`,title:r,subtitle:t,icon:i,accessories:o?[{text:"\u26A0\uFE0F Invalid URL - Cannot open",tooltip:"This URL uses an unsupported protocol"}]:void 0,actions:(0,F.jsx)(M.TabHistory,{title:r,url:t,profile:e})})}function Et(e){return(0,F.jsx)(v.List.Item,{title:e.tab.title,subtitle:e.tab.urlWithoutScheme(),keywords:[e.tab.urlWithoutScheme()],actions:(0,F.jsx)(M.TabList,{tab:e.tab,onTabClosed:e.onTabClosed}),icon:e.useOriginalFavicon?e.tab.realFavicon():e.tab.googleFavicon()})}var ie=require("react");var De=require("@raycast/api");function Ne(e){if(!e)return{includeTerms:[],excludeTerms:[]};let t=e.trim().split(/\s+/),r=[],a=[];for(let n of t)n.startsWith("\\-")&&n.length>1?r.push(n.slice(1).toLowerCase()):n.startsWith("-")&&n.length>1?a.push(n.slice(1).toLowerCase()):n.length>0&&n!=="-"&&r.push(n.toLowerCase());return{includeTerms:r,excludeTerms:a}}function se(e,t){let{includeTerms:r,excludeTerms:a}=t,n=r.length===0||r.every(o=>e.includes(o)),i=a.length===0||!a.some(o=>e.includes(o));return n&&i}var ce=require("react/jsx-runtime");function Me(e=""){let{useOriginalFavicon:t}=(0,De.getPreferenceValues)(),[r,a]=(0,ie.useState)(),[n,i]=(0,ie.useState)(!1),{isLoading:o,data:d}=Ce(async($,k)=>{let h=await Ie($),b=Ne(k);return a(void 0),i(h.length===0),b.includeTerms.length===0&&b.excludeTerms.length===0?h:h.filter(x=>{try{let P=`${x.title.toLowerCase()} ${x.urlWithoutScheme().toLowerCase()}`;return se(P,b)}catch{let P=`${x.title.toLowerCase()} ${x.url.toLowerCase()}`;return se(P,b)}})},[t,e],{onError($){$.message===B?a((0,ce.jsx)(ke,{})):a((0,ce.jsx)(xe,{}))}});return{data:n?[]:d||[],isLoading:o,errorView:r}}var le=require("react/jsx-runtime");function We(){let{useOriginalFavicon:e}=(0,Y.getPreferenceValues)(),[t,r]=(0,Fe.useState)(""),{data:a,errorView:n,isLoading:i}=Me(t);return n??(0,le.jsx)(Y.List,{isLoading:i,onSearchTextChange:r,children:a.map(o=>(0,le.jsx)(q.TabList,{tab:o,useOriginalFavicon:e},o.key()))})}
